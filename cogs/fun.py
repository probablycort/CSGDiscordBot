from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import asyncio
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import CSGDiscordBot


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot: CSGDiscordBot = bot

    @commands.hybrid_command(aliases=["dice"], description="Roll a dice")
    async def roll(self, ctx, max: int = 6):
        number = random.randint(1, max)
        await ctx.send(f"You have rolled a **{number}**.")

    @commands.command(aliases=["guessinggame", "startgame"])
    async def guess(self, ctx, max: int = 100):
        MAX_GUESSES = 15
        number = random.randint(1, max)
        await ctx.send(
            f"## Guessing game has been started!\nPlease guess a number between **1-{max}.**\nYou have **{MAX_GUESSES}** guesses.\n-# This command is currently marked as [**], which is [May have issues or doesn't function properly]. We encourage you to NOT WIN the game as even after winning the game, you will be spammed and notified with the 'Please send a number.' message. *I would* like to fix the code but I'm just a rookie at Python coding and just too lazy. -Cort"
        )

        def check(m):
            return m.author == ctx.author and m.channel == ctx.message.channel

        for i in range(MAX_GUESSES):
            try:
                guess = await self.bot.wait_for("message", check=check, timeout=15)
                try:
                    int(guess.content)
                    if guess.content == str(number):
                        await ctx.send(
                            f"Congrats, you guessed it correctly! It took you **{i+1}** tries."
                        )
                    elif guess.content >= str(number):
                        await ctx.send(f"Lower!")
                    elif guess.content <= str(number):
                        await ctx.send(f"Higher!")
                except:
                    await ctx.send(
                        "Please send a number.\n-# If you've already won the game and this message still being posted, please immediately let us know to restart the bot."
                    )
            except asyncio.TimeoutError:
                pass
        else:
            await ctx.send(
                f"Game over! You have ran out of tries.\n-# Remember, you only get **{MAX_GUESSES}** guesses!"
            )

    @commands.command(aliases=["choice"])
    async def choose(self, ctx, *, args):
        arguements = args.split(" ")
        choice = random.choice(arguements)
        thinking = await ctx.send(":clock1: Thinking, please wait...")
        await asyncio.sleep(0.2)
        for i in range(4):
            await thinking.edit(content=f":clock{i+1}: Thinking, please wait...")
            await asyncio.sleep(0.2)
        await ctx.send(choice)


async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Fun(bot))
