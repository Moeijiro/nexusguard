"""Mass-mention protection.

Severity:
    user + role mentions >= max_mentions        -> medium
    user + role mentions >= 2 x max_mentions    -> high
    @everyone / @here from a non-moderator      -> high (when block_everyone is on)
"""

from __future__ import annotations

from app.engine.detectors.base import Detection, EventType
from app.engine.events import MessageEvent
from app.engine.rules_schema import MassMentionsRule, Module
from app.engine.severity import Severity
from app.engine.state import WindowStore


class MassMentionsDetector:
    module = Module.MASS_MENTIONS
    handles = (MessageEvent,)

    def detect(self, event: MessageEvent, rule: MassMentionsRule, state: WindowStore) -> Detection | None:
        mentions = event.user_mentions + event.role_mentions
        everyone = rule.block_everyone and event.mentions_everyone
        if mentions < rule.max_mentions and not everyone:
            return None

        severity = Severity.MEDIUM
        if everyone or mentions >= 2 * rule.max_mentions:
            severity = Severity.HIGH
        parts = []
        if everyone:
            parts.append("@everyone/@here")
        if mentions:
            parts.append(f"{mentions} mentions")
        return Detection(
            module=self.module,
            type=EventType.MASS_MENTIONS,
            severity=severity,
            summary=" + ".join(parts) + " in one message",
            user=event.author,
            channel_id=event.channel_id,
            message_id=event.message_id,
            metadata={"mentions": mentions, "everyone": event.mentions_everyone, "limit": rule.max_mentions,
                      "excerpt": event.content[:120]},
        )
