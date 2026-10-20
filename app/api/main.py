"""FastAPI application for MemoryNest."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is on sys.path so 'app' imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


def _create_lifespan(db_path: Optional[str] = None):
    """Create a lifespan context manager with optional custom db_path."""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialize DB and directories at startup."""
        from app.database.database import init_db
        from app.utils.config import ensure_dirs
        from app.api.security import get_jwt_secret

        ensure_dirs()
        init_db(db_path) if db_path else init_db()
        get_jwt_secret()  # Initialize JWT secret early (logs warning if unset)
        yield
    return lifespan


def create_app(db_path: Optional[str] = None) -> FastAPI:
    app = FastAPI(
        title="MemoryNest API",
        description="API for MemoryNest — local RAG over your documents.",
        version="0.1.0",
        lifespan=_create_lifespan(db_path),
    )

    # CORS
    from app.utils.config import CORS_ORIGINS
    origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Include routers
    from app.api.routers import auth, documents, health, reminders, chat, summaries, dashboard, search
    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(health.router)
    app.include_router(reminders.router)
    app.include_router(chat.router)
    app.include_router(summaries.router)
    app.include_router(dashboard.router)
    app.include_router(search.router)

    return app


app = create_app()