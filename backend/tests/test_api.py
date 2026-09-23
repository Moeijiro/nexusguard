"""OAuth, guild permissions, demo isolation, and the dashboard's write paths."""

from __future__ import annotations

import asyncio
import json
import random
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import generate_oauth_state
from app.db.base import utcnow
from app.db.session import SessionLocal
from app.demo.setup import ensure_demo_guilds
from app.demo.simulator import tick
from app.engine.pipeline import Pipeline
from app.demo.world import NIMBUS
from app.main import app
from app.models import AuditEntry, Flag, Guild, GuildAccess, ModerationLog, RuleConfig, User
from app.services import discord_oauth
from app.services import guilds as guild_service
from app.services.executors import SimulatedExecutor
from app.services.store import SqlStore

MANAGED = "222222222222222222"      # user has Manage Server here
MEMBER_ONLY = "333333333333333333"  # user is a plain member here
NOT_INSTALLED = "444444444444444444"  # user manages it, but the bot isn't there
MANAGE_GUILD = str(1 << 5)


def discord_transport(user_id: str = "555") -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth2/token"):
            assert b"code=good-code" in request.content
            return httpx.Response(200, json={"access_token": "user-token", "token_type": "Bearer"})
        assert request.headers["Authorization"] == "Bearer user-token"
        if request.url.path.endswith("/users/@me"):
            return httpx.Response(200, json={"id": user_id, "username": "alex", "global_name": "Alex"})
        if request.url.path.endswith("/users/@me/guilds"):
            return httpx.Response(200, json=[
                {"id": MANAGED, "name": "Managed", "owner": False, "permissions": MANAGE_GUILD},
                {"id": MEMBER_ONLY, "name": "Member", "owner": False, "permissions": "0"},
                {"id": NOT_INSTALLED, "name": "No bot", "owner": True, "permissions": "0"},
            ])
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.fixture
def installed() -> None:
    with SessionLocal() as db:
        for gid, name in [(MANAGED, "Managed"), (MEMBER_ONLY, "Member")]:
            g = guild_service.ensure_guild(db, gid, name)
            g.channels = [{"id": "900", "name": "mod-alerts", "kind": "text"}]
            g.roles = [{"id": "700", "name": "Restricted", "assignable": True}, {"id": "701", "name": "Admin", "assignable": False}]
        ensure_demo_guilds(db)
        db.commit()


def oauth_login(client: TestClient, user_id: str = "555") -> httpx.Response:
    discord_oauth.set_transport(discord_transport(user_id))
    state = generate_oauth_state()
    client.cookies.set("nexusguard_oauth_state", state, path="/api/auth")
    try:
        return client.get(f"/api/auth/callback?code=good-code&state={state}", follow_redirects=False)
    finally:
        discord_oauth.set_transport(None)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, base_url="http://localhost:8000") as c:
        yield c


@pytest.fixture
def logged_in(client: TestClient, installed: None) -> TestClient:
    response = oauth_login(client)
    assert response.status_code == 302 and response.headers["location"].endswith("/servers")
    return client


# --- OAuth ---------------------------------------------------------------------------------------
def test_login_redirects_to_discord_with_a_signed_state(client: TestClient) -> None:
    response = client.get("/api/auth/login", follow_redirects=False)
    target = urlparse(response.headers["location"])
    query = parse_qs(target.query)
    assert target.netloc == "discord.com" and query["scope"] == ["identify guilds"]
    assert query["redirect_uri"] == ["http://localhost:8000/api/auth/callback"]
    assert "nexusguard_oauth_state" in response.headers["set-cookie"] and "HttpOnly" in response.headers["set-cookie"]


def test_a_callback_with_a_forged_state_is_rejected(client: TestClient, installed: None) -> None:
    client.cookies.set("nexusguard_oauth_state", generate_oauth_state(), path="/api/auth")
    response = client.get("/api/auth/callback?code=good-code&state=attacker.value", follow_redirects=False)
    assert response.headers["location"].endswith("/login?error=invalid_state")
    assert client.get("/api/me").status_code == 401


