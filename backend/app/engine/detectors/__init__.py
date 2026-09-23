"""One detector per protection module."""

from app.engine.detectors.account_age import AccountAgeDetector
from app.engine.detectors.base import Detection, Detector, EventType
from app.engine.detectors.mentions import MassMentionsDetector
from app.engine.detectors.raid import RaidDetector
from app.engine.detectors.roles import PrivilegedRoleDetector
from app.engine.detectors.spam import DuplicateMessagesDetector, MessageFloodDetector

DETECTORS: list[Detector] = [
    MessageFloodDetector(),
    DuplicateMessagesDetector(),
    MassMentionsDetector(),
    RaidDetector(),
    AccountAgeDetector(),
    PrivilegedRoleDetector(),
]

__all__ = ["DETECTORS", "Detection", "Detector", "EventType"]
