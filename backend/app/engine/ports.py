"""The engine's only two dependencies on the outside world.

``ActionExecutor`` performs Discord actions: a REST client in live mode, a
recorder in the demo and the tests. ``Store`` reads guild configuration and
writes what happened: the database in the app, the same database in tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.engine.rules_schema import Module, Rule


class ExecutorError(Exception):
    """Discord refused or failed an action (missing permission, hierarchy, gone)."""


class ActionExecutor(Protocol):
    simulated: bool

    async def delete_message(self, channel_id: str, message_id: str, reason: str) -> None: ...
    async def timeout_member(self, guild_id: str, user_id: str, until: datetime, reason: str) -> None: ...
    async def add_role(self, guild_id: str, user_id: str, role_id: str, reason: str) -> None: ...
    async def kick_member(self, guild_id: str, user_id: str, reason: str) -> None: ...
    async def send_channel_message(self, channel_id: str, content: str | None = None, embed: dict[str, Any] | None = None) -> None: ...
    async def send_dm(self, user_id: str, content: str) -> bool: ...


@dataclass(slots=True)
class GuildContext:
    guild_id: str
    name: str
    rules: dict[Module, Rule]
    raid_mode: bool = False
    raid_mode_until: datetime | None = None
    alert_channel_id: str | None = None
    restricted_role_id: str | None = None
    is_demo: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def rule(self, module: Module) -> Rule:
        return self.rules[module]


class Store(Protocol):
    def guild_context(self, guild_id: str) -> GuildContext | None: ...
    def recent_offenses(self, guild_id: str, user_id: str, since: datetime) -> int: ...
    def set_raid_mode(self, guild_id: str, enabled: bool, until: datetime | None, reason: str, by: str) -> None: ...
    def record(self, outcome: "Outcome") -> int: ...  # noqa: F821  (defined in pipeline)
