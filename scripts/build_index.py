"""
Chunks scraped text, embeds with sentence-transformers, and builds a FAISS index.

Usage:
    python scripts/build_index.py
"""

import json
import pickle
import sys
from pathlib import Path

import faiss
import numpy as np
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import cfg
from src.embedder import Embedder
from src.utils import ensure_dirs, setup_logger

logger = setup_logger("indexer")


def chunk_text(text: str, chunk_size: int, overlap: int, metadata: dict) -> list[dict]:
    """Sliding-window character chunker that breaks on sentence/paragraph boundaries."""
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # Try to break on paragraph boundary first
        if end < text_len:
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + overlap:
                end = para_break
            else:
                # Try sentence boundary (. or ? or !)
                for punct in [".", "?", "!"]:
                    sent_break = text.rfind(punct, start, end)
                    if sent_break > start + overlap:
                        end = sent_break + 1
                        break

        chunk_text_val = text[start:end].strip()
        if len(chunk_text_val) >= 80:  # skip tiny fragments
            chunks.append({
                "text": chunk_text_val,
                "source_url": metadata.get("url", ""),
                "source_label": metadata.get("label", ""),
                "char_offset": start,
            })

        # Advance with overlap
        next_start = end - overlap
        if next_start <= start:
            next_start = start + max(chunk_size // 2, 1)
        start = next_start

    return chunks


def build_index():
    ensure_dirs(cfg.vectorstore_dir)

    manifest_path = cfg.raw_data_dir / "sources_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Manifest not found at {manifest_path}. "
            "Run: python scripts\\scrape_data.py"
        )

    with open(str(manifest_path), encoding="utf-8") as f:
        manifest = json.load(f)

    logger.info("Loading %d source files...", len(manifest))

    all_chunks: list[dict] = []
    for slug, meta in manifest.items():
        txt_path = cfg.raw_data_dir / f"{slug}.txt"
        if not txt_path.exists():
            logger.warning("Missing file: %s — skipping", txt_path)
            continue
        text = txt_path.read_text(encoding="utf-8")
        file_chunks = chunk_text(text, cfg.chunk_size, cfg.chunk_overlap, meta)
        all_chunks.extend(file_chunks)
        logger.info("  %s → %d chunks", slug, len(file_chunks))

    if not all_chunks:
        raise RuntimeError("No chunks produced — check data/raw/ has .txt files.")

    logger.info("Total chunks: %d", len(all_chunks))

    # Embed
    embedder = Embedder.get()
    texts = [c["text"] for c in all_chunks]

    logger.info("Encoding %d chunks (this may take a minute)...", len(texts))
    batch_size = 64
    all_vecs = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding"):
        batch = texts[i: i + batch_size]
        vecs = embedder.embed(batch)
        all_vecs.append(vecs)

    embeddings = np.vstack(all_vecs).astype(np.float32)
    logger.info("Embeddings shape: %s", embeddings.shape)

    # Build FAISS index (cosine similarity via inner product on normalized vectors)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    logger.info("FAISS index built: %d vectors, dim=%d", index.ntotal, dim)

    # Persist
    faiss.write_index(index, str(cfg.faiss_index_path))
    with open(str(cfg.docstore_path), "wb") as f:
        pickle.dump(all_chunks, f)

    logger.info("Index saved → %s", cfg.faiss_index_path)
    logger.info("Docstore saved → %s", cfg.docstore_path)
    return index.ntotal


if __name__ == "__main__":
    n = build_index()
    print(f"\nIndex built successfully: {n} vectors stored.")
    print(f"  FAISS index : {cfg.faiss_index_path}")
    print(f"  Docstore    : {cfg.docstore_path}")
