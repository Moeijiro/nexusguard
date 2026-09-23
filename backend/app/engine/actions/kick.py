"""Kick the member. Only ever runs when a rule was explicitly set to kick."""

from __future__ import annotations

from app.engine.actions.base import ActionContext, ActionResult, ok
from app.engine.rules_schema import ActionName


async def run(ctx: ActionContext) -> ActionResult:
    member = ctx.detection.user
    assert member is not None
    await ctx.executor.kick_member(ctx.guild.guild_id, member.id, ctx.reason)
    return ok(ctx, ActionName.KICK, "Member kicked")
