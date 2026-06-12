from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).parent


@dataclass
class Config:
    # Paths
    base_dir: Path = field(default_factory=lambda: BASE_DIR)
    raw_data_dir: Path = field(default_factory=lambda: BASE_DIR / "data" / "raw")
    vectorstore_dir: Path = field(default_factory=lambda: BASE_DIR / "data" / "vectorstore")
    models_dir: Path = field(default_factory=lambda: BASE_DIR / "models")

    # Groq API (cloud inference — fast, free tier, no token limit issues)
    use_groq: bool = True
    groq_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str = ""      # set via GROQ_API_KEY env var or sidebar input

    # Local GGUF model (fallback when use_groq=False)
    model_filename: str = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    model_family: str = "llama3"
    n_ctx: int = 2048
    n_threads: int = 8
    n_batch: int = 512
    n_gpu_layers: int = 0
    use_mlock: bool = False
    repeat_penalty: float = 1.1

    # Shared generation settings
    temperature: float = 0.7
    top_k: int = 40
    top_p: float = 0.95
    max_tokens: int = 2048      # Groq handles full itineraries; local fallback uses this too
    history_turns: int = 6      # number of past message pairs to include in prompt

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # RAG
    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 4

    # Scraping
    scrape_delay_seconds: float = 1.5
    request_timeout: int = 15
    user_agent: str = "SafarnamaGPT/1.0 (educational project)"

    @property
    def model_path(self) -> Path:
        return self.models_dir / self.model_filename

    @property
    def faiss_index_path(self) -> Path:
        return self.vectorstore_dir / "index.faiss"

    @property
    def docstore_path(self) -> Path:
        return self.vectorstore_dir / "index.pkl"


cfg = Config()
