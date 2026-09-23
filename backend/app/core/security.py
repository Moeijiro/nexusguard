"""Sessions and OAuth state.

The browser only ever holds an HttpOnly session cookie. NexusGuard does not
keep users' Discord access tokens: at login it records which guilds the user
may manage, then discards the token.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings

SESSION_COOKIE_NAME = "nexusguard_session"
OAUTH_STATE_COOKIE_NAME = "nexusguard_oauth_state"
JWT_ALGORITHM = "HS256"


def create_session_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=settings.session_ttl_minutes)).timestamp()),
            "jti": secrets.token_urlsafe(8),
        },
        settings.secret_key,
        algorithm=JWT_ALGORITHM,
    )


def read_session_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def _sign(nonce: str) -> str:
    return hmac.new(settings.secret_key.encode(), nonce.encode(), hashlib.sha256).hexdigest()[:32]


def generate_oauth_state() -> str:
    """``nonce.signature`` — also stored in a short-lived cookie and compared on callback."""
    nonce = secrets.token_urlsafe(24)
    return f"{nonce}.{_sign(nonce)}"


def verify_oauth_state(returned: str | None, cookie: str | None) -> bool:
    """The state Discord hands back must equal our cookie *and* carry our signature.

    The cookie binds the flow to this browser (stopping login CSRF); the
    signature means a cookie planted by someone else is useless too.
    """
    if not returned or not cookie or not hmac.compare_digest(returned, cookie):
        return False
    nonce, _, signature = returned.partition(".")
    return bool(nonce) and hmac.compare_digest(signature, _sign(nonce))
