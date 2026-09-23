"""Incident scenarios for the demo guilds, as streams of engine events.

They go through the real pipeline — the dashboard shows exactly what
NexusGuard would record for these patterns. Only the Discord side is simulated.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import datetime, timedelta

from app.demo.world import GUILDS, member_id, member_name, raider_name, text_channels
from app.engine.events import Event, Member, MemberJoinEvent, MessageEvent, ModerationEvent, RoleGrantEvent

Scenario = Callable[[random.Random, str, datetime], list[Event]]
_ids = iter(range(10**15, 10**16))


def _msg(guild: str, channel: str, author: Member, text: str, at: datetime, **kw) -> MessageEvent:  # noqa: ANN003
    return MessageEvent(guild_id=guild, channel_id=channel, message_id=str(next(_ids)), author=author,
                        content=text, at=at, **kw)


def _member(rng: random.Random, *, age_days: float = 400, at: datetime, raider: bool = False) -> Member:
    return Member(id=member_id(rng), name=raider_name(rng) if raider else member_name(rng),
                  account_created_at=at - timedelta(days=age_days))


def flood(rng: random.Random, guild: str, at: datetime) -> list[Event]:
    who, channel = _member(rng, at=at), rng.choice(text_channels(guild))
    lines = ["lol", "LOL", "wait what", "no way", "hahaha", "look", "???", "!!!", "ok ok", "bruh"]
    gap = rng.uniform(0.15, 0.7)
    return [_msg(guild, channel, who, rng.choice(lines), at + timedelta(seconds=i * gap)) for i in range(rng.randint(7, 11))]


def link_spam(rng: random.Random, guild: str, at: datetime) -> list[Event]:
    who, channel = _member(rng, at=at, age_days=rng.uniform(0.2, 3)), rng.choice(text_channels(guild))
    text = rng.choice([
        "Free nitro for everyone who joins first 👉 https://dlscord-gift.example/claim",
        "steam is giving away 50$ cards https://steamcommunlty.example/gift",
        "check my new server discord.gg/xyzfree",
    ])
    return [_msg(guild, channel, who, text, at + timedelta(seconds=i * rng.uniform(4, 8))) for i in range(3)]


def everyone_ping(rng: random.Random, guild: str, at: datetime) -> list[Event]:
    who = _member(rng, at=at, age_days=rng.uniform(1, 30))
    return [_msg(guild, rng.choice(text_channels(guild)), who, "@everyone GIVEAWAY IN MY PROFILE", at, mentions_everyone=True)]


def mention_spam(rng: random.Random, guild: str, at: datetime) -> list[Event]:
    who = _member(rng, at=at)
    count = rng.choice([6, 7, 9, 12])
    return [_msg(guild, rng.choice(text_channels(guild)), who, "yo " + " ".join("<@1>" for _ in range(count)), at,
                 user_mentions=count)]


def raid(rng: random.Random, guild: str, at: datetime) -> list[Event]:
    joins = rng.randint(12, 24)
    span = rng.uniform(6, 9)
    return [MemberJoinEvent(guild, _member(rng, at=at, raider=True, age_days=rng.uniform(0.01, 0.5)),
                            at + timedelta(seconds=span * i / joins)) for i in range(joins)]


def new_accounts(rng: random.Random, guild: str, at: datetime) -> list[Event]:
    return [MemberJoinEvent(guild, _member(rng, at=at, age_days=rng.uniform(0.02, 0.9)),
                            at + timedelta(seconds=i * rng.uniform(5, 40))) for i in range(rng.randint(1, 2))]


def admin_grant(rng: random.Random, guild: str, at: datetime) -> list[Event]:
    role_id, role_name, _, _ = GUILDS[guild]["roles"][0]
    return [RoleGrantEvent(guild, _member(rng, at=at), role_id, role_name, 1 << 3, at,
                           granted_by=Member(id="1", name="server-owner"))]


def manual_kick(rng: random.Random, guild: str, at: datetime) -> list[Event]:
    return [ModerationEvent(guild, "kick", _member(rng, at=at), Member(id="2", name="mod.ellis"),
                            "Ignoring warnings in #help", at)]


# Weighted: floods and link spam are common, raids and admin grants are rare.
ROUTINE: list[tuple[Scenario, int]] = [
    (flood, 5), (link_spam, 4), (everyone_ping, 3), (mention_spam, 2), (new_accounts, 3), (manual_kick, 1),
]
RARE: list[tuple[Scenario, int]] = [(raid, 1), (admin_grant, 1)]


def pick(rng: random.Random, include_rare: bool = True) -> Scenario:
    pool = ROUTINE + (RARE if include_rare else [])
    return rng.choices([s for s, _ in pool], weights=[w for _, w in pool])[0]
