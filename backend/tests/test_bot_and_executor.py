"""The discord.py adapter and the REST executor, with no network."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

import httpx
import pytest

from app.bot import adapter
from app.engine.ports import ExecutorError
from app.services.executors import RestExecutor
from tests.conftest import run

NOW = datetime(2026, 9, 23, 22, 41, tzinfo=timezone.utc)


def perms(**flags) -> NS:  # noqa: ANN003
    base = dict(administrator=False, manage_guild=False, moderate_members=False, manage_messages=False)
    return NS(**{**base, **flags})


def discord_member(member_id: int = 42, *, bot: bool = False, **perm_flags) -> NS:  # noqa: ANN003
    return NS(id=member_id, name=f"user{member_id}", bot=bot, created_at=NOW - timedelta(days=3),
              guild_permissions=perms(**perm_flags), guild=NS(id=1, owner_id=1))


def discord_message(content: str, author: NS | None = None, **kw) -> NS:  # noqa: ANN003
    base = dict(guild=NS(id=1), webhook_id=None, channel=NS(id=5), id=99, author=author or discord_member(),
                content=content, created_at=NOW, mentions=[], role_mentions=[], mention_everyone=False)
    return NS(**{**base, **kw})


# --- adapter -------------------------------------------------------------------------------
def test_messages_become_engine_events() -> None:
    mentions = [NS(id=i, bot=False) for i in range(6)] + [NS(id=3, bot=False), NS(id=77, bot=True)]
    event = adapter.message_event(discord_message("hey all", mentions=mentions, role_mentions=[NS(id=1)]))
    assert (event.guild_id, event.channel_id, event.message_id) == ("1", "5", "99")
    assert event.user_mentions == 6, "unique humans only"
    assert event.role_mentions == 1 and event.at == NOW


def test_an_everyone_attempt_counts_even_without_the_ping() -> None:
    assert adapter.message_event(discord_message("@everyone free nitro")).mentions_everyone is True
    assert adapter.message_event(discord_message("email me at team@everyone.dev")).mentions_everyone is False


def test_dms_and_webhooks_are_ignored() -> None:
    assert adapter.message_event(discord_message("x", guild=None)) is None
    assert adapter.message_event(discord_message("x", webhook_id=123)) is None


@pytest.mark.parametrize("flags,expected", [({}, False), ({"manage_messages": True}, True),
                                             ({"moderate_members": True}, True), ({"administrator": True}, True)])
def test_moderators_are_recognised_by_permission(flags: dict, expected: bool) -> None:
    assert adapter.is_moderator(discord_member(**flags)) is expected


def test_the_owner_is_a_moderator() -> None:
    assert adapter.is_moderator(discord_member(1)) is True


def test_role_grants_are_the_added_roles_only() -> None:
    admin = NS(id=10, name="Admin", permissions=NS(value=1 << 3))
    member_role = NS(id=11, name="Member", permissions=NS(value=0))
    before = NS(roles=[member_role])
    after = NS(roles=[member_role, admin], guild=NS(id=1), id=42, name="x", bot=False,
               guild_permissions=perms(), created_at=NOW)
    [grant] = adapter.role_grants(before, after, NOW)
    assert (grant.role_name, grant.role_permissions) == ("Admin", 8)


def test_the_bots_own_audit_entries_are_skipped() -> None:
    entry = NS(user_id=500, user=NS(id=500, name="NexusGuard"), target=NS(id=42, name="spammer"),
               action=NS(name="kick"), reason="x", guild=NS(id=1), created_at=NOW, after=None)
    assert adapter.moderation_event(entry, bot_user_id=500) is None
    entry.user_id, entry.user = 600, NS(id=600, name="mod.ellis")
    event = adapter.moderation_event(entry, bot_user_id=500)
    assert (event.action, event.moderator.name, event.target.name) == ("kick", "mod.ellis", "spammer")


def test_a_manual_timeout_is_read_from_member_update_entries() -> None:
    entry = NS(user_id=600, user=NS(id=600, name="mod"), target=NS(id=42, name="t"), action=NS(name="member_update"),
               reason=None, guild=NS(id=1), created_at=NOW, after=NS(timed_out_until=NOW + timedelta(hours=1)))
    assert adapter.moderation_event(entry, 500).action == "timeout"
    entry.after = NS(timed_out_until=None)  # a nickname change, say
    assert adapter.moderation_event(entry, 500) is None


# --- REST executor ----------------------------------------------------------------------------------
def recording(responses: list[httpx.Response]) -> tuple[RestExecutor, list[httpx.Request]]:
    seen: list[httpx.Request] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return queue.pop(0) if queue else httpx.Response(204)

    return RestExecutor(token="bot-token", transport=httpx.MockTransport(handler)), seen


def test_actions_are_the_right_discord_calls() -> None:
    executor, seen = recording([])
    until = NOW + timedelta(minutes=10)
    run(executor.delete_message("5", "99", "NexusGuard: 7 messages in 2.0 s"))
    run(executor.timeout_member("1", "42", until, "NexusGuard: spam"))
    run(executor.add_role("1", "42", "700", "raid mode"))
    run(executor.kick_member("1", "42", "kick"))
    assert [(r.method, r.url.path) for r in seen] == [
        ("DELETE", "/api/v10/channels/5/messages/99"),
        ("PATCH", "/api/v10/guilds/1/members/42"),
        ("PUT", "/api/v10/guilds/1/members/42/roles/700"),
        ("DELETE", "/api/v10/guilds/1/members/42"),
    ]
    assert json.loads(seen[1].content) == {"communication_disabled_until": until.isoformat()}
    assert seen[0].headers["Authorization"] == "Bot bot-token"
    assert seen[0].headers["X-Audit-Log-Reason"] == "NexusGuard%3A 7 messages in 2.0 s"


def test_alerts_never_ping_anyone() -> None:
    executor, seen = recording([httpx.Response(200, json={"id": "1"})])
    run(executor.send_channel_message("900", embed={"title": "Join spike detected"}))
    assert json.loads(seen[0].content)["allowed_mentions"] == {"parse": []}


def test_discord_rate_limits_are_retried() -> None:
    executor, seen = recording([httpx.Response(429, headers={"Retry-After": "0.01"}, json={"retry_after": 0.01}),
                                httpx.Response(204)])
    run(executor.delete_message("5", "99", "x"))
    assert len(seen) == 2


def test_a_persistent_rate_limit_gives_up_cleanly() -> None:
    executor, _ = recording([httpx.Response(429, headers={"Retry-After": "0"}, json={})] * 3)
    with pytest.raises(ExecutorError, match="Rate limited"):
        run(executor.kick_member("1", "42", "x"))


def test_permission_errors_explain_the_role_hierarchy() -> None:
    executor, _ = recording([httpx.Response(403, json={"message": "Missing Permissions"})])
    with pytest.raises(ExecutorError, match="above NexusGuard's role"):
        run(executor.add_role("1", "42", "700", "x"))


def test_closed_dms_are_not_an_error() -> None:
    executor, _ = recording([httpx.Response(403, json={})])
    assert run(executor.send_dm("42", "hi")) is False
