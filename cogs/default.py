from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import CSGDiscordBot


class Default(commands.Cog):
    def __init__(self, bot):
        self.bot: CSGDiscordBot = bot

    @commands.hybrid_command(description="Show bot uptime")
    async def uptime(self, ctx: commands.Context):
        return await ctx.reply(
            "I have been up for "
            + self.bot.humanize_timedelta(
                timedelta=(discord.utils.utcnow() - self.bot.start_time)
            )
            + f" (since {discord.utils.format_dt(self.bot.start_time)})"
        )

    @commands.hybrid_command(description="Make me say something")
    @app_commands.describe(message="The message you want me to say")
    async def echo(self, ctx: commands.Context, *, message):
        await ctx.send(message)

    @commands.hybrid_command(description="Make me say something inside an embed.")
    @app_commands.describe(message="The message you want me to say")
    async def embedecho(self, ctx: commands.Context, *, message):
        embed = discord.Embed(description=message, color=0x1E66F5)
        await ctx.send(embed=embed)


async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Default(bot))
