"""discord.py objects -> engine events. The only place the engine meets discord.py.

Kept free of I/O so it can be tested with plain stand-in objects.
"""

from __future__ import annotations

import re
from typing import Any

from app.engine.events import Member, MemberJoinEvent, MessageEvent, ModerationEvent, RoleGrantEvent

# An @everyone/@here *attempt* matters even when it didn't ping: members
# without the permission trying it is a classic scam signal.
# Must stand on its own, so "team@everyone.dev" isn't one.
_EVERYONE = re.compile(r"(?<!\S)@(everyone|here)\b")


def is_moderator(member: Any) -> bool:
    perms = getattr(member, "guild_permissions", None)
    if perms is None:
        return False
    guild = getattr(member, "guild", None)
    owner = guild is not None and getattr(guild, "owner_id", None) == member.id
    return bool(owner or perms.administrator or perms.manage_guild or perms.moderate_members or perms.manage_messages)


def to_member(member: Any) -> Member:
    return Member(
        id=str(member.id),
        name=str(getattr(member, "name", member.id)),
        is_bot=bool(getattr(member, "bot", False)),
        is_moderator=is_moderator(member),
        account_created_at=getattr(member, "created_at", None),
    )


def message_event(message: Any) -> MessageEvent | None:
    if message.guild is None or message.webhook_id is not None:
        return None  # DMs and webhooks aren't members
    content = message.content or ""
    return MessageEvent(
        guild_id=str(message.guild.id),
        channel_id=str(message.channel.id),
        message_id=str(message.id),
        author=to_member(message.author),
        content=content,
        at=message.created_at,
        user_mentions=len({m.id for m in message.mentions if not getattr(m, "bot", False)}),
        role_mentions=len(message.role_mentions),
        mentions_everyone=bool(message.mention_everyone or _EVERYONE.search(content)),
    )


def join_event(member: Any, at: Any) -> MemberJoinEvent:
    return MemberJoinEvent(guild_id=str(member.guild.id), member=to_member(member), at=at)


def role_grants(before: Any, after: Any, at: Any) -> list[RoleGrantEvent]:
    """One event per role added in this update."""
    old = {role.id for role in before.roles}
    return [
        RoleGrantEvent(
            guild_id=str(after.guild.id), member=to_member(after), role_id=str(role.id), role_name=role.name,
            role_permissions=role.permissions.value, at=at,
        )
        for role in after.roles
        if role.id not in old
    ]


AUDIT_ACTIONS = {"kick": "kick", "ban": "ban", "unban": "unban"}


def moderation_event(entry: Any, bot_user_id: int) -> ModerationEvent | None:
    """Manual moderation seen in the audit log. NexusGuard's own actions are skipped."""
    if entry.user_id == bot_user_id or entry.target is None:
        return None
    action = AUDIT_ACTIONS.get(entry.action.name)
    extra: dict[str, Any] = {}
    if action is None and entry.action.name == "member_update":
        until = getattr(entry.after, "timed_out_until", None)
        if until is None:
            return None
        action, extra = "timeout", {"until": until.isoformat()}
    if action is None:
        return None
    target = entry.target
    moderator = entry.user
    return ModerationEvent(
        guild_id=str(entry.guild.id),
        action=action,
        target=Member(id=str(target.id), name=str(getattr(target, "name", target.id))),
        moderator=Member(id=str(moderator.id), name=str(moderator.name)) if moderator else None,
        reason=entry.reason,
        at=entry.created_at,
        extra=extra,
    )
