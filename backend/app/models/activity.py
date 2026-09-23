"""Hourly counters for the dashboard's server-activity chart.

The bot increments these as events arrive; nothing about message content is kept.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime


class ActivityBucket(Base):
    __tablename__ = "activity_buckets"
    __table_args__ = (UniqueConstraint("guild_id", "hour", name="uq_activity_guild_hour"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), index=True)
    hour: Mapped[datetime] = mapped_column(UTCDateTime())
    messages: Mapped[int] = mapped_column(default=0)
    joins: Mapped[int] = mapped_column(default=0)
    leaves: Mapped[int] = mapped_column(default=0)
