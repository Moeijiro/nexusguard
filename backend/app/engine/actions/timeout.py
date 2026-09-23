"""Time the member out (Discord's native communication timeout)."""

from __future__ import annotations

from datetime import timedelta

from app.engine.actions.base import ActionContext, ActionResult, ok
from app.engine.rules_schema import ActionName


async def run(ctx: ActionContext) -> ActionResult:
    member = ctx.detection.user
    assert member is not None
    until = ctx.at + timedelta(minutes=ctx.timeout_minutes)
    await ctx.executor.timeout_member(ctx.guild.guild_id, member.id, until, ctx.reason)
    return ok(ctx, ActionName.TIMEOUT, f"Timed out for {ctx.timeout_minutes} min")
