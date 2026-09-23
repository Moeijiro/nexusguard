"""FastAPI application: the dashboard's API.

The bot is a separate process (``python -m app.bot``) that shares the database.
In demo mode this process also runs the simulator that feeds the demo guilds.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, events, guilds, system
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
logger = logging.getLogger("nexusguard")

DESCRIPTION = """
NexusGuard's dashboard API. Sign in with Discord (OAuth2) or as the demo user.
Every `/api/guilds/{guild_id}` route checks that you own or can manage that
server; other servers return 404.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    task = None
    if settings.demo_enabled and settings.demo_simulator_interval > 0:
        from app.demo.simulator import run_forever

        task = asyncio.create_task(run_forever(settings.demo_simulator_interval))
    logger.info("NexusGuard API ready (discord=%s, demo=%s)", settings.discord_configured, settings.demo_enabled)
    yield
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="NexusGuard API", description=DESCRIPTION, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
install_error_handlers(app)
for router in (system.router, auth.router, guilds.router, events.router):
    app.include_router(router)


@app.get("/", include_in_schema=False)
def index() -> JSONResponse:
    return JSONResponse({"service": "nexusguard-api", "docs": "/docs"})
