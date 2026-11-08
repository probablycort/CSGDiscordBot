from __future__ import annotations

import discord
from discord.ext import commands

import logging
import os
import sys

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bot import CSGDiscordBot


log = logging.getLogger("CSGDiscordBot")


def restart_bot():
    os.execv(sys.executable, [sys.executable] + sys.argv)


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot: CSGDiscordBot = bot

    @commands.is_owner()
    @commands.command(hidden=True)
    async def load(self, ctx: commands.Context, *, mod: str):
        try:
            await ctx.channel.typing()
            await self.bot.load_extension(mod)
        except commands.ExtensionError as e:
            log.exception("%s: Unable to load:", mod, exc_info=e)
            await ctx.reply(f"{e.__class__.__name__}: {e}")
        else:
            await ctx.reply("Loaded.")

    @commands.is_owner()
    @commands.command(hidden=True)
    async def unload(self, ctx: commands.Context, *, mod: str):
        if mod == "cogs.owner":
            return await ctx.reply("Are you stupid?")
        try:
            await ctx.channel.typing()
            await self.bot.unload_extension(mod)
        except commands.ExtensionError as e:
            log.exception("%s: Unable to unload:", mod, exc_info=e)
            await ctx.reply(f"{e.__class__.__name__}: {e}")
        else:
            await ctx.reply("Unloaded.")

    @commands.is_owner()
    @commands.command(hidden=True)
    async def reload(self, ctx: commands.Context, *, mod: str):
        try:
            await ctx.channel.typing()
            await self.bot.reload_extension(mod)
        except commands.ExtensionError as e:
            log.exception("%s: Unable to reload:", mod, exc_info=e)
            await ctx.reply(f"{e.__class__.__name__}: {e}")
        else:
            await ctx.reply("Reloaded.")

    @commands.group(invoke_without_command=True, hidden=True)
    @commands.is_owner()
    @commands.guild_only()
    async def sync(
        self, ctx: commands.Context, guild_id: Optional[int], copy: bool = False
    ):
        if guild_id:
            guild = discord.Object(guild_id)
        else:
            guild = ctx.guild

        await ctx.channel.typing()
        if copy:
            self.bot.tree.copy_global_to(guild=guild)

        commands_list = await self.bot.tree.sync(guild=guild)
        await ctx.reply(f"Successfully synced {len(commands_list)} commands.")

    @sync.command(name="global")
    @commands.is_owner()
    async def sync_global(self, ctx: commands.Context):
        commands_list = await self.bot.tree.sync()
        await ctx.reply(f"Successfully synced {len(commands_list)} commands.")

    @commands.is_owner()
    @commands.command(hidden=True)
    async def shutdown(self, ctx: commands.Context):
        await ctx.reply("Shutting down, goodbye! :wave:")
        await self.bot.change_presence(activity=discord.CustomActivity(name="Shutting down..."))
        await self.bot.close()

    @commands.is_owner()
    @commands.command(hidden=True)
    async def restart(self, ctx: commands.Context):
        msg = await ctx.reply(
            "Restarting, please wait...\n"
            "-# Check the bot's status or this message for any changes.\n"
            "-# If you think it's stuck on \"Restarting\", it usually means an error occurred on the host's side and refuses to start."
        )
        await self.bot.change_presence(activity=discord.CustomActivity(name="Restarting..."))
        with open("restart.txt", "w") as f:
            f.write(f"{ctx.channel.id}\n{msg.id}")
        restart_bot()


async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Core(bot))