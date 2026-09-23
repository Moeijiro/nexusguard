"""Rows -> API models, plus the module catalogue shown on rule cards."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utcnow
from app.engine.rules_schema import ALLOWED_ACTIONS, Module
from app.models import Guild, SecurityEvent
from app.schemas.api import EventOut, GuildDetail, GuildSummary, RaidModeOut
from app.services import discord_oauth
from app.services.guilds import load_rules

MODULE_INFO: dict[Module, tuple[str, str]] = {
    Module.MESSAGE_FLOOD: ("Message flood", "Too many messages from one member in a short window."),
    Module.DUPLICATE_MESSAGES: ("Duplicate messages", "The same message posted again and again — the usual scam pattern."),
    Module.MASS_MENTIONS: ("Mass mentions", "@everyone / @here from members, or too many pings in one message."),
    Module.RAID_DETECTION: ("Raid detection", "A spike of joins. Can switch raid mode on automatically."),
    Module.ACCOUNT_AGE: ("Account age", "Flag or restrict very new Discord accounts. Off by default."),
    Module.PRIVILEGED_ROLES: ("Privileged roles", "Alerts when a role with dangerous permissions is granted."),
}


def icon_url(guild: Guild) -> str | None:
    if guild.icon and not guild.is_demo:
        return f"https://cdn.discordapp.com/icons/{guild.discord_id}/{guild.icon}.png?size=128"
    return None


def events_since(db: Session, guild_pks: list[int], hours: int = 24) -> dict[int, int]:
    if not guild_pks:
        return {}
    since = utcnow() - timedelta(hours=hours)
    return dict(db.execute(
        select(SecurityEvent.guild_id, func.count())
        .where(SecurityEvent.guild_id.in_(guild_pks), SecurityEvent.created_at >= since)
        .group_by(SecurityEvent.guild_id)
    ).all())


def guild_summary(guild: Guild, events_today: int) -> GuildSummary:
    rules = load_rules(guild)
    return GuildSummary(
        id=guild.discord_id, name=guild.name, icon_url=icon_url(guild), member_count=guild.member_count,
        is_demo=guild.is_demo, bot_present=guild.bot_present, raid_mode=guild.raid_mode,
        modules_enabled=sum(rule.enabled for rule in rules.values()), modules_total=len(rules),
        events_today=events_today,
    )


def guild_detail(db: Session, guild: Guild) -> GuildDetail:
    summary = guild_summary(guild, events_since(db, [guild.id]).get(guild.id, 0))
    return GuildDetail(
        **summary.model_dump(),
        alert_channel_id=guild.alert_channel_id,
        restricted_role_id=guild.restricted_role_id,
        raid=RaidModeOut(enabled=guild.raid_mode, since=guild.raid_mode_since, until=guild.raid_mode_until,
                         reason=guild.raid_mode_reason, by=guild.raid_mode_by),
        bot_invite_url=None if guild.is_demo or not settings.discord_client_id else discord_oauth.bot_invite_url(guild.discord_id),
    )


def event_out(event: SecurityEvent, channel_names: dict[str, str] | None = None) -> EventOut:
    return EventOut(
        id=event.id, type=event.type, module=event.module, severity=event.severity,  # type: ignore[arg-type]
        summary=event.summary, user_id=event.user_id, username=event.username, channel_id=event.channel_id,
        channel_name=(channel_names or {}).get(event.channel_id or ""),
        action_taken=event.action_taken, actions=event.actions, notes=event.notes,  # type: ignore[arg-type]
        metadata=event.details, simulated=event.simulated, created_at=event.created_at,
    )


def channel_names(guild: Guild) -> dict[str, str]:
    return {str(c["id"]): c["name"] for c in guild.channels or []}


def allowed_actions(module: Module) -> list[str]:
    return sorted(a.value for a in ALLOWED_ACTIONS[module])
