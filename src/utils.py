import logging
import re
import unicodedata
from pathlib import Path


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def clean_text(text: str) -> str:
    # Normalize unicode (e.g. fancy quotes, zero-width chars)
    text = unicodedata.normalize("NFKC", text)
    # Remove non-printable characters except newlines/tabs
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E-￿]", "", text)
    # Collapse multiple spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Drop lines shorter than 40 chars (stubs, nav fragments)
    lines = [ln for ln in text.splitlines() if len(ln.strip()) >= 40]
    return "\n".join(lines).strip()


def slugify(url: str) -> str:
    slug = re.sub(r"https?://", "", url)
    slug = re.sub(r"[^\w]", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:80]
