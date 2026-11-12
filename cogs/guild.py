from __future__ import annotations

import sqlite3
import pytz
import discord
from discord import app_commands
from discord.ext import commands

import logging
import json
import os

from datetime import datetime, timezone, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from bot import CSGDiscordBot

log = logging.getLogger("CSGDiscordBot")


# Helper functions to manage saved server settings (from owner.py)
def load_settings():
    if not os.path.exists("guild_settings.json"):
        return {}
    with open("guild_settings.json", "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_settings(data):
    with open("guild_settings.json", "w") as f:
        json.dump(data, f, indent=4)


class Guild(commands.Cog):
    """Server management and configuration commands for owners and moderators."""

    def __init__(self, bot: CSGDiscordBot):
        self.bot = bot
        self.db_path = "bot_settings.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS server_settings (
                    guild_id INTEGER PRIMARY KEY,
                    timezone TEXT DEFAULT 'Asia/Kuala_Lumpur',
                    prefixless_enabled INTEGER DEFAULT 1
                )
                """
            )
            try:
                cursor.execute("ALTER TABLE server_settings ADD COLUMN prefixless_enabled INTEGER DEFAULT 1")
            except sqlite3.OperationalError:
                pass
            conn.commit()

    @staticmethod
    def get_timezone(guild_id: Optional[int], db_path: str = "bot_settings.db") -> datetime.tzinfo:
        """Static helper for any cog to fetch a server's configured timezone (defaults to UTC+8 / Malaysia)."""
        if not guild_id:
            return timezone(timedelta(hours=8))
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT timezone FROM server_settings WHERE guild_id = ?", (guild_id,))
            row = cursor.fetchone()
            
        tz_str = row[0] if row and row[0] else 'Asia/Kuala_Lumpur'
        try:
            return pytz.timezone(tz_str)
        except Exception:
            return timezone(timedelta(hours=8))

    @staticmethod
    def is_prefixless_enabled(guild_id: Optional[int], db_path: str = "bot_settings.db") -> bool:
        """Static helper to check if prefixless commands are enabled for a server."""
        if not guild_id:
            return True
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT prefixless_enabled FROM server_settings WHERE guild_id = ?", (guild_id,))
            row = cursor.fetchone()
        if row is not None and row[0] is not None:
            return bool(row[0])
        return True

    async def send_mod_log(self, guild: discord.Guild, title: str, color: int, target, moderator: discord.abc.User, reason: str):
        settings = load_settings()
        log_channel_id = settings.get(str(guild.id))
        if not log_channel_id:
            return
        channel = self.bot.get_channel(log_channel_id)
        if not channel:
            return
        embed = discord.Embed(
            title=f"{title}",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Target", value=f"{target} (`{target.id}`)", inline=False)
        embed.add_field(name="Moderator", value=f"{moderator} (`{moderator.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        if hasattr(target, "avatar") and target.avatar:
            embed.set_thumbnail(url=target.avatar.url)
        await channel.send(embed=embed)

    @commands.hybrid_command(name="timezone", description="Set the server's local timezone - MANAGER ONLY")
    @app_commands.describe(timezone_str="Valid timezone name (e.g., Asia/Kuala_Lumpur, America/New_York, UTC)")
    async def set_timezone(self, ctx: commands.Context, timezone_str: str):
        """Sets the operating timezone for server-based scheduling and commands."""
        if not ctx.guild:
            return await ctx.reply("❌ This command can only be used in a server.", mention_author=False)

        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.administrator):
            return await ctx.reply("❌ You need Manager permissions to change the server timezone.", mention_author=False)

        if timezone_str not in pytz.all_timezones:
            return await ctx.reply(f"❌ Invalid timezone! Please use a valid tz database name (e.g., `Asia/Kuala_Lumpur`, `UTC`).", mention_author=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO server_settings (guild_id, timezone)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET timezone = excluded.timezone
                """,
                (ctx.guild.id, timezone_str)
            )
            conn.commit()

        await ctx.reply(f"🌍 Server timezone successfully updated to **{timezone_str}**!", mention_author=False)

    @commands.hybrid_command(name="prefixless", description="Enable or disable prefixless trigger commands - ADMIN / BOT OWNER ONLY")
    @app_commands.describe(status="Choose whether to enable or disable prefixless commands")
    async def prefixless(self, ctx: commands.Context, status: Optional[bool] = None):
        """Enables or disables prefixless message trigger responses in this server."""
        if ctx.guild:
            is_owner = await self.bot.is_owner(ctx.author)
            is_guild_admin = ctx.author.id == ctx.guild.owner_id or ctx.author.guild_permissions.administrator
            if not is_owner and not is_guild_admin:
                return await ctx.reply("❌ You must be a server administrator or the bot owner to use this command.", mention_author=False)
        else:
            is_owner = await self.bot.is_owner(ctx.author)
            if not is_owner:
                return await ctx.reply("❌ This command can only be used in a server by an administrator.", mention_author=False)

        guild_id = ctx.guild.id
        current_status = self.is_prefixless_enabled(guild_id, self.db_path)
        new_status = status if status is not None else not current_status

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO server_settings (guild_id, prefixless_enabled)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET prefixless_enabled = excluded.prefixless_enabled
                """,
                (guild_id, int(new_status))
            )
            conn.commit()

        state_str = "**enabled**" if new_status else "**disabled**"
        await ctx.reply(f"✅ Prefixless trigger commands have been {state_str} for this server.", mention_author=False)

    @commands.has_permissions(manage_emojis=True)
    @commands.command()
    async def dm(self, ctx: commands.Context, user: discord.User, *, content: str):
        try:
            embed = discord.Embed(
                title=f"Message from {ctx.guild.name}",
                description=content,
                color=0xcba6f7
            )
            embed.set_footer(text=f"Sent by {ctx.author.name}")
            await user.send(embed=embed)
            await ctx.send(f"✅ Message successfully sent to **{user}**!")
            log.info("[LOG] %s sent a DM to %s: %s", ctx.author, user, content)
        except discord.Forbidden:
            await ctx.send(f"❌ Unable to DM **{user}**, likely have their DMs disabled.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: \n{e}")

    @commands.has_permissions(administrator=True)
    @commands.hybrid_command(name="setlogchannel", description="Set the moderation log channel for this server")
    @app_commands.describe(channel="The text channel to send moderation logs to")
    async def setlogchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        settings = load_settings()
        settings[str(ctx.guild.id)] = channel.id
        save_settings(settings)
        
        await ctx.reply(f"✅ Successfully set the moderation log channel to {channel.mention}!", ephemeral=True)
        log.info("[CONFIG] Moderation log channel set to %s (%d) in guild %s", channel.name, channel.id, ctx.guild.name)

    @commands.has_permissions(kick_members=True)
    @commands.hybrid_command(name="warn", description="Issue a warning to a server member")
    @app_commands.describe(member="The member to warn", reason="The reason for the warning")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        try:
            embed = discord.Embed(
                title=f"You have been warned from {ctx.guild.name}",
                description=f"**Reason:** {reason}",
                color=0xFEE75C
            )
            embed.set_footer(text=f"Issued by {ctx.author.name}")
            await member.send(embed=embed)
            dm_status = f"**{member}** has been warned successfully."
        except discord.Forbidden:
            dm_status = "⚠️ Could not DM member (DMs disabled)."
        await ctx.reply(f"{dm_status}")
        log.info("[MOD WARN] %s warned %s: %s", ctx.author, member, reason)
        await self.send_mod_log(ctx.guild, title="Member Warned", color=0xFEE75C, target=member, moderator=ctx.author, reason=reason)

    @commands.has_permissions(kick_members=True)
    @commands.hybrid_command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="The reason for the kick")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("❌ You cannot kick someone with an equal or higher role.")
        try:
            embed = discord.Embed(
                title=f"You have been kicked from {ctx.guild.name}",
                description=f"**Reason:** {reason}",
                color=0xED4245
            )
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        try:
            await member.kick(reason=f"{reason} (Issued by {ctx.author})")
            await ctx.reply(f"**{member}** has been kicked from the server!\n**Reason:** {reason}")
            log.info("[MOD KICK] %s kicked %s: %s", ctx.author, member, reason)
            await self.send_mod_log(ctx.guild, title="Member Kicked", color=0xED4245, target=member, moderator=ctx.author, reason=reason)
        except discord.Forbidden:
            await ctx.reply("❌ I do not have permission to kick this member.")

    @commands.has_permissions(ban_members=True)
    @commands.hybrid_command(name="ban", description="Ban a user from the server")
    @app_commands.describe(user="The user to ban", reason="The reason for the ban")
    async def ban(self, ctx: commands.Context, user: discord.User, *, reason: str = "No reason provided"):
        member = ctx.guild.get_member(user.id)
        if member and member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("❌ You cannot ban someone with an equal or higher role.")
        if member:
            try:
                embed = discord.Embed(
                    title=f"You have been banned from {ctx.guild.name}",
                    description=f"**Reason:** {reason}",
                    color=0x992D22
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
        try:
            await ctx.guild.ban(user, reason=f"{reason} (Issued by {ctx.author})")
            await ctx.reply(f"**{user}** has been banned!\n**Reason:** {reason}")
            log.info("[MOD BAN] %s banned %s: %s", ctx.author, user, reason)
            await self.send_mod_log(ctx.guild, title="Member Banned", color=0x992D22, target=user, moderator=ctx.author, reason=reason)
        except discord.Forbidden:
            await ctx.reply("❌ I do not have permission to ban this user.")


async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Guild(bot))