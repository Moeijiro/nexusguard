"""Response and request models for the dashboard API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UserOut(BaseModel):
    id: int
    discord_id: str
    username: str
    global_name: str | None
    avatar_url: str | None
    is_demo: bool


class ModeOut(BaseModel):
    discord_login: bool   # OAuth configured on this instance
    demo: bool            # "Explore the demo" available
    bot_invite_url: str | None


class GuildSummary(BaseModel):
    id: str
    name: str
    icon_url: str | None
    member_count: int
    is_demo: bool
    bot_present: bool
    raid_mode: bool
    modules_enabled: int
    modules_total: int
    events_today: int


class RaidModeOut(BaseModel):
    enabled: bool
    since: datetime | None
    until: datetime | None
    reason: str | None
    by: str | None


class GuildDetail(GuildSummary):
    alert_channel_id: str | None
    restricted_role_id: str | None
    raid: RaidModeOut
    bot_invite_url: str | None


class Resource(BaseModel):
    id: str
    name: str
    kind: Literal["text", "announcement", "role"]
    position: int = 0
    assignable: bool = True   # roles only: below NexusGuard's highest role and not managed
    color: int | None = None


class ResourcesOut(BaseModel):
    channels: list[Resource]
    roles: list[Resource]


class SettingsIn(Input):
    alert_channel_id: str | None = Field(default=None, max_length=32)
    restricted_role_id: str | None = Field(default=None, max_length=32)


class RuleOut(BaseModel):
    module: str
    name: str
    description: str
    enabled: bool
    params: dict[str, Any]
    allowed_actions: list[str]
    updated_at: datetime | None
    updated_by: str | None


class RaidModeIn(Input):
    enabled: bool
    minutes: int | None = Field(default=None, ge=5, le=1440)


class ActionResultOut(BaseModel):
    action: str
    status: str
    detail: str


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    module: str
    severity: Literal["low", "medium", "high", "critical"]
    summary: str
    user_id: str | None
    username: str | None
    channel_id: str | None
    channel_name: str | None = None
    action_taken: str
    actions: list[ActionResultOut]
    notes: list[str]
    metadata: dict[str, Any]
    simulated: bool
    created_at: datetime


class EventPage(BaseModel):
    items: list[EventOut]
    next_before_id: int | None


class ModerationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    action: str
    target_id: str
    target_name: str | None
    moderator_name: str
    source: Literal["automatic", "dashboard", "command"]
    reason: str | None
    status: str
    event_id: int | None
    created_at: datetime


class FlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: str
    username: str | None
    reason: str
    severity: str
    status: Literal["open", "dismissed", "actioned"]
    event_id: int | None
    resolved_by: str | None
    resolved_at: datetime | None
    created_at: datetime


class ResolveFlagIn(Input):
    action: Literal["dismiss", "timeout", "restrict", "kick"]
    minutes: int = Field(default=60, ge=1, le=10080)
    reason: str | None = Field(default=None, max_length=300)


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_name: str
    action: str
    target: str | None
    changes: dict[str, Any]
    created_at: datetime


class ActivityPoint(BaseModel):
    hour: datetime
    messages: int
    joins: int
    events: int


class OverviewOut(BaseModel):
    guild: GuildDetail
    protection: dict[str, Any]         # {"enabled": 5, "total": 6, "modules": [...]}
    stats: dict[str, int]              # events_today, users_flagged, active_rules, actions_today, open_flags
    severity_today: dict[str, int]
    activity: list[ActivityPoint]
    recent_events: list[EventOut]
