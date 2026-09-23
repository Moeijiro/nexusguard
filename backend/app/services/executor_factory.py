"""Pick the executor for a guild: simulated for demo guilds, Discord REST otherwise."""

from __future__ import annotations

from app.core.config import settings
from app.core.errors import APIError
from app.engine.ports import ActionExecutor
from app.models import Guild
from app.services.executors import RestExecutor, SimulatedExecutor


def executor_for(guild: Guild) -> ActionExecutor:
    if guild.is_demo:
        return SimulatedExecutor()
    if not settings.discord_bot_token:
        raise APIError("bot_not_configured", "DISCORD_BOT_TOKEN isn't set, so actions can't reach Discord.", 503)
    return RestExecutor()
