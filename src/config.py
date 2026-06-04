"""Project configuration for Finance Docs Insights."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass

DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DOCS_DIR = DATA_DIR / "sample_docs"
EXTERNAL_DOCS_DIR = DATA_DIR / "external_financial_docs"
UPLOADS_DIR = DATA_DIR / "uploads"
VECTORSTORE_DIR = DATA_DIR / "chroma_db"
EVALUATION_DIR = DATA_DIR / "evaluation"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

DEFAULT_CHAT_MODEL = os.getenv("FIN_DOC_LLM_CHAT_MODEL", "llama3.2:3b")
DEFAULT_EMBED_MODEL = os.getenv("FIN_DOC_LLM_EMBED_MODEL", "nomic-embed-text")
DEFAULT_LLM_PROVIDER = os.getenv("FIN_DOC_LLM_PROVIDER", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

CHUNK_SIZE = int(os.getenv("FIN_DOC_LLM_CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("FIN_DOC_LLM_CHUNK_OVERLAP", "150"))
DEFAULT_TOP_K = int(os.getenv("FIN_DOC_LLM_TOP_K", "4"))

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"} | IMAGE_EXTENSIONS


def ensure_project_dirs() -> None:
    """Create runtime directories used by the app and scripts."""

    for path in [DATA_DIR, SAMPLE_DOCS_DIR, EXTERNAL_DOCS_DIR, UPLOADS_DIR, VECTORSTORE_DIR, EVALUATION_DIR, OUTPUTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def offline_demo_enabled() -> bool:
    """Return true when the deterministic local demo mode is requested."""

    return os.getenv("FIN_DOC_LLM_OFFLINE_DEMO", "0").strip().lower() in {"1", "true", "yes", "on"}

