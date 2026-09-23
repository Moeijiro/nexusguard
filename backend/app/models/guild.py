"""Guilds, who may manage them, and their protection rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UpdatedMixin, UTCDateTime


class Guild(Base, UpdatedMixin):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    icon: Mapped[str | None] = mapped_column(String(64), default=None)
    member_count: Mapped[int] = mapped_column(default=0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    # False once the bot is removed: history stays, protection stops.
    bot_present: Mapped[bool] = mapped_column(Boolean, default=True)

    alert_channel_id: Mapped[str | None] = mapped_column(String(32), default=None)
    restricted_role_id: Mapped[str | None] = mapped_column(String(32), default=None)

    raid_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    raid_mode_since: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
    raid_mode_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
    raid_mode_reason: Mapped[str | None] = mapped_column(String(200), default=None)
    raid_mode_by: Mapped[str | None] = mapped_column(String(100), default=None)

    # Snapshots the bot keeps fresh, so the dashboard's pickers don't call Discord.
    channels: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    roles: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    rules: Mapped[list["RuleConfig"]] = relationship(back_populates="guild", cascade="all, delete-orphan")


class GuildAccess(Base):
    """A login-time snapshot: this user may manage this guild.

    Built from Discord's /users/@me/guilds at OAuth callback (owner or Manage
    Server). Discord tokens are not kept, so the snapshot expires and a fresh
    login refreshes it.
    """

    __tablename__ = "guild_access"
    __table_args__ = (UniqueConstraint("user_id", "guild_id", name="uq_access_user_guild"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True)
    permissions: Mapped[str] = mapped_column(String(32), default="0")
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[datetime] = mapped_column(UTCDateTime())


class RuleConfig(Base, TimestampMixin):
    """One row per guild and module. ``params`` is the module's validated rule JSON."""

    __tablename__ = "rule_configs"
    __table_args__ = (UniqueConstraint("guild_id", "module", name="uq_rule_guild_module"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True)
    module: Mapped[str] = mapped_column(String(40))
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
    updated_by: Mapped[str | None] = mapped_column(String(100), default=None)

    guild: Mapped[Guild] = relationship(back_populates="rules")
