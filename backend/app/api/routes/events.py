"""Security events, moderation logs, the review queue and the config audit trail."""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import actor_name, get_current_user, guild_for_user
from app.api.routes.guilds import audit, write_limit
from app.core.errors import APIError
from app.db.base import utcnow
from app.db.session import get_db
from app.engine.ports import ExecutorError
from app.models import AuditEntry, Flag, Guild, ModerationLog, SecurityEvent, User
from app.schemas.api import AuditOut, EventOut, EventPage, FlagOut, ModerationOut, ResolveFlagIn
from app.services.executor_factory import executor_for
from app.services.present import channel_names, event_out

router = APIRouter(prefix="/api/guilds", tags=["events"])

Severity = Literal["low", "medium", "high", "critical"]


@router.get("/{guild_id}/events", response_model=EventPage, summary="Security events, newest first")
def list_events(
    severity: list[Severity] = Query(default=[]),
    type: str | None = Query(default=None, max_length=32),
    user_id: str | None = Query(default=None, pattern=r"^\d{5,25}$"),
    after_id: int | None = Query(default=None, ge=0, description="Only newer events — for the live stream"),
    before_id: int | None = Query(default=None, ge=0, description="Pagination cursor"),
    limit: int = Query(default=50, ge=1, le=200),
    guild: Guild = Depends(guild_for_user),
    db: Session = Depends(get_db),
) -> EventPage:
    query = select(SecurityEvent).where(SecurityEvent.guild_id == guild.id)
    if severity:
        query = query.where(SecurityEvent.severity.in_(severity))
    if type:
        query = query.where(SecurityEvent.type == type)
    if user_id:
        query = query.where(SecurityEvent.user_id == user_id)
    if after_id is not None:
        query = query.where(SecurityEvent.id > after_id)
    if before_id is not None:
        query = query.where(SecurityEvent.id < before_id)
    rows = list(db.execute(query.order_by(SecurityEvent.id.desc()).limit(limit + 1)).scalars())
    more = len(rows) > limit
    rows = rows[:limit]
    names = channel_names(guild)
    return EventPage(items=[event_out(r, names) for r in rows], next_before_id=rows[-1].id if more else None)


@router.get("/{guild_id}/events/{event_id}", response_model=EventOut, summary="One event")
def get_event(event_id: int, guild: Guild = Depends(guild_for_user), db: Session = Depends(get_db)) -> EventOut:
    event = db.get(SecurityEvent, event_id)
    if event is None or event.guild_id != guild.id:
        raise APIError("not_found", "Event not found.", 404)
    return event_out(event, channel_names(guild))


@router.get("/{guild_id}/moderation", response_model=list[ModerationOut], summary="Moderation performed through NexusGuard")
def moderation_log(
    source: Literal["automatic", "dashboard", "command"] | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    guild: Guild = Depends(guild_for_user),
    db: Session = Depends(get_db),
) -> list[ModerationLog]:
    query = select(ModerationLog).where(ModerationLog.guild_id == guild.id)
    if source:
        query = query.where(ModerationLog.source == source)
    return list(db.execute(query.order_by(ModerationLog.created_at.desc(), ModerationLog.id.desc()).limit(limit)).scalars())


@router.get("/{guild_id}/flags", response_model=list[FlagOut], summary="Review queue")
def list_flags(
    status: Literal["open", "dismissed", "actioned", "all"] = "open",
    guild: Guild = Depends(guild_for_user),
    db: Session = Depends(get_db),
) -> list[Flag]:
    query = select(Flag).where(Flag.guild_id == guild.id)
    if status != "all":
        query = query.where(Flag.status == status)
    return list(db.execute(query.order_by(Flag.created_at.desc()).limit(200)).scalars())


@router.post("/{guild_id}/flags/{flag_id}/resolve", response_model=FlagOut, summary="Dismiss a flag or act on the member")
async def resolve_flag(
    flag_id: int,
    payload: ResolveFlagIn,
    guild: Guild = Depends(guild_for_user),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Flag:
    write_limit(user)
    flag = db.get(Flag, flag_id)
    if flag is None or flag.guild_id != guild.id:
        raise APIError("not_found", "Flag not found.", 404)
    if flag.status != "open":
        raise APIError("already_resolved", "This flag has already been resolved.", 409)

    name = actor_name(user)
    reason = payload.reason or f"Reviewed on the dashboard: {flag.reason}"
    if payload.action != "dismiss":
        executor = executor_for(guild)
        try:
            if payload.action == "timeout":
                await executor.timeout_member(guild.discord_id, flag.user_id, utcnow() + timedelta(minutes=payload.minutes), reason)
            elif payload.action == "restrict":
                if not guild.restricted_role_id:
                    raise APIError("no_restricted_role", "Set a restricted role in Settings first.", 409)
                await executor.add_role(guild.discord_id, flag.user_id, guild.restricted_role_id, reason)
            elif payload.action == "kick":
                await executor.kick_member(guild.discord_id, flag.user_id, reason)
            status = "simulated" if executor.simulated else "done"
        except ExecutorError as exc:
            db.add(ModerationLog(guild_id=guild.id, action=payload.action, target_id=flag.user_id, target_name=flag.username,
                                 moderator_id=user.discord_id, moderator_name=name, source="dashboard", reason=reason,
                                 status="failed", event_id=flag.event_id))
            db.commit()
            raise APIError("discord_error", str(exc), 502) from None
        db.add(ModerationLog(guild_id=guild.id, action=payload.action, target_id=flag.user_id, target_name=flag.username,
                             moderator_id=user.discord_id, moderator_name=name, source="dashboard", reason=reason,
                             status=status, event_id=flag.event_id))

    flag.status = "dismissed" if payload.action == "dismiss" else "actioned"
    flag.resolved_by, flag.resolved_at = name, utcnow()
    audit(db, guild, user, f"flag.{payload.action}", flag.username or flag.user_id, {"flag_id": flag.id})
    db.commit()
    return flag


@router.get("/{guild_id}/audit", response_model=list[AuditOut], summary="Who changed what")
def audit_log(guild: Guild = Depends(guild_for_user), db: Session = Depends(get_db)) -> list[AuditEntry]:
    return list(db.execute(select(AuditEntry).where(AuditEntry.guild_id == guild.id)
                           .order_by(AuditEntry.created_at.desc(), AuditEntry.id.desc()).limit(100)).scalars())
