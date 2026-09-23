"""Four slash commands. The dashboard is the main interface; these cover what
moderators need without leaving Discord."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from sqlalchemy import func, select

from app.db.base import utcnow
from app.db.session import SessionLocal
from app.engine.actions.notify import COLOURS, TITLES
from app.engine.severity import Severity
from app.models import AuditEntry, Flag, Guild, ModerationLog, SecurityEvent
from app.services import guilds as guild_service

if TYPE_CHECKING:
    from app.bot.client import NexusGuardBot

SEVERITY_DOT = {"low": "⚪", "medium": "🟡", "high": "🟠", "critical": "🔴"}


def _guild(db, guild_id: int) -> Guild | None:  # noqa: ANN001
    return db.execute(select(Guild).where(Guild.discord_id == str(guild_id))).scalar_one_or_none()


def register(bot: "NexusGuardBot") -> None:
    tree = bot.tree

    @tree.command(name="security", description="Protection status for this server")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def security(interaction: discord.Interaction) -> None:
        with SessionLocal() as db:
            guild = _guild(db, interaction.guild_id)
            if guild is None:
                await interaction.response.send_message("This server isn't set up yet.", ephemeral=True)
                return
            rules = guild_service.load_rules(guild)
            since = utcnow() - timedelta(hours=24)
            events = db.scalar(select(func.count()).select_from(SecurityEvent)
                               .where(SecurityEvent.guild_id == guild.id, SecurityEvent.created_at >= since)) or 0
            flags = db.scalar(select(func.count()).select_from(Flag).where(Flag.guild_id == guild.id, Flag.status == "open")) or 0
            enabled = [r for r in rules.values() if r.enabled]
            embed = discord.Embed(title="NexusGuard status", color=COLOURS[Severity.HIGH if guild.raid_mode else Severity.LOW])
            embed.add_field(name="Protection", value=f"{len(enabled)} of {len(rules)} modules enabled")
            embed.add_field(name="Raid mode", value="**ON**" if guild.raid_mode else "Off")
            embed.add_field(name="Last 24 h", value=f"{events} events · {flags} open flags")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="incidents", description="The latest security events")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def incidents(interaction: discord.Interaction, count: app_commands.Range[int, 1, 10] = 5) -> None:
        with SessionLocal() as db:
            guild = _guild(db, interaction.guild_id)
            rows = [] if guild is None else list(db.execute(
                select(SecurityEvent).where(SecurityEvent.guild_id == guild.id)
                .order_by(SecurityEvent.created_at.desc()).limit(count)).scalars())
            lines = [
                f"{SEVERITY_DOT[e.severity]} <t:{int(e.created_at.timestamp())}:t> **{TITLES.get(e.type, e.type)}** — "
                f"{e.summary}{f' · {e.username}' if e.username else ''} · _{e.action_taken}_"
                for e in rows
            ]
        await interaction.response.send_message("\n".join(lines) or "No incidents recorded yet.", ephemeral=True)

    @tree.command(name="raidmode", description="Turn raid mode on or off")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(state="on or off", minutes="Switch off automatically after this many minutes")
    async def raidmode(interaction: discord.Interaction, state: bool, minutes: app_commands.Range[int, 5, 1440] | None = None) -> None:
        by = f"{interaction.user.name} (/raidmode)"
        until = utcnow() + timedelta(minutes=minutes) if state and minutes else None
        with SessionLocal() as db:
            guild = _guild(db, interaction.guild_id)
            if guild is None:
                await interaction.response.send_message("This server isn't set up yet.", ephemeral=True)
                return
            guild_service.set_raid_mode(guild, state, until, "Enabled with /raidmode", by)
            db.add(AuditEntry(guild_id=guild.id, actor_id=str(interaction.user.id), actor_name=interaction.user.name,
                              action=f"raid_mode.{'enabled' if state else 'disabled'}", changes={"minutes": minutes}))
            db.add(SecurityEvent(guild_id=guild.id, type="moderation_action", module="raid_detection",
                                 severity="high" if state else "low", summary=f"Raid mode {'enabled' if state else 'disabled'} by {interaction.user.name}",
                                 action_taken="Logged", actions=[], notes=[], details={"source": "command"}))
            db.commit()
        bot.store.invalidate(str(interaction.guild_id))
        await interaction.response.send_message(f"Raid mode is now **{'ON' if state else 'off'}**.", ephemeral=True)

    @tree.command(name="warn", description="Warn a member by DM and log it")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    async def warn(interaction: discord.Interaction, member: discord.Member, reason: app_commands.Range[str, 3, 300]) -> None:
        delivered = await bot.executor.send_dm(str(member.id), f"⚠️ Warning from **{interaction.guild.name}** moderators: {reason}")
        with SessionLocal() as db:
            guild = _guild(db, interaction.guild_id)
            if guild is not None:
                db.add(ModerationLog(guild_id=guild.id, action="warn", target_id=str(member.id), target_name=member.name,
                                     moderator_id=str(interaction.user.id), moderator_name=interaction.user.name,
                                     source="command", reason=reason, status="done"))
                db.commit()
        note = "" if delivered else " (their DMs are closed, so it's logged only)"
        await interaction.response.send_message(f"Warned {member.mention}{note}.", ephemeral=True,
                                                allowed_mentions=discord.AllowedMentions.none())
