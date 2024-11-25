from __future__ import annotations

import discord
from discord.ext import commands

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from bot import CSGDiscordBot


log = logging.getLogger("CSGDiscordBot")


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot: CSGDiscordBot = bot

    @commands.is_owner()
    @commands.hybrid_command(description="Gives out server rules")
    async def rulestxt(self, ctx: commands.Context):
        embed = discord.Embed(
            title="DISCORD SERVER RULES",
            description="**Welcome to CortSiriGoogle Studios!** While you're here, we'll ask you to follow the following rules:",
            colour=0x9357B3,
        )
        embed.set_author(
            name="CortSiriGoogle Studios",
            icon_url="https://cdn.discordapp.com/emojis/1284567633022156845.webp",
        )
        embed.add_field(
            name="Treat everyone with respect.",
            value="- Absolutely no harassment, witch-hunting, racism, or hate speech.",
            inline=False,
        )
        embed.add_field(
            name="Swearing is allowed. However...",
            value="- If it is a slur, used sexually, or towards hate, it's not allowed.\n - If AutoMod *somehow* got your message moderated but it does not break the rules, let us know!",
            inline=False,
        )
        embed.add_field(
            name="No spamming or self-promotion.",
            value="- This includes messaging our members.",
            inline=False,
        )
        embed.add_field(
            name="Be friendly to others.",
            value="- Even though we allow swearing, just be friendly to each other.\n- Seriously, do not harass anyone, please.",
            inline=False,
        )
        embed.add_field(
            name="Absolutely NO NSFW or GORE CONTENT.",
            value="- This includes text, images, and links featuring nudity, sex, hard violence, or other graphically disturbing content.",
            inline=False,
        )
        embed.add_field(
            name="Underage members are NOT allowed.",
            value="- Even though we sound like a server for all ages, we are not allowing underage members that is under the age of 13.\n - Any underage members that is under the age of 13 will be banned and will be reported immediately to Discord.",
            inline=False,
        )
        embed.add_field(
            name="Follow Discord's Terms of Service.",
            value="- We highly recommend you to follow Discord's Terms of Service.",
            inline=False,
        )
        embed.add_field(
            name="And please, USE COMMON SENSE.",
            value="- Don't even try to share your ACTUAL information and identity **anywhere** on this platform.\n - And please, keep yourself safe online.",
            inline=False,
        )
        embed.add_field(
            name="WARNING:",
            value="-# **Please be warned that if you're not following the rules, it can result you of getting warned, muted, kicked, or banned.**",
            inline=False,
        )
        embed.add_field(
            name=":white_check_mark: We encourage you to invite anyone!",
            value="Go ahead, invite your friend who knows all about Roblox Studio, a tech enthusiast that always uses Linux and never Windows, a Visual Studio Code user that works on their project 24/7, or **literally anyone**! Invite them at discord.gg/Nm6fWfjcyh",
            inline=True,
        )
        embed.add_field(
            name=":warning: You may need to mute some channels from this server.",
            value="This is because of the default notification setting is set to all messages. This setting may will be changed in the future.",
            inline=True,
        )
        embed.add_field(
            name="Other Information",
            value="-# :art: CortSiriGoogle Studios server roles are using [Catppuccin](https://catppuccin.com/) color palettes! Check out #roles for more information about it.\n-# :link: Check out our [website](https://bit.ly/CortSiriGoogle) to learn more about us, links to our socials, and more.\n-# :grey_question: Need help/report something? Ping @Moderator or any higher ranked members.\n-# :rolling_eyes: No, the :dognerd: emoji does not affect you if you reacted to it or not.",
            inline=False,
        )

        await ctx.send(embed=embed)

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
        if mod == 'cogs.owner':
            return await ctx.reply("Are u stupid?")
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

        commands = await self.bot.tree.sync(guild=guild)
        await ctx.reply(f"Successfully synced {len(commands)} commands.")

    @sync.command(name="global")
    @commands.is_owner()
    async def sync_global(self, ctx: commands.Context):

        commands = await self.bot.tree.sync()
        await ctx.reply(f"Successfully synced {len(commands)} commands.")

    @commands.is_owner()
    @commands.command(hidden=True)
    async def shutdown(self, ctx: commands.Context):
        await ctx.reply("Shutting down :wave:")
        await self.bot.close()


async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Core(bot))
