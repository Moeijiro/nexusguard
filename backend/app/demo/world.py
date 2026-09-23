"""The simulated guilds. Everything here is fictional and marked as demo data."""

from __future__ import annotations

import random

NIMBUS = "910000000000000001"
PIXEL = "910000000000000002"

GUILDS = {
    NIMBUS: {
        "name": "Nimbus Labs",
        "member_count": 12_480,
        "channels": [
            ("920000000000000001", "announcements", "announcement"),
            ("920000000000000002", "general", "text"),
            ("920000000000000003", "help", "text"),
            ("920000000000000004", "showcase", "text"),
            ("920000000000000005", "off-topic", "text"),
            ("920000000000000006", "welcome", "text"),
            ("920000000000000009", "mod-alerts", "text"),
        ],
        "roles": [
            ("930000000000000001", "Admin", 0xE11D48, False),
            ("930000000000000002", "NexusGuard", 0x22C55E, False),  # the bot's own role
            ("930000000000000003", "Moderator", 0x3B82F6, True),
            ("930000000000000004", "Contributor", 0xA855F7, True),
            ("930000000000000005", "Member", 0x94A3B8, True),
            ("930000000000000006", "Restricted", 0x64748B, True),
        ],
        "alert_channel": "920000000000000009",
        "restricted_role": "930000000000000006",
    },
    PIXEL: {
        "name": "Pixel Forge Community",
        "member_count": 3_214,
        "channels": [
            ("921000000000000001", "rules", "text"),
            ("921000000000000002", "chat", "text"),
            ("921000000000000003", "wip", "text"),
            ("921000000000000004", "critique", "text"),
            ("921000000000000009", "staff-alerts", "text"),
        ],
        "roles": [
            ("931000000000000001", "Owner", 0xF59E0B, False),
            ("931000000000000002", "NexusGuard", 0x22C55E, False),
            ("931000000000000003", "Staff", 0x06B6D4, True),
            ("931000000000000004", "Artist", 0xEC4899, True),
            ("931000000000000005", "Quarantine", 0x64748B, True),
        ],
        "alert_channel": "921000000000000009",
        "restricted_role": "931000000000000005",
    },
}

_FIRST = ["nova", "kai", "mira", "echo", "rune", "juno", "vex", "lumen", "orin", "sable", "tavi", "wren", "zed",
          "ash", "iris", "koa", "nyx", "pax", "remy", "sol"]
_LAST = ["ray", "moth", "dev", "byte", "fox", "stone", "loop", "arc", "vale", "drift", "pixel", "grid", "wave"]
_RAIDER = ["freenitro", "giveaway", "drop", "claimbot", "airdrop", "steamgift"]


def member_name(rng: random.Random) -> str:
    return f"{rng.choice(_FIRST)}{rng.choice(['_', '.', ''])}{rng.choice(_LAST)}{rng.choice(['', str(rng.randint(1, 99))])}"


def raider_name(rng: random.Random) -> str:
    return f"{rng.choice(_RAIDER)}_{rng.randint(1000, 9999)}"


def member_id(rng: random.Random) -> str:
    return str(rng.randint(10**17, 10**18 - 1))


def text_channels(guild_id: str) -> list[str]:
    return [cid for cid, name, kind in GUILDS[guild_id]["channels"] if kind == "text" and "alert" not in name and name != "rules"]
