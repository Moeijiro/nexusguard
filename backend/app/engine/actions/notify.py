"""Alert moderators in the configured channel with an embed."""

from __future__ import annotations

from app.engine.actions.base import ActionContext, ActionResult, ok
from app.engine.rules_schema import ActionName
from app.engine.severity import Severity

TITLES = {
    "spam_detected": "Spam detected",
    "raid_detected": "Join spike detected",
    "mass_mentions": "Mass mention blocked",
    "suspicious_join": "Suspicious join",
    "role_change": "Privileged role granted",
    "moderation_action": "Moderation action",
}
COLOURS = {Severity.LOW: 0x64748B, Severity.MEDIUM: 0xF5A524, Severity.HIGH: 0xF97316, Severity.CRITICAL: 0xEF4444}


def build_embed(ctx: ActionContext) -> dict:
    d = ctx.detection
    fields = [{"name": "Severity", "value": ctx.severity.value.title(), "inline": True}]
    if d.user:
        fields.append({"name": "Member", "value": f"<@{d.user.id}> ({d.user.name})", "inline": True})
    if d.channel_id:
        fields.append({"name": "Channel", "value": f"<#{d.channel_id}>", "inline": True})
    fields.append({"name": "Action", "value": ", ".join(ctx.done_so_far) or "Logged", "inline": False})
    return {
        "title": TITLES.get(d.type, "Security event"),
        "description": d.summary,
        "color": COLOURS[ctx.severity],
        "fields": fields,
        "footer": {"text": "NexusGuard"},
        "timestamp": ctx.at.isoformat(),
    }


async def run(ctx: ActionContext) -> ActionResult:
    assert ctx.guild.alert_channel_id
    await ctx.executor.send_channel_message(ctx.guild.alert_channel_id, embed=build_embed(ctx))
    return ok(ctx, ActionName.NOTIFY, "Moderators notified")
