"""Guilds: list, overview, settings, raid mode and protection rules."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import actor_name, get_current_user, guild_for_user, manageable_guilds
from app.core import rate_limit
from app.core.errors import APIError
from app.db.base import utcnow
from app.db.session import get_db
from app.engine.actions.notify import COLOURS
from app.engine.ports import ExecutorError
from app.engine.rules_schema import Module, parse_rule
from app.engine.severity import Severity
from app.models import ActivityBucket, AuditEntry, Flag, Guild, ModerationLog, RuleConfig, SecurityEvent, User
from app.schemas.api import (
    ActivityPoint,
    GuildDetail,
    GuildSummary,
    OverviewOut,
    RaidModeIn,
    Resource,
    ResourcesOut,
    RuleOut,
    SettingsIn,
)
from app.services import guilds as guild_service
from app.services.executor_factory import executor_for
from app.services.present import (
    MODULE_INFO,
    allowed_actions,
    channel_names,
    event_out,
    events_since,
    guild_detail,
    guild_summary,
)

router = APIRouter(prefix="/api/guilds", tags=["guilds"])


def write_limit(user: User) -> None:
    rate_limit.check(f"write:{user.id}", times=60, seconds=60)


def audit(db: Session, guild: Guild, user: User, action: str, target: str | None, changes: dict) -> None:
    db.add(AuditEntry(guild_id=guild.id, actor_id=user.discord_id, actor_name=actor_name(user),
                      action=action, target=target, changes=changes))


@router.get("", response_model=list[GuildSummary], summary="Servers you can manage")
def list_guilds(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[GuildSummary]:
    guilds = manageable_guilds(db, user)
    counts = events_since(db, [g.id for g in guilds])
    return [guild_summary(g, counts.get(g.id, 0)) for g in guilds]


@router.get("/{guild_id}", response_model=GuildDetail, summary="One server")
def get_guild(guild: Guild = Depends(guild_for_user), db: Session = Depends(get_db)) -> GuildDetail:
    return guild_detail(db, guild)


@router.get("/{guild_id}/overview", response_model=OverviewOut, summary="Dashboard: status, stats, activity, recent events")
def overview(guild: Guild = Depends(guild_for_user), db: Session = Depends(get_db)) -> OverviewOut:
    now = utcnow()
    since = now - timedelta(hours=24)
    rules = guild_service.load_rules(guild)
    modules = [
        {"module": m.value, "name": MODULE_INFO[m][0], "enabled": rules[m].enabled} for m in Module
    ]
    severity = dict(db.execute(
        select(SecurityEvent.severity, func.count()).where(SecurityEvent.guild_id == guild.id, SecurityEvent.created_at >= since)
        .group_by(SecurityEvent.severity)
    ).all())
    flagged_users = db.scalar(
        select(func.count(func.distinct(SecurityEvent.user_id))).where(
            SecurityEvent.guild_id == guild.id, SecurityEvent.created_at >= since, SecurityEvent.user_id.is_not(None),
            SecurityEvent.severity.in_(["medium", "high", "critical"]),
        )
    ) or 0
    actions = db.scalar(select(func.count()).select_from(ModerationLog).where(
        ModerationLog.guild_id == guild.id, ModerationLog.created_at >= since)) or 0
    open_flags = db.scalar(select(func.count()).select_from(Flag).where(Flag.guild_id == guild.id, Flag.status == "open")) or 0

    start = (now - timedelta(hours=23)).replace(minute=0, second=0, microsecond=0)
    buckets = {b.hour: b for b in db.execute(
        select(ActivityBucket).where(ActivityBucket.guild_id == guild.id, ActivityBucket.hour >= start)).scalars()}
    event_hours: dict = {}
    for created in db.execute(select(SecurityEvent.created_at).where(
            SecurityEvent.guild_id == guild.id, SecurityEvent.created_at >= start)).scalars():
        hour = created.replace(minute=0, second=0, microsecond=0)
        event_hours[hour] = event_hours.get(hour, 0) + 1
    activity = []
    for offset in range(24):
        hour = start + timedelta(hours=offset)
        bucket = buckets.get(hour)
        activity.append(ActivityPoint(hour=hour, messages=bucket.messages if bucket else 0,
                                      joins=bucket.joins if bucket else 0, events=event_hours.get(hour, 0)))

    recent = db.execute(select(SecurityEvent).where(SecurityEvent.guild_id == guild.id)
                        .order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc()).limit(12)).scalars()
    names = channel_names(guild)
    return OverviewOut(
        guild=guild_detail(db, guild),
        protection={"enabled": sum(m["enabled"] for m in modules), "total": len(modules), "modules": modules},
        stats={
            "events_today": sum(severity.values()),
            "users_flagged": flagged_users,
            "active_rules": sum(m["enabled"] for m in modules),
            "actions_today": actions,
            "open_flags": open_flags,
        },
        severity_today={s.value: severity.get(s.value, 0) for s in Severity},
        activity=activity,
        recent_events=[event_out(e, names) for e in recent],
    )


@router.get("/{guild_id}/resources", response_model=ResourcesOut, summary="Channels and roles for the pickers")
def resources(guild: Guild = Depends(guild_for_user)) -> ResourcesOut:
    channels = [Resource(id=str(c["id"]), name=c["name"], kind=c.get("kind", "text"), position=c.get("position", 0))
                for c in guild.channels or []]
    roles = [Resource(id=str(r["id"]), name=r["name"], kind="role", position=r.get("position", 0),
                      assignable=r.get("assignable", True), color=r.get("color"))
             for r in guild.roles or []]
    return ResourcesOut(channels=sorted(channels, key=lambda c: c.position),
                        roles=sorted(roles, key=lambda r: -r.position))


@router.patch("/{guild_id}/settings", response_model=GuildDetail, summary="Alert channel and restricted role")
def update_settings(
    payload: SettingsIn,
    guild: Guild = Depends(guild_for_user),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GuildDetail:
    write_limit(user)
    changes = payload.model_dump(exclude_unset=True)
    channel_ids = {str(c["id"]) for c in guild.channels or []}
    roles = {str(r["id"]): r for r in guild.roles or []}
    if changes.get("alert_channel_id") and changes["alert_channel_id"] not in channel_ids:
        raise APIError("unknown_channel", "That channel isn't a text channel in this server.", 422)
    role_id = changes.get("restricted_role_id")
    if role_id:
        if role_id not in roles:
            raise APIError("unknown_role", "That role isn't in this server.", 422)
        if not roles[role_id].get("assignable", True):
            raise APIError("role_not_assignable", "NexusGuard can't assign that role — move its role above it.", 422)
    before = {k: getattr(guild, k) for k in changes}
    for key, value in changes.items():
        setattr(guild, key, value or None)
    audit(db, guild, user, "settings.updated", None, {"before": before, "after": changes})
    db.commit()
    return guild_detail(db, guild)


@router.post("/{guild_id}/raid-mode", response_model=GuildDetail, summary="Turn raid mode on or off")
async def raid_mode(
    payload: RaidModeIn,
    guild: Guild = Depends(guild_for_user),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GuildDetail:
    write_limit(user)
    name = actor_name(user)
    until = utcnow() + timedelta(minutes=payload.minutes) if payload.enabled and payload.minutes else None
    guild_service.set_raid_mode(guild, payload.enabled, until, "Enabled from the dashboard", f"{name} (dashboard)")
    state = "enabled" if payload.enabled else "disabled"
    audit(db, guild, user, f"raid_mode.{state}", None, {"minutes": payload.minutes})
    summary = f"Raid mode {state} by {name}"
    event = SecurityEvent(
        guild_id=guild.id, type="moderation_action", module="raid_detection",
        severity="high" if payload.enabled else "low", summary=summary, action_taken="Logged",
        actions=[], notes=[], details={"raid_mode": payload.enabled, "until": until.isoformat() if until else None},
        simulated=guild.is_demo,
    )
    db.add(event)
    if guild.alert_channel_id:
        severity = Severity.HIGH if payload.enabled else Severity.LOW
        try:
            await executor_for(guild).send_channel_message(guild.alert_channel_id, embed={
                "title": f"Raid mode {state}", "description": summary, "color": COLOURS[severity],
                "footer": {"text": "NexusGuard"},
            })
            event.action_taken = "Moderators notified"
        except ExecutorError as exc:
            event.action_taken = f"Alert failed: {exc}"[:300]
    db.commit()
    return guild_detail(db, guild)


# --- rules -----------------------------------------------------------------------------
def _rule_out(module: Module, row: RuleConfig | None, rule) -> RuleOut:  # noqa: ANN001
    name, description = MODULE_INFO[module]
    params = rule.model_dump(mode="json", exclude={"module"})
    return RuleOut(module=module.value, name=name, description=description, enabled=params.pop("enabled"),
                   params=params, allowed_actions=allowed_actions(module),
                   updated_at=row.updated_at if row else None, updated_by=row.updated_by if row else None)


@router.get("/{guild_id}/rules", response_model=list[RuleOut], summary="Protection modules")
def list_rules(guild: Guild = Depends(guild_for_user)) -> list[RuleOut]:
    rules = guild_service.load_rules(guild)
    rows = {row.module: row for row in guild.rules}
    return [_rule_out(m, rows.get(m.value), rules[m]) for m in Module]


@router.put("/{guild_id}/rules/{module}", response_model=RuleOut, summary="Update a protection module")
def update_rule(
    module: Module,
    payload: dict,
    guild: Guild = Depends(guild_for_user),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RuleOut:
    """The body is validated by the module's own schema (bounds, allowed actions)."""
    write_limit(user)
    payload.pop("module", None)
    try:
        rule = parse_rule(module, payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(part) for part in first["loc"])
        message = first["msg"].removeprefix("Value error, ")
        raise APIError("validation_error", f"{where}: {message}" if where else message, 422) from None
    row = next((r for r in guild.rules if r.module == module.value), None)
    before = dict(row.params) if row else {}
    if row is None:
        row = RuleConfig(guild_id=guild.id, module=module.value)
        db.add(row)
    row.params = rule.model_dump(mode="json")
    row.updated_at, row.updated_by = utcnow(), actor_name(user)
    changed = {k: {"from": before.get(k), "to": v} for k, v in row.params.items() if before.get(k) != v}
    audit(db, guild, user, "rule.updated", module.value, changed)
    db.commit()
    return _rule_out(module, row, rule)
