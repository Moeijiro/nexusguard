"""Create or reset the simulated guilds."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.demo.world import GUILDS
from app.engine.rules_schema import Module
from app.models import ActivityBucket, AuditEntry, Flag, Guild, ModerationLog, SecurityEvent
from app.services import guilds as guild_service


def ensure_demo_guilds(db: Session, *, reset: bool = False) -> list[Guild]:
    guilds = []
    for discord_id, spec in GUILDS.items():
        guild = db.execute(select(Guild).where(Guild.discord_id == discord_id)).scalar_one_or_none()
        if guild is not None and reset:
            for model in (ModerationLog, Flag, AuditEntry, ActivityBucket, SecurityEvent):
                db.execute(delete(model).where(model.guild_id == guild.id))
            db.delete(guild)
            db.flush()
            guild = None
        if guild is None:
            guild = guild_service.ensure_guild(db, discord_id, spec["name"], is_demo=True, member_count=spec["member_count"])
            guild.channels = [{"id": cid, "name": name, "kind": kind, "position": i}
                              for i, (cid, name, kind) in enumerate(spec["channels"])]
            guild.roles = [{"id": rid, "name": name, "color": color, "assignable": assignable, "position": 100 - i}
                           for i, (rid, name, color, assignable) in enumerate(spec["roles"])]
            guild.alert_channel_id = spec["alert_channel"]
            guild.restricted_role_id = spec["restricted_role"]
            # Show account-age checks on the main demo guild (it's opt-in by default).
            for row in guild.rules:
                if row.module == Module.ACCOUNT_AGE.value and discord_id.endswith("1"):
                    row.params = {**row.params, "enabled": True, "min_account_age_hours": 24}
        guilds.append(guild)
    db.commit()
    return guilds
