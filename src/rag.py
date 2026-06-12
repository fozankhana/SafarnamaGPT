import pickle
import re
from typing import Generator

import faiss

from config import cfg
from src.embedder import Embedder
from src.llm import LLM
from src.utils import setup_logger

logger = setup_logger(__name__)

# Pakistani place names — used to enrich retrieval query from conversation history
_PAKISTAN_PLACES = re.compile(
    r"\b(lahore|karachi|islamabad|peshawar|quetta|multan|rawalpindi|faisalabad|"
    r"gilgit|baltistan|hunza|skardu|swat|naran|kaghan|murree|taxila|mohenjo.?daro|"
    r"k2|fairy\s+meadows|karakoram|khunjerab|chitral|kalash|bahawalpur|sialkot|"
    r"gwadar|makran|deosai|attabad|rakaposhi|nanga\s+parbat)\b",
    re.IGNORECASE,
)


def _extract_place_context(history: list[dict]) -> str:
    """Pull unique place names from user turns in conversation history."""
    text = " ".join(m["content"] for m in history if m["role"] == "user")
    found = _PAKISTAN_PLACES.findall(text)
    if not found:
        return ""
    unique = list(dict.fromkeys(p.lower() for p in found))
    return " ".join(unique)


class RAGPipeline:
    def __init__(self):
        self.embedder = Embedder.get()
        self.index, self.docstore = self._load_vectorstore()
        self.llm = LLM.get()

    def _load_vectorstore(self):
        if not cfg.faiss_index_path.exists():
            raise FileNotFoundError(
                f"Vector store not found at: {cfg.faiss_index_path}\n"
                "Run: python scripts\\build_index.py"
            )
        logger.info("Loading FAISS index from: %s", cfg.faiss_index_path)
        index = faiss.read_index(str(cfg.faiss_index_path))
        with open(str(cfg.docstore_path), "rb") as f:
            docstore = pickle.load(f)
        logger.info("Loaded %d vectors from index.", index.ntotal)
        return index, docstore

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        k = top_k or cfg.retrieval_top_k
        q_vec = self.embedder.embed_query(query).reshape(1, -1)
        distances, indices = self.index.search(q_vec, k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0:
                doc = self.docstore[int(idx)].copy()
                doc["score"] = float(dist)
                results.append(doc)
        return results

    def _build_context(self, docs: list[dict]) -> str:
        return "\n\n---\n\n".join(d["text"] for d in docs)

    def stream(self, query: str, history: list[dict] | None = None) -> Generator:
        history = history or []

        # Enrich retrieval query with place names mentioned earlier in the conversation
        place_ctx = _extract_place_context(history)
        retrieval_query = f"{query} {place_ctx}".strip() if place_ctx else query

        docs = self.retrieve(retrieval_query)
        context = self._build_context(docs)

        # history here is all prior messages (the current user turn is passed separately as query)
        prompt = self.llm.build_prompt(query, context, history=history)
        logger.info("Streaming response for query: %s", query[:80])
        yield from self.llm.stream(prompt)
        # Sentinel — carries source docs; filtered out in app.py before write_stream
        yield {"type": "sources", "docs": docs}
