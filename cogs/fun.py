from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import asyncio
import random
from typing import TYPE_CHECKING

from config import SONG_INFO, LYRICS, LYRIC_DELAY

if TYPE_CHECKING:
    from bot import CSGDiscordBot


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot: CSGDiscordBot = bot

    @commands.hybrid_command(
        aliases=["status", "lyrics"],
        description="Displays info about the status lyric sequence",
    )
    async def song(self, ctx: commands.Context):
        """Displays details about the status lyric sequence."""
        status_mode = (
            "Lyric Sequence (Active)"
            if self.bot.lyric_mode
            else "Normal Status Cycle"
        )

        embed = discord.Embed(
            title=f"🎵 {SONG_INFO['title']}",
            description=f"By **{SONG_INFO['artist']}**",
            color=0x7289DA,
            url=SONG_INFO.get("youtube_url"),
        )
        embed.add_field(
            name="Album",
            value=f"`{SONG_INFO.get('album', 'N/A')}`",
            inline=True,
        )
        embed.add_field(
            name="Year",
            value=f"`{SONG_INFO.get('release_year', 'N/A')}`",
            inline=True,
        )
        embed.add_field(
            name="Status Mode", value=f"`{status_mode}`", inline=False
        )
        embed.add_field(
            name="Total Lyric Lines",
            value=f"`{len(LYRICS)} lines`",
            inline=True,
        )
        embed.add_field(
            name="Lyric Delay", value=f"`{LYRIC_DELAY} seconds / line`", inline=True
        )

        if SONG_INFO.get("youtube_url"):
            embed.add_field(
                name="Links",
                value=f"[YouTube]({SONG_INFO['youtube_url']})",
                inline=False,
            )

        embed.set_footer(text="Statuses Info")

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["dice"], description="Roll a dice")
    async def roll(self, ctx, max: int = 6):
        number = random.randint(1, max)
        await ctx.send(f"You have rolled a **{number}**.")

    @commands.command(aliases=["guessinggame", "startgame"])
    async def guess(self, ctx, max: int = 100):
        MAX_GUESSES = 15
        number = random.randint(1, max)
        await ctx.send(
            f"## Guessing game has been started!\nPlease guess a number between **1-{max}.**\nYou have **{MAX_GUESSES}** guesses."
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.message.channel

        for i in range(MAX_GUESSES):
            try:
                msg = await self.bot.wait_for(
                    "message", check=check, timeout=15
                )
                try:
                    val = int(msg.content)
                    if val == number:
                        await ctx.send(
                            f"Congrats, you guessed it correctly! It took you **{i+1}** tries."
                        )
                        break
                    elif val > number:
                        await ctx.send("Lower!")
                    else:
                        await ctx.send("Higher!")
                except ValueError:
                    await ctx.send("Please send a valid number.")
            except asyncio.TimeoutError:
                await ctx.send("Timed out waiting for a guess!")
                break
        else:
            await ctx.send(
                f"## Game over!\nYou ran out of tries. The number was **{number}**."
            )

    @commands.command(aliases=["choice"])
    async def choose(self, ctx, *, args):
        arguements = args.split(" ")
        choice = random.choice(arguements)
        thinking = await ctx.send(":clock1: Thinking, please wait...")
        await asyncio.sleep(0.2)
        for i in range(4):
            await thinking.edit(
                content=f":clock{i+1}: Thinking, please wait..."
            )
            await asyncio.sleep(0.2)
        await ctx.send(choice)


async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Fun(bot))