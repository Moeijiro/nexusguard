"""Optional account-age check on join.

This only ever *flags* or restricts — a new account is a reason to look, not
proof of bad intent. The module is off by default.

Severity:
    younger than min_account_age_hours  -> low
    younger than one hour               -> medium
"""

from __future__ import annotations

from app.engine.detectors.base import Detection, EventType
from app.engine.events import MemberJoinEvent
from app.engine.rules_schema import AccountAgeRule, Module
from app.engine.severity import Severity
from app.engine.state import WindowStore


def _age_label(hours: float) -> str:
    if hours < 1:
        return f"{max(int(hours * 60), 1)} min"
    if hours < 48:
        return f"{int(hours)} h"
    return f"{int(hours // 24)} days"


class AccountAgeDetector:
    module = Module.ACCOUNT_AGE
    handles = (MemberJoinEvent,)

    def detect(self, event: MemberJoinEvent, rule: AccountAgeRule, state: WindowStore) -> Detection | None:
        created = event.member.account_created_at
        if created is None or event.member.is_bot:
            return None
        hours = (event.at - created).total_seconds() / 3600
        if hours >= rule.min_account_age_hours:
            return None
        return Detection(
            module=self.module,
            type=EventType.SUSPICIOUS_JOIN,
            severity=Severity.MEDIUM if hours < 1 else Severity.LOW,
            summary=f"Account created {_age_label(hours)} ago",
            user=event.member,
            metadata={"account_age_hours": round(hours, 2), "threshold_hours": rule.min_account_age_hours},
        )
