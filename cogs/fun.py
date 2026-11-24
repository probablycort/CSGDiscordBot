from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import cowsay
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
        aliases=["status"],
        description="Displays info about the status lyric sequence",
    )
    async def song(self, ctx: commands.Context):
        """Displays details about the status lyric sequence."""
        info = getattr(self.bot, "active_song_info", SONG_INFO)
        status_mode = (
            "Lyric Sequence (Active)"
            if self.bot.lyric_mode
            else "Normal Status Cycle"
        )
        timing_str = (
            "LRCLIB Synced Timestamps"
            if info.get("synced")
            else f"{LYRIC_DELAY} seconds / line"
        )

        embed = discord.Embed(
            title=f"🎵 {info.get('title', 'Unknown')}",
            description=f"By **{info.get('artist', 'Unknown')}**",
            color=0x7289DA,
            url=info.get("youtube_url"),
        )
        embed.add_field(
            name="Album",
            value=f"`{info.get('album', 'N/A')}`",
            inline=True,
        )
        embed.add_field(
            name="Year",
            value=f"`{info.get('release_year', 'N/A')}`",
            inline=True,
        )
        embed.add_field(
            name="Status Mode", value=f"`{status_mode}`", inline=False
        )
        embed.add_field(
            name="Total Lyric Entries",
            value=f"`{info.get('line_count', len(LYRICS))} entries`",
            inline=True,
        )
        embed.add_field(
            name="Timing", value=f"`{timing_str}`", inline=True
        )

        if info.get("youtube_url"):
            embed.add_field(
                name="Links",
                value=f"[YouTube]({info['youtube_url']})",
                inline=False,
            )

        embed.set_footer(text="Statuses Info • Powered by lrclib.net")

        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["dice"], description="Roll a dice")
    @app_commands.describe(max_val="The maximum number to roll (default: 6)")
    async def roll(self, ctx: commands.Context, max_val: int = 6):
        number = random.randint(1, max_val)
        await ctx.send(f"You have rolled a **{number}**.")

    @commands.hybrid_command(
        name="8ball",
        aliases=["eightball", "8b"],
        description="Ask the magic 8-ball a question",
    )
    @app_commands.describe(question="The question you want to ask the 8-ball")
    async def eight_ball(self, ctx: commands.Context, *, question: str):
        responses = [
            "It is certain",
            "Without a doubt",
            "Reply hazy, try again",
            "Ask again later",
            "Don't count on it",
            "My reply is no",
        ]

        answer = random.choice(responses)

        embed = discord.Embed(title="🎱 8-Ball", color=0x5865F2)
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=answer, inline=False)

        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(
        aliases=["guessinggame", "startgame"],
        description="Start a number guessing game",
    )
    @app_commands.describe(
        min_val="The minimum number in the range (default: 1)",
        max_val="The maximum number in the range (default: 100)",
        max_guesses="The maximum number of allowed guesses (default: 15)",
    )
    async def guess(
        self,
        ctx: commands.Context,
        min_val: int = 1,
        max_val: int = 100,
        max_guesses: int = 15,
    ):
        """Start a number guessing game with custom ranges and guess limits."""
        if min_val >= max_val:
            return await ctx.send(
                "❌ The minimum number must be strictly less than the maximum number!"
            )

        if max_guesses <= 0:
            return await ctx.send("❌ Maximum guesses must be at least 1!")

        number = random.randint(min_val, max_val)
        await ctx.send(
            f"## Guessing game started!\n"
            f"Please guess a number between **{min_val}** and **{max_val}**.\n"
            f"You have **{max_guesses}** guesses."
        )

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        for i in range(max_guesses):
            try:
                msg = await self.bot.wait_for(
                    "message", check=check, timeout=30
                )
                try:
                    val = int(msg.content)
                    if val == number:
                        await ctx.send(
                            f"🎉 Congrats, you guessed it correctly! It took you **{i + 1}** tries."
                        )
                        break
                    elif val > number:
                        await ctx.send("Lower!")
                    else:
                        await ctx.send("Higher!")
                except ValueError:
                    await ctx.send("Please send a valid integer.")
            except asyncio.TimeoutError:
                await ctx.send("⏰ You ran out of time! Game over.")
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

    @commands.hybrid_command(
        name="cowsay",
        aliases=["cow"],
        description="Make an ASCII cow speak your message",
    )
    @app_commands.describe(message="The message for the cow to say")
    async def cowsay_cmd(self, ctx: commands.Context, *, message: str):
        """Make an ASCII cow speak your message."""
        cow_output = cowsay.get_output_string("cow", message)

        embed = discord.Embed(
            title="Cowsay",
            description=f"```\n{cow_output}\n```",
            color=0x5865F2,
        )

        await ctx.send(embed=embed)


async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Fun(bot))