def test_the_access_snapshot_contains_only_manageable_installed_guilds(logged_in: TestClient) -> None:
    ids = [g["id"] for g in logged_in.get("/api/guilds").json()]
    assert ids == [MANAGED]
    with SessionLocal() as db:
        assert db.query(GuildAccess).count() == 1


def test_no_discord_token_is_stored(logged_in: TestClient) -> None:
    with SessionLocal() as db:
        user = db.execute(select(User)).scalars().first()
        row = {c.name: getattr(user, c.name) for c in user.__table__.columns}
    assert "user-token" not in json.dumps(row, default=str)


# --- guild permissions ------------------------------------------------------------------------------
@pytest.mark.parametrize("guild", [MEMBER_ONLY, NOT_INSTALLED, NIMBUS, "999999999999999999"])
def test_other_guilds_are_404(logged_in: TestClient, guild: str) -> None:
    assert logged_in.get(f"/api/guilds/{guild}/overview").status_code == 404
    assert logged_in.put(f"/api/guilds/{guild}/rules/mass_mentions", json={"enabled": False}).status_code == 404
    assert logged_in.post(f"/api/guilds/{guild}/raid-mode", json={"enabled": True}).status_code == 404


def test_a_stale_permission_snapshot_needs_a_fresh_login(logged_in: TestClient) -> None:
    with SessionLocal() as db:
        db.query(GuildAccess).update({"synced_at": utcnow() - timedelta(days=2)})
        db.commit()
    response = logged_in.get(f"/api/guilds/{MANAGED}/overview")
    assert response.status_code == 401 and response.json()["error"]["code"] == "access_expired"


def test_logging_in_again_drops_guilds_you_lost_access_to(client: TestClient, installed: None) -> None:
    oauth_login(client)
    with SessionLocal() as db:
        g = db.execute(select(Guild).where(Guild.discord_id == MEMBER_ONLY)).scalar_one()
        user_id = db.query(GuildAccess).first().user_id
        db.add(GuildAccess(user_id=user_id, guild_id=g.id, permissions="0", synced_at=utcnow()))
        db.commit()
    oauth_login(client)  # Discord still says "plain member" there
    assert [g["id"] for g in client.get("/api/guilds").json()] == [MANAGED]


def test_demo_sessions_only_see_simulated_guilds(client: TestClient, installed: None) -> None:
    assert client.post("/api/auth/demo").status_code == 200
    guilds = client.get("/api/guilds").json()
    assert guilds and all(g["is_demo"] for g in guilds)
    assert client.get(f"/api/guilds/{MANAGED}/overview").status_code == 404


def test_signed_out_users_get_401(client: TestClient) -> None:
    assert client.get("/api/guilds").status_code == 401


# --- config persistence and audit ------------------------------------------------------------------------
def test_rule_updates_are_validated_persisted_and_audited(logged_in: TestClient) -> None:
    url = f"/api/guilds/{MANAGED}/rules/mass_mentions"
    assert logged_in.put(url, json={"max_mentions": 1}).status_code == 422
    bad = logged_in.put(url, json={"actions": ["ban"]})
    assert bad.status_code == 422
    ok = logged_in.put(url, json={"max_mentions": 8, "actions": ["delete_message", "timeout"], "timeout_minutes": 30})
    assert ok.status_code == 200 and ok.json()["params"]["max_mentions"] == 8

    rules = {r["module"]: r for r in logged_in.get(f"/api/guilds/{MANAGED}/rules").json()}
    assert rules["mass_mentions"]["params"]["actions"] == ["delete_message", "timeout"]
    assert rules["mass_mentions"]["updated_by"] == "Alex"
    with SessionLocal() as db:
        entry = db.query(AuditEntry).one()
        stored = db.query(RuleConfig).filter_by(module="mass_mentions").first().params
    assert entry.action == "rule.updated" and entry.changes["max_mentions"] == {"from": 5, "to": 8}
    assert stored["timeout_minutes"] == 30


