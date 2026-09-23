"""Warn the member by DM. Closed DMs aren't an error — the event still records it."""

from __future__ import annotations

from app.engine.actions.base import ActionContext, ActionResult, ok
from app.engine.rules_schema import ActionName


async def run(ctx: ActionContext) -> ActionResult:
    member = ctx.detection.user
    assert member is not None
    text = (
        f"⚠️ Your message in **{ctx.guild.name}** was flagged by the server's protection: "
        f"{ctx.detection.summary}. Please slow down and avoid mass mentions."
    )
    delivered = await ctx.executor.send_dm(member.id, text)
    return ok(ctx, ActionName.WARN, "Warning sent" if delivered else "Warning logged (DMs closed)")
