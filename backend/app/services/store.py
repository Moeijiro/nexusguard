"""The engine's ``Store``, backed by the database.

Used by the bot and the demo simulator. Guild context is cached for a few
seconds so a busy channel doesn't cost a query per message; a dashboard edit
reaches the bot within ``CONTEXT_TTL`` seconds.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine.actions import MODERATION_ACTIONS, Status
from app.engine.detectors import EventType
from app.engine.pipeline import Outcome
from app.engine.ports import GuildContext
from app.engine.rules_schema import ActionName
from app.models import Flag, Guild, ModerationLog, SecurityEvent
from app.services import guilds as guild_service

CONTEXT_TTL = 3.0
OFFENCE_TYPES = (EventType.SPAM_DETECTED, EventType.MASS_MENTIONS)
OFFENCE_SEVERITIES = ("medium", "high", "critical")


class SqlStore:
    def __init__(self, session_factory: Callable[[], Session], context_ttl: float = CONTEXT_TTL) -> None:
        self._session_factory = session_factory
        self._ttl = context_ttl
        self._cache: dict[str, tuple[float, GuildContext | None]] = {}

    def invalidate(self, guild_id: str | None = None) -> None:
        if guild_id is None:
            self._cache.clear()
        else:
            self._cache.pop(guild_id, None)

    def _guild(self, db: Session, guild_id: str) -> Guild | None:
        return db.execute(select(Guild).where(Guild.discord_id == guild_id)).scalar_one_or_none()

    def guild_context(self, guild_id: str) -> GuildContext | None:
        cached = self._cache.get(guild_id)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        with self._session_factory() as db:
            guild = self._guild(db, guild_id)
            ctx = guild_service.context_for(guild) if guild is not None and guild.bot_present else None
        self._cache[guild_id] = (time.monotonic() + self._ttl, ctx)
        return ctx

    def recent_offenses(self, guild_id: str, user_id: str, since: datetime) -> int:
        with self._session_factory() as db:
            guild = self._guild(db, guild_id)
            if guild is None:
                return 0
            return db.scalar(
                select(func.count()).select_from(SecurityEvent).where(
                    SecurityEvent.guild_id == guild.id,
                    SecurityEvent.user_id == user_id,
                    SecurityEvent.created_at >= since,
                    SecurityEvent.type.in_(OFFENCE_TYPES),
                    SecurityEvent.severity.in_(OFFENCE_SEVERITIES),
                )
            ) or 0

    def set_raid_mode(self, guild_id: str, enabled: bool, until: datetime | None, reason: str, by: str) -> None:
        with self._session_factory() as db:
            guild = self._guild(db, guild_id)
            if guild is not None:
                guild_service.set_raid_mode(guild, enabled, until, reason, by)
                db.commit()
        self.invalidate(guild_id)

    def record(self, outcome: Outcome) -> int:
        d = outcome.detection
        with self._session_factory() as db:
            guild = self._guild(db, outcome.guild_id)
            if guild is None:
                return 0
            event = SecurityEvent(
                guild_id=guild.id,
                type=d.type,
                module=d.module.value,
                severity=outcome.severity.value,
                summary=d.summary[:200],
                user_id=d.user.id if d.user else None,
                username=d.user.name if d.user else None,
                channel_id=d.channel_id,
                action_taken=outcome.action_summary[:300],
                actions=[r.as_dict() for r in outcome.results],
                notes=outcome.notes,
                details={**d.metadata, **outcome.extra},
                simulated=outcome.simulated,
                created_at=outcome.at,
            )
            db.add(event)
            db.flush()
            for result in outcome.results:
                if d.user is None:
                    break
                if result.name in MODERATION_ACTIONS and result.status in (Status.DONE, Status.SIMULATED, Status.FAILED):
                    db.add(ModerationLog(
                        guild_id=guild.id, action=result.name.value, target_id=d.user.id, target_name=d.user.name,
                        moderator_name="NexusGuard", source="automatic", reason=d.summary[:500],
                        status=result.status.value, event_id=event.id, created_at=outcome.at,
                    ))
                if result.name == ActionName.FLAG and result.status == Status.DONE:
                    db.add(Flag(
                        guild_id=guild.id, user_id=d.user.id, username=d.user.name, reason=d.summary[:200],
                        severity=outcome.severity.value, event_id=event.id, created_at=outcome.at,
                    ))
            db.commit()
            return event.id
