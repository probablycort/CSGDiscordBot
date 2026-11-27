from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands, tasks
import wavelink
import aiohttp
import asyncio
import time
from typing import Optional, Literal

from config import LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASSWORD, LAVALINK_SECURE


class SearchSelect(discord.ui.Select):
    def __init__(self, tracks: list[wavelink.Playable], cog: Music):
        self.tracks = tracks
        self.cog = cog

        options = []
        for idx, track in enumerate(tracks[:5]):
            dur_str = cog.format_millis(track.length) if not track.is_stream else "LIVE"
            label = f"{idx + 1}. {track.title}"[:100]
            description = f"By {track.author} ({dur_str})"[:100]
            options.append(discord.SelectOption(label=label, description=description, value=str(idx)))

        super().__init__(
            placeholder="Choose a song to play...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        selected_index = int(self.values[0])
        track = self.tracks[selected_index]
        player: wavelink.Player = interaction.guild.voice_client

        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.followup.send("❌ You must be in a voice channel to select a track.", ephemeral=True)

        voice_channel = interaction.user.voice.channel
        if not player:
            await self.cog.ensure_node()
            try:
                player = await self.cog.connect_player(voice_channel)
            except (wavelink.ChannelTimeoutException, wavelink.InvalidNodeException):
                return await interaction.followup.send(
                    "❌ I couldn't finish connecting to voice. The Lavalink node never completed the handshake. Please try again in a bit.",
                    ephemeral=True,
                )
            player.home = interaction.channel
        elif player.channel != voice_channel:
            await player.move_to(voice_channel)
            player.home = interaction.channel
        else:
            player.home = interaction.channel

        try:
            if not player.playing:
                await player.play(track)
                embed = discord.Embed(
                    title="🎶 Now Playing",
                    description=f"[{track.title}]({track.uri}) by **{track.author}**",
                    color=0x5865F2,
                )
                if track.artwork:
                    embed.set_thumbnail(url=track.artwork)
                await interaction.followup.edit_message(interaction.message.id, content=None, embed=embed, view=None)
            else:
                await player.queue.put_wait(track)
                await interaction.followup.edit_message(
                    interaction.message.id,
                    content=f"➕ Added **[{track.title}]({track.uri})** to the queue!",
                    embed=None,
                    view=None,
                )
        except Exception as e:
            if getattr(e, "status", None) == 404 or "404" in str(e):
                await self.cog.reconnect_node()
                await interaction.followup.send("⚠️ Lavalink session expired. Reconnected node—please try your command again.", ephemeral=True)
            else:
                raise e


class SearchView(discord.ui.View):
    def __init__(self, tracks: list[wavelink.Playable], author: discord.User | discord.Member, cog: Music, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.author = author
        self.message: discord.Message | None = None
        self.add_item(SearchSelect(tracks, cog))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Only the person who ran the search command can choose a song.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(content="⏰ Search selection timed out.", embed=None, view=None)
            except discord.HTTPException:
                pass


class MusicControlsView(discord.ui.View):
    def __init__(self, cog: Music, player: wavelink.Player, author: discord.User | discord.Member):
        super().__init__(timeout=None)
        self.cog = cog
        self.player = player
        self.author = author
        self.update_buttons()

    def update_buttons(self):
        mode = self.player.queue.mode if self.player else wavelink.QueueMode.normal
        
        self.off_btn.style = discord.ButtonStyle.primary if mode == wavelink.QueueMode.normal else discord.ButtonStyle.secondary
        self.track_btn.style = discord.ButtonStyle.primary if mode == wavelink.QueueMode.loop else discord.ButtonStyle.secondary
        self.queue_btn.style = discord.ButtonStyle.primary if mode == wavelink.QueueMode.loop_all else discord.ButtonStyle.secondary

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice or interaction.user.voice.channel != self.player.channel:
            await interaction.response.send_message("❌ You must be in the same voice channel to use music controls.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Off", emoji="➡️", custom_id="loop_off")
    async def off_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.player.queue.mode = wavelink.QueueMode.normal
        self.update_buttons()
        embed = self.cog.build_queue_embed(self.player) if hasattr(interaction.message, "embeds") and interaction.message.embeds and "Queue" in interaction.message.embeds[0].title else self.cog.build_nowplaying_embed(self.player)
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)

    @discord.ui.button(label="Track", emoji="🔂", custom_id="loop_track")
    async def track_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.player.queue.mode = wavelink.QueueMode.loop
        self.update_buttons()
        embed = self.cog.build_queue_embed(self.player) if hasattr(interaction.message, "embeds") and interaction.message.embeds and "Queue" in interaction.message.embeds[0].title else self.cog.build_nowplaying_embed(self.player)
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)

    @discord.ui.button(label="Queue", emoji="🔁", custom_id="loop_queue")
    async def queue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.player.queue.mode = wavelink.QueueMode.loop_all
        self.update_buttons()
        embed = self.cog.build_queue_embed(self.player) if hasattr(interaction.message, "embeds") and interaction.message.embeds and "Queue" in interaction.message.embeds[0].title else self.cog.build_nowplaying_embed(self.player)
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)

    @discord.ui.button(label="Shuffle", emoji="🔀", style=discord.ButtonStyle.secondary, custom_id="loop_shuffle")
    async def shuffle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.player.queue.is_empty:
            return await interaction.followup.send("❌ Queue is empty, nothing to shuffle!", ephemeral=True)
        
        self.player.queue.shuffle()
        embed = self.cog.build_queue_embed(self.player) if hasattr(interaction.message, "embeds") and interaction.message.embeds and "Queue" in interaction.message.embeds[0].title else self.cog.build_nowplaying_embed(self.player)
        await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)


