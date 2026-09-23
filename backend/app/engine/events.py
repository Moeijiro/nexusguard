"""Normalised Discord events — the engine's only input.

The bot turns gateway events into these; the demo simulator and the tests
build them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Member:
    id: str
    name: str
    is_bot: bool = False
    # Owner, Administrator, Manage Server or Moderate Members: exempt from message rules.
    is_moderator: bool = False
    account_created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class MessageEvent:
    guild_id: str
    channel_id: str
    message_id: str
    author: Member
    content: str
    at: datetime
    user_mentions: int = 0
    role_mentions: int = 0
    mentions_everyone: bool = False  # @everyone or @here that would actually ping


@dataclass(frozen=True, slots=True)
class MemberJoinEvent:
    guild_id: str
    member: Member
    at: datetime


@dataclass(frozen=True, slots=True)
class RoleGrantEvent:
    """A role was added to a member."""

    guild_id: str
    member: Member
    role_id: str
    role_name: str
    role_permissions: int
    at: datetime
    granted_by: Member | None = None


@dataclass(frozen=True, slots=True)
class ModerationEvent:
    """A moderation action someone took by hand, seen in the audit log."""

    guild_id: str
    action: str  # "kick", "ban", "timeout", "unban", ...
    target: Member
    moderator: Member | None
    reason: str | None
    at: datetime
    extra: dict = field(default_factory=dict)


Event = MessageEvent | MemberJoinEvent | RoleGrantEvent | ModerationEvent
