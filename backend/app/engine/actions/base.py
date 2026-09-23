"""Shared pieces of the action engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.engine.detectors.base import Detection
from app.engine.ports import ActionExecutor, GuildContext
from app.engine.rules_schema import ActionName
from app.engine.severity import Severity


class Status(StrEnum):
    DONE = "done"
    SIMULATED = "simulated"   # demo mode: recorded, nothing sent to Discord
    SKIPPED = "skipped"       # prerequisite missing (no role, no channel, no message)
    SUPPRESSED = "suppressed" # safety limit reached
    FAILED = "failed"         # Discord refused (permissions, hierarchy, member gone)


@dataclass(slots=True)
class ActionContext:
    guild: GuildContext
    detection: Detection
    severity: Severity
    executor: ActionExecutor
    at: datetime
    timeout_minutes: int = 10
    done_so_far: tuple[str, ...] = ()

    @property
    def reason(self) -> str:
        return f"NexusGuard: {self.detection.summary}"[:500]


@dataclass(slots=True)
class ActionResult:
    name: ActionName
    status: Status
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"action": self.name.value, "status": self.status.value, "detail": self.detail}


def ok(ctx: ActionContext, name: ActionName, detail: str) -> ActionResult:
    return ActionResult(name, Status.SIMULATED if ctx.executor.simulated else Status.DONE, detail)
