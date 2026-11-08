from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands, tasks
import wavelink
import aiohttp
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
            player = await voice_channel.connect(cls=wavelink.Player)
            player.home = interaction.channel
        elif player.channel != voice_channel:
            await player.move_to(voice_channel)
            player.home = interaction.channel
        else:
            player.home = interaction.channel

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
        
        # Loop Off Button
        self.off_btn.style = discord.ButtonStyle.primary if mode == wavelink.QueueMode.normal else discord.ButtonStyle.secondary
        # Loop Track Button
        self.track_btn.style = discord.ButtonStyle.primary if mode == wavelink.QueueMode.loop else discord.ButtonStyle.secondary
        # Loop Queue Button
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
    """Music player commands powered by Wavelink & Lavalink, organized under /music."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        """Connect to the Lavalink node and start background tasks when the Cog is loaded."""
        uri = f"https://{LAVALINK_HOST}" if LAVALINK_SECURE else f"http://{LAVALINK_HOST}:{LAVALINK_PORT}"
        node = wavelink.Node(
            uri=uri,
            password=LAVALINK_PASSWORD
        )
        await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)
        self.check_inactivity.start()

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

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"✅ Connected to Lavalink Node: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Automatically handle next track, queue looping, or notify queue completion."""
        player: wavelink.Player = payload.player
        if not player:
            return

        if player.queue.mode == wavelink.QueueMode.loop:
            await player.play(payload.track)
            return

        if player.queue.is_empty:
            if hasattr(player, "home") and player.home:
                try:
                    await player.home.send("⏹️ Queue has finished! No more tracks left to play.")
                except discord.HTTPException:
                    pass
            return

        next_track = await player.queue.get_wait()
        await player.play(next_track)

        if hasattr(player, "home") and player.home:
            try:
                embed = discord.Embed(
                    title="🎶 Now Playing",
                    description=f"[{next_track.title}]({next_track.uri}) by **{next_track.author}**",
                    color=0x5865F2
                )
                if next_track.artwork:
                    embed.set_thumbnail(url=next_track.artwork)
                await player.home.send(embed=embed)
            except discord.HTTPException:
                pass

    def format_millis(self, millis: int) -> str:
        """Helper to format milliseconds into MM:SS or HH:MM:SS format."""
        seconds = int((millis / 1000) % 60)
        minutes = int((millis / (1000 * 60)) % 60)
        hours = int((millis / (1000 * 60 * 60)) % 24)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def parse_time_string(self, time_str: str) -> Optional[int]:
        """Parses MM:SS, H:MM:SS, or raw seconds into total milliseconds."""
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
        """Constructs the Embed representation of the current player queue."""
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
        """Constructs the Embed representation of the currently playing track."""
        track = player.current
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

    @commands.hybrid_group(name="music", aliases=["m"], description="Music player commands powered by Wavelink & Lavalink")
    async def music_group(self, ctx: commands.Context):
        """Parent command group for music."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @music_group.command(name="join", description="Connects the bot to your current voice channel")
    async def join(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("❌ You must be connected to a voice channel to use this command.", mention_author=False)

        voice_channel = ctx.author.voice.channel
        player: wavelink.Player = ctx.voice_client

        if player:
            if player.channel == voice_channel:
                return await ctx.reply(f"ℹ️ I am already connected to **{voice_channel.name}**!", mention_author=False)
            await player.move_to(voice_channel)
            player.home = ctx.channel
            return await ctx.reply(f"🚚 Moved to **{voice_channel.name}**!", mention_author=False)

        player = await voice_channel.connect(cls=wavelink.Player)
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

    @music_group.command(name="loop", description="Set loop mode interactively via UI buttons")
    @app_commands.describe(mode="Choose loop mode: off, track, or queue")
    async def loop(self, ctx: commands.Context, mode: Optional[Literal["off", "track", "queue"]] = None):
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.reply("❌ The bot is not in a voice channel.", mention_author=False)

        if mode:
            if mode == "track":
                player.queue.mode = wavelink.QueueMode.loop
            elif mode == "queue":
                player.queue.mode = wavelink.QueueMode.loop_all
            else:
                player.queue.mode = wavelink.QueueMode.normal

        view = MusicControlsView(self, player, ctx.author)
        embed = self.build_queue_embed(player) if (player.playing or not player.queue.is_empty) else discord.Embed(
            title="🔁 Loop Controls",
            description="Use the buttons below to toggle loop mode or shuffle the queue.",
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

        search_query = query if query.startswith("http") else f"ytsearch:{query}"

        try:
            tracks: wavelink.Search = await wavelink.Playable.search(search_query)
        except Exception as e:
            error_message = str(e).lower()
            if any(keyword in error_message for keyword in ["not supported", "disabled", "plugin", "manager", "unsupported"]):
                return await ctx.reply(
                    "❌ **Text searching is disabled on this public Lavalink node.** "
                    "The node operator has turned off search plugins. Please use a direct URL with `.music play <URL>` instead!",
                    mention_author=False
                )
            tracks = None

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

        voice_channel = ctx.author.voice.channel
        player: wavelink.Player = ctx.voice_client

        if not player:
            player = await voice_channel.connect(cls=wavelink.Player)
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
            audio_url = query if query.startswith("http") else f"ytsearch:{query}"

        tracks: wavelink.Search = await wavelink.Playable.search(audio_url)
        if not tracks:
            return await ctx.reply(f"❌ Could not find or load tracks for `{query or 'uploaded file'}`.", mention_author=False)

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
            await player.skip(force=True)
            msg = await ctx.reply("⏭️ Skipped current track!", mention_author=False)
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
            await player.skip(force=True)
            msg = await ctx.reply(f"⏭️ Vote-skip passed ({current_votes}/{required_votes} votes)! Skipped current track.", mention_author=False)
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

    @music_group.command(name="volume", description="Set or check player volume (1 to 100)")
    @app_commands.describe(volume="Volume level from 1 to 100")
    async def volume(self, ctx: commands.Context, volume: Optional[int] = None):
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
    @commands.command(name="p", hidden=True)
    async def play_alias(self, ctx: commands.Context, *, query: Optional[str] = None):
        await self.play(ctx, query=query)

    @commands.command(name="s", hidden=True)
    async def skip_alias(self, ctx: commands.Context):
        await self.skip(ctx)

    @commands.command(name="q", hidden=True)
    async def queue_alias(self, ctx: commands.Context):
        await self.queue(ctx)

    @commands.command(name="np", hidden=True)
    async def nowplaying_alias(self, ctx: commands.Context):
        await self.nowplaying(ctx)

    @commands.command(name="vol", hidden=True)
    async def volume_alias(self, ctx: commands.Context, volume: Optional[int] = None):
        await self.volume(ctx, volume=volume)

    @commands.command(name="rm", hidden=True)
    async def remove_alias(self, ctx: commands.Context, index: int):
        await self.remove(ctx, index=index)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))