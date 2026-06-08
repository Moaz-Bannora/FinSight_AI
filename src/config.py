"""Project configuration for Finance Docs Insights."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def load_project_env(override: bool = False) -> None:
    """Load private runtime settings from .env when python-dotenv is installed."""

    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env", override=override)


load_project_env()

DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DOCS_DIR = DATA_DIR / "sample_docs"
UPLOADS_DIR = DATA_DIR / "uploads"
VECTORSTORE_DIR = DATA_DIR / "chroma_db"
EVALUATION_DIR = DATA_DIR / "evaluation"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

DEFAULT_CHAT_MODEL = os.getenv("FIN_DOC_LLM_CHAT_MODEL", "llama3.2:3b")
DEFAULT_EMBED_MODEL = os.getenv("FIN_DOC_LLM_EMBED_MODEL", "nomic-embed-text")
DEFAULT_LLM_PROVIDER = os.getenv("FIN_DOC_LLM_PROVIDER", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

CHUNK_SIZE = int(os.getenv("FIN_DOC_LLM_CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("FIN_DOC_LLM_CHUNK_OVERLAP", "150"))
DEFAULT_TOP_K = int(os.getenv("FIN_DOC_LLM_TOP_K", "4"))

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv"} | IMAGE_EXTENSIONS


def ensure_project_dirs() -> None:
    """Create runtime directories used by the app and scripts."""

    for path in [DATA_DIR, SAMPLE_DOCS_DIR, UPLOADS_DIR, VECTORSTORE_DIR, EVALUATION_DIR, OUTPUTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def get_google_api_key() -> str:
    """Return the Gemini API key from either supported environment variable."""

    load_project_env(override=True)
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""


def gemini_env_status() -> dict[str, bool]:
    """Return non-secret Gemini setup status for UI checks."""

    load_project_env(override=True)
    google_key = bool(os.getenv("GOOGLE_API_KEY", "").strip())
    gemini_key = bool(os.getenv("GEMINI_API_KEY", "").strip())
    return {
        "env_file_exists": (PROJECT_ROOT / ".env").exists(),
        "google_api_key_set": google_key,
        "gemini_api_key_set": gemini_key,
        "any_key_set": google_key or gemini_key,
        "both_keys_set": google_key and gemini_key,
    }

