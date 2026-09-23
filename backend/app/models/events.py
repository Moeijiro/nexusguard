"""What happened: security events, moderation actions, and the review queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utcnow


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (Index("ix_events_guild_time", "guild_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(32), index=True)
    module: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(16), index=True)
    summary: Mapped[str] = mapped_column(String(200))
    user_id: Mapped[str | None] = mapped_column(String(32), default=None, index=True)
    username: Mapped[str | None] = mapped_column(String(100), default=None)
    channel_id: Mapped[str | None] = mapped_column(String(32), default=None)
    action_taken: Mapped[str] = mapped_column(String(300), default="Logged")
    actions: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    notes: Mapped[list[str]] = mapped_column(JSON, default=list)
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class ModerationLog(Base):
    """Moderation performed *through NexusGuard*: automatically, from the dashboard, or by slash command."""

    __tablename__ = "moderation_logs"
    __table_args__ = (Index("ix_modlog_guild_time", "guild_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[str] = mapped_column(String(32))
    target_name: Mapped[str | None] = mapped_column(String(100), default=None)
    moderator_id: Mapped[str | None] = mapped_column(String(32), default=None)
    moderator_name: Mapped[str] = mapped_column(String(100), default="NexusGuard")
    source: Mapped[str] = mapped_column(String(16))  # automatic | dashboard | command
    reason: Mapped[str | None] = mapped_column(String(500), default=None)
    status: Mapped[str] = mapped_column(String(16), default="done")
    event_id: Mapped[int | None] = mapped_column(ForeignKey("security_events.id", ondelete="SET NULL"), default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class Flag(Base):
    """A member someone should look at. Resolved from the dashboard."""

    __tablename__ = "flags"
    __table_args__ = (Index("ix_flags_guild_status", "guild_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(String(32))
    username: Mapped[str | None] = mapped_column(String(100), default=None)
    reason: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | dismissed | actioned
    event_id: Mapped[int | None] = mapped_column(ForeignKey("security_events.id", ondelete="SET NULL"), default=None)
    resolved_by: Mapped[str | None] = mapped_column(String(100), default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class AuditEntry(Base):
    """Who changed what from the dashboard or a slash command: rules, settings,
    raid mode, review decisions. Protection config is security-relevant too."""

    __tablename__ = "audit_entries"
    __table_args__ = (Index("ix_audit_guild_time", "guild_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"))
    actor_id: Mapped[str | None] = mapped_column(String(32), default=None)
    actor_name: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(40))  # rule.updated, settings.updated, raid_mode.enabled, ...
    target: Mapped[str | None] = mapped_column(String(100), default=None)
    changes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
