"""Fixtures: a fresh database per test, a protected guild, and a pipeline wired
to the real SqlStore with a recording executor."""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest

_TMP = tempfile.mkdtemp(prefix="nexusguard-tests-")
os.environ.update(
    ENVIRONMENT="development",
    DATABASE_URL=f"sqlite:///{_TMP}/test.db",
    SECRET_KEY="test-secret-not-used-anywhere-else-0123456789",
    DISCORD_CLIENT_ID="1234",
    DISCORD_CLIENT_SECRET="test-client-secret",
    DISCORD_BOT_TOKEN="test-bot-token",
    DEMO_ENABLED="true",
    DEMO_SIMULATOR_INTERVAL="0",
    APP_URL="http://localhost:3000",
    API_URL="http://localhost:8000",
)

from app.core.rate_limit import reset_rate_limits  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.engine.events import Member, MemberJoinEvent, MessageEvent  # noqa: E402
from app.engine.pipeline import Pipeline  # noqa: E402
from app.services import guilds as guild_service  # noqa: E402
from app.services.executors import SimulatedExecutor  # noqa: E402
from app.services.store import SqlStore  # noqa: E402

GUILD = "111111111111111111"
T0 = datetime(2026, 9, 23, 22, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def fresh_db() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    reset_rate_limits()
    yield


@pytest.fixture
def guild() -> str:
    with SessionLocal() as db:
        g = guild_service.ensure_guild(db, GUILD, "Test Server")
        g.alert_channel_id = "900"
        g.restricted_role_id = "700"
        db.commit()
    return GUILD


@pytest.fixture
def executor() -> SimulatedExecutor:
    return SimulatedExecutor()


@pytest.fixture
def store() -> SqlStore:
    return SqlStore(SessionLocal, context_ttl=0)


@pytest.fixture
def pipeline(guild: str, store: SqlStore, executor: SimulatedExecutor) -> Pipeline:
    return Pipeline(store, executor)


def run(coro):  # noqa: ANN001, ANN201
    return asyncio.run(coro)


def member(user_id: str = "42", name: str = "spammer", **kwargs) -> Member:  # noqa: ANN003
    return Member(id=user_id, name=name, **kwargs)


_counter = iter(range(1, 10**6))


def message(content: str = "hello", at: datetime = T0, author: Member | None = None, **kwargs) -> MessageEvent:  # noqa: ANN003
    return MessageEvent(
        guild_id=GUILD, channel_id="500", message_id=str(next(_counter)),
        author=author or member(), content=content, at=at, **kwargs,
    )


def join(user_id: str, at: datetime, age: timedelta | None = timedelta(days=400)) -> MemberJoinEvent:
    created = at - age if age is not None else None
    return MemberJoinEvent(guild_id=GUILD, member=Member(id=user_id, name=f"user{user_id}", account_created_at=created), at=at)


def set_rule(module: str, **changes) -> None:  # noqa: ANN003
    from sqlalchemy import select

    from app.models import Guild, RuleConfig

    with SessionLocal() as db:
        g = db.execute(select(Guild).where(Guild.discord_id == GUILD)).scalar_one()
        row = next(r for r in g.rules if r.module == module)
        row.params = {**row.params, **changes}
        db.commit()
