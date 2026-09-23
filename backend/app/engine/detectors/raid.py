"""Join-spike (raid) detection.

A guild-wide sliding window over joins. Normal traffic of a few joins a minute
never gets near the threshold; a burst of accounts arriving together does.
After it fires, a cooldown of three windows stops one raid producing a string
of duplicate alerts — except for one escalation if the spike keeps growing.

Severity:
    join_threshold joins within the window                  -> high
    the spike reaches 2 x join_threshold during the cooldown -> critical (once)
"""

from __future__ import annotations

from app.engine.detectors.base import Detection, EventType
from app.engine.events import MemberJoinEvent
from app.engine.rules_schema import Module, RaidDetectionRule
from app.engine.severity import Severity
from app.engine.state import WindowStore


class RaidDetector:
    module = Module.RAID_DETECTION
    handles = (MemberJoinEvent,)

    def detect(self, event: MemberJoinEvent, rule: RaidDetectionRule, state: WindowStore) -> Detection | None:
        key = f"joins:{event.guild_id}"
        joins = state.add(key, event.at, rule.window_seconds, value=event.member.id)
        cooldown_key = f"raid:{event.guild_id}"
        escalation_key = f"raid-escalated:{event.guild_id}"
        span = max((joins[-1][0] - joins[0][0]).total_seconds(), 0.1)

        if state.cooling_down(cooldown_key, event.at):
            # Already reported. Report once more only if it has doubled.
            if len(joins) < 2 * rule.join_threshold or state.cooling_down(escalation_key, event.at):
                return None
            state.start_cooldown(escalation_key, event.at, rule.window_seconds * 3)
            severity, summary = Severity.CRITICAL, f"Raid escalating: {len(joins)} joins in {span:.0f} s"
        else:
            if len(joins) < rule.join_threshold:
                return None
            state.start_cooldown(cooldown_key, event.at, rule.window_seconds * 3)
            severity, summary = Severity.HIGH, f"{len(joins)} joins in {span:.0f} s"

        return Detection(
            module=self.module,
            type=EventType.RAID_DETECTED,
            severity=severity,
            summary=summary,
            metadata={
                "joins": len(joins),
                "window_seconds": rule.window_seconds,
                "threshold": rule.join_threshold,
                "member_ids": [member_id for _, member_id in joins][-50:],
            },
        )
