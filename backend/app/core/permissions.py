"""Discord permission bitfields.

Only the flags NexusGuard actually checks are modelled; a short list is easier
to audit than the full set.
"""

from __future__ import annotations

from enum import IntFlag


class Permission(IntFlag):
    KICK_MEMBERS = 1 << 1
    BAN_MEMBERS = 1 << 2
    ADMINISTRATOR = 1 << 3
    MANAGE_CHANNELS = 1 << 4
    MANAGE_GUILD = 1 << 5
    VIEW_AUDIT_LOG = 1 << 7
    VIEW_CHANNEL = 1 << 10
    SEND_MESSAGES = 1 << 11
    MANAGE_MESSAGES = 1 << 13
    EMBED_LINKS = 1 << 14
    READ_MESSAGE_HISTORY = 1 << 16
    MENTION_EVERYONE = 1 << 17
    MANAGE_ROLES = 1 << 28
    MANAGE_WEBHOOKS = 1 << 29
    MODERATE_MEMBERS = 1 << 40


# What the bot asks for when it's invited — each one maps to a feature:
BOT_PERMISSIONS = (
    Permission.VIEW_CHANNEL          # see the channels it protects
    | Permission.SEND_MESSAGES       # moderator alerts, warnings
    | Permission.EMBED_LINKS         # alert embeds
    | Permission.READ_MESSAGE_HISTORY
    | Permission.MANAGE_MESSAGES     # delete spam / mass-mention messages
    | Permission.MODERATE_MEMBERS    # timeouts
    | Permission.MANAGE_ROLES        # assign the restricted role
    | Permission.KICK_MEMBERS        # only if a rule is configured to kick
    | Permission.VIEW_AUDIT_LOG      # attribute manual moderation actions
)

# Granting any of these through a role is treated as a privileged change.
DANGEROUS = (
    Permission.ADMINISTRATOR
    | Permission.MANAGE_GUILD
    | Permission.MANAGE_ROLES
    | Permission.MANAGE_CHANNELS
    | Permission.MANAGE_WEBHOOKS
    | Permission.BAN_MEMBERS
    | Permission.KICK_MEMBERS
    | Permission.MENTION_EVERYONE
)


def parse(raw: str | int | None) -> Permission:
    """Discord sends the bitfield as a string; treat anything unparsable as none."""
    try:
        return Permission(int(raw or 0) & sum(Permission))
    except (TypeError, ValueError):
        return Permission(0)


def has(raw: str | int | None, flag: Permission) -> bool:
    """ADMINISTRATOR implies every other permission, exactly as Discord does."""
    bits = parse(raw)
    return bool(bits & Permission.ADMINISTRATOR or bits & flag == flag)


def can_manage_guild(raw: str | int | None, *, is_owner: bool = False) -> bool:
    """Who may see and change a guild's protection: the owner, or Manage Server."""
    return is_owner or has(raw, Permission.MANAGE_GUILD)


def dangerous_flags(raw: str | int | None) -> list[str]:
    return [flag.name for flag in Permission if flag.name and flag in DANGEROUS and parse(raw) & flag]


def names(raw: str | int | None) -> list[str]:
    return [flag.name for flag in Permission if flag.name and parse(raw) & flag]
