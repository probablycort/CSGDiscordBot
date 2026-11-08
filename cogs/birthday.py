from __future__ import annotations

import sqlite3
import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional
from cogs.guild import Guild


class Birthday(commands.Cog):
    """Cog for storing user birthdays, grouped under /birthday, running on server-configured timezones."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "birthdays.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS birthdays (
                    user_id INTEGER PRIMARY KEY,
                    guild_id INTEGER,
                    month INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    channel_id INTEGER
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS birthday_settings (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    ping_role_id INTEGER,
                    custom_message TEXT
                )
                """
            )
            conn.commit()

    async def cog_load(self):
        self.daily_birthday_check.start()

    def cog_unload(self):
        self.daily_birthday_check.cancel()

    @tasks.loop(minutes=30)
    async def daily_birthday_check(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT guild_id FROM birthdays UNION SELECT DISTINCT guild_id FROM birthday_settings")
            guilds = cursor.fetchall()

        for (guild_id,) in guilds:
            if not guild_id:
                continue
            guild_tz = Guild.get_timezone(guild_id)
            now_local = datetime.datetime.now(guild_tz)
            
            if now_local.hour == 0:
                await self._process_birthday_announcements(now_local.month, now_local.day, guild_id=guild_id)

    @daily_birthday_check.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    def _get_guild_settings(self, guild_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT channel_id, ping_role_id, custom_message FROM birthday_settings WHERE guild_id = ?",
                (guild_id,)
            )
            return cursor.fetchone()

    async def _process_birthday_announcements(self, month: int, day: int, target_channel: Optional[discord.TextChannel] = None, is_test: bool = False, test_member: Optional[discord.Member] = None, guild_id: Optional[int] = None):
        target_guild_id = guild_id or (target_channel.guild.id if target_channel else None)
        settings = self._get_guild_settings(target_guild_id) if target_guild_id else None

        channel = target_channel
        if not channel and target_guild_id:
            cfg_channel_id = settings[0] if settings else None
            if cfg_channel_id:
                channel = self.bot.get_channel(cfg_channel_id) or await self.bot.fetch_channel(cfg_channel_id)

        ping_role_id = settings[1] if settings else None
        custom_msg_template = settings[2] if settings and settings[2] else "Hope you have an awesome day! 🎈✨"

        months_fmt = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        date_str = f"{months_fmt[month - 1]} {day}"

        if is_test:
            users_to_test = [test_member] if test_member else []
        else:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id FROM birthdays WHERE month = ? AND day = ? AND guild_id = ?",
                    (month, day, target_guild_id)
                )
                birthday_users = cursor.fetchall()
            
            users_to_test = []
            for (u_id,) in birthday_users:
                u = self.bot.get_user(u_id) or await self.bot.fetch_user(u_id)
                if u:
                    users_to_test.append(u)

        if not users_to_test and channel and not is_test:
            return

        for user in users_to_test:
            if not channel:
                continue

            formatted_desc = custom_msg_template.replace("{user}", user.mention).replace("{date}", date_str)
            if is_test:
                formatted_desc += f" *(Placeholder Test for {date_str})*"

            content = f"<@&{ping_role_id}>" if ping_role_id else None

            title_prefix = "[TEST] " if is_test else ""
            embed = discord.Embed(
                title=f"{title_prefix}🎉 Happy Birthday, {user.mention}! 🎂",
                description=formatted_desc,
                color=0xFEE75C
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            try:
                await channel.send(content=content, embed=embed)
            except discord.HTTPException:
                pass

    # Hybrid Group Parent
    @commands.hybrid_group(name="birthday", aliases=["bd"], description="Manage and view birthday reminders")
    async def birthday_group(self, ctx: commands.Context):
        """Parent command group for birthdays."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @birthday_group.group(name="set", description="Configure birthday settings for this server - MANAGER ONLY")
    async def set_group(self, ctx: commands.Context):
        """Subcommand group for managing server settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @set_group.command(name="channel", description="Set the default channel for birthday announcements")
    @app_commands.describe(channel="The channel where announcements should post")
    async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the announcement channel for this server."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_channels or perms.administrator):
            return await ctx.reply("❌ You need Manager permissions to set the announcement channel.", mention_author=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO birthday_settings (guild_id, channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id
                """,
                (ctx.guild.id, channel.id)
            )
            conn.commit()

        await ctx.reply(f"📢 Birthday announcements for this server will now post in {channel.mention}!", mention_author=False)

    @set_group.command(name="ping", description="Set a role to ping on birthday announcements")
    @app_commands.describe(role="The role to tag, or leave empty to clear the ping role")
    async def set_ping(self, ctx: commands.Context, role: Optional[discord.Role] = None):
        """Configures or clears the role pinged during birthday announcements."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_channels or perms.administrator):
            return await ctx.reply("❌ You need Manager permissions to set the ping role.", mention_author=False)

        role_id = role.id if role else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO birthday_settings (guild_id, ping_role_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET ping_role_id = excluded.ping_role_id
                """,
                (ctx.guild.id, role_id)
            )
            conn.commit()

        if role:
            await ctx.reply(f"🔔 Birthday announcements will now ping {role.mention}!", mention_author=False)
        else:
            await ctx.reply("🔕 Cleared the birthday announcement role ping.", mention_author=False)

    @set_group.command(name="message", description="Set a custom announcement message template")
    @app_commands.describe(message="Custom message template. Use {user} to mention the user and {date} for the date.")
    async def set_message(self, ctx: commands.Context, *, message: str):
        """Configures the announcement message template for this server."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_channels or perms.administrator):
            return await ctx.reply("❌ You need Manager permissions to edit the announcement message.", mention_author=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO birthday_settings (guild_id, custom_message)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET custom_message = excluded.custom_message
                """,
                (ctx.guild.id, message)
            )
            conn.commit()

        await ctx.reply(f"✏️ Updated custom birthday message! Preview:\n>>> {message.replace('{user}', ctx.author.mention).replace('{date}', 'May 20')}", mention_author=False)

    @birthday_group.command(name="register", description="Register a new Birthday")
    @app_commands.describe(date="Your birthday (e.g., 5/20, 05-20, or 5/20/2000)")
    async def register(self, ctx: commands.Context, *, date: str):
        """Register your birthday supporting slashes, hyphens, or spaces (with optional year)."""
        import re
        parts = re.split(r'[-/,\s]+', date.strip())

        if len(parts) < 2 or len(parts) > 3:
            return await ctx.reply("❌ Invalid format! Please use `MM/DD`, `MM-DD`, or include the year (e.g., `5/20/2000`).", mention_author=False)

        try:
            month = int(parts[0])
            day = int(parts[1])
            year = int(parts[2]) if len(parts) == 3 else None

            check_year = year if year is not None else 2004
            datetime.date(check_year, month, day)
        except ValueError:
            return await ctx.reply("❌ Invalid date! Please provide a valid Month (1-12) and Day.", mention_author=False)

        guild_id = ctx.guild.id if ctx.guild else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO birthdays (user_id, guild_id, month, day, channel_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    guild_id = excluded.guild_id,
                    month = excluded.month,
                    day = excluded.day,
                    channel_id = excluded.channel_id
                """,
                (ctx.author.id, guild_id, month, day, ctx.channel.id)
            )
            conn.commit()

        months_fmt = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        date_str = f"{months_fmt[month - 1]} {day}" + (f", {year}" if year else "")

        await ctx.reply(f"🎂 Registered your birthday as **{date_str}**!", mention_author=False)

    @birthday_group.command(name="show", description="Show the Birthday of you or another person")
    @app_commands.describe(user="The user whose birthday you want to check")
    async def show(self, ctx: commands.Context, user: Optional[discord.User] = None):
        """Displays saved birthday information for yourself or another user."""
        target = user or ctx.author

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT month, day FROM birthdays WHERE user_id = ?", (target.id,))
            result = cursor.fetchone()

        if not result:
            msg = "You haven't registered your birthday yet! Use `birthday register MM-DD`." if target == ctx.author else f"**{target.display_name}** hasn't registered their birthday yet."
            return await ctx.reply(f"❌ {msg}", mention_author=False)

        month, day = result
        months_fmt = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        date_str = f"{months_fmt[month - 1]} {day}"

        embed = discord.Embed(
            title="🎂 Birthday Record",
            description=f"**{target.display_name}**'s birthday is on **{date_str}**!",
            color=0x5865F2
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @birthday_group.command(name="list", description="List all Birthdays in this Discord server")
    async def list_birthdays(self, ctx: commands.Context):
        """Lists registered birthdays for members in the current server."""
        if not ctx.guild:
            return await ctx.reply("❌ This command can only be used in a server.", mention_author=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, month, day FROM birthdays WHERE guild_id = ? ORDER BY month ASC, day ASC", (ctx.guild.id,))
            records = cursor.fetchall()

        if not records:
            return await ctx.reply("ℹ️ No birthdays registered in this server yet.", mention_author=False)

        months_fmt = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        bday_lines = []

        for user_id, month, day in records:
            member = ctx.guild.get_member(user_id)
            name = member.display_name if member else f"User ID: {user_id}"
            bday_lines.append(f"• **{name}** — `{months_fmt[month - 1]} {day:02d}`")

        embed = discord.Embed(
            title=f"🎂 Server Birthdays ({len(records)})",
            description="\n".join(bday_lines[:25]),
            color=0x5865F2
        )
        await ctx.reply(embed=embed, mention_author=False)

    @birthday_group.command(name="remove", description="Remove a birthday - MANAGER ONLY")
    @app_commands.describe(user="The user whose birthday to remove")
    async def remove(self, ctx: commands.Context, user: discord.User):
        """Removes a user's birthday entry (restricted to managers)."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_channels or perms.administrator):
            return await ctx.reply("❌ You need Manager permissions (`Manage Server` or `Manage Channels`) to use this command.", mention_author=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM birthdays WHERE user_id = ?", (user.id,))
            conn.commit()

        await ctx.reply(f"🗑️ Removed birthday record for **{user.display_name}**.", mention_author=False)

    @birthday_group.command(name="test", description="Test birthday announcements for today or a specific date")
    @app_commands.describe(
        date="Optional date to test (e.g., 5/20 or 5/20/2000), defaults to today",
        channel="Optional target channel to send the test message to"
    )
    async def test(self, ctx: commands.Context, date: Optional[str] = None, channel: Optional[discord.TextChannel] = None):
        """Simulates checking birthdays immediately for a specified date and optional channel."""
        import re
        
        test_date = None
        if date:
            parts = re.split(r'[-/,\s]+', date.strip())
            if len(parts) >= 2:
                try:
                    month = int(parts[0])
                    day = int(parts[1])
                    check_year = int(parts[2]) if len(parts) > 2 else 2004
                    datetime.date(check_year, month, day)
                    test_date = datetime.datetime(2004, month, day, tzinfo=datetime.timezone.utc)
                except ValueError:
                    pass

        if not test_date:
            guild_tz = Guild.get_timezone(ctx.guild.id if ctx.guild else None)
            test_date = datetime.datetime.now(guild_tz)

        months_fmt = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        date_str = f"{months_fmt[test_date.month - 1]} {test_date.day}"

        guild_id = ctx.guild.id if ctx.guild else None
        settings = self._get_guild_settings(guild_id) if guild_id else None
        cfg_channel_id = settings[0] if settings else None
        
        target_ch = channel
        if not target_ch and cfg_channel_id:
            target_ch = self.bot.get_channel(cfg_channel_id) or await self.bot.fetch_channel(cfg_channel_id)
        if not target_ch:
            target_ch = ctx.channel

        await ctx.reply(f"⚙️ Running birthday test check for **{date_str}** in {target_ch.mention}...", mention_author=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM birthdays WHERE month = ? AND day = ?",
                (test_date.month, test_date.day)
            )
            records = cursor.fetchall()

        if records:
            await self._process_birthday_announcements(test_date.month, test_date.day, target_channel=target_ch, is_test=True, guild_id=guild_id)
        else:
            await self._process_birthday_announcements

async def setup(bot: commands.Bot):
    await bot.add_cog(Birthday(bot))