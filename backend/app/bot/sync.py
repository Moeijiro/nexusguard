"""Keep the database's picture of each guild current: name, size, channels, roles."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Guild
from app.services import guilds as guild_service

TEXT = 0
ANNOUNCEMENT = 5


def snapshot(guild: Any) -> tuple[list[dict], list[dict]]:
    channels = [
        {"id": str(c.id), "name": c.name, "kind": "announcement" if c.type.value == ANNOUNCEMENT else "text",
         "position": c.position}
        for c in guild.channels
        if getattr(c.type, "value", None) in (TEXT, ANNOUNCEMENT)
    ]
    top = guild.me.top_role.position if guild.me else 0
    roles = [
        {"id": str(r.id), "name": r.name, "color": r.color.value, "position": r.position,
         # Discord only lets a bot assign roles below its own highest role.
         "assignable": not r.managed and not r.is_default() and r.position < top}
        for r in guild.roles
        if not r.is_default()
    ]
    return channels, roles


def sync_guild(guild: Any) -> None:
    channels, roles = snapshot(guild)
    with SessionLocal() as db:
        record = guild_service.ensure_guild(db, str(guild.id), guild.name,
                                            icon=guild.icon.key if guild.icon else None,
                                            member_count=guild.member_count)
        record.channels, record.roles = channels, roles
        db.commit()


def mark_removed(guild_id: int) -> None:
    with SessionLocal() as db:
        record = db.execute(select(Guild).where(Guild.discord_id == str(guild_id))).scalar_one_or_none()
        if record is not None:
            record.bot_present = False
            db.commit()
