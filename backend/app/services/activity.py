"""Hourly activity counters (messages, joins, leaves) — counts only, no content."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActivityBucket


def bump(db: Session, guild_pk: int, at: datetime, *, messages: int = 0, joins: int = 0, leaves: int = 0) -> None:
    hour = at.replace(minute=0, second=0, microsecond=0)
    bucket = db.execute(
        select(ActivityBucket).where(ActivityBucket.guild_id == guild_pk, ActivityBucket.hour == hour)
    ).scalar_one_or_none()
    if bucket is None:
        bucket = ActivityBucket(guild_id=guild_pk, hour=hour, messages=0, joins=0, leaves=0)
        db.add(bucket)
    bucket.messages += messages
    bucket.joins += joins
    bucket.leaves += leaves
