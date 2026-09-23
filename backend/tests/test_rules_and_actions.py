"""Rule engine decisions, the action engine, safety limits and storage."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.engine import rules as rule_engine
from app.engine.detectors.base import Detection
from app.engine.ports import GuildContext
from app.engine.rules_schema import ActionName, MassMentionsRule, Module, default_rules, parse_rule
from app.engine.severity import Severity
from app.models import Flag, Guild, ModerationLog, SecurityEvent
from tests.conftest import GUILD, T0, join, member, message, run, set_rule


def ctx(**overrides) -> GuildContext:  # noqa: ANN003
    base = dict(guild_id=GUILD, name="T", rules=default_rules(), alert_channel_id="900", restricted_role_id="700")
    return GuildContext(**{**base, **overrides})


def detection(module: Module = Module.MASS_MENTIONS, severity: Severity = Severity.MEDIUM, message_id: str | None = "1") -> Detection:
    return Detection(module=module, type="mass_mentions", severity=severity, summary="x", user=member(), message_id=message_id)


def names(decision) -> list[str]:  # noqa: ANN001
    return [(a.name.value if not a.skip_reason else f"{a.name.value}:skipped") for a in decision.actions]


# --- rule disabled state ---------------------------------------------------------------
def test_a_disabled_module_never_runs_or_acts(pipeline, executor) -> None:
    set_rule("mass_mentions", enabled=False)
    run(pipeline.handle(message("@everyone", mentions_everyone=True, user_mentions=30)))
    assert executor.calls == []
    with SessionLocal() as db:
        assert db.query(SecurityEvent).count() == 0


def test_disabling_one_module_leaves_the_others_on(pipeline) -> None:
    set_rule("message_flood", enabled=False)
    for i in range(8):
        run(pipeline.handle(message("same text", T0 + timedelta(seconds=i))))
    with SessionLocal() as db:
        modules = {e.module for e in db.query(SecurityEvent)}
    assert modules == {"duplicate_messages"}


# --- action selection -------------------------------------------------------------------
def test_actions_follow_the_rule_in_a_fixed_order() -> None:
    rule = MassMentionsRule(actions=[ActionName.NOTIFY, ActionName.WARN, ActionName.DELETE_MESSAGE])
    assert names(rule_engine.decide(detection(), rule, ctx())) == ["delete_message", "warn", "notify"]


def test_repeat_offenders_are_escalated_with_a_timeout() -> None:
    rule = MassMentionsRule(actions=[ActionName.DELETE_MESSAGE, ActionName.WARN])
    decision = rule_engine.decide(detection(), rule, ctx(), prior_offenses=2)
    assert decision.escalated and decision.severity == Severity.HIGH
    assert names(decision) == ["delete_message", "warn", "timeout"]
    assert any("Repeat offender" in note for note in decision.notes)


def test_kick_supersedes_timeout() -> None:
    rule = MassMentionsRule(actions=[ActionName.TIMEOUT, ActionName.KICK])
    decision = rule_engine.decide(detection(), rule, ctx())
    assert names(decision) == ["kick"] and "Kick supersedes timeout" in decision.notes


def test_missing_prerequisites_are_skipped_with_a_reason() -> None:
    rule = parse_rule("account_age", {"actions": ["restrict", "notify"]})
    decision = rule_engine.decide(detection(Module.ACCOUNT_AGE, message_id=None), rule, ctx(alert_channel_id=None, restricted_role_id=None))
    assert names(decision) == ["restrict:skipped", "notify:skipped"]
    assert [a.skip_reason for a in decision.actions] == ["No restricted role configured", "No moderator alert channel configured"]


def test_critical_events_always_alert_moderators() -> None:
    rule = parse_rule("privileged_roles", {"actions": []})
    decision = rule_engine.decide(detection(Module.PRIVILEGED_ROLES, Severity.CRITICAL, None), rule, ctx())
    assert names(decision) == ["notify"]


@pytest.mark.parametrize("module", [m.value for m in Module])
def test_no_module_can_ban_and_defaults_never_kick(module: str) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        parse_rule(module, {"actions": ["ban"]})
    assert ActionName.KICK not in default_rules()[Module(module)].actions


def test_raid_detection_cannot_be_configured_to_kick() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="raid_detection can't use: kick"):
        parse_rule("raid_detection", {"actions": ["kick"]})


# --- action engine and safety limits ----------------------------------------------------------
def test_safety_limits_cap_kicks_per_minute(pipeline, executor) -> None:
    set_rule("mass_mentions", actions=["delete_message", "kick"])
    for i in range(8):
        run(pipeline.handle(message("@everyone", T0 + timedelta(seconds=i), author=member(str(100 + i)), mentions_everyone=True)))
    assert executor.names().count("kick_member") == 5
    with SessionLocal() as db:
        suppressed = [a for e in db.query(SecurityEvent) for a in e.actions if a["status"] == "suppressed"]
    assert len(suppressed) == 3 and suppressed[0]["detail"] == "Safety limit: 5/min"


def test_a_discord_failure_is_recorded_not_raised(pipeline, executor) -> None:
    executor.fail = {"timeout_member"}
    for i in range(6):
        run(pipeline.handle(message(f"m{i}", T0 + timedelta(seconds=i * 0.2))))
    with SessionLocal() as db:
        event = db.query(SecurityEvent).filter_by(module="message_flood").one()
        log = db.query(ModerationLog).one()
    assert [a["status"] for a in event.actions] == ["simulated", "failed"]
    assert event.action_taken == "Message deleted"
    assert log.action == "timeout" and log.status == "failed"


# --- event storage ------------------------------------------------------------------------------
def test_events_store_guild_user_type_severity_time_metadata_and_action(pipeline) -> None:
    run(pipeline.handle(message("@everyone free stuff", T0, mentions_everyone=True)))
    with SessionLocal() as db:
        event = db.execute(select(SecurityEvent)).scalar_one()
        guild = db.get(Guild, event.guild_id)
        logs = db.query(ModerationLog).all()
    assert guild.discord_id == GUILD
    assert (event.user_id, event.username, event.type, event.severity) == ("42", "spammer", "mass_mentions", "high")
    assert event.created_at == T0
    assert event.details["everyone"] is True and event.details["excerpt"] == "@everyone free stuff"
    assert event.action_taken == "Message deleted; Warning sent"
    assert event.simulated is True
    assert [(log.action, log.source, log.moderator_name) for log in logs] == [("warn", "automatic", "NexusGuard")]


def test_flag_actions_create_review_items(pipeline) -> None:
    set_rule("account_age", enabled=True)
    run(pipeline.handle(join("77", T0, age=timedelta(hours=2))))
    with SessionLocal() as db:
        flag = db.query(Flag).one()
    assert (flag.user_id, flag.status, flag.severity) == ("77", "open", "low")


def test_unknown_guilds_are_ignored(store, executor) -> None:
    from app.engine.pipeline import Pipeline

    stray = message()
    object.__setattr__(stray, "guild_id", "999")
    assert run(Pipeline(store, executor).handle(stray)) == []