def test_settings_only_accept_this_guilds_channels_and_assignable_roles(logged_in: TestClient) -> None:
    url = f"/api/guilds/{MANAGED}/settings"
    assert logged_in.patch(url, json={"alert_channel_id": "123"}).status_code == 422
    assert logged_in.patch(url, json={"restricted_role_id": "701"}).json()["error"]["code"] == "role_not_assignable"
    ok = logged_in.patch(url, json={"alert_channel_id": "900", "restricted_role_id": "700"}).json()
    assert (ok["alert_channel_id"], ok["restricted_role_id"]) == ("900", "700")


def test_overview_reports_module_status_factually(logged_in: TestClient) -> None:
    logged_in.put(f"/api/guilds/{MANAGED}/rules/message_flood", json={"enabled": False})
    protection = logged_in.get(f"/api/guilds/{MANAGED}/overview").json()["protection"]
    # Defaults: 5 of 6 on (account age is opt-in); flood now off too.
    assert (protection["enabled"], protection["total"]) == (4, 6)


# --- raid mode and review queue (demo guild: actions are simulated) ------------------------------------------
@pytest.fixture
def demo(client: TestClient, installed: None) -> TestClient:
    client.post("/api/auth/demo")
    return client


def test_raid_mode_toggle_is_visible_logged_and_alerts_moderators(demo: TestClient) -> None:
    on = demo.post(f"/api/guilds/{NIMBUS}/raid-mode", json={"enabled": True, "minutes": 30}).json()
    assert on["raid"]["enabled"] and on["raid"]["by"] == "Demo moderator (dashboard)" and on["raid"]["until"]
    event = demo.get(f"/api/guilds/{NIMBUS}/events?limit=1").json()["items"][0]
    assert event["summary"] == "Raid mode enabled by Demo moderator" and event["action_taken"] == "Moderators notified"
    off = demo.post(f"/api/guilds/{NIMBUS}/raid-mode", json={"enabled": False}).json()
    assert off["raid"] == {"enabled": False, "since": None, "until": None, "reason": None, "by": None}


def test_resolving_a_flag_records_moderation_and_can_only_happen_once(demo: TestClient) -> None:
    with SessionLocal() as db:
        guild = db.execute(select(Guild).where(Guild.discord_id == NIMBUS)).scalar_one()
        flag = Flag(guild_id=guild.id, user_id="123456789012345678", username="newbie", reason="Account created 3 h ago", severity="low")
        db.add(flag)
        db.commit()
        flag_id = flag.id
    url = f"/api/guilds/{NIMBUS}/flags/{flag_id}/resolve"
    resolved = demo.post(url, json={"action": "timeout", "minutes": 60}).json()
    assert resolved["status"] == "actioned" and resolved["resolved_by"] == "Demo moderator"
    assert demo.post(url, json={"action": "dismiss"}).status_code == 409
    with SessionLocal() as db:
        log = db.query(ModerationLog).one()
    assert (log.action, log.source, log.status, log.moderator_name) == ("timeout", "dashboard", "simulated", "Demo moderator")


def test_the_event_stream_polls_by_id(demo: TestClient) -> None:
    first = demo.get(f"/api/guilds/{NIMBUS}/events?limit=5").json()["items"]
    newest = first[0]["id"] if first else 0
    pipeline = Pipeline(SqlStore(SessionLocal, context_ttl=0), SimulatedExecutor())
    rng = random.Random(3)
    fresh: list = []
    for _ in range(50):  # the simulator picks a guild at random; tick until this one gets something
        asyncio.run(tick(pipeline, rng))
        fresh = demo.get(f"/api/guilds/{NIMBUS}/events?after_id={newest}").json()["items"]
        if fresh:
            break
    assert fresh and all(e["id"] > newest for e in fresh) and all(e["simulated"] for e in fresh)
