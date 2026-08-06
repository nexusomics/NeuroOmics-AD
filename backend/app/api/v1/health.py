"""Health & system status endpoints."""
from __future__ import annotations

import platform
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from app import __version__
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.redis import get_redis

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/info")
def info() -> dict:
    db_status = "ok"
    try:
        with engine.connect():
            pass
    except Exception:  # noqa: BLE001
        db_status = "degraded"
    redis = get_redis()
    return {
        "app": settings.APP_NAME,
        "version": __version__,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "redis": "ok" if redis else "in-memory-fallback",
        "python": platform.python_version(),
        "api_prefix": settings.API_V1_PREFIX,
    }
