"""Four rule-based severity levels. Each detector documents how it picks one."""

from __future__ import annotations

from enum import StrEnum


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return ORDER.index(self)

    def bump(self) -> "Severity":
        return ORDER[min(self.rank + 1, len(ORDER) - 1)]


ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
