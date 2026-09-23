"""What each protection module can be configured to do.

These models are the single source of truth for rule settings: the API
validates dashboard input with them, the database stores their JSON, and the
engine reads them back. Bounds keep a typo from turning a module into
something that times out the whole server.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ActionName(StrEnum):
    WARN = "warn"
    DELETE_MESSAGE = "delete_message"
    TIMEOUT = "timeout"
    RESTRICT = "restrict"        # assign the guild's restricted role
    KICK = "kick"
    NOTIFY = "notify"            # alert the moderator channel
    FLAG = "flag"                # add to the dashboard review queue


class Module(StrEnum):
    MESSAGE_FLOOD = "message_flood"
    DUPLICATE_MESSAGES = "duplicate_messages"
    MASS_MENTIONS = "mass_mentions"
    RAID_DETECTION = "raid_detection"
    ACCOUNT_AGE = "account_age"
    PRIVILEGED_ROLES = "privileged_roles"


MESSAGE_ACTIONS = {ActionName.WARN, ActionName.DELETE_MESSAGE, ActionName.TIMEOUT, ActionName.KICK, ActionName.NOTIFY, ActionName.FLAG}

# Bans are deliberately absent everywhere. Kick is available on message rules
# only, and never on by default.
ALLOWED_ACTIONS: dict[Module, set[ActionName]] = {
    Module.MESSAGE_FLOOD: MESSAGE_ACTIONS,
    Module.DUPLICATE_MESSAGES: MESSAGE_ACTIONS,
    Module.MASS_MENTIONS: MESSAGE_ACTIONS,
    Module.RAID_DETECTION: {ActionName.NOTIFY},
    Module.ACCOUNT_AGE: {ActionName.FLAG, ActionName.RESTRICT, ActionName.NOTIFY},
    Module.PRIVILEGED_ROLES: {ActionName.NOTIFY, ActionName.FLAG},
}


class _Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)
    module: Module
    enabled: bool = True
    actions: list[ActionName] = []

    @field_validator("actions")
    @classmethod
    def _dedupe(cls, value: list[ActionName]) -> list[ActionName]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def _allowed(self) -> "_Rule":
        not_allowed = set(self.actions) - ALLOWED_ACTIONS[self.module]
        if not_allowed:
            names = ", ".join(sorted(a.value for a in not_allowed))
            raise ValueError(f"{self.module.value} can't use: {names}")
        return self


class MessageFloodRule(_Rule):
    module: Literal[Module.MESSAGE_FLOOD] = Module.MESSAGE_FLOOD
    max_messages: int = Field(default=6, ge=2, le=50)
    window_seconds: int = Field(default=5, ge=2, le=60)
    timeout_minutes: int = Field(default=10, ge=1, le=1440)
    actions: list[ActionName] = [ActionName.DELETE_MESSAGE, ActionName.TIMEOUT]


class DuplicateMessagesRule(_Rule):
    module: Literal[Module.DUPLICATE_MESSAGES] = Module.DUPLICATE_MESSAGES
    max_repeats: int = Field(default=3, ge=2, le=20)
    window_seconds: int = Field(default=30, ge=5, le=600)
    timeout_minutes: int = Field(default=10, ge=1, le=1440)
    actions: list[ActionName] = [ActionName.DELETE_MESSAGE, ActionName.WARN]


class MassMentionsRule(_Rule):
    module: Literal[Module.MASS_MENTIONS] = Module.MASS_MENTIONS
    max_mentions: int = Field(default=5, ge=2, le=50)
    block_everyone: bool = True  # @everyone / @here from non-moderators
    timeout_minutes: int = Field(default=10, ge=1, le=1440)
    actions: list[ActionName] = [ActionName.DELETE_MESSAGE, ActionName.WARN]


class RaidDetectionRule(_Rule):
    module: Literal[Module.RAID_DETECTION] = Module.RAID_DETECTION
    join_threshold: int = Field(default=10, ge=3, le=500)
    window_seconds: int = Field(default=10, ge=5, le=600)
    auto_raid_mode: bool = True
    raid_mode_minutes: int = Field(default=30, ge=5, le=1440)
    # While raid mode is on, give every new member the restricted role.
    restrict_new_members: bool = True
    actions: list[ActionName] = [ActionName.NOTIFY]


class AccountAgeRule(_Rule):
    module: Literal[Module.ACCOUNT_AGE] = Module.ACCOUNT_AGE
    min_account_age_hours: int = Field(default=24, ge=1, le=24 * 90)
    actions: list[ActionName] = [ActionName.FLAG]


class PrivilegedRolesRule(_Rule):
    module: Literal[Module.PRIVILEGED_ROLES] = Module.PRIVILEGED_ROLES
    actions: list[ActionName] = [ActionName.NOTIFY]


AnyRule = Annotated[
    MessageFloodRule | DuplicateMessagesRule | MassMentionsRule | RaidDetectionRule | AccountAgeRule | PrivilegedRolesRule,
    Field(discriminator="module"),
]

RULE_TYPES: dict[Module, type[_Rule]] = {
    Module.MESSAGE_FLOOD: MessageFloodRule,
    Module.DUPLICATE_MESSAGES: DuplicateMessagesRule,
    Module.MASS_MENTIONS: MassMentionsRule,
    Module.RAID_DETECTION: RaidDetectionRule,
    Module.ACCOUNT_AGE: AccountAgeRule,
    Module.PRIVILEGED_ROLES: PrivilegedRolesRule,
}


def default_rules() -> dict[Module, _Rule]:
    """What a guild gets when NexusGuard joins: everything on except account age,
    which is opt-in so new accounts aren't treated as suspicious by default."""
    rules = {module: model() for module, model in RULE_TYPES.items()}
    rules[Module.ACCOUNT_AGE].enabled = False
    return rules


def parse_rule(module: Module | str, data: dict) -> _Rule:
    module = Module(module)
    return RULE_TYPES[module].model_validate({**data, "module": module})


Rule = _Rule
