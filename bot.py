import discord
from discord.ext import commands
from discord.ext import tasks

import datetime
import sys
import os
import logging
import asyncio
from itertools import cycle
from typing import Iterable, SupportsInt, Optional

from config import (
    PREFIX,
    VERSION,
    NORMAL_STATUSES,
    LYRICS,
    NORMAL_DELAY,
    LYRIC_DELAY,
    STICKER_TRIGGERS,
    TRACKER_WARNINGS,
    check_battery_trigger,
    get_match_response,
)

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
        self.testing_guild = testing_guild
        self.debug_mode = debug_mode
        self.extensions_ = extensions
        self.start_time = discord.utils.utcnow()

        # Dictionary to track active tracker warnings
        self.active_warnings = {}

        # Status cycles
        self.normal_statuses = cycle(NORMAL_STATUSES)
        self.lyric_statuses = cycle(LYRICS)

        # Dynamically determine the last lyric line as the exit trigger
        self.last_lyric_line = LYRICS[-1] if LYRICS else None
        self.lyric_mode = False

        super().__init__(
            command_prefix=PREFIX,
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

    @tasks.loop(seconds=1)
    async def statusChanger(self):
        await self.wait_until_ready()

        if self.lyric_mode:
            status = next(self.lyric_statuses)
            delay = LYRIC_DELAY

            if status == self.last_lyric_line:
                self.lyric_mode = False
        else:
            status = next(self.normal_statuses)
            delay = NORMAL_DELAY

            if status == "...":
                self.lyric_mode = True

        await self.change_presence(activity=discord.CustomActivity(name=status))
        await asyncio.sleep(delay)

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

        if self.platform == "win32":
            await self.load_extension("cogs.windows")
            log.info("Running on Windows. Loaded cogs.windows.")
        else:
            await self.load_extension("cogs.linux")
            log.info("Running on Linux/Unix. Loaded cogs.linux.")

        if self.debug_mode and self.testing_guild:
            guild = discord.Object(int(self.testing_guild))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

        self.statusChanger.start()

    async def on_ready(self):
        log.info(" Logged in as " + self.user.name)
        log.info(" Bot ID " + str(self.user.id))
        log.info(" Discord Version " + discord.__version__)
        if self.debug_mode:
            log.info(" RUNNING IN DEBUG MODE ")

        if os.path.exists("restart.txt"):
            try:
                with open("restart.txt", "r") as f:
                    lines = f.read().splitlines()
                    if len(lines) >= 2:
                        channel_id = int(lines[0])
                        message_id = int(lines[1])
                        
                        channel = self.get_channel(channel_id)
                        if channel:
                            try:
                                msg = await channel.fetch_message(message_id)
                                await msg.edit(content="✅ Bot has been restarted successfully and is back online!")
                            except discord.NotFound:
                                await channel.send("✅ Bot has been restarted successfully and is back online!")
            except Exception as e:
                log.error(f"Failed to send restart message: {e}")
            finally:
                os.remove("restart.txt")

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        content = message.content.lower()

        # Sticker triggers configured in config.py
        for trigger, sticker_id in STICKER_TRIGGERS.items():
            if trigger in content:
                sticker = self.get_sticker(sticker_id)
                if sticker:
                    return await message.reply(stickers=[sticker], mention_author=False)

        # Tracker warnings configured in config.py
        for tracker_param, warning_data in TRACKER_WARNINGS.items():
            if tracker_param in content:
                embed = discord.Embed(
                    title=warning_data["title"],
                    description=warning_data["description"],
                    color=warning_data["color"]
                )
                warning = await message.reply(embed=embed, mention_author=False)
                self.active_warnings[message.id] = warning
                return await self.process_commands(message)

        # Battery pattern response configured in config.py
        battery_response = check_battery_trigger(content)
        if battery_response:
            return await message.channel.send(battery_response)

        # Match case responses configured in config.py
        match_response = get_match_response(content, self.user.mention.lower())
        if match_response:
            await message.channel.send(match_response)

        await self.process_commands(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.id in self.active_warnings:
            new_content = after.content.lower()
            if "?si=" not in new_content and "?a=" not in new_content:
                warning_msg = self.active_warnings[before.id]
                try:
                    await warning_msg.delete()
                except discord.HTTPException:
                    pass

                del self.active_warnings[before.id]