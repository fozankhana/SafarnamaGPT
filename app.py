import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="SafarnāmaGPT",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config import cfg           # noqa: E402
from src.rag import RAGPipeline  # noqa: E402

# ── Persistence helpers ────────────────────────────────────────────────────────
HISTORY_DIR = cfg.base_dir / "data" / "chat_history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _conv_path(cid: str) -> Path:
    return HISTORY_DIR / f"{cid}.json"


def save_conversation(cid: str, messages: list, title: str) -> None:
    data = {"id": cid, "title": title, "updated": datetime.now().isoformat(), "messages": messages}
    _conv_path(cid).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_conversation(cid: str) -> dict | None:
    p = _conv_path(cid)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def list_conversations() -> list[dict]:
    convs = []
    for p in sorted(HISTORY_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            convs.append({"id": d["id"], "title": d.get("title", "Untitled"), "updated": d.get("updated", "")})
        except Exception:
            pass
    return convs


def make_title(first_user_msg: str) -> str:
    return first_user_msg[:45] + ("…" if len(first_user_msg) > 45 else "")


# ── Session state bootstrap ────────────────────────────────────────────────────
def _init_state():
    if "conv_id" not in st.session_state:
        st.session_state.conv_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "sources" not in st.session_state:
        st.session_state.sources = []
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None
    if "groq_api_key" not in st.session_state:
        st.session_state.groq_api_key = os.environ.get("GROQ_API_KEY", "")


_init_state()


# ── LLM pipeline ───────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading SafarnāmaGPT… (first load takes ~30 s)")
def load_pipeline() -> RAGPipeline:
    return RAGPipeline()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/32/Flag_of_Pakistan.svg/200px-Flag_of_Pakistan.svg.png",
        width=60,
    )
    st.markdown("## SafarnāmaGPT")
    st.caption("AI Travel Agent for Pakistan — Powered by Groq" if cfg.use_groq else "AI Travel Agent for Pakistan")

    if st.button("＋  New Chat", use_container_width=True, type="primary"):
        st.session_state.conv_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.sources = []
        st.session_state.pending_question = None
        st.rerun()

    st.divider()

    # ── Chat history list ──────────────────────────────────────────────────────
    conversations = list_conversations()
    if conversations:
        st.markdown("**Recent chats**")
        for conv in conversations[:20]:
            is_active = conv["id"] == st.session_state.conv_id
            label = ("▶ " if is_active else "") + conv["title"]
            if st.button(label, key=f"hist_{conv['id']}", use_container_width=True,
                         help=conv["updated"][:16].replace("T", " ")):
                if not is_active:
                    loaded = load_conversation(conv["id"])
                    if loaded:
                        st.session_state.conv_id = conv["id"]
                        st.session_state.messages = loaded["messages"]
                        st.session_state.sources = []
                        st.session_state.pending_question = None
                        st.rerun()
        st.divider()

    # ── API key input (Groq mode) ──────────────────────────────────────────────
    if cfg.use_groq:
        api_key_input = st.text_input(
            "Groq API Key",
            value=st.session_state.groq_api_key,
            type="password",
            placeholder="gsk_...",
            help="Get a free key at console.groq.com",
        )
        if api_key_input != st.session_state.groq_api_key:
            st.session_state.groq_api_key = api_key_input
            cfg.groq_api_key = api_key_input
            from src.llm import LLM
            LLM.reset()  # force re-init with new key on next request
        else:
            cfg.groq_api_key = st.session_state.groq_api_key
        st.divider()

    # ── Model settings ─────────────────────────────────────────────────────────
    st.markdown("**Model Settings**")
    cfg.temperature = st.slider("Temperature", 0.1, 1.0, cfg.temperature, 0.05,
                                help="Higher = more creative, lower = more factual")
    cfg.retrieval_top_k = st.slider("Retrieved chunks (top-k)", 1, 8, cfg.retrieval_top_k,
                                    help="Chunks retrieved per query")
    cfg.max_tokens = st.slider("Max response tokens", 256, 4096, cfg.max_tokens, 128,
                               help="Groq supports up to 4096. Higher = more complete itineraries.")
    st.divider()
    if cfg.use_groq:
        st.caption(f"**Model:** `{cfg.groq_model}` (Groq)")
    else:
        st.caption(f"**Model:** `{cfg.model_filename}` (local)")
    st.caption(f"**Embeddings:** `{cfg.embedding_model}`")

    # ── Retrieved sources (last response) ─────────────────────────────────────
    if st.session_state.sources:
        st.divider()
        st.markdown("**Retrieved Sources**")
        for i, doc in enumerate(st.session_state.sources, 1):
            score_pct = int(doc.get("score", 0) * 100)
            with st.expander(f"{i}. {doc['source_label']} ({score_pct}% match)", expanded=False):
                st.caption(doc["source_url"])
                st.text(doc["text"][:400] + ("..." if len(doc["text"]) > 400 else ""))


# ── Main chat area ─────────────────────────────────────────────────────────────
st.title("🕌 SafarnāmaGPT")
st.caption("Your AI travel agent for Pakistan — tell me your plans and I'll build a personalized itinerary.")
st.divider()

# Render existing chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Welcome + starter prompts (shown only on empty chat)
STARTERS = [
    "I'm planning a 7-day trip to Pakistan. Help me plan!",
    "Plan a 5-day trip to Lahore and Islamabad",
    "I want to trek in Gilgit-Baltistan for 10 days",
    "What are the best places to visit in Hunza Valley?",
    "Plan a cultural tour of historic cities in Pakistan",
    "I have 3 days in Karachi — what should I do?",
]

if not st.session_state.messages:
    st.info(
        "👋 **Welcome!** I'm SafarnāmaGPT, your personal AI travel agent for Pakistan.\n\n"
        "Tell me how many days you're traveling, which cities or regions interest you, "
        "and I'll create a detailed day-by-day itinerary with Google Maps links for every attraction!",
        icon="🗺️",
    )
    st.markdown("**Start planning:**")
    col1, col2 = st.columns(2)
    for i, q in enumerate(STARTERS):
        col = col1 if i % 2 == 0 else col2
        if col.button(q, key=f"starter_{i}", use_container_width=True):
            st.session_state.pending_question = q
            st.rerun()

# Resolve prompt: from chat_input OR from a starter button click
prompt: str | None = st.chat_input("Tell me your travel plans or ask about Pakistan...")
if prompt is None and st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = None

# Process prompt
if prompt:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate and stream assistant response
    with st.chat_message("assistant"):
        pipeline = load_pipeline()
        captured_sources: list[dict] = []

        # Pass all prior messages as history (everything except the current user turn we just added)
        history_for_llm = st.session_state.messages[:-1]

        def token_generator():
            for item in pipeline.stream(prompt, history=history_for_llm):
                if isinstance(item, dict) and item.get("type") == "sources":
                    captured_sources.extend(item["docs"])
                else:
                    yield item

        response_text = st.write_stream(token_generator())

    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.session_state.sources = captured_sources

    # Persist conversation
    title = make_title(st.session_state.messages[0]["content"])
    save_conversation(st.session_state.conv_id, st.session_state.messages, title)

    st.rerun()
