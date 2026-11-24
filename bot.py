import discord
from discord.ext import commands
from discord.ext import tasks

import datetime
import sys
import os
import logging
import asyncio
import aiohttp
import re
from collections import OrderedDict
from itertools import cycle
from typing import Iterable, SupportsInt, Optional

from config import (
    PREFIX,
    VERSION,
    NORMAL_STATUSES,
    DEFAULT_LYRICS,
    SONG_INFO,
    NORMAL_DELAY,
    LYRIC_DELAY,
    STICKER_TRIGGERS,
    TRACKER_WARNINGS,
    check_battery_trigger,
    get_match_response,
    load_bot_data,
    save_bot_data,
)
from cogs.guild import Guild

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

        intents.message_content = True
        intents.voice_states = True

        self.active_warnings = OrderedDict()
        self.MAX_WARNINGS = 200

        self.normal_statuses = cycle(NORMAL_STATUSES)

        # Load saved song from bot_data.json if present, else fallback to config.py SONG_INFO
        saved_song = self._load_saved_song()
        initial_info = saved_song if saved_song else SONG_INFO

        self.active_song_info = {
            "title": initial_info.get("title", "Unknown"),
            "artist": initial_info.get("artist", "Unknown"),
            "album": initial_info.get("album", "N/A"),
            "release_year": initial_info.get("release_year", "N/A"),
            "youtube_url": initial_info.get("youtube_url"),
            "line_count": len(DEFAULT_LYRICS),
            "synced": initial_info.get("synced", False),
        }

        default_timed = [(float(LYRIC_DELAY), l) for l in DEFAULT_LYRICS]
        self.lyric_statuses = cycle(default_timed)
        self.last_lyric_line = DEFAULT_LYRICS[-1] if DEFAULT_LYRICS else "🍀"
        self.lyric_mode = False

        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=False
            ),
        )

    def _load_saved_song(self) -> dict | None:
        data = load_bot_data()
        return data.get("status_song") or None

    def _save_saved_song(self, meta: dict):
        data = load_bot_data()
        data["status_song"] = meta
        save_bot_data(data)

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

    def _build_timed_lyrics(self, synced_lyrics: str) -> list[tuple[float, str]]:
        """Parses LRC syncedLyrics into (delay_seconds, status_text) tuples, converting blank paragraph gaps into '...'."""
        raw_entries = []
        pattern = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")

        for line in synced_lyrics.splitlines():
            match = pattern.match(line.strip())
            if match:
                mins, secs, ms, text = match.groups()
                ts = int(mins) * 60 + int(secs) + int(ms) / (1000 if len(ms) == 3 else 100)
                clean_text = text.strip()
                if not clean_text:
                    if not raw_entries or raw_entries[-1][1] != '"..."':
                        raw_entries.append((ts, '"..."'))
                else:
                    raw_entries.append((ts, f'"{clean_text[:125]}"'))

        if not raw_entries:
            return []

        timed_lines = []
        if raw_entries[0][1] != '"..."':
            timed_lines.append((3.0, '"..."'))

        for i, (ts, text) in enumerate(raw_entries):
            if i + 1 < len(raw_entries):
                gap = raw_entries[i + 1][0] - ts
            else:
                gap = float(LYRIC_DELAY)

            if gap > 6.5 and text != '"..."':
                timed_lines.append((4.5, text))
                timed_lines.append((max(4.5, round(gap - 4.5, 2)), '"..."'))
            else:
                safe_delay = max(4.5, round(gap, 2))
                timed_lines.append((safe_delay, text))

        timed_lines.append((float(LYRIC_DELAY), "🍀"))
        return timed_lines

    async def fetch_lrclib_statuses(
        self, query: str, artist: Optional[str] = None
    ) -> tuple[list[tuple[float, str]], dict]:
        headers = {
            "User-Agent": f"CortDB-DiscordBot/{VERSION} (https://github.com/probablycort/cortdb)"
        }
        song_record = None

        try:
            async with aiohttp.ClientSession() as session:
                if artist:
                    async with session.get(
                        "https://lrclib.net/api/get",
                        params={"track_name": query, "artist_name": artist},
                        headers=headers,
                    ) as resp:
                        if resp.status == 200:
                            song_record = await resp.json()

                if not song_record:
                    search_q = f"{query} {artist}".strip() if artist else query.strip()
                    async with session.get(
                        "https://lrclib.net/api/search",
                        params={"q": search_q},
                        headers=headers,
                    ) as search_resp:
                        if search_resp.status == 200:
                            results = await search_resp.json()
                            if results and isinstance(results, list):
                                song_record = next(
                                    (r for r in results if r.get("syncedLyrics")),
                                    results[0],
                                )

            if song_record:
                synced = song_record.get("syncedLyrics")
                plain = song_record.get("plainLyrics")
                timed_lines = []
                is_synced = False

                if synced:
                    timed_lines = self._build_timed_lyrics(synced)
                    is_synced = bool(timed_lines)

                if not timed_lines and plain:
                    lines = ['"..."']
                    for raw_line in plain.splitlines():
                        clean = raw_line.strip()
                        if not clean:
                            if lines[-1] != '"..."':
                                lines.append('"..."')
                        else:
                            lines.append(f'"{clean[:125]}"')
                    lines.append("🍀")
                    timed_lines = [(float(LYRIC_DELAY), ln) for ln in lines]

                if timed_lines:
                    meta = {
                        "title": song_record.get("trackName") or query,
                        "artist": song_record.get("artistName") or artist or "Unknown",
                        "album": song_record.get("albumName") or "N/A",
                        "release_year": SONG_INFO.get("release_year", "N/A")
                        if (song_record.get("trackName") or "").lower()
                        == SONG_INFO.get("title", "").lower()
                        else "N/A",
                        "youtube_url": SONG_INFO.get("youtube_url")
                        if (song_record.get("trackName") or "").lower()
                        == SONG_INFO.get("title", "").lower()
                        else None,
                        "line_count": len(timed_lines),
                        "synced": is_synced,
                    }
                    return timed_lines, meta

        except Exception as e:
            log.warning(f"⚠️ Failed to fetch LRCLIB data: {e}")

        fallback = [(float(LYRIC_DELAY), l) for l in DEFAULT_LYRICS]
        return fallback, self.active_song_info

    async def update_status_song(
        self, query: str, artist: Optional[str] = None
    ) -> Optional[dict]:
        fetched, meta = await self.fetch_lrclib_statuses(query, artist)
        if meta == self.active_song_info and not fetched:
            return None

        self.active_song_info = meta
        self._save_saved_song(meta)
        self.lyric_statuses = cycle(fetched)
        self.last_lyric_line = fetched[-1][1] if fetched else "🍀"
        log.info(
            f"🎵 Updated status lyrics to: {meta['title']} - {meta['artist']} ({len(fetched)} entries, synced={meta['synced']})"
        )
        return meta

    @tasks.loop(seconds=1)
    async def statusChanger(self):
        await self.wait_until_ready()

        if self.lyric_mode:
            delay, status = next(self.lyric_statuses)

            if status == self.last_lyric_line:
                self.lyric_mode = False
        else:
            status = next(self.normal_statuses)
            delay = NORMAL_DELAY

            if status == "...":
                self.lyric_mode = True

        try:
            await self.change_presence(activity=discord.CustomActivity(name=status))
        except Exception:
            pass
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
        saved_song = self._load_saved_song()
        target_title = saved_song.get("title") if saved_song else SONG_INFO.get("title")
        target_artist = saved_song.get("artist") if saved_song else SONG_INFO.get("artist")

        fetched_lyrics, meta = await self.fetch_lrclib_statuses(target_title, target_artist)
        if saved_song:
            meta.update(saved_song)

        self.active_song_info = meta
        self.lyric_statuses = cycle(fetched_lyrics)
        self.last_lyric_line = fetched_lyrics[-1][1] if fetched_lyrics else "🍀"
        log.info(
            f"🎵 Loaded {len(fetched_lyrics)} lyric entries for status rotation from LRCLIB."
        )

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
                                await msg.edit(
                                    content="✅ Bot has been restarted successfully and is back online!"
                                )
                            except discord.NotFound:
                                await channel.send(
                                    "✅ Bot has been restarted successfully and is back online!"
                                )
            except Exception as e:
                log.error(f"Failed to send restart message: {e}")
            finally:
                os.remove("restart.txt")

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return

        content = message.content.lower()

        for trigger, sticker_id in STICKER_TRIGGERS.items():
            if trigger in content:
                sticker = self.get_sticker(sticker_id)
                if sticker:
                    await message.reply(stickers=[sticker], mention_author=False)
                    break

        for tracker_param, warning_data in TRACKER_WARNINGS.items():
            if tracker_param in content:
                embed = discord.Embed(
                    title=warning_data["title"],
                    description=warning_data["description"],
                    color=warning_data["color"],
                )
                warning = await message.reply(embed=embed, mention_author=False)
                self.active_warnings[message.id] = warning
                if len(self.active_warnings) > self.MAX_WARNINGS:
                    self.active_warnings.popitem(last=False)
                break

        guild_id = message.guild.id if message.guild else None
        prefixless_enabled = Guild.is_prefixless_enabled(guild_id)

        battery_response = check_battery_trigger(
            content, prefixless_enabled=prefixless_enabled
        )
        if battery_response:
            await message.channel.send(battery_response)

        match_response = get_match_response(
            content, self.user.mention.lower(), prefixless_enabled=prefixless_enabled
        )
        if match_response:
            if isinstance(match_response, discord.Embed):
                await message.reply(embed=match_response, mention_author=False)
            else:
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