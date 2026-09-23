"""Guild records, their rules, and the engine's view of them."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.engine.ports import GuildContext
from app.engine.rules_schema import Module, Rule, default_rules, parse_rule
from app.models import Guild, RuleConfig


def ensure_guild(
    db: Session,
    discord_id: str,
    name: str,
    *,
    icon: str | None = None,
    is_demo: bool = False,
    member_count: int | None = None,
) -> Guild:
    """Create the guild with default rules the first time we see it; refresh its name after."""
    guild = db.execute(select(Guild).where(Guild.discord_id == discord_id)).scalar_one_or_none()
    if guild is None:
        guild = Guild(discord_id=discord_id, name=name, icon=icon, is_demo=is_demo, member_count=member_count or 0)
        db.add(guild)
        db.flush()
        for module, rule in default_rules().items():
            db.add(RuleConfig(guild_id=guild.id, module=module.value, params=rule.model_dump(mode="json")))
        db.flush()
    else:
        guild.name, guild.icon, guild.bot_present = name, icon, True
        if member_count is not None:
            guild.member_count = member_count
    return guild


def load_rules(guild: Guild) -> dict[Module, Rule]:
    """Parse stored rules, falling back to defaults for any module that is missing or invalid."""
    rules = default_rules()
    for row in guild.rules:
        try:
            rules[Module(row.module)] = parse_rule(row.module, row.params)
        except ValueError:
            continue  # unknown module from an older version, or hand-edited JSON
    return rules


def context_for(guild: Guild) -> GuildContext:
    return GuildContext(
        guild_id=guild.discord_id,
        name=guild.name,
        rules=load_rules(guild),
        raid_mode=guild.raid_mode,
        raid_mode_until=guild.raid_mode_until,
        alert_channel_id=guild.alert_channel_id,
        restricted_role_id=guild.restricted_role_id,
        is_demo=guild.is_demo,
    )


def set_raid_mode(guild: Guild, enabled: bool, until: datetime | None, reason: str, by: str) -> None:
    guild.raid_mode = enabled
    guild.raid_mode_until = until if enabled else None
    guild.raid_mode_since = utcnow() if enabled else None
    guild.raid_mode_reason = reason if enabled else None
    guild.raid_mode_by = by if enabled else None
