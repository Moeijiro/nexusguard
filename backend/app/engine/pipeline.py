"""Event -> detectors -> rule engine -> action engine -> store.

    event ──► detectors (enabled modules only)
                 │ Detection
                 ▼
            rule engine ── notes, escalation, raid mode
                 │ Decision
                 ▼
            safety limits ── per-guild caps on kicks, timeouts, alerts
                 │
                 ▼
            action engine ──► ActionExecutor (Discord REST / demo recorder)
                 │ results
                 ▼
               Store ──► security_events, moderation_logs, flags

One pipeline instance serves every guild; per-guild state lives in the
WindowStore and the database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.engine import rules as rule_engine
from app.engine.actions import HANDLERS, ActionContext, ActionResult, Status
from app.engine.detectors import DETECTORS, Detection, Detector, EventType
from app.engine.events import Event, MemberJoinEvent, MessageEvent, ModerationEvent
from app.engine.ports import ActionExecutor, ExecutorError, GuildContext, Store
from app.engine.rules_schema import ActionName, Module, RaidDetectionRule
from app.engine.severity import Severity
from app.engine.state import WindowStore

logger = logging.getLogger("nexusguard.pipeline")

# Blast-radius limits per guild per minute. A misconfigured rule or a flood of
# false positives degrades to "log and alert", never to kicking half a server.
SAFETY_LIMITS: dict[ActionName, int] = {
    ActionName.KICK: 5,
    ActionName.TIMEOUT: 20,
    ActionName.RESTRICT: 60,
    ActionName.WARN: 30,
    ActionName.NOTIFY: 12,
}


@dataclass(slots=True)
class Outcome:
    guild_id: str
    detection: Detection
    severity: Severity
    results: list[ActionResult]
    notes: list[str]
    at: datetime
    simulated: bool
    event_id: int | None = None
    extra: dict = field(default_factory=dict)

    @property
    def action_summary(self) -> str:
        """What the event stream shows as "Action:"."""
        done = [r.detail for r in self.results if r.status in (Status.DONE, Status.SIMULATED)]
        return "; ".join(done) if done else "Logged"


class Pipeline:
    def __init__(
        self,
        store: Store,
        executor: ActionExecutor,
        state: WindowStore | None = None,
        detectors: list[Detector] | None = None,
    ) -> None:
        self.store = store
        self.executor = executor
        self.state = state or WindowStore()
        self.detectors = detectors if detectors is not None else DETECTORS

    async def handle(self, event: Event) -> list[Outcome]:
        ctx = self.store.guild_context(event.guild_id)
        if ctx is None:
            return []  # not a protected guild
        if ctx.raid_mode and ctx.raid_mode_until and event.at >= ctx.raid_mode_until:
            self.store.set_raid_mode(ctx.guild_id, False, None, "Raid mode expired", "NexusGuard")
            ctx.raid_mode = False

        if isinstance(event, ModerationEvent):
            return [self._record(self._moderation_outcome(event, ctx.is_demo))]
        if isinstance(event, MessageEvent) and (event.author.is_bot or event.author.is_moderator):
            return []  # moderators and bots are exempt from message rules

        outcomes: list[Outcome] = []
        for detector in self.detectors:
            if not isinstance(event, detector.handles):
                continue
            rule = ctx.rules.get(detector.module)
            if rule is None or not rule.enabled:
                continue  # a disabled module never runs, so it can't act either
            detection = detector.detect(event, rule, self.state)
            if detection is not None:
                outcomes.append(await self._act(detection, rule, ctx, event.at))

        if isinstance(event, MemberJoinEvent) and ctx.raid_mode:
            outcomes.append(await self._raid_mode_join(event, ctx))
        return outcomes

    # -- internals ---------------------------------------------------------------
    async def _act(self, detection: Detection, rule, ctx: GuildContext, at: datetime) -> Outcome:
        prior = 0
        if detection.user is not None:
            prior = self.store.recent_offenses(ctx.guild_id, detection.user.id, at - rule_engine.REPEAT_WINDOW)
        decision = rule_engine.decide(detection, rule, ctx, prior)

        if decision.raid_mode_minutes:
            until = at + timedelta(minutes=decision.raid_mode_minutes)
            self.store.set_raid_mode(ctx.guild_id, True, until, detection.summary, "NexusGuard (automatic)")
            ctx.raid_mode, ctx.raid_mode_until = True, until

        results = await self._execute(decision.actions, detection, decision.severity, ctx, at,
                                      getattr(rule, "timeout_minutes", 10))
        outcome = Outcome(ctx.guild_id, detection, decision.severity, results, decision.notes, at,
                          self.executor.simulated, extra={"escalated": decision.escalated})
        return self._record(outcome)

    async def _execute(self, planned, detection, severity, ctx, at, timeout_minutes) -> list[ActionResult]:
        results: list[ActionResult] = []
        for step in planned:
            if step.skip_reason:
                results.append(ActionResult(step.name, Status.SKIPPED, step.skip_reason))
                continue
            limit = SAFETY_LIMITS.get(step.name)
            if limit is not None:
                used = self.state.add(f"limit:{ctx.guild_id}:{step.name.value}", at, 60)
                if len(used) > limit:
                    results.append(ActionResult(step.name, Status.SUPPRESSED, f"Safety limit: {limit}/min"))
                    continue
            action_ctx = ActionContext(
                guild=ctx, detection=detection, severity=severity, executor=self.executor, at=at,
                timeout_minutes=timeout_minutes,
                done_so_far=tuple(r.detail for r in results if r.status in (Status.DONE, Status.SIMULATED)),
            )
            try:
                results.append(await HANDLERS[step.name](action_ctx))
            except ExecutorError as exc:
                logger.warning("%s failed in guild %s: %s", step.name.value, ctx.guild_id, exc)
                results.append(ActionResult(step.name, Status.FAILED, str(exc)[:200]))
        return results

    async def _raid_mode_join(self, event: MemberJoinEvent, ctx: GuildContext) -> Outcome:
        """While raid mode is on, every join is logged and (optionally) restricted."""
        rule = ctx.rules.get(Module.RAID_DETECTION)
        restrict = isinstance(rule, RaidDetectionRule) and rule.restrict_new_members
        detection = Detection(
            module=Module.RAID_DETECTION,
            type=EventType.SUSPICIOUS_JOIN,
            severity=Severity.LOW,
            summary="Joined during raid mode",
            user=event.member,
            metadata={"raid_mode": True},
        )
        planned = []
        if restrict:
            skip = None if ctx.restricted_role_id else "No restricted role configured"
            planned.append(rule_engine.PlannedAction(ActionName.RESTRICT, skip))
        results = await self._execute(planned, detection, Severity.LOW, ctx, event.at, 10)
        return self._record(Outcome(ctx.guild_id, detection, Severity.LOW, results, [], event.at, self.executor.simulated))

    def _moderation_outcome(self, event: ModerationEvent, simulated: bool) -> Outcome:
        severity = Severity.MEDIUM if event.action in {"kick", "ban"} else Severity.LOW
        by = event.moderator.name if event.moderator else "someone"
        detection = Detection(
            module=Module.PRIVILEGED_ROLES,  # attribution only; no module gates audit events
            type=EventType.MODERATION_ACTION,
            severity=severity,
            summary=f"{event.action.title()} by {by}",
            user=event.target,
            metadata={"action": event.action, "moderator": by, "reason": event.reason, **event.extra},
        )
        return Outcome(event.guild_id, detection, severity, [], [], event.at, simulated)

    def _record(self, outcome: Outcome) -> Outcome:
        outcome.event_id = self.store.record(outcome)
        return outcome
