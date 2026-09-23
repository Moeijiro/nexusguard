"""Action executors: live Discord REST, and the demo/test recorder.

The bot and the dashboard use the same ``RestExecutor``: every action is one
REST call with the bot token. Discord's 429s are honoured (Retry-After) a few
times before giving up, and 403/404 become ``ExecutorError`` with a message a
moderator can act on — usually "move the NexusGuard role above X".
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import DISCORD_API_BASE, settings
from app.engine.ports import ExecutorError

logger = logging.getLogger("nexusguard.executor")
MAX_ATTEMPTS = 3


class RestExecutor:
    simulated = False

    def __init__(self, token: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._token = token or settings.discord_bot_token
        self._transport = transport

    async def _call(self, method: str, path: str, *, reason: str | None = None, json: Any = None) -> Any:
        headers = {"Authorization": f"Bot {self._token}", "User-Agent": "NexusGuard (portfolio, 1.0)"}
        if reason:
            # Discord shows this in the server's audit log; it must be URL-encoded.
            headers["X-Audit-Log-Reason"] = quote(reason[:400], safe=" ")
        async with httpx.AsyncClient(base_url=DISCORD_API_BASE, timeout=10, transport=self._transport) as client:
            for attempt in range(MAX_ATTEMPTS):
                response = await client.request(method, path, headers=headers, json=json)
                if response.status_code == 429 and attempt + 1 < MAX_ATTEMPTS:
                    retry = float(response.headers.get("Retry-After") or response.json().get("retry_after", 1))
                    logger.warning("Discord rate limit on %s; retrying in %.2fs", path, retry)
                    await asyncio.sleep(min(retry, 10))
                    continue
                if response.status_code == 403:
                    raise ExecutorError("Missing permission, or the member is above NexusGuard's role")
                if response.status_code == 404:
                    raise ExecutorError("Not found — the message or member is already gone")
                if response.status_code >= 400:
                    raise ExecutorError(f"Discord returned {response.status_code}")
                return response.json() if response.content else None
        raise ExecutorError("Rate limited by Discord")

    async def delete_message(self, channel_id: str, message_id: str, reason: str) -> None:
        await self._call("DELETE", f"/channels/{channel_id}/messages/{message_id}", reason=reason)

    async def timeout_member(self, guild_id: str, user_id: str, until: datetime, reason: str) -> None:
        await self._call("PATCH", f"/guilds/{guild_id}/members/{user_id}", reason=reason,
                         json={"communication_disabled_until": until.isoformat()})

    async def add_role(self, guild_id: str, user_id: str, role_id: str, reason: str) -> None:
        await self._call("PUT", f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}", reason=reason)

    async def kick_member(self, guild_id: str, user_id: str, reason: str) -> None:
        await self._call("DELETE", f"/guilds/{guild_id}/members/{user_id}", reason=reason)

    async def send_channel_message(self, channel_id: str, content: str | None = None, embed: dict | None = None) -> None:
        body: dict[str, Any] = {"allowed_mentions": {"parse": []}}  # alerts never ping anyone
        if content:
            body["content"] = content
        if embed:
            body["embeds"] = [embed]
        await self._call("POST", f"/channels/{channel_id}/messages", json=body)

    async def send_dm(self, user_id: str, content: str) -> bool:
        try:
            channel = await self._call("POST", "/users/@me/channels", json={"recipient_id": user_id})
            await self._call("POST", f"/channels/{channel['id']}/messages", json={"content": content, "allowed_mentions": {"parse": []}})
            return True
        except ExecutorError:
            return False  # DMs closed: the warning is still logged


@dataclass
class SimulatedExecutor:
    """Records what would have been sent. Used by demo guilds and the tests."""

    simulated: bool = True
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    fail: set[str] = field(default_factory=set)  # method names to fail, for tests

    def _record(self, name: str, **kwargs: Any) -> None:
        if name in self.fail:
            raise ExecutorError(f"Simulated failure: {name}")
        self.calls.append((name, kwargs))

    async def delete_message(self, channel_id: str, message_id: str, reason: str) -> None:
        self._record("delete_message", channel_id=channel_id, message_id=message_id)

    async def timeout_member(self, guild_id: str, user_id: str, until: datetime, reason: str) -> None:
        self._record("timeout_member", user_id=user_id, until=until)

    async def add_role(self, guild_id: str, user_id: str, role_id: str, reason: str) -> None:
        self._record("add_role", user_id=user_id, role_id=role_id)

    async def kick_member(self, guild_id: str, user_id: str, reason: str) -> None:
        self._record("kick_member", user_id=user_id)

    async def send_channel_message(self, channel_id: str, content: str | None = None, embed: dict | None = None) -> None:
        self._record("send_channel_message", channel_id=channel_id, content=content, embed=embed)

    async def send_dm(self, user_id: str, content: str) -> bool:
        self._record("send_dm", user_id=user_id)
        return True

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]
