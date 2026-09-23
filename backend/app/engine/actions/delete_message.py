"""Delete the message that triggered the detection."""

from __future__ import annotations

from app.engine.actions.base import ActionContext, ActionResult, ok
from app.engine.rules_schema import ActionName


async def run(ctx: ActionContext) -> ActionResult:
    d = ctx.detection
    await ctx.executor.delete_message(d.channel_id or "", d.message_id or "", ctx.reason)
    return ok(ctx, ActionName.DELETE_MESSAGE, "Message deleted")
