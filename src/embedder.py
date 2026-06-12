import os
import numpy as np
from sentence_transformers import SentenceTransformer

from config import cfg
from src.utils import setup_logger

# Disable HF symlink warning (Windows doesn't support symlinks by default)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
# Store embedding model locally inside project to avoid permission issues
_LOCAL_CACHE = str(cfg.base_dir / ".model_cache")
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", _LOCAL_CACHE)

logger = setup_logger(__name__)


class Embedder:
    _instance = None

    @classmethod
    def get(cls) -> "Embedder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        logger.info("Loading embedding model: %s", cfg.embedding_model)
        self.model = SentenceTransformer(cfg.embedding_model)
        logger.info("Embedding model loaded.")

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=64,
        )
        return vecs.astype(np.float32)

    def embed_batch(self, texts: list[str], show_progress: bool = False) -> np.ndarray:
        vecs = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
            batch_size=64,
        )
        return vecs.astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed([text])[0]
