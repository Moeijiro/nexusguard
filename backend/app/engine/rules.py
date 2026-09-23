"""The rule engine: turns a detection into a plan of actions.

Every choice here is deterministic and explainable — each adjustment adds a
note that is stored with the event, so "why did NexusGuard do that?" always
has an answer on the dashboard.

1. Start from the actions the guild configured for the module.
2. Drop what can't apply (no message to delete, no restricted role or alert
   channel configured) — with a note, not silently.
3. Repeat offenders (2+ medium-or-worse events in 10 minutes) are escalated:
   severity goes up one level and a timeout is added to message rules.
4. Kick supersedes timeout; notify always runs last so the alert can say
   what was done.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from app.engine.detectors.base import Detection
from app.engine.ports import GuildContext
from app.engine.rules_schema import MESSAGE_ACTIONS, ActionName, Module, RaidDetectionRule, Rule
from app.engine.severity import Severity

REPEAT_WINDOW = timedelta(minutes=10)
REPEAT_THRESHOLD = 2
MESSAGE_MODULES = {Module.MESSAGE_FLOOD, Module.DUPLICATE_MESSAGES, Module.MASS_MENTIONS}

ORDER = [
    ActionName.DELETE_MESSAGE,
    ActionName.WARN,
    ActionName.TIMEOUT,
    ActionName.RESTRICT,
    ActionName.KICK,
    ActionName.FLAG,
    ActionName.NOTIFY,
]


@dataclass(slots=True)
class PlannedAction:
    name: ActionName
    skip_reason: str | None = None


@dataclass(slots=True)
class Decision:
    severity: Severity
    actions: list[PlannedAction]
    notes: list[str] = field(default_factory=list)
    escalated: bool = False
    raid_mode_minutes: int | None = None  # set when this detection should switch raid mode on


def decide(detection: Detection, rule: Rule, ctx: GuildContext, prior_offenses: int = 0) -> Decision:
    severity = detection.severity
    wanted = list(rule.actions)
    notes: list[str] = []
    escalated = False

    if detection.module in MESSAGE_MODULES and prior_offenses >= REPEAT_THRESHOLD:
        escalated = True
        severity = severity.bump()
        notes.append(f"Repeat offender ({prior_offenses} recent incidents): severity raised to {severity.value}")
        if ActionName.TIMEOUT not in wanted and ActionName.KICK not in wanted:
            wanted.append(ActionName.TIMEOUT)
            notes.append("Timeout added for a repeat offence")

    if ActionName.KICK in wanted and ActionName.TIMEOUT in wanted:
        wanted.remove(ActionName.TIMEOUT)
        notes.append("Kick supersedes timeout")

    if severity == Severity.CRITICAL and ActionName.NOTIFY not in wanted:
        wanted.append(ActionName.NOTIFY)
        notes.append("Critical severity: moderators are always alerted")

    planned: list[PlannedAction] = []
    for name in sorted(set(wanted), key=ORDER.index):
        skip = None
        if name == ActionName.DELETE_MESSAGE and not detection.message_id:
            skip = "No message to delete"
        elif name in MESSAGE_ACTIONS - {ActionName.NOTIFY, ActionName.FLAG} and detection.user is None:
            skip = "No member to act on"
        elif name == ActionName.RESTRICT and not ctx.restricted_role_id:
            skip = "No restricted role configured"
        elif name == ActionName.NOTIFY and not ctx.alert_channel_id:
            skip = "No moderator alert channel configured"
        planned.append(PlannedAction(name, skip))

    decision = Decision(severity=severity, actions=planned, notes=notes, escalated=escalated)
    if isinstance(rule, RaidDetectionRule) and rule.auto_raid_mode and not ctx.raid_mode:
        decision.raid_mode_minutes = rule.raid_mode_minutes
        decision.notes.append(f"Raid mode switched on for {rule.raid_mode_minutes} minutes")
    return decision
