"""The NexusGuard bot: gateway events in, pipeline out.

Intents:
    guilds            channels, roles, joins/leaves of the bot itself
    members           (privileged) member joins and role changes
    messages          message events in guilds
    message_content   (privileged) the text the spam detectors look at
    moderation        audit-log events, to attribute manual moderation

Actions go through the same REST executor the dashboard uses, so there is one
code path for "do something in Discord", with one rate-limit policy.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import defaultdict
from datetime import datetime, timezone

import discord
from discord import app_commands

from app.bot import adapter, commands, sync
from app.db.session import SessionLocal, init_db
from app.engine.pipeline import Pipeline
from app.models import Guild
from app.services import activity
from app.services.executors import RestExecutor
from app.services.store import SqlStore

logger = logging.getLogger("nexusguard.bot")
FLUSH_SECONDS = 30


def intents() -> discord.Intents:
    value = discord.Intents.none()
    value.guilds = True
    value.members = True
    value.guild_messages = True
    value.message_content = True
    value.moderation = True
    return value


class NexusGuardBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=intents(), allowed_mentions=discord.AllowedMentions.none())
        self.tree = app_commands.CommandTree(self)
        self.store = SqlStore(SessionLocal)
        self.executor = RestExecutor()
        self.pipeline = Pipeline(self.store, self.executor)
        # (guild_id, hour) -> [messages, joins, leaves]; flushed every FLUSH_SECONDS.
        self._counts: dict[tuple[str, datetime], list[int]] = defaultdict(lambda: [0, 0, 0])
        self._flusher: asyncio.Task | None = None
        commands.register(self)

    async def setup_hook(self) -> None:
        init_db()
        await self.tree.sync()
        self._flusher = asyncio.create_task(self._flush_forever())

    async def close(self) -> None:
        if self._flusher:
            self._flusher.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._flusher
        self._flush()
        await super().close()

    # --- lifecycle -------------------------------------------------------------------
    async def on_ready(self) -> None:
        for guild in self.guilds:
            sync.sync_guild(guild)
        logger.info("Protecting %d guild(s) as %s", len(self.guilds), self.user)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        sync.sync_guild(guild)

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        sync.mark_removed(guild.id)

    async def on_guild_channel_create(self, channel) -> None:  # noqa: ANN001
        sync.sync_guild(channel.guild)

    on_guild_channel_delete = on_guild_channel_update = on_guild_channel_create

    async def on_guild_role_create(self, role: discord.Role) -> None:
        sync.sync_guild(role.guild)

    on_guild_role_delete = on_guild_role_update = on_guild_role_create

    # --- protected events --------------------------------------------------------------
    async def on_message(self, message: discord.Message) -> None:
        event = adapter.message_event(message)
        if event is None:
            return
        self._count(event.guild_id, event.at, 0)
        await self._run(event)

    async def on_member_join(self, member: discord.Member) -> None:
        now = datetime.now(timezone.utc)
        self._count(str(member.guild.id), now, 1)
        await self._run(adapter.join_event(member, now))

    async def on_member_remove(self, member: discord.Member) -> None:
        self._count(str(member.guild.id), datetime.now(timezone.utc), 2)

    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.roles == after.roles:
            return
        for event in adapter.role_grants(before, after, datetime.now(timezone.utc)):
            await self._run(event)

    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        event = adapter.moderation_event(entry, self.user.id if self.user else 0)
        if event is not None:
            await self._run(event)

    # --- internals ----------------------------------------------------------------------------
    async def _run(self, event) -> None:  # noqa: ANN001
        try:
            await self.pipeline.handle(event)
        except Exception:  # noqa: BLE001 — one bad event must not stop protection
            logger.exception("Pipeline failed for %s in guild %s", type(event).__name__, event.guild_id)

    def _count(self, guild_id: str, at: datetime, index: int) -> None:
        self._counts[(guild_id, at.replace(minute=0, second=0, microsecond=0))][index] += 1

    def _flush(self) -> None:
        if not self._counts:
            return
        counts, self._counts = self._counts, defaultdict(lambda: [0, 0, 0])
        with SessionLocal() as db:
            ids = {g.discord_id: g.id for g in db.query(Guild).filter(Guild.discord_id.in_({k[0] for k in counts}))}
            for (guild_id, hour), (messages, joins, leaves) in counts.items():
                if guild_id in ids:
                    activity.bump(db, ids[guild_id], hour, messages=messages, joins=joins, leaves=leaves)
            db.commit()

    async def _flush_forever(self) -> None:
        while True:
            await asyncio.sleep(FLUSH_SECONDS)
            try:
                self._flush()
            except Exception:  # noqa: BLE001
                logger.exception("Activity flush failed")
