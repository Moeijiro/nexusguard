"""Liveness."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", summary="Liveness and mode")
def health() -> dict[str, object]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # noqa: BLE001
        database = "unavailable"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "discord_configured": settings.discord_configured,
        "demo": settings.demo_enabled,
    }
