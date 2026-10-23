"""Central configuration for MemoryNest.

Loads .env if present; every value can be overridden via environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _path(value: str, default: str) -> Path:
    p = Path(os.environ.get(value, default))
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


# --- Ollama ---
OLLAMA_HOST: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b-instruct")

# --- Embeddings ---
EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- Storage ---
def get_db_path() -> Path:
    return _path("DB_PATH", "data/memorynest.db")

def get_chroma_dir() -> Path:
    return _path("CHROMA_DIR", "data/chroma")

def get_upload_dir() -> Path:
    return _path("UPLOAD_DIR", "data/uploads")

def get_audio_dir() -> Path:
    return _path("AUDIO_DIR", "data/audio")

# Backward compatibility - these will be updated when env vars change
DB_PATH: Path = get_db_path()
CHROMA_DIR: Path = get_chroma_dir()
UPLOAD_DIR: Path = get_upload_dir()
AUDIO_DIR: Path = get_audio_dir()


def refresh_paths() -> None:
    """Refresh path variables from environment variables.
    
    Call this after modifying environment variables to update the path constants.
    """
    global DB_PATH, CHROMA_DIR, UPLOAD_DIR, AUDIO_DIR
    DB_PATH = get_db_path()
    CHROMA_DIR = get_chroma_dir()
    UPLOAD_DIR = get_upload_dir()
    AUDIO_DIR = get_audio_dir()


# --- RAG ---
RAG_TOP_K: int = int(os.environ.get("RAG_TOP_K", "5"))
RAG_MIN_SIMILARITY: float = float(os.environ.get("RAG_MIN_SIMILARITY", "0.30"))
CHUNK_SIZE: int = int(os.environ.get("CHUNK_SIZE", "450"))
CHUNK_OVERLAP: int = int(os.environ.get("CHUNK_OVERLAP", "50"))

# --- Document Map (related documents) ---
LINK_MIN_SIMILARITY: float = float(os.environ.get("LINK_MIN_SIMILARITY", "0.45"))
LINK_STORE_MIN_SIMILARITY: float = float(os.environ.get("LINK_STORE_MIN_SIMILARITY", "0.30"))
LINK_MAX_PER_DOC: int = int(os.environ.get("LINK_MAX_PER_DOC", "3"))

# --- Upload ---
MAX_FILE_SIZE_MB: int = int(os.environ.get("MAX_FILE_SIZE_MB", "20"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

# --- Email ---
EMAIL_HOST: str = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT: int = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USERNAME: str = os.environ.get("EMAIL_USERNAME", "")
EMAIL_APP_PASSWORD: str = os.environ.get("EMAIL_APP_PASSWORD", "")
RECIPIENT_EMAIL: str = os.environ.get("RECIPIENT_EMAIL", "")

# --- Auth / JWT (FastAPI) ---
JWT_SECRET: str = os.environ.get("JWT_SECRET", "")  # empty -> generate random at startup
JWT_EXPIRE_MINUTES: int = int(os.environ.get("JWT_EXPIRE_MINUTES", "720"))
CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
COOKIE_SECURE: bool = os.environ.get("COOKIE_SECURE", "false").lower() == "true"

# --- Google OAuth & Calendar ---
GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI: str = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/google/callback")
FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")
TOKEN_ENCRYPTION_KEY: str = os.environ.get("TOKEN_ENCRYPTION_KEY", "")


def ensure_dirs() -> None:
    """Create all runtime directories if they do not exist yet."""
    for d in (get_db_path().parent, get_chroma_dir(), get_upload_dir(), get_audio_dir()):
        d.mkdir(parents=True, exist_ok=True)