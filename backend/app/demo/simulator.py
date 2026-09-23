"""Keeps the demo alive: a new simulated incident every few seconds.

Runs inside the API process when ``DEMO_SIMULATOR_INTERVAL`` > 0. It uses the
same pipeline as the bot, so the dashboard's live stream shows real engine
output — only the Discord side is simulated.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.demo import scenarios
from app.demo.setup import ensure_demo_guilds
from app.demo.world import NIMBUS, PIXEL
from app.engine.pipeline import Pipeline
from app.services import activity
from app.services.executors import SimulatedExecutor
from app.services.store import SqlStore

logger = logging.getLogger("nexusguard.demo")


async def tick(pipeline: Pipeline, rng: random.Random) -> int:
    guild_id = NIMBUS if rng.random() < 0.8 else PIXEL
    now = datetime.now(timezone.utc)
    events = scenarios.pick(rng, include_rare=rng.random() < 0.08)(rng, guild_id, now)
    recorded = 0
    for event in events:
        recorded += len(await pipeline.handle(event))
    with SessionLocal() as db:
        guild = next(g for g in ensure_demo_guilds(db) if g.discord_id == guild_id)
        activity.bump(db, guild.id, now, messages=rng.randint(3, 15), joins=int(rng.random() < 0.3))
        db.commit()
    return recorded


async def run_forever(interval: int) -> None:
    with SessionLocal() as db:
        ensure_demo_guilds(db)
    pipeline = Pipeline(SqlStore(SessionLocal), SimulatedExecutor())
    rng = random.Random()
    logger.info("Demo simulator running every %ss", interval)
    while True:
        await asyncio.sleep(interval * rng.uniform(0.6, 1.4))
        try:
            await tick(pipeline, rng)
        except Exception:  # noqa: BLE001 — the demo must never take the API down
            logger.exception("Demo tick failed")
