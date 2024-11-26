from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import CSGDiscordBot


class PutCogNameHere(commands.Cog):
    def __init__(self, bot):
        self.bot: CSGDiscordBot = bot

    # Use this as a base to add more cogs to your bot.
    #
    # Put whatever command you want to be in this cog using these decorators:
    #  @commands.command for prefix commands
    #  @commands.hybrid_command for both prefix and slash
    #  @app_commands.command for app/slash commands
    #
    # Then add the file name (without the .py) on the
    # extensions variable on start.py:
    #
    #  extensions = ['owner', 'fun', 'default', 'filename']
    #
    # ~ Kita

async def setup(bot: CSGDiscordBot):
    await bot.add_cog(PutCogNameHere(bot))
