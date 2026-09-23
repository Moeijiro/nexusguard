"""Detectors and thresholds, through the real pipeline and store."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import SecurityEvent
from tests.conftest import T0, join, member, message, run, set_rule


def events() -> list[SecurityEvent]:
    with SessionLocal() as db:
        return list(db.execute(select(SecurityEvent).order_by(SecurityEvent.id)).scalars())


def test_messages_under_the_flood_threshold_are_fine(pipeline) -> None:
    for i in range(5):  # default: 6 in 5 s
        assert run(pipeline.handle(message(f"msg {i}", T0 + timedelta(seconds=i * 0.5)))) == []
    assert events() == []


def test_a_flood_fires_once_per_burst(pipeline, executor) -> None:
    outcomes = []
    for i in range(12):
        outcomes += run(pipeline.handle(message(f"msg {i}", T0 + timedelta(seconds=i * 0.3))))
    flood = [o for o in outcomes if o.detection.module.value == "message_flood"]
    assert len(flood) == 1, "a burst is one incident, not one per message"
    assert flood[0].severity.value == "high", "6 messages in 1.5 s is faster than half the window"
    assert flood[0].detection.summary.startswith("6 messages in")
    assert executor.names()[:2] == ["delete_message", "timeout_member"]


def test_a_slower_burst_is_medium(pipeline) -> None:
    for i in range(6):
        run(pipeline.handle(message(f"msg {i}", T0 + timedelta(seconds=i * 0.9))))
    assert [e.severity for e in events() if e.module == "message_flood"] == ["medium"]


def test_messages_spread_out_never_trigger_a_flood(pipeline) -> None:
    for i in range(20):
        run(pipeline.handle(message(f"msg {i}", T0 + timedelta(seconds=i * 2))))
    assert not [e for e in events() if e.module == "message_flood"]


def test_the_flood_threshold_is_configurable(pipeline) -> None:
    set_rule("message_flood", max_messages=3, window_seconds=10)
    for i in range(3):
        run(pipeline.handle(message(f"msg {i}", T0 + timedelta(seconds=i))))
    assert [e.summary.split(" ")[0] for e in events() if e.module == "message_flood"] == ["3"]


def test_repeated_identical_messages_are_spam(pipeline) -> None:
    for i, text in enumerate(["FREE NITRO here", "free nitro   HERE", "Free Nitro Here"]):
        run(pipeline.handle(message(text, T0 + timedelta(seconds=i * 4))))
    dupes = [e for e in events() if e.module == "duplicate_messages"]
    assert len(dupes) == 1 and dupes[0].type == "spam_detected"
    assert dupes[0].details["repeats"] == 3 and dupes[0].severity == "medium"


def test_repeated_links_are_high_severity(pipeline) -> None:
    for i in range(3):
        run(pipeline.handle(message("claim here https://free-nitro.example", T0 + timedelta(seconds=i * 5))))
    [dupe] = [e for e in events() if e.module == "duplicate_messages"]
    assert dupe.severity == "high" and dupe.details["has_link_or_mention"] is True


def test_everyone_ping_from_a_member_is_blocked(pipeline, executor) -> None:
    run(pipeline.handle(message("@everyone look", mentions_everyone=True)))
    [event] = events()
    assert event.type == "mass_mentions" and event.severity == "high"
    assert "delete_message" in executor.names()


def test_mention_limits(pipeline) -> None:
    run(pipeline.handle(message("hi", user_mentions=4)))           # under the limit of 5
    run(pipeline.handle(message("hi", user_mentions=5, author=member("43"))))
    run(pipeline.handle(message("hi", user_mentions=10, author=member("44"))))
    assert [(e.user_id, e.severity) for e in events()] == [("43", "medium"), ("44", "high")]


def test_moderators_and_bots_are_exempt_from_message_rules(pipeline) -> None:
    mod = member("7", "mod", is_moderator=True)
    bot = member("8", "bot", is_bot=True)
    run(pipeline.handle(message("@everyone release notes", author=mod, mentions_everyone=True)))
    for i in range(10):
        run(pipeline.handle(message(f"x{i}", T0 + timedelta(seconds=i * 0.1), author=bot)))
    assert events() == []


def test_a_join_spike_is_a_raid_and_turns_on_raid_mode(pipeline, executor) -> None:
    outcomes = []
    for i in range(10):  # default: 10 joins in 10 s
        outcomes += run(pipeline.handle(join(str(1000 + i), T0 + timedelta(seconds=i * 0.8))))
    raids = [o for o in outcomes if o.detection.type == "raid_detected"]
    assert len(raids) == 1 and raids[0].severity.value == "high"
    assert "Raid mode switched on" in " ".join(raids[0].notes)
    assert "send_channel_message" in executor.names()  # moderators alerted

    # While raid mode is on, the next joins are restricted and logged.
    later = run(pipeline.handle(join("2000", T0 + timedelta(seconds=30))))
    assert [o.detection.summary for o in later] == ["Joined during raid mode"]
    assert ("add_role", {"user_id": "2000", "role_id": "700"}) in executor.calls


def test_normal_join_traffic_is_not_a_raid(pipeline) -> None:
    for i in range(30):  # one join every 20 s
        run(pipeline.handle(join(str(i), T0 + timedelta(seconds=i * 20))))
    assert not [e for e in events() if e.type == "raid_detected"]


def test_a_growing_raid_escalates_to_critical_once(pipeline) -> None:
    set_rule("raid_detection", join_threshold=5, auto_raid_mode=False)
    outcomes = []
    for i in range(20):
        outcomes += run(pipeline.handle(join(str(i), T0 + timedelta(seconds=i * 0.2))))
    raids = [o for o in outcomes if o.detection.type == "raid_detected"]
    # 20 joins: one alert at 5, one escalation at 10, then silence — not 15 alerts.
    assert [o.severity.value for o in raids] == ["high", "critical"]
    assert raids[1].detection.summary.startswith("Raid escalating: 10 joins")


def test_account_age_is_opt_in_and_only_flags(pipeline, executor) -> None:
    run(pipeline.handle(join("1", T0, age=timedelta(minutes=30))))
    assert events() == [], "the module is off by default"

    set_rule("account_age", enabled=True, min_account_age_hours=24)
    run(pipeline.handle(join("2", T0, age=timedelta(minutes=30))))
    run(pipeline.handle(join("3", T0, age=timedelta(hours=5))))
    run(pipeline.handle(join("4", T0, age=timedelta(days=10))))
    assert [(e.user_id, e.type, e.severity, e.action_taken) for e in events()] == [
        ("2", "suspicious_join", "medium", "Flagged for review"),
        ("3", "suspicious_join", "low", "Flagged for review"),
    ]
    assert executor.calls == [], "flagging never touches Discord"


def test_admin_role_grants_are_critical(pipeline) -> None:
    from app.engine.events import RoleGrantEvent

    run(pipeline.handle(RoleGrantEvent("111111111111111111", member("9", "newbie"), "55", "Admin", 1 << 3, T0,
                                       granted_by=member("1", "owner"))))
    run(pipeline.handle(RoleGrantEvent("111111111111111111", member("9", "newbie"), "56", "Regular", 1 << 11, T0)))
    [event] = events()
    assert event.type == "role_change" and event.severity == "critical"
    assert event.details["permissions"] == ["ADMINISTRATOR"]
