"""Dashboard users: a Discord identity, or the demo visitor."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UTCDateTime


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(64))
    global_name: Mapped[str | None] = mapped_column(String(64), default=None)
    avatar: Mapped[str | None] = mapped_column(String(64), default=None)
    # Demo users can only ever see demo guilds, and real users never see them.
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)
