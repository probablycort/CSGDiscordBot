import discord
from discord.ext import commands
from discord.ext import tasks

import datetime
import sys
import logging
from itertools import cycle
from typing import Iterable, SupportsInt, Optional

log = logging.getLogger("CSGDiscordBot")


class CSGDiscordBot(commands.Bot):
    def __init__(
        self,
        intents: discord.Intents,
        statuses: Iterable,
        extensions: list,
        testing_guild: int = None,
        debug_mode: bool = False,
    ):
        self.is_restart = False
        self.platform = sys.platform
        self.testing_guild = int(testing_guild)
        self.debug_mode = debug_mode
        self.extensions_ = extensions
        self.statuses = cycle(statuses)
        self.start_time = discord.utils.utcnow()

        super().__init__(
            command_prefix=".",
            intents=intents,
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=False
            ),
        )

    @staticmethod
    def humanize_timedelta(
        *,
        timedelta: Optional[datetime.timedelta] = None,
        seconds: Optional[SupportsInt] = None,
    ) -> str:
        """
        Get a locale aware human timedelta representation.

        This works with either a timedelta object or a number of seconds.

        Fractional values will be omitted, and values less than 1 second
        an empty string.

        Parameters
        ----------
        timedelta: Optional[datetime.timedelta]
            A timedelta object
        seconds: Optional[SupportsInt]
            A number of seconds

        Returns
        -------
        str
            A locale aware representation of the timedelta or seconds.

        Raises
        ------
        ValueError
            The function was called with neither a number of seconds nor a timedelta object
        """

        try:
            obj = seconds if seconds is not None else timedelta.total_seconds()
        except AttributeError:
            raise ValueError(
                "You must provide either a timedelta or a number of seconds"
            )

        seconds = int(obj)
        periods = [
            ("year", "years", 60 * 60 * 24 * 365),
            ("month", "months", 60 * 60 * 24 * 30),
            ("day", "days", 60 * 60 * 24),
            ("hour", "hours", 60 * 60),
            ("minute", "minutes", 60),
            ("second", "seconds", 1),
        ]

        strings = []
        for period_name, plural_period_name, period_seconds in periods:
            if seconds >= period_seconds:
                period_value, seconds = divmod(seconds, period_seconds)
                if period_value == 0:
                    continue
                unit = plural_period_name if period_value > 1 else period_name
                strings.append(f"{period_value} {unit}")

        return ", ".join(strings)

    @tasks.loop(minutes=1)
    async def statusChanger(self):
        await self.wait_until_ready()
        status: str = next(self.statuses)
        await self.change_presence(activity=discord.Game(status))

    async def handle_error(
        self, ctx: discord.Interaction | commands.Context, exc: Exception
    ):

        if isinstance(exc, commands.CommandNotFound):
            return

        log.exception("Something went wrong trying to process something:", exc_info=exc)

        embed = discord.Embed(
            title="Sorry, an error occurred!",
            description=f"{exc.__class__.__name__}: {exc}",
            color=0xFF0000,
        )

        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                return await ctx.followup.send(embed=embed)
            else:
                return await ctx.response.send_message(embed=embed)
        else:
            return await ctx.reply(embed=embed, mention_author=False)

    async def setup_hook(self):

        for extension in self.extensions_:
            await self.load_extension("cogs." + extension)

        self.on_command_error = self.handle_error
        self.tree.error(self.handle_error)

        if self.platform == "windows":
            await self.load_extension("cogs.windows")
        else:
            log.warning("Not running on Windows. Windows-only commands disabled.")

        if self.debug_mode and self.testing_guild:

            guild = discord.Object(self.testing_guild)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

        self.statusChanger.start()

    async def on_ready(self):
        log.info(" Logged in as " + self.user.name)
        log.info(" Bot ID " + str(self.user.id))
        log.info(" Discord Version " + discord.__version__)
        if self.debug_mode:
            log.info(" RUNNING IN DEBUG MODE ")

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        content = message.content.lower()

        match content:
            case "probably cort":
                await message.channel.send(
                    "https://media.discordapp.net/attachments/763430451217432589/793847564045647872/unknown.png?width=130&height=177"
                )
            case "cantaloupe":
                await message.channel.send(
                    "https://cdn.discordapp.com/attachments/1079702225774972958/1148636977265123500/lv_0_20230804133527.mp4"
                )
            case "🧱":
                await message.channel.send("🧱")
            case ":bricks:":
                await message.channel.send("🧱")
            case "<:pomni:1164212247866912889><:pomni:1164212247866912889><:pomni:1164212247866912889>":
                await message.channel.send(
                    "https://tenor.com/view/pomni-digitalcircus-digital-circus-the-amazing-digital-circus-tadc-gif-87641691478271811"
                )
            case "<:pomni:1164212247866912889> <:pomni:1164212247866912889> <:pomni:1164212247866912889>":
                await message.channel.send(
                    "https://tenor.com/view/pomni-digitalcircus-digital-circus-the-amazing-digital-circus-tadc-gif-87641691478271811"
                )
            case self.user.mention:
                await message.channel.send(
                    """# Hello there!
My default prefix is `.` and cannot be changed. If you want to see commands that I can provide you with, do the `.help` command.
However, if you want to do my commands in DMs, do my commands on my DM!
-# v3.0 | https://bit.ly/CSGDiscordBot
"""
                )
            case "testwithoutprefix":
                await message.channel.send(
                    "```Command without prefix is functional.```"
                )
            case "ping":
                await message.channel.send("Pong")
            case "!barn":
                await message.channel.send("https://tenor.com/view/barn-gif-19719443")
            case _:
                pass

        await self.process_commands(message)