class Music(commands.Cog):
    """Music player commands powered by Wavelink & Lavalink, organized under /music.
    Alias for this category is `.m`.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        """Connect to the Lavalink node and start background tasks when the Cog is loaded."""
        await self.reconnect_node()
        self.check_inactivity.start()

    async def reconnect_node(self):
        """Cleanly (re)connect the Lavalink node, fully removing old/stale ones first."""
        # Pool.close() only disconnects nodes; it leaves them registered, which makes the
        # next connect get skipped ("already have a node with identifier"). Eject each node instead.
        for old in list(wavelink.Pool.nodes.values()):
            try:
                await old.close(eject=True)
            except Exception as e:
                print(f"⚠️ Failed to close old Lavalink node '{old.identifier}': {e}")

        # If an old node is somehow still registered, use a fresh identifier so we're never skipped.
        identifier = "main" if "main" not in wavelink.Pool.nodes else f"main-{int(time.time())}"

        try:
            uri = f"https://{LAVALINK_HOST}" if LAVALINK_SECURE else f"http://{LAVALINK_HOST}:{LAVALINK_PORT}"
            node = wavelink.Node(
                identifier=identifier,
                uri=uri,
                password=LAVALINK_PASSWORD
            )
            await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)

            # Pool.connect can return before the node is READY, so wait for it (up to ~10s).
            for _ in range(20):
                if node.status is wavelink.NodeStatus.CONNECTED:
                    print(f"✅ Lavalink node '{identifier}' connected/reconnected.")
                    return
                await asyncio.sleep(0.5)
            print(f"⚠️ Lavalink node '{identifier}' was created but did not reach CONNECTED in time.")
        except Exception as e:
            print(f"❌ Failed to connect Lavalink node: {e}")

    async def node_is_healthy(self) -> bool:
        """True only if a node is CONNECTED *and* the server still recognises our Lavalink session.

        A public node can restart or drop sessions while wavelink still reports CONNECTED; in that
        state voice joins fail even though everything looks fine.
        """
        try:
            node = wavelink.Pool.get_node()
        except wavelink.InvalidNodeException:
            return False
        if node.status is not wavelink.NodeStatus.CONNECTED:
            return False

        probe = getattr(node, "fetch_players", None)
        if probe is None:
            return True  # can't probe on this wavelink version; trust the status

        last_error = None
        for attempt in range(2):  # one quick retry so a single network blip doesn't trigger a reconnect
            try:
                # Lists this session's players; errors (e.g. 404) if the server forgot our session.
                await probe()
                return True
            except Exception as e:
                last_error = e
                if attempt == 0:
                    await asyncio.sleep(1.0)
        print(f"⚠️ Lavalink session check failed ({last_error.__class__.__name__}: {last_error})")
        return False

    async def ensure_node(self):
        """Reconnects the node if it is missing, disconnected, or its session has gone stale."""
        if not await self.node_is_healthy():
            await self.reconnect_node()

    async def connect_player(self, voice_channel: discord.VoiceChannel) -> wavelink.Player:
        """Connect to voice. On a handshake timeout, clean up, refresh the node if needed, and retry once."""
        for attempt in (1, 2):
            try:
                return await voice_channel.connect(cls=wavelink.Player, timeout=20.0)
            except (wavelink.ChannelTimeoutException, asyncio.TimeoutError):
                vc = voice_channel.guild.voice_client
                if vc:
                    await vc.disconnect(force=True)
                if attempt == 2:
                    raise
                print("⚠️ Voice connect timed out; checking the Lavalink node and retrying once...")
                if not await self.node_is_healthy():
                    await self.reconnect_node()

    async def _skip_track(self, player: wavelink.Player) -> bool:
        """Skips the current track. If the current track is being looped, loop is turned off first,
        otherwise the queue would just hand the same track back. Returns True if loop was disabled."""
        loop_disabled = False
        if player.queue.mode == wavelink.QueueMode.loop:
            player.queue.mode = wavelink.QueueMode.normal
            loop_disabled = True
        await player.skip(force=True)
        return loop_disabled

    def cog_unload(self):
        self.check_inactivity.cancel()

    @tasks.loop(minutes=1.0)
    async def check_inactivity(self):
        """Automatically disconnects the bot if the voice channel is empty of humans."""
        for guild in self.bot.guilds:
            player: wavelink.Player = guild.voice_client
            if not player or not player.channel:
                continue

            human_members = [m for m in player.channel.members if not m.bot]
            if len(human_members) == 0:
                player.queue.clear()
                await player.disconnect()
                if hasattr(player, "home") and player.home:
                    try:
                        await player.home.send("💤 Left the voice channel because everyone left.")
                    except discord.HTTPException:
                        pass

    async def robust_search(self, query: str) -> wavelink.Search | None:
        """Tries searching with different prefixes/formats as a fallback for unpredictable public nodes."""
        if query.startswith("http"):
            variants = [query]
        else:
            variants = [query, f"ytsearch:{query}", f"ytmsearch:{query}"]

        for variant in variants:
            try:
                tracks: wavelink.Search = await wavelink.Playable.search(variant)
                if tracks:
                    return tracks
            except Exception:
                continue
        return None

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"✅ Connected to Lavalink Node: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_websocket_closed(self, payload: wavelink.WebsocketClosedEventPayload):
        """Diagnostic: shows why a voice websocket was closed (useful for voice handshake failures)."""
        print(f"⚠️ Voice websocket closed: code={payload.code} reason={payload.reason!r} by_remote={payload.by_remote}")

    @commands.Cog.listener()
    async def on_wavelink_track_exception(self, payload: wavelink.TrackExceptionEventPayload):
        """Diagnostic: the node failed to load/stream a track."""
        title = getattr(payload.track, "title", "?")
        print(f"⚠️ Track exception on '{title}': {payload.exception}")

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, payload: wavelink.TrackStuckEventPayload):
        """Diagnostic: the stream stalled mid-track."""
        title = getattr(payload.track, "title", "?")
        print(f"⚠️ Track stuck on '{title}' (threshold: {payload.threshold} ms)")

    async def _notify_home(self, player: wavelink.Player, content: Optional[str] = None, embed: Optional[discord.Embed] = None):
        home = getattr(player, "home", None)
        if not home:
            return
        try:
            await home.send(content=content, embed=embed)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Handle next track, queue looping, failed streams, or queue completion, depending on WHY the track ended."""
        player: wavelink.Player = payload.player
        if not player:
            return

        # Lavalink reasons: finished, loadFailed, stopped (skip), replaced, cleanup.
        reason = str(getattr(payload, "reason", "") or "").lower()
        track = payload.track
        if reason != "finished":
            print(f"ℹ️ Track ended early: '{getattr(track, 'title', '?')}' (reason: {payload.reason})")

        # 'replaced' = another track was started on top of it, 'cleanup' = the player was destroyed.
        # Neither means "move on to the next track" (and neither means the queue finished).
        if reason in ("replaced", "cleanup"):
            return

        failed = reason == "loadfailed"
        key = getattr(track, "identifier", None) or getattr(track, "title", None)

        try:
            if reason == "finished" and hasattr(player, "retried_tracks"):
                player.retried_tracks.discard(key)

            if failed:
                # The node couldn't stream the track. Retry it once, then give up and move on.
                retried = getattr(player, "retried_tracks", None)
                if retried is None:
                    retried = set()
                    player.retried_tracks = retried
                if key not in retried:
                    retried.add(key)
                    await self._notify_home(player, f"⚠️ Playback of **{track.title}** failed. Retrying once...")
                    await player.play(track)
                    return
                retried.discard(key)
                await self._notify_home(player, f"❌ Couldn't play **{track.title}**. The stream failed twice.")
            elif player.queue.mode == wavelink.QueueMode.loop and reason == "finished":
                await player.play(track)
                return

            if player.queue.is_empty:
                if not failed:
                    await self._notify_home(player, "⏹️ Queue has finished! No more tracks left to play.")
                return

            next_track = await player.queue.get_wait()
            await player.play(next_track)

            embed = discord.Embed(
                title="🎶 Now Playing",
                description=f"[{next_track.title}]({next_track.uri}) by **{next_track.author}**",
                color=0x5865F2
            )
            if next_track.artwork:
                embed.set_thumbnail(url=next_track.artwork)
            await self._notify_home(player, embed=embed)
        except Exception as e:
            print(f"⚠️ Lavalink node error during track end handling: {e}")
            if getattr(e, "status", None) == 404 or "404" in str(e):
                print("🔄 Stale session detected (404). Reconnecting node...")
                await self.reconnect_node()
            await self._notify_home(player, "⚠️ The public Lavalink node session expired or hit an error. Attempting auto-reconnect.")

    def format_millis(self, millis: int) -> str:
        seconds = int((millis / 1000) % 60)
        minutes = int((millis / (1000 * 60)) % 60)
        hours = int((millis / (1000 * 60 * 60)) % 24)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def parse_time_string(self, time_str: str) -> Optional[int]:
        time_str = time_str.strip()
        if time_str.isdigit():
            return int(time_str) * 1000

        parts = time_str.split(":")
        try:
            parts = [int(p) for p in parts]
            if len(parts) == 2:
                minutes, seconds = parts
                return (minutes * 60 + seconds) * 1000
            elif len(parts) == 3:
                hours, minutes, seconds = parts
                return (hours * 3600 + minutes * 60 + seconds) * 1000
        except ValueError:
            return None
        return None

    def build_queue_embed(self, player: wavelink.Player) -> discord.Embed:
        embed = discord.Embed(title="🎵 Music Queue", color=0x5865F2)
        
        if player.current:
            embed.add_field(
                name="Now Playing",
                value=f"[{player.current.title}]({player.current.uri}) by **{player.current.author}**",
                inline=False
            )

        if not player.queue.is_empty:
            queue_list = []
            for idx, track in enumerate(player.queue, start=1):
                if idx > 10:
                    queue_list.append(f"*...and {len(player.queue) - 10} more tracks*")
                    break
                queue_list.append(f"`{idx}.` [{track.title}]({track.uri}) - **{track.author}**")
            
            embed.add_field(name="Up Next", value="\n".join(queue_list), inline=False)

        mode_str = {
            wavelink.QueueMode.normal: "Off",
            wavelink.QueueMode.loop: "Track",
            wavelink.QueueMode.loop_all: "Queue"
        }.get(player.queue.mode, "Off")

        embed.set_footer(text=f"Loop Mode: {mode_str} | Total Tracks in Queue: {len(player.queue)}")
        return embed

    def build_nowplaying_embed(self, player: wavelink.Player) -> discord.Embed:
        track = player.current
        if not track:
            return discord.Embed(
                title="🎶 Now Playing",
                description="Nothing is currently playing.",
                color=0x5865F2
            )

        position = player.position
        duration = track.length

        bar_size = 15
        progress = min(int((position / duration) * bar_size), bar_size) if duration > 0 else 0
        progress_bar = "🔘" + "─" * progress + "🔘" + "─" * (bar_size - progress)

        pos_str = self.format_millis(position)
        dur_str = self.format_millis(duration) if not track.is_stream else "LIVE"

        mode_str = {
            wavelink.QueueMode.normal: "Off",
            wavelink.QueueMode.loop: "Track",
            wavelink.QueueMode.loop_all: "Queue"
        }.get(player.queue.mode, "Off")

        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"[{track.title}]({track.uri})\nBy **{track.author}**\n\n`{pos_str}` {progress_bar} `{dur_str}`",
            color=0x5865F2
        )
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        embed.set_footer(text=f"Loop Mode: {mode_str}")
        return embed

    @commands.is_owner()
    @commands.command(name="nodes", hidden=True)
    async def nodes_cmd(self, ctx: commands.Context):
        """Owner-only diagnostic: lists the Lavalink nodes currently in the pool."""
        lines = []
        for n in wavelink.Pool.nodes.values():
            try:
                await n.fetch_players()
                session = "session OK"
            except Exception as e:
                session = f"session check failed ({e.__class__.__name__})"
            lines.append(f"`{n.identifier}`: {n.status.name}, {len(n.players)} players, {session}")
        await ctx.reply("\n".join(lines) or "No nodes.", mention_author=False)

    @commands.hybrid_group(name="music", aliases=["m"], description="Music player commands powered by Wavelink & Lavalink")
    async def music_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @music_group.command(name="join", description="Connects the bot to your current voice channel")
    async def join(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("❌ You must be connected to a voice channel to use this command.", mention_author=False)

        if ctx.interaction:
            await ctx.interaction.response.defer()
        else:
            await ctx.typing()

        voice_channel = ctx.author.voice.channel
        player: wavelink.Player = ctx.voice_client

        if player:
            if player.channel == voice_channel:
                return await ctx.reply(f"ℹ️ I am already connected to **{voice_channel.name}**!", mention_author=False)
            await player.move_to(voice_channel)
            player.home = ctx.channel
            return await ctx.reply(f"🚚 Moved to **{voice_channel.name}**!", mention_author=False)

        await self.ensure_node()
        try:
            player = await self.connect_player(voice_channel)
        except (wavelink.ChannelTimeoutException, wavelink.InvalidNodeException):
            return await ctx.reply(
                "❌ I couldn't finish connecting to voice. The Lavalink node never completed the handshake. Please try again in a bit.",
                mention_author=False,
            )

        player.home = ctx.channel
        await ctx.reply(f"🔌 Connected to **{voice_channel.name}**!", mention_author=False)

    @music_group.command(name="leave", description="Disconnects the bot from the voice channel and clears the queue")
    async def leave(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.reply("❌ I am not connected to any voice channel.", mention_author=False)

        player.queue.clear()
        await player.disconnect()
        await ctx.reply("👋 Disconnected from the voice channel and cleared queue.", mention_author=False)

    @music_group.command(name="loop", description="Loop the current track (or choose off/queue) and show the controls")
    @app_commands.describe(mode="Loop mode: track (default), queue, or off")
    async def loop(self, ctx: commands.Context, mode: Optional[Literal["off", "track", "queue"]] = None):
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.reply("❌ The bot is not in a voice channel.", mention_author=False)

        # With no argument, loop the current track.
        mode = mode or "track"
        if mode == "track":
            player.queue.mode = wavelink.QueueMode.loop
            note = "🔂 Now looping the **current track**."
        elif mode == "queue":
            player.queue.mode = wavelink.QueueMode.loop_all
            note = "🔁 Now looping the **whole queue**."
        else:
            player.queue.mode = wavelink.QueueMode.normal
            note = "➡️ Loop is now **off**."

        # The view is created AFTER the mode is set, so the buttons show the right state.
        view = MusicControlsView(self, player, ctx.author)
        if player.playing or not player.queue.is_empty:
            embed = self.build_queue_embed(player)
            embed.description = note
        else:
            embed = discord.Embed(
                title="🔁 Loop Controls",
                description=f"{note}\n\nUse the buttons below to toggle loop mode or shuffle the queue.",
                color=0x5865F2
            )
        await ctx.reply(embed=embed, view=view, mention_author=False)

    @music_group.command(name="queue", description="Shows the current song queue with interactive loop & shuffle buttons")
    async def queue(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or (not player.playing and player.queue.is_empty):
            return await ctx.reply("❌ The queue is currently empty.", mention_author=False)

        embed = self.build_queue_embed(player)
        view = MusicControlsView(self, player, ctx.author)
        await ctx.reply(embed=embed, view=view, mention_author=False)

    @music_group.command(name="nowplaying", description="Shows details, progress, and controls for the currently playing track")
    async def nowplaying(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.reply("❌ Nothing is currently playing.", mention_author=False)

        embed = self.build_nowplaying_embed(player)
        view = MusicControlsView(self, player, ctx.author)
        await ctx.reply(embed=embed, view=view, mention_author=False)

    @music_group.command(name="lyrics", description="Fetches lyrics for the currently playing song or a search query")
    @app_commands.describe(query="Optional specific song query to fetch lyrics for")
    async def lyrics(self, ctx: commands.Context, *, query: Optional[str] = None):
        player: wavelink.Player = ctx.voice_client
        
        search_term = query
        if not search_term:
            if player and player.current:
                search_term = f"{player.current.title} {player.current.author}"
            else:
                return await ctx.reply("❌ Nothing is currently playing! Please provide a song query (e.g., `.music lyrics <song name>`).", mention_author=False)

        await ctx.typing()

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://lrclib.net/api/search?q={search_term}") as resp:
                if resp.status != 200:
                    return await ctx.reply("❌ Failed to fetch lyrics from the API service.", mention_author=False)
                data = await resp.json()

        if not data or not isinstance(data, list):
            return await ctx.reply(f"❌ Could not find any lyrics for `{search_term}`.", mention_author=False)

        song_data = data[0]
        track_name = song_data.get("trackName", "Unknown Track")
        artist_name = song_data.get("artistName", "Unknown Artist")
        lyrics_text = song_data.get("plainLyrics") or song_data.get("syncedLyrics")

        if not lyrics_text:
            return await ctx.reply(f"❌ No lyrics content available for **{track_name}** by **{artist_name}**.", mention_author=False)

        if len(lyrics_text) > 4000:
            lyrics_text = lyrics_text[:3997] + "..."

        embed = discord.Embed(
            title=f"📜 Lyrics: {track_name}",
            description=f"**Artist:** {artist_name}\n\n{lyrics_text}",
            color=0x5865F2
        )
        embed.set_footer(text="Powered by lrclib.net")
        await ctx.reply(embed=embed, mention_author=False)

    @music_group.command(name="search", description="Search for songs and pick one from an interactive dropdown menu")
    @app_commands.describe(query="Song title or search keywords")
    async def search(self, ctx: commands.Context, *, query: str):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("❌ You must be connected to a voice channel to use this command.", mention_author=False)

        if ctx.interaction:
            await ctx.interaction.response.defer()
        else:
            await ctx.typing()

        await self.ensure_node()
        tracks = await self.robust_search(query)

        if not tracks:
            return await ctx.reply(f"❌ Could not find any tracks matching `{query}`.", mention_author=False)

        if isinstance(tracks, wavelink.Playlist):
            tracks = tracks.tracks

        results_list = []
        for idx, track in enumerate(tracks[:5], start=1):
            dur_str = self.format_millis(track.length) if not track.is_stream else "LIVE"
            results_list.append(f"`{idx}.` [{track.title}]({track.uri}) - **{track.author}** (`{dur_str}`)")

        embed = discord.Embed(
            title=f"🔎 Search Results for '{query}'",
            description="\n".join(results_list),
            color=0x5865F2,
        )
        embed.set_footer(text="Select a song from the dropdown menu below within 30 seconds.")

        view = SearchView(tracks[:5], ctx.author, self)
        msg = await ctx.reply(embed=embed, view=view, mention_author=False)
        view.message = msg

    @music_group.command(name="play", description="Plays a song, URL, or uploaded audio file")
    @app_commands.describe(query="Song title, URL, or attach an audio file")
    async def play(self, ctx: commands.Context, *, query: Optional[str] = None):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("❌ You must be connected to a voice channel to use this command.", mention_author=False)

        if ctx.interaction:
            await ctx.interaction.response.defer()
        else:
            await ctx.typing()

        await self.ensure_node()

        voice_channel = ctx.author.voice.channel
        player: wavelink.Player = ctx.voice_client

        if not player:
            try:
                player = await self.connect_player(voice_channel)
            except (wavelink.ChannelTimeoutException, wavelink.InvalidNodeException):
                return await ctx.reply(
                    "❌ I couldn't finish connecting to voice. The Lavalink node never completed the handshake. Please try again in a bit.",
                    mention_author=False,
                )
            player.home = ctx.channel
        elif player.channel != voice_channel:
            await player.move_to(voice_channel)
            player.home = ctx.channel
        else:
            player.home = ctx.channel

        audio_url = None
        if ctx.message and ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.filename.lower().endswith(('.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac')):
                audio_url = attachment.url

        if not audio_url:
            if not query:
                return await ctx.reply("❌ Please provide a search query, URL, or upload an audio file!", mention_author=False)
            audio_url = query

        tracks = await self.robust_search(audio_url)

        if not tracks:
            return await ctx.reply(f"❌ Could not find or load tracks for `{query or 'uploaded file'}`.", mention_author=False)

        try:
            if isinstance(tracks, wavelink.Playlist):
                added_count = len(tracks.tracks)
                await player.queue.put_wait(tracks)
                
                if not player.playing:
                    await player.play(player.queue.get())
                    await ctx.reply(f"🎵 Started playing playlist **{tracks.name}** ({added_count} tracks)!", mention_author=False)
                else:
                    await ctx.reply(f"➕ Added playlist **{tracks.name}** ({added_count} tracks) to the queue!", mention_author=False)
            else:
                track = tracks[0]
                if not player.playing:
                    await player.play(track)
                    embed = discord.Embed(
                        title="🎶 Now Playing",
                        description=f"[{track.title}]({track.uri}) by **{track.author}**",
                        color=0x5865F2
                    )
                    if track.artwork:
                        embed.set_thumbnail(url=track.artwork)
                    await ctx.reply(embed=embed, mention_author=False)
                else:
                    await player.queue.put_wait(track)
                    await ctx.reply(f"➕ Added **[{track.title}]({track.uri})** to the queue!", mention_author=False)
        except Exception as e:
            if getattr(e, "status", None) == 404 or "404" in str(e):
                await self.reconnect_node()
                await ctx.reply("⚠️ Lavalink session was dead (404). Node reconnected—please run your `.m play` command again.", mention_author=False)
            else:
                raise e

    @music_group.command(name="skip", description="Skips the currently playing song (Vote-skip if > 5 members)")
    async def skip(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.reply("❌ There is no music currently playing.", mention_author=False)

        perms = ctx.author.guild_permissions
        is_mod = perms.manage_guild or perms.manage_channels or perms.administrator

        human_members = [m for m in player.channel.members if not m.bot]

        if len(human_members) <= 5 or is_mod:
            if hasattr(player, "skip_votes"):
                player.skip_votes.clear()
            loop_disabled = await self._skip_track(player)
            note = " Track loop was turned off." if loop_disabled else ""
            await ctx.reply(f"⏭️ Skipped current track!{note}", mention_author=False)
            return

        if not hasattr(player, "skip_votes"):
            player.skip_votes = set()

        if ctx.author.id in player.skip_votes:
            return await ctx.reply("❌ You have already voted to skip this track!", mention_author=False, ephemeral=True)

        player.skip_votes.add(ctx.author.id)
        required_votes = max(2, len(human_members) // 2 + 1)
        current_votes = len(player.skip_votes)

        if current_votes >= required_votes:
            player.skip_votes.clear()
            loop_disabled = await self._skip_track(player)
            note = " Track loop was turned off." if loop_disabled else ""
            msg = await ctx.reply(f"⏭️ Vote-skip passed ({current_votes}/{required_votes} votes)! Skipped current track.{note}", mention_author=False)
            try:
                await msg.add_reaction("✅")
            except discord.HTTPException:
                pass
        else:
            msg = await ctx.reply(f"⏭️ **{ctx.author.display_name}** voted to skip (`{current_votes}/{required_votes}` votes needed).", mention_author=False)
            try:
                await msg.add_reaction("⏭️")
            except discord.HTTPException:
                pass

    @music_group.command(name="pause", description="Pauses the current track")
    async def pause(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.reply("❌ Nothing is playing right now.", mention_author=False)

        await player.pause(True)
        await ctx.reply("⏸️ Paused audio playback.", mention_author=False)

    @music_group.command(name="resume", description="Resumes paused track")
    async def resume(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.paused:
            return await ctx.reply("❌ Music is not currently paused.", mention_author=False)

        await player.pause(False)
        await ctx.reply("▶️ Resumed audio playback.", mention_author=False)

    @music_group.command(name="stop", description="Stops music and disconnects the bot from voice")
    async def stop(self, ctx: commands.Context):
        if ctx.interaction:
            await ctx.interaction.response.defer()
        else:
            await ctx.typing()

        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.reply("❌ The bot is not in a voice channel.", mention_author=False)

        player.queue.clear()
        await player.disconnect()
        await ctx.reply("⏹️ Stopped playback and left the voice channel.", mention_author=False)
        
    @music_group.command(name="remove", description="Remove a specific track from the queue by position")
    @app_commands.describe(index="The 1-based index position of the track in the queue")
    async def remove(self, ctx: commands.Context, index: int):
        player: wavelink.Player = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.reply("❌ The queue is empty.", mention_author=False)

        if index < 1 or index > len(player.queue):
            return await ctx.reply(f"❌ Invalid index! Please enter a number between 1 and {len(player.queue)}.", mention_author=False)

        removed_track = player.queue[index - 1]
        del player.queue[index - 1]

        await ctx.reply(f"🗑️ Removed **[{removed_track.title}]({removed_track.uri})** from the queue.", mention_author=False)

    @music_group.command(name="shuffle", description="Shuffles the song queue")
    async def shuffle(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.reply("❌ The queue is empty.", mention_author=False)

        player.queue.shuffle()
        embed = self.build_queue_embed(player)
        view = MusicControlsView(self, player, ctx.author)
        await ctx.reply(embed=embed, view=view, mention_author=False)

    @music_group.command(name="clear", description="Clears all songs from the queue")
    async def clear(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or player.queue.is_empty:
            return await ctx.reply("❌ Queue is already empty.", mention_author=False)

        player.queue.clear()
        await ctx.reply("🧹 Cleared all tracks from the queue.", mention_author=False)

    @music_group.command(name="volume", aliases=["vol"], description="Set or check player volume (1 to 100)")
    @app_commands.describe(volume="Volume level from 1 to 100")
    async def volume(self, ctx: commands.Context, volume: Optional[int] = None):
        if ctx.interaction:
            await ctx.interaction.response.defer()
        else:
            await ctx.typing()

        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.reply("❌ The bot is not in a voice channel.", mention_author=False)

        if volume is None:
            return await ctx.reply(f"🔊 Current volume is set to **{player.volume}%**.", mention_author=False)

        if volume < 1 or volume > 100:
            return await ctx.reply("❌ Volume must be set between 1 and 100.", mention_author=False)

        await player.set_volume(volume)
        await ctx.reply(f"🔊 Volume set to **{volume}%**.", mention_author=False)

    @music_group.command(name="seek", description="Skips to the specified timestamp in the currently playing track format: M:S or H:M:S")
    @app_commands.describe(time="Timestamp to seek to (e.g., 1:30, 2:15:00, or 90)")
    async def seek(self, ctx: commands.Context, *, time: str):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.reply("❌ Nothing is currently playing.", mention_author=False)

        millis = self.parse_time_string(time)
        if millis is None:
            return await ctx.reply("❌ Invalid format! Please use `SS`, `MM:SS`, or `HH:MM:SS` (e.g., `1:30`).", mention_author=False)

        if millis < 0 or millis > player.current.length:
            return await ctx.reply(f"❌ Position out of range! Track length is `{self.format_millis(player.current.length)}`.", mention_author=False)

        await player.seek(millis)
        await ctx.reply(f"⏩ Seeked to **{self.format_millis(millis)}**.", mention_author=False)

    @music_group.command(name="replay", description="Replay the currently playing song from the start")
    async def replay(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.current:
            return await ctx.reply("❌ Nothing is currently playing.", mention_author=False)

        await player.seek(0)
        await ctx.reply("🔄 Replaying current track from the beginning.", mention_author=False)

    # Short aliases defined as root prefix commands for convenience
    @commands.command(name="p", aliases=["play"], hidden=True)
    async def play_alias(self, ctx: commands.Context, *, query: Optional[str] = None):
        ctx.command = self.play
        await self.play(ctx, query=query)

    @commands.command(name="s", aliases=["skip"], hidden=True)
    async def skip_alias(self, ctx: commands.Context):
        ctx.command = self.skip
        await self.skip(ctx)

    @commands.command(name="q", aliases=["queue"], hidden=True)
    async def queue_alias(self, ctx: commands.Context):
        ctx.command = self.queue
        await self.queue(ctx)

    @commands.command(name="np", hidden=True)
    async def nowplaying_alias(self, ctx: commands.Context):
        ctx.command = self.nowplaying
        await self.nowplaying(ctx)

    @commands.command(name="vol", hidden=True)
    async def volume_alias(self, ctx: commands.Context, volume: Optional[int] = None):
        ctx.command = self.volume
        await self.volume(ctx, volume=volume)

    @commands.command(name="rm", hidden=True)
    async def remove_alias(self, ctx: commands.Context, index: int):
        ctx.command = self.remove
        await self.remove(ctx, index=index)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))