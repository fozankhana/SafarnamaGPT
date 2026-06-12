"""FastAPI backend for SafarnamaGPT mobile app."""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import cfg
from src.llm import LLM
from src.rag import RAGPipeline

app = FastAPI(title="SafarnamaGPT API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORY_DIR = cfg.base_dir / "data" / "chat_history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)

_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


# ── Models ────────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    history: list[Message] = []
    groq_api_key: str = ""
    temperature: float = 0.7
    retrieval_top_k: int = 4
    max_tokens: int = 2048


class ConversationSave(BaseModel):
    title: str
    messages: list[Message]


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream chat response as Server-Sent Events."""
    cfg.groq_api_key = req.groq_api_key or os.environ.get("GROQ_API_KEY", "")
    cfg.temperature = req.temperature
    cfg.retrieval_top_k = req.retrieval_top_k
    cfg.max_tokens = req.max_tokens
    LLM.reset()

    history = [{"role": m.role, "content": m.content} for m in req.history]

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            pipeline = get_pipeline()
            for chunk in pipeline.stream(req.message, history):
                if isinstance(chunk, dict) and chunk.get("type") == "sources":
                    payload = json.dumps({"type": "sources", "docs": chunk["docs"]})
                    yield f"data: {payload}\n\n"
                else:
                    payload = json.dumps({"type": "token", "value": chunk})
                    yield f"data: {payload}\n\n"
            yield 'data: {"type":"done"}\n\n'
        except ValueError as exc:
            payload = json.dumps({"type": "error", "message": str(exc)})
            yield f"data: {payload}\n\n"
        except Exception as exc:
            payload = json.dumps({"type": "error", "message": f"Server error: {exc}"})
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Conversations ─────────────────────────────────────────────────────────────

def _conv_path(cid: str) -> Path:
    return HISTORY_DIR / f"{cid}.json"


@app.get("/conversations")
def list_conversations():
    convs = []
    for p in sorted(HISTORY_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            convs.append({"id": d["id"], "title": d.get("title", "Untitled"), "updated": d.get("updated", "")})
        except Exception:
            pass
    return convs[:50]


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    p = _conv_path(conversation_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Conversation not found")
    return json.loads(p.read_text(encoding="utf-8"))


@app.post("/conversations/{conversation_id}")
def save_conversation(conversation_id: str, body: ConversationSave):
    data = {
        "id": conversation_id,
        "title": body.title,
        "updated": datetime.now().isoformat(),
        "messages": [m.model_dump() for m in body.messages],
    }
    _conv_path(conversation_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True}


@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    p = _conv_path(conversation_id)
    if p.exists():
        p.unlink()
    return {"ok": True}
