"""Who is asking, and may they touch this guild?

``guild_for_user`` is the only way a route reaches a guild. It requires:

* a valid session;
* a GuildAccess row for (user, guild) — written at OAuth login only for
  guilds where the user is the owner or has Manage Server;
* that snapshot to be fresh (``GUILD_ACCESS_TTL_MINUTES``), since Discord
  tokens aren't kept to re-check later;
* the same world: demo sessions see only simulated guilds, and real sessions
  never see them.

Anything else is a 404, so the existence of other guilds isn't revealed.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import Depends, Path, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import APIError
from app.core.security import SESSION_COOKIE_NAME, read_session_token
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Guild, GuildAccess, User

UNAUTHENTICATED = APIError("unauthenticated", "Sign in to continue.", status.HTTP_401_UNAUTHORIZED)
GUILD_NOT_FOUND = APIError("not_found", "Server not found, or you can't manage it.", status.HTTP_404_NOT_FOUND)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    payload = read_session_token(token) if token else None
    if not payload:
        raise UNAUTHENTICATED
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise UNAUTHENTICATED
    return user


def manageable_guilds(db: Session, user: User) -> list[Guild]:
    if user.is_demo:
        return list(db.execute(select(Guild).where(Guild.is_demo.is_(True)).order_by(Guild.name)).scalars())
    fresh = utcnow() - timedelta(minutes=settings.guild_access_ttl_minutes)
    return list(
        db.execute(
            select(Guild)
            .join(GuildAccess, GuildAccess.guild_id == Guild.id)
            .where(GuildAccess.user_id == user.id, GuildAccess.synced_at >= fresh, Guild.is_demo.is_(False))
            .order_by(Guild.name)
        ).scalars()
    )


def guild_for_user(
    guild_id: str = Path(pattern=r"^\d{5,25}$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Guild:
    guild = db.execute(select(Guild).where(Guild.discord_id == guild_id)).scalar_one_or_none()
    if guild is None or guild.is_demo != user.is_demo:
        raise GUILD_NOT_FOUND
    if not user.is_demo:
        access = db.execute(
            select(GuildAccess).where(GuildAccess.user_id == user.id, GuildAccess.guild_id == guild.id)
        ).scalar_one_or_none()
        if access is None:
            raise GUILD_NOT_FOUND
        if access.synced_at < utcnow() - timedelta(minutes=settings.guild_access_ttl_minutes):
            raise APIError("access_expired", "Your server permissions need refreshing. Sign in again.", 401)
    return guild


def actor_name(user: User) -> str:
    return user.global_name or user.username
