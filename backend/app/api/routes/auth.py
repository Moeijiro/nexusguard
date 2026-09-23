"""Discord OAuth2 login, the demo login, and sign-out.

    GET  /api/auth/login     signed state in an HttpOnly cookie, redirect to Discord
    GET  /api/auth/callback  check state, exchange the code, snapshot manageable guilds
    POST /api/auth/demo      a session that can only see the simulated guilds
    POST /api/auth/logout

The Discord access token is used for two calls during the callback (who are
you, which servers are you in) and then discarded. What's kept is the list of
servers where you're the owner or have Manage Server — the permission check
every guild route relies on.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import permissions
from app.core.config import settings
from app.core.errors import APIError
from app.core.rate_limit import RateLimiter
from app.core.security import (
    OAUTH_STATE_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    create_session_token,
    generate_oauth_state,
    verify_oauth_state,
)
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Guild, GuildAccess, User
from app.schemas.api import ModeOut, UserOut
from app.services import discord_oauth

logger = logging.getLogger("nexusguard.auth")
router = APIRouter(prefix="/api", tags=["auth"])
auth_limit = RateLimiter(times=10, seconds=60, scope="auth")

DEMO_DISCORD_ID = "demo-visitor"


def user_out(user: User) -> UserOut:
    avatar = None
    if user.avatar and not user.is_demo:
        avatar = f"https://cdn.discordapp.com/avatars/{user.discord_id}/{user.avatar}.png?size=64"
    return UserOut(id=user.id, discord_id=user.discord_id, username=user.username, global_name=user.global_name,
                   avatar_url=avatar, is_demo=user.is_demo)


def _session(response: Response, user: User) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME, create_session_token(user.id), max_age=settings.session_ttl_minutes * 60,
        httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, path="/",
    )


@router.get("/auth/mode", response_model=ModeOut, summary="What the login screen can offer")
def mode() -> ModeOut:
    return ModeOut(
        discord_login=settings.discord_configured,
        demo=settings.demo_enabled,
        bot_invite_url=discord_oauth.bot_invite_url() if settings.discord_client_id else None,
    )


@router.get("/auth/login", summary="Start Discord OAuth2")
def login(_: None = Depends(auth_limit)) -> RedirectResponse:
    if not settings.discord_configured:
        raise APIError("discord_not_configured", "Discord login isn't configured on this instance. Try the demo.", 503)
    state = generate_oauth_state()
    response = RedirectResponse(discord_oauth.authorize_url(state), status_code=302)
    response.set_cookie(OAUTH_STATE_COOKIE_NAME, state, max_age=600, httponly=True,
                        secure=settings.cookie_secure, samesite="lax", path="/api/auth")
    return response


@router.get("/auth/callback", summary="Discord redirects here")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(auth_limit),
) -> RedirectResponse:
    def fail(reason: str) -> RedirectResponse:
        logger.warning("OAuth callback rejected: %s", reason)
        redirect = RedirectResponse(f"{settings.app_url}/login?error={reason}", status_code=302)
        redirect.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/api/auth")
        return redirect

    if error:
        return fail("access_denied")
    if not code:
        return fail("missing_code")
    if not verify_oauth_state(state, request.cookies.get(OAUTH_STATE_COOKIE_NAME)):
        return fail("invalid_state")
    try:
        token = await discord_oauth.exchange_code(code)
        identity, user_guilds = await discord_oauth.fetch_identity_and_guilds(token)
    except discord_oauth.OAuthError as exc:
        logger.error("OAuth failed: %s", exc)
        return fail("discord_error")
    del token  # not stored anywhere

    user = db.execute(select(User).where(User.discord_id == identity.id)).scalar_one_or_none()
    if user is None:
        user = User(discord_id=identity.id, username=identity.username)
        db.add(user)
    user.username, user.global_name, user.avatar = identity.username, identity.global_name, identity.avatar
    user.last_login_at = utcnow()
    db.flush()

    # Rebuild the snapshot: only guilds the bot is in *and* the user can manage.
    db.execute(delete(GuildAccess).where(GuildAccess.user_id == user.id))
    manageable = {g.id: g for g in user_guilds if permissions.can_manage_guild(g.permissions, is_owner=g.owner)}
    if manageable:
        known = db.execute(
            select(Guild).where(Guild.discord_id.in_(manageable), Guild.is_demo.is_(False), Guild.bot_present.is_(True))
        ).scalars()
        now = utcnow()
        for guild in known:
            partial = manageable[guild.discord_id]
            db.add(GuildAccess(user_id=user.id, guild_id=guild.id, permissions=partial.permissions,
                               is_owner=partial.owner, synced_at=now))
    db.commit()

    redirect = RedirectResponse(f"{settings.app_url}/servers", status_code=302)
    redirect.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/api/auth")
    _session(redirect, user)
    return redirect


@router.post("/auth/demo", response_model=UserOut, summary="Explore the simulated guilds")
def demo_login(response: Response, db: Session = Depends(get_db), _: None = Depends(auth_limit)) -> UserOut:
    if not settings.demo_enabled:
        raise APIError("demo_disabled", "The demo is turned off on this instance.", 404)
    user = db.execute(select(User).where(User.discord_id == DEMO_DISCORD_ID)).scalar_one_or_none()
    if user is None:
        user = User(discord_id=DEMO_DISCORD_ID, username="demo", global_name="Demo moderator", is_demo=True)
        db.add(user)
    user.last_login_at = utcnow()
    db.commit()
    _session(response, user)
    return user_out(user)


@router.post("/auth/logout", status_code=204, summary="Sign out")
def logout(response: Response) -> Response:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut, summary="Current user")
def me(user: User = Depends(get_current_user)) -> UserOut:
    return user_out(user)
