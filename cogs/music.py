import discord
from discord import app_commands
from discord.ext import commands
import wavelink
from typing import Optional

from config import LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASSWORD, LAVALINK_SECURE


class Music(commands.Cog):
    """Music player commands powered by Wavelink & Lavalink."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        """Connect to the Lavalink node when the Cog is loaded."""
        node = wavelink.Node(
            uri=f"{'https' if LAVALINK_SECURE else 'http'}://{LAVALINK_HOST}:{LAVALINK_PORT}",
            password=LAVALINK_PASSWORD
        )
        await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"✅ Connected to Lavalink Node: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Automatically play the next song in the queue when the current track finishes."""
        player: wavelink.Player = payload.player
        if not player or player.queue.is_empty:
            return

        next_track = await player.queue.get_wait()
        await player.play(next_track)

    @commands.hybrid_command(name="play", aliases=["p"], description="Plays a song or playlist from YouTube, Spotify, or SoundCloud")
    @app_commands.describe(query="Song title, YouTube URL, or Spotify link")
    async def play(self, ctx: commands.Context, *, query: str):
        """Play audio from YouTube, Spotify, or SoundCloud in your voice channel."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.reply("❌ You must be connected to a voice channel to use this command.", mention_author=False)

        voice_channel = ctx.author.voice.channel
        player: wavelink.Player = ctx.voice_client

        # Connect to the voice channel if not already connected
        if not player:
            player = await voice_channel.connect(cls=wavelink.Player)
        elif player.channel != voice_channel:
            await player.move_to(voice_channel)

        # Search for track or playlist
        tracks: wavelink.Search = await wavelink.Playable.search(query)
        if not tracks:
            return await ctx.reply(f"❌ Could not find any tracks for `{query}`.", mention_author=False)

        # If search returned a playlist
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

    @commands.hybrid_command(name="skip", aliases=["s"], description="Skips the currently playing song")
    async def skip(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.reply("❌ There is no music currently playing.", mention_author=False)

        await player.skip(force=True)
        await ctx.reply("⏭️ Skipped current track!", mention_author=False)

    @commands.hybrid_command(name="pause", description="Pauses the current track")
    async def pause(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            return await ctx.reply("❌ Nothing is playing right now.", mention_author=False)

        await player.pause(True)
        await ctx.reply("⏸️ Paused audio playback.", mention_author=False)

    @commands.hybrid_command(name="resume", description="Resumes paused track")
    async def resume(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.paused:
            return await ctx.reply("❌ Music is not currently paused.", mention_author=False)

        await player.pause(False)
        await ctx.reply("▶️ Resumed audio playback.", mention_author=False)

    @commands.hybrid_command(name="stop", aliases=["disconnect", "leave"], description="Stops music and disconnects the bot from voice")
    async def stop(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player:
            return await ctx.reply("❌ The bot is not in a voice channel.", mention_author=False)

        player.queue.clear()
        await player.disconnect()
        await ctx.reply("⏹️ Stopped playback and left the voice channel.", mention_author=False)

    @commands.hybrid_command(name="queue", aliases=["q"], description="Shows the current song queue")
    async def queue(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or (not player.playing and player.queue.is_empty):
            return await ctx.reply("❌ The queue is currently empty.", mention_author=False)

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

        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))