"""What a detector returns, and the shape every detector has."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.engine.events import Event, Member
from app.engine.rules_schema import Module, Rule
from app.engine.severity import Severity
from app.engine.state import WindowStore


class EventType:
    """The security event types stored and shown on the dashboard."""

    SPAM_DETECTED = "spam_detected"
    RAID_DETECTED = "raid_detected"
    MASS_MENTIONS = "mass_mentions"
    SUSPICIOUS_JOIN = "suspicious_join"
    ROLE_CHANGE = "role_change"
    MODERATION_ACTION = "moderation_action"


@dataclass(slots=True)
class Detection:
    module: Module
    type: str
    severity: Severity
    summary: str                      # "7 messages in 5 s" — shown in the event stream
    user: Member | None = None
    channel_id: str | None = None
    message_id: str | None = None     # set when the offending message can be deleted
    metadata: dict[str, Any] = field(default_factory=dict)


class Detector(Protocol):
    module: Module
    handles: tuple[type, ...]

    def detect(self, event: Event, rule: Rule, state: WindowStore) -> Detection | None: ...
