from __future__ import annotations

import re
import sqlite3
import datetime
import logging
import discord
from discord import app_commands
from discord.ext import commands, tasks
from typing import Optional

from cogs.guild import Guild

log = logging.getLogger("CSGDiscordBot")

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTHS_SHORT = [m[:3] for m in MONTHS]
DEFAULT_MESSAGE = "Hope you have an awesome day! 🎈✨"


class Birthday(commands.Cog):
    """[EXPERIMENTAL, MAY NOT WORK] Cog for storing user birthdays, grouped under /birthday, running on server-configured timezones.
    Alias for this category is `.bd`.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "birthdays.db"
        self._init_db()

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Migrate the old schema, where user_id alone was the primary key
            # (which meant one birthday per user across ALL servers).
            migrate_from_old = False
            exists = cursor.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'birthdays'"
            ).fetchone()
            if exists:
                info = cursor.execute("PRAGMA table_info(birthdays)").fetchall()
                guild_pk = next((row[5] for row in info if row[1] == "guild_id"), 0)
                if guild_pk == 0:
                    cursor.execute("ALTER TABLE birthdays RENAME TO birthdays_old")
                    migrate_from_old = True

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS birthdays (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    day INTEGER NOT NULL,
                    channel_id INTEGER,
                    PRIMARY KEY (user_id, guild_id)
                )
                """
            )

            if migrate_from_old:
                # Rows registered in DMs have no guild and could never be announced, so they are dropped.
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO birthdays (user_id, guild_id, month, day, channel_id)
                    SELECT user_id, guild_id, month, day, channel_id
                    FROM birthdays_old WHERE guild_id IS NOT NULL
                    """
                )
                cursor.execute("DROP TABLE birthdays_old")

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
            # Remembers the last local date each server was announced, so nobody is announced twice.
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS birthday_announced (
                    guild_id INTEGER PRIMARY KEY,
                    last_date TEXT
                )
                """
            )
            conn.commit()

    def _get_guild_settings(self, guild_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT channel_id, ping_role_id, custom_message FROM birthday_settings WHERE guild_id = ?",
                (guild_id,),
            )
            return cursor.fetchone()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_manager(member: discord.Member) -> bool:
        perms = member.guild_permissions
        return perms.manage_guild or perms.manage_channels or perms.administrator

    @staticmethod
    def _parse_date(text: str) -> Optional[tuple[int, int, bool]]:
        """Parses 'MM/DD', 'MM-DD' or 'MM/DD/YYYY'. Returns (month, day, had_year) or None if invalid."""
        parts = re.split(r"[-/,\s]+", text.strip())
        if len(parts) not in (2, 3):
            return None
        try:
            month = int(parts[0])
            day = int(parts[1])
            year = int(parts[2]) if len(parts) == 3 else 2004  # 2004 is a leap year, so 2/29 is accepted
            datetime.date(year, month, day)
        except ValueError:
            return None
        return month, day, len(parts) == 3

    async def _resolve_channel(self, channel_id: Optional[int]):
        if not channel_id:
            return None
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                return None
        return channel

    async def _get_birthday_members(
        self, guild: discord.Guild, month: int, day: int
    ) -> list[discord.Member]:
        """Members of this guild whose birthday is on the given date (skips people who left the server)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id FROM birthdays WHERE month = ? AND day = ? AND guild_id = ?",
                (month, day, guild.id),
            )
            rows = cursor.fetchall()

        members = []
        for (user_id,) in rows:
            member = guild.get_member(user_id)
            if member is None:
                try:
                    member = await guild.fetch_member(user_id)
                except discord.NotFound:
                    continue  # no longer in the server
                except discord.HTTPException as e:
                    log.warning("[BIRTHDAY] Could not fetch member %s in guild %s: %s", user_id, guild.id, e)
                    continue
            members.append(member)
        return members

    async def _send_announcements(
        self,
        channel,
        members: list[discord.Member],
        date_str: str,
        settings,
        test_note: Optional[str] = None,
    ) -> int:
        """Sends one announcement embed per member. Returns how many were actually sent."""
        ping_role_id = settings[1] if settings else None
        template = settings[2] if settings and settings[2] else DEFAULT_MESSAGE

        sent = 0
        for i, member in enumerate(members):
            description = template.replace("{user}", member.mention).replace("{date}", date_str)
            if test_note:
                description += f" *({test_note})*"

            # Mentions never render inside embed titles, so use the display name there.
            embed = discord.Embed(
                title=f"{'[TEST] ' if test_note else ''}🎉 Happy Birthday, {member.display_name}! 🎂",
                description=description,
                color=0xFEE75C,
            )
            embed.set_thumbnail(url=member.display_avatar.url)

            # The bot's global AllowedMentions blocks role pings, so allow exactly this one role.
            # Only ping on the first message of a batch, and never on tests.
            content = None
            allowed = discord.AllowedMentions.none()
            if ping_role_id and not test_note and i == 0:
                content = f"<@&{ping_role_id}>"
                allowed = discord.AllowedMentions(roles=[discord.Object(id=ping_role_id)])

            try:
                await channel.send(content=content, embed=embed, allowed_mentions=allowed)
                sent += 1
            except discord.HTTPException as e:
                log.warning("[BIRTHDAY] Could not send announcement in channel %s: %s", getattr(channel, "id", "?"), e)
        return sent

    # ------------------------------------------------------------------
    # Daily check
    # ------------------------------------------------------------------
    async def cog_load(self):
        self.daily_birthday_check.start()

    def cog_unload(self):
        self.daily_birthday_check.cancel()

    @tasks.loop(minutes=15)
    async def daily_birthday_check(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT guild_id FROM birthdays UNION SELECT guild_id FROM birthday_settings"
                )
                guild_ids = [row[0] for row in cursor.fetchall()]
        except Exception:
            log.exception("[BIRTHDAY] Failed to read guild list")
            return

        for guild_id in guild_ids:
            if not guild_id:
                continue
            # One broken server must never stop the task for everyone else.
            try:
                await self._check_guild(guild_id)
            except Exception:
                log.exception("[BIRTHDAY] Failed to process guild %s", guild_id)

    @daily_birthday_check.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    async def _check_guild(self, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return

        now_local = datetime.datetime.now(Guild.get_timezone(guild_id))
        today = now_local.date().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_date FROM birthday_announced WHERE guild_id = ?", (guild_id,)
            )
            row = cursor.fetchone()
        if row and row[0] == today:
            return  # already announced today

        settings = self._get_guild_settings(guild_id)
        channel = await self._resolve_channel(settings[0] if settings else None)
        if channel is None:
            return  # no announcement channel configured/reachable; try again on the next tick

        members = await self._get_birthday_members(guild, now_local.month, now_local.day)
        if members:
            date_str = f"{MONTHS[now_local.month - 1]} {now_local.day}"
            await self._send_announcements(channel, members, date_str, settings)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO birthday_announced (guild_id, last_date) VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET last_date = excluded.last_date
                """,
                (guild_id, today),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    @commands.hybrid_group(name="birthday", aliases=["bd"], description="Manage and view birthday reminders")
    @commands.guild_only()
    async def birthday_group(self, ctx: commands.Context):
        """Parent command group for birthdays."""
        if ctx.invoked_subcommand is None:
            await ctx.reply(
                "ℹ️ Use `/birthday register`, `/birthday show`, `/birthday list`, `/birthday remove`, or `/birthday set ...`.",
                mention_author=False,
            )

    @birthday_group.group(name="set", description="Configure birthday settings for this server - MANAGER ONLY")
    async def set_group(self, ctx: commands.Context):
        """Subcommand group for managing server settings."""
        if ctx.invoked_subcommand is None:
            await ctx.reply(
                "ℹ️ Use `/birthday set channel`, `/birthday set ping`, or `/birthday set message`.",
                mention_author=False,
            )

    @set_group.command(name="channel", description="Set the default channel for birthday announcements")
    @app_commands.describe(channel="The channel where announcements should post")
    async def set_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the announcement channel for this server."""
        if not self._is_manager(ctx.author):
            return await ctx.reply("❌ You need Manager permissions to set the announcement channel.", mention_author=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO birthday_settings (guild_id, channel_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id
                """,
                (ctx.guild.id, channel.id),
            )
            conn.commit()

        await ctx.reply(f"📢 Birthday announcements for this server will now post in {channel.mention}!", mention_author=False)

    @set_group.command(name="ping", description="Set a role to ping on birthday announcements")
    @app_commands.describe(role="The role to tag, or leave empty to clear the ping role")
    async def set_ping(self, ctx: commands.Context, role: Optional[discord.Role] = None):
        """Configures or clears the role pinged during birthday announcements."""
        if not self._is_manager(ctx.author):
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
                (ctx.guild.id, role_id),
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
        if not self._is_manager(ctx.author):
            return await ctx.reply("❌ You need Manager permissions to edit the announcement message.", mention_author=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO birthday_settings (guild_id, custom_message)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET custom_message = excluded.custom_message
                """,
                (ctx.guild.id, message),
            )
            conn.commit()

        preview = message.replace("{user}", ctx.author.mention).replace("{date}", "May 20")
        await ctx.reply(f"✏️ Updated custom birthday message! Preview:\n>>> {preview}", mention_author=False)

    @birthday_group.command(name="register", description="Register a new Birthday")
    @app_commands.describe(date="Your birthday (e.g., 5/20, 05-20, or 5/20/2000)")
    async def register(self, ctx: commands.Context, *, date: str):
        """Register your birthday supporting slashes, hyphens, or spaces (with optional year)."""
        parsed = self._parse_date(date)
        if parsed is None:
            return await ctx.reply(
                "❌ Invalid date! Please use `MM/DD`, `MM-DD`, or include the year (e.g., `5/20/2000`).",
                mention_author=False,
            )
        month, day, had_year = parsed

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO birthdays (user_id, guild_id, month, day, channel_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    month = excluded.month,
                    day = excluded.day,
                    channel_id = excluded.channel_id
                """,
                (ctx.author.id, ctx.guild.id, month, day, ctx.channel.id),
            )
            conn.commit()

        date_str = f"{MONTHS_SHORT[month - 1]} {day}"
        note = " (Only the month and day are saved, not the year.)" if had_year else ""
        await ctx.reply(f"🎂 Registered your birthday as **{date_str}**!{note}", mention_author=False)

    @birthday_group.command(name="show", description="Show the Birthday of you or another person")
    @app_commands.describe(user="The user whose birthday you want to check")
    async def show(self, ctx: commands.Context, user: Optional[discord.User] = None):
        """Displays saved birthday information for yourself or another user."""
        target = user or ctx.author

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT month, day FROM birthdays WHERE user_id = ? AND guild_id = ?",
                (target.id, ctx.guild.id),
            )
            result = cursor.fetchone()

        if not result:
            msg = (
                "You haven't registered your birthday yet! Use `birthday register MM-DD`."
                if target.id == ctx.author.id
                else f"**{target.display_name}** hasn't registered their birthday yet."
            )
            return await ctx.reply(f"❌ {msg}", mention_author=False)

        month, day = result
        date_str = f"{MONTHS[month - 1]} {day}"

        embed = discord.Embed(
            title="🎂 Birthday Record",
            description=f"**{target.display_name}**'s birthday is on **{date_str}**!",
            color=0x5865F2,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @birthday_group.command(name="list", description="List all Birthdays in this Discord server")
    async def list_birthdays(self, ctx: commands.Context):
        """Lists registered birthdays for members in the current server."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, month, day FROM birthdays WHERE guild_id = ? ORDER BY month ASC, day ASC",
                (ctx.guild.id,),
            )
            records = cursor.fetchall()

        if not records:
            return await ctx.reply("ℹ️ No birthdays registered in this server yet.", mention_author=False)

        lines = []
        total_chars = 0
        for user_id, month, day in records:
            # Without the Members intent the member cache is incomplete, so fall back to the user cache.
            member = ctx.guild.get_member(user_id) or self.bot.get_user(user_id)
            name = member.display_name if member else f"User ID: {user_id}"
            line = f"• **{name}** — `{MONTHS_SHORT[month - 1]} {day:02d}`"
            if total_chars + len(line) + 1 > 3800:  # embed descriptions max out at 4096 characters
                break
            lines.append(line)
            total_chars += len(line) + 1

        hidden = len(records) - len(lines)
        if hidden > 0:
            lines.append(f"*...and {hidden} more*")

        embed = discord.Embed(
            title=f"🎂 Server Birthdays ({len(records)})",
            description="\n".join(lines),
            color=0x5865F2,
        )
        await ctx.reply(embed=embed, mention_author=False)

    @birthday_group.command(name="remove", description="Remove your birthday (managers can remove anyone's)")
    @app_commands.describe(user="The user whose birthday to remove (defaults to you)")
    async def remove(self, ctx: commands.Context, user: Optional[discord.User] = None):
        """Removes a birthday entry. Anyone can remove their own; removing someone else's needs Manager permissions."""
        target = user or ctx.author

        if target.id != ctx.author.id and not self._is_manager(ctx.author):
            return await ctx.reply(
                "❌ You need Manager permissions (`Manage Server` or `Manage Channels`) to remove someone else's birthday.",
                mention_author=False,
            )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM birthdays WHERE user_id = ? AND guild_id = ?",
                (target.id, ctx.guild.id),
            )
            removed = cursor.rowcount
            conn.commit()

        if removed == 0:
            return await ctx.reply(f"ℹ️ **{target.display_name}** doesn't have a birthday registered here.", mention_author=False)

        await ctx.reply(f"🗑️ Removed birthday record for **{target.display_name}**.", mention_author=False)

    @birthday_group.command(name="test", description="Test birthday announcements for today or a specific date - MANAGER ONLY")
    @app_commands.describe(
        date="Optional date to test (e.g., 5/20 or 5/20/2000), defaults to today",
        channel="Optional target channel to send the test message to",
    )
    async def test(self, ctx: commands.Context, date: Optional[str] = None, channel: Optional[discord.TextChannel] = None):
        """Sends a test announcement for a date. Uses real registered birthdays if any match, otherwise you as a placeholder."""
        if not self._is_manager(ctx.author):
            return await ctx.reply("❌ You need Manager permissions to run a birthday test.", mention_author=False)

        if date:
            parsed = self._parse_date(date)
            if parsed is None:
                return await ctx.reply("❌ Invalid date! Please use `MM/DD` (e.g., `5/20`).", mention_author=False)
            month, day, _ = parsed
        else:
            now_local = datetime.datetime.now(Guild.get_timezone(ctx.guild.id))
            month, day = now_local.month, now_local.day

        date_str = f"{MONTHS[month - 1]} {day}"
        settings = self._get_guild_settings(ctx.guild.id)

        target_ch = channel or await self._resolve_channel(settings[0] if settings else None) or ctx.channel

        await ctx.reply(f"⚙️ Running birthday test for **{date_str}** in {target_ch.mention}...", mention_author=False)

        members = await self._get_birthday_members(ctx.guild, month, day)
        if members:
            note = f"Test run for {date_str}"
        else:
            members = [ctx.author]
            note = f"Placeholder test for {date_str}, no birthdays are registered on this date"

        sent = await self._send_announcements(target_ch, members, date_str, settings, test_note=note)
        if sent == 0:
            await ctx.send("❌ I couldn't send the test message. Check that I can send messages and embed links in that channel.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Birthday(bot))