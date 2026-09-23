"""Assign the guild's restricted role (e.g. read-only, verification channel only)."""

from __future__ import annotations

from app.engine.actions.base import ActionContext, ActionResult, ok
from app.engine.rules_schema import ActionName


async def run(ctx: ActionContext) -> ActionResult:
    member = ctx.detection.user
    assert member is not None and ctx.guild.restricted_role_id
    await ctx.executor.add_role(ctx.guild.guild_id, member.id, ctx.guild.restricted_role_id, ctx.reason)
    return ok(ctx, ActionName.RESTRICT, "Restricted role assigned")
