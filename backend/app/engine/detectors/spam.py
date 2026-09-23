"""Message flood and duplicate-message detection.

Both are sliding windows per member. When one fires, the member's window is
cleared and a cooldown starts, so one burst becomes one security event rather
than one per message.

Both fire the moment a threshold is reached, so severity comes from *what*
the burst looks like, not from overshooting the threshold:

    flood       max_messages within the window             -> medium
                ...and within half the window (scripted)    -> high
    duplicates  max_repeats of the same message             -> medium
                ...and the message has a link or a mention  -> high (scam pattern)
"""

from __future__ import annotations

import hashlib
import re

from app.engine.detectors.base import Detection, EventType
from app.engine.events import MessageEvent
from app.engine.rules_schema import DuplicateMessagesRule, MessageFloodRule, Module
from app.engine.severity import Severity
from app.engine.state import WindowStore

_WHITESPACE = re.compile(r"\s+")
_LINK_OR_MENTION = re.compile(r"https?://|discord\.gg/|<@[!&]?\d+>", re.IGNORECASE)


def _fingerprint(content: str) -> str:
    """Case- and whitespace-insensitive, so "BUY NOW" and "buy  now" count as repeats."""
    normalised = _WHITESPACE.sub(" ", content.strip().lower())
    return hashlib.sha1(normalised.encode()).hexdigest()[:16]


class MessageFloodDetector:
    module = Module.MESSAGE_FLOOD
    handles = (MessageEvent,)

    def detect(self, event: MessageEvent, rule: MessageFloodRule, state: WindowStore) -> Detection | None:
        key = f"flood:{event.guild_id}:{event.author.id}"
        if state.cooling_down(key, event.at):
            return None
        hits = state.add(key, event.at, rule.window_seconds)
        count = len(hits)
        if count < rule.max_messages:
            return None
        state.clear(key)
        state.start_cooldown(key, event.at, rule.window_seconds)
        span = max((hits[-1][0] - hits[0][0]).total_seconds(), 0.1)
        severity = Severity.HIGH if span <= rule.window_seconds / 2 else Severity.MEDIUM
        return Detection(
            module=self.module,
            type=EventType.SPAM_DETECTED,
            severity=severity,
            summary=f"{count} messages in {span:.1f} s",
            user=event.author,
            channel_id=event.channel_id,
            message_id=event.message_id,
            metadata={"messages": count, "window_seconds": rule.window_seconds, "threshold": rule.max_messages,
                      "kind": "flood"},
        )


class DuplicateMessagesDetector:
    module = Module.DUPLICATE_MESSAGES
    handles = (MessageEvent,)

    def detect(self, event: MessageEvent, rule: DuplicateMessagesRule, state: WindowStore) -> Detection | None:
        if not event.content.strip():
            return None  # attachments or embeds only
        fingerprint = _fingerprint(event.content)
        key = f"dupe:{event.guild_id}:{event.author.id}:{fingerprint}"
        if state.cooling_down(key, event.at):
            return None
        repeats = len(state.add(key, event.at, rule.window_seconds))
        if repeats < rule.max_repeats:
            return None
        state.clear(key)
        state.start_cooldown(key, event.at, rule.window_seconds)
        has_link = bool(_LINK_OR_MENTION.search(event.content))
        severity = Severity.HIGH if has_link else Severity.MEDIUM
        return Detection(
            module=self.module,
            type=EventType.SPAM_DETECTED,
            severity=severity,
            summary=f"Same message {repeats}× in {rule.window_seconds} s",
            user=event.author,
            channel_id=event.channel_id,
            message_id=event.message_id,
            metadata={"repeats": repeats, "window_seconds": rule.window_seconds, "threshold": rule.max_repeats,
                      "kind": "duplicate", "has_link_or_mention": has_link, "excerpt": event.content[:120]},
        )
