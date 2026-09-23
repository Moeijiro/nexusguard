"""The three Discord calls OAuth2 login needs. ``transport`` is a test hook."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import DISCORD_API_BASE, OAUTH_SCOPES, settings

_transport: httpx.AsyncBaseTransport | None = None


def set_transport(transport: httpx.AsyncBaseTransport | None) -> None:
    global _transport
    _transport = transport


class OAuthError(Exception):
    pass


@dataclass(slots=True)
class DiscordIdentity:
    id: str
    username: str
    global_name: str | None
    avatar: str | None


@dataclass(slots=True)
class UserGuild:
    id: str
    name: str
    icon: str | None
    owner: bool
    permissions: str


def authorize_url(state: str) -> str:
    query = urlencode({
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "state": state,
        "prompt": "none",
    })
    return f"https://discord.com/oauth2/authorize?{query}"


def bot_invite_url(guild_id: str | None = None) -> str:
    from app.core.permissions import BOT_PERMISSIONS

    params = {"client_id": settings.discord_client_id, "scope": "bot applications.commands",
              "permissions": str(int(BOT_PERMISSIONS))}
    if guild_id:
        params |= {"guild_id": guild_id, "disable_guild_select": "true"}
    return f"https://discord.com/oauth2/authorize?{urlencode(params)}"


async def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=DISCORD_API_BASE, timeout=10, transport=_transport)


async def exchange_code(code: str) -> str:
    """Returns the access token. It is used for two calls and then dropped."""
    async with await _client() as client:
        response = await client.post(
            "/oauth2/token",
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": settings.oauth_redirect_uri},
            auth=(settings.discord_client_id, settings.discord_client_secret),
        )
    if response.status_code != 200:
        raise OAuthError(f"Token exchange failed ({response.status_code})")
    return response.json()["access_token"]


async def fetch_identity_and_guilds(access_token: str) -> tuple[DiscordIdentity, list[UserGuild]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with await _client() as client:
        me = await client.get("/users/@me", headers=headers)
        guilds = await client.get("/users/@me/guilds", headers=headers)
    if me.status_code != 200 or guilds.status_code != 200:
        raise OAuthError("Could not read the Discord profile")
    data = me.json()
    identity = DiscordIdentity(data["id"], data["username"], data.get("global_name"), data.get("avatar"))
    return identity, [
        UserGuild(g["id"], g["name"], g.get("icon"), bool(g.get("owner")), str(g.get("permissions", "0")))
        for g in guilds.json()
    ]
