"""Build the demo: ``python -m app.demo.seed [--reset]``.

Plays a week of incidents through the real pipeline (with a simulated
executor), adds hourly activity counters, and a few dashboard and slash-command
moderation entries. Everything is flagged as simulated and every guild, member
and message is fictional.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import random
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal, init_db
from app.demo import scenarios
from app.demo.setup import ensure_demo_guilds
from app.demo.world import NIMBUS, PIXEL
from app.engine.pipeline import Pipeline
from app.models import ActivityBucket, AuditEntry, Guild, ModerationLog
from app.services.executors import SimulatedExecutor
from app.services.store import SqlStore

DAYS = 7


def _activity(db, guild: Guild, rng: random.Random, now: datetime, scale: float) -> None:  # noqa: ANN001
    start = (now - timedelta(days=DAYS)).replace(minute=0, second=0, microsecond=0)
    hours = int((now - start).total_seconds() // 3600) + 1
    for h in range(hours):
        hour = start + timedelta(hours=h)
        # Busy in the (UTC) evening, quiet before dawn.
        daily = 0.55 + 0.45 * math.sin((hour.hour - 9) / 24 * 2 * math.pi)
        db.add(ActivityBucket(guild_id=guild.id, hour=hour, messages=int(scale * (40 + 260 * daily) * rng.uniform(0.8, 1.2)),
                              joins=max(0, int(scale * 6 * daily * rng.uniform(0.3, 1.6))), leaves=int(rng.uniform(0, 3) * scale)))


async def _history(pipeline: Pipeline, rng: random.Random, guild_id: str, now: datetime, per_day: tuple[int, int],
                   rare: list[tuple[float, scenarios.Scenario]]) -> None:
    moments: list[tuple[datetime, scenarios.Scenario]] = []
    for day in range(DAYS, 0, -1):
        for _ in range(rng.randint(*per_day)):
            at = now - timedelta(days=day) + timedelta(hours=rng.uniform(0, 24))
            if at < now - timedelta(minutes=20):
                moments.append((at, scenarios.pick(rng, include_rare=False)))
    moments += [(now - timedelta(hours=hours_ago), scenario) for hours_ago, scenario in rare]
    for at, scenario in sorted(moments, key=lambda item: item[0]):
        for event in scenario(rng, guild_id, at):
            await pipeline.handle(event)


def _manual_entries(db, guild: Guild, now: datetime) -> None:  # noqa: ANN001
    entries = [
        (now - timedelta(days=3, hours=2), "timeout", "rune.byte", "dashboard", "mod.ellis", "Repeated off-topic promotion"),
        (now - timedelta(days=1, hours=6), "warn", "kai_loop42", "command", "mod.ellis", "Please keep #help on topic"),
        (now - timedelta(hours=9), "restrict", "vexdrift", "dashboard", "harper (Admin)", "Account-age flag reviewed"),
    ]
    for at, action, target, source, moderator, reason in entries:
        db.add(ModerationLog(guild_id=guild.id, action=action, target_id=str(10**17 + hash(target) % 10**17), target_name=target,
                             moderator_name=moderator, source=source, reason=reason, status="simulated", created_at=at))
    db.add(AuditEntry(guild_id=guild.id, actor_name="harper (Admin)", action="rule.updated", target="mass_mentions",
                      changes={"max_mentions": {"from": 8, "to": 5}}, created_at=now - timedelta(days=5)))
    db.add(AuditEntry(guild_id=guild.id, actor_name="harper (Admin)", action="settings.updated", target=None,
                      changes={"after": {"alert_channel_id": "#mod-alerts"}}, created_at=now - timedelta(days=6)))


async def build(reset: bool) -> None:
    init_db()
    now = datetime.now(timezone.utc)
    rng = random.Random(7)
    with SessionLocal() as db:
        existing = db.execute(select(Guild).where(Guild.is_demo.is_(True))).scalars().first()
        if existing is not None and not reset:
            print("Demo guilds already exist. Re-run with --reset to rebuild them.")
            return
        guilds = {g.discord_id: g for g in ensure_demo_guilds(db, reset=True)}
        _activity(db, guilds[NIMBUS], rng, now, 1.0)
        _activity(db, guilds[PIXEL], rng, now, 0.35)
        db.commit()

    pipeline = Pipeline(SqlStore(SessionLocal, context_ttl=0), SimulatedExecutor())
    await _history(pipeline, rng, NIMBUS, now, (4, 9),
                   [(52, scenarios.raid), (97, scenarios.admin_grant), (0.25, scenarios.flood), (0.12, scenarios.everyone_ping)])
    # Pixel Forge is mid-raid right now, so the demo shows raid mode switched on.
    await _history(Pipeline(SqlStore(SessionLocal, context_ttl=0), SimulatedExecutor()), rng, PIXEL, now, (1, 3),
                   [(0.07, scenarios.raid)])

    with SessionLocal() as db:
        nimbus = db.execute(select(Guild).where(Guild.discord_id == NIMBUS)).scalar_one()
        _manual_entries(db, nimbus, now)
        nimbus.raid_mode = False  # the older raid's raid mode has long expired
        nimbus.raid_mode_until = nimbus.raid_mode_since = nimbus.raid_mode_reason = nimbus.raid_mode_by = None
        db.commit()
    print("Demo guilds ready (simulated): Nimbus Labs, Pixel Forge Community.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild the demo guilds.")
    asyncio.run(build(parser.parse_args().reset))
    return 0


if __name__ == "__main__":
    sys.exit(main())
