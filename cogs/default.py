from __future__ import annotations

import sys
import discord
from discord import app_commands
from discord.ext import commands

from typing import Optional
from typing import TYPE_CHECKING

from config import VERSION

if TYPE_CHECKING:
    from bot import CSGDiscordBot


class Default(commands.Cog):
    """General bot utility commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_os_label(self) -> str:
        """Returns a clean string representation of the current host operating system."""
        platform_map = {
            "win32": "Windows",
            "linux": "Linux",
            "darwin": "macOS",
        }
        return platform_map.get(sys.platform, sys.platform.title())

    @commands.hybrid_command(
        name="help",
        description="Shows help information for commands and categories",
    )
    @app_commands.describe(
        query="The specific command or category you want help for"
    )
    async def help(self, ctx: commands.Context, *, query: Optional[str] = None):
        """Shows help information for commands and categories."""
        prefix = ctx.clean_prefix
        os_label = self.get_os_label()

        # 1. SPECIFIC QUERY (.help <command> or .help <category>)
        if query:
            query = query.strip()
            
            # Check if query matches a Cog/Category
            cog = self.bot.get_cog(query) or self.bot.get_cog(query.title())
            if cog:
                embed = discord.Embed(
                    title=f"⚙️ {cog.qualified_name} Commands",
                    description=f"Current Prefix: `{prefix}`\n{cog.description or 'No category description provided.'}",
                    color=0x5865F2,
                )
                
                # Filter visible commands in this cog
                for cmd in cog.get_commands():
                    if cmd.hidden:
                        continue
                    desc = cmd.short_doc or cmd.description or "No description provided."
                    embed.add_field(
                        name=f"{prefix}{cmd.qualified_name} {cmd.signature}".strip(),
                        value=desc,
                        inline=False,
                    )

                embed.set_footer(
                    text=f"v{VERSION} | OS: {os_label} | Use {prefix}help <command> for parameters."
                )
                return await ctx.reply(embed=embed, mention_author=False)

            # Check if query matches a Command
            cmd = self.bot.get_command(query)
            if cmd and not cmd.hidden:
                desc = cmd.help or cmd.short_doc or cmd.description or "No description provided."
                embed = discord.Embed(
                    title=f"Command: {prefix}{cmd.qualified_name}",
                    description=desc,
                    color=0x5865F2,
                )
                embed.add_field(
                    name="Current Prefix",
                    value=f"`{prefix}`",
                    inline=True,
                )
                embed.add_field(
                    name="Usage",
                    value=f"`{prefix}{cmd.qualified_name} {cmd.signature}`".strip(),
                    inline=True,
                )

                if cmd.aliases:
                    embed.add_field(
                        name="Aliases",
                        value=", ".join([f"`{a}`" for a in cmd.aliases]),
                        inline=False,
                    )

                embed.set_footer(text=f"v{VERSION} | OS: {os_label}")
                return await ctx.reply(embed=embed, mention_author=False)

            # If neither cog nor command was found
            embed = discord.Embed(
                title="❌ Help Error",
                description=f"No command or category named `{query}` was found.",
                color=0xED4245,
            )
            return await ctx.reply(embed=embed, mention_author=False)

        # 2. GENERAL HELP PAGE (.help)
        embed = discord.Embed(
            title="CortDB Command Help",
            description=(
                f"Commands start with `/` or `{prefix}` and the prefix can only be changed by the bot host.\n"
                f"This bot is currently hosted on **{os_label}**.\n\n"
                f"Use `{prefix}help <command>` for detailed info on a command.\n"
                f"Use `{prefix}help <category>` for category info."
            ),
            color=0x5865F2,
        )

        for cog_name, cog in sorted(self.bot.cogs.items()):
            # Filter commands user can see
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if not cmds:
                continue

            command_list = [f"`{c.name}`" for c in cmds]
            embed.add_field(
                name=f"{cog_name}",
                value=" ".join(command_list),
                inline=False,
            )

        # Uncategorized commands (if any exist outside cogs)
        uncategorized = [c for c in self.bot.commands if c.cog is None and not c.hidden]
        if uncategorized:
            command_list = [f"`{c.name}`" for c in uncategorized]
            embed.add_field(
                name="General",
                value=" ".join(command_list),
                inline=False,
            )

        embed.set_footer(
            text=f"v{VERSION} | Total Commands: {len(self.bot.commands)}"
        )
        await ctx.reply(embed=embed, mention_author=False)


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

    @commands.command(name="hiddenecho", aliases=["hecho"], description="Echoes back your message and deletes your command invocation message.")
    async def hiddenecho(self, ctx: commands.Context, *, message: str):
        """Prefix-only command that sends your message and removes the command trigger."""
        # Safely attempt to delete the triggering message
        if ctx.guild:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                # Safe fallback if bot lacks 'Manage Messages' permission or message was already removed
                pass

        await ctx.send(message)

    @commands.hybrid_command(description="Make me say something inside an embed.")
    @app_commands.describe(message="The message you want me to say")
    async def embedecho(self, ctx: commands.Context, *, message):
        embed = discord.Embed(description=message, color=0x1E66F5)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", aliases=["av", "pfp"], description="Gets a user's avatar")
    @app_commands.describe(
        user="The user whose avatar you want to fetch (defaults to you)",
        server="Fetch server-specific avatar if true, or global avatar if false"
    )
    async def avatar(
        self, 
        ctx: commands.Context, 
        user: Optional[discord.Member | discord.User] = None, 
        server: bool = False
    ):
        target = user or ctx.author
        
        # Determine avatar URL (Server avatar vs Global avatar)
        if server and isinstance(target, discord.Member) and target.guild_avatar:
            avatar_url = target.guild_avatar.url
            title_type = "Server Avatar"
        else:
            avatar_url = target.display_avatar.url
            title_type = "Avatar"

        embed = discord.Embed(
            title=f"{target.display_name}'s {title_type}",
            color=0x5865F2
        )
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        await ctx.reply(embed=embed, mention_author=False)

    @commands.hybrid_command(name="banner", description="Gets a user's banner")
    @app_commands.describe(
        user="The user whose banner you want to fetch (defaults to you)",
        server="Fetch server-specific banner if true, or global banner if false"
    )
    async def banner(
        self, 
        ctx: commands.Context, 
        user: Optional[discord.Member | discord.User] = None, 
        server: bool = False
    ):
        target = user or ctx.author

        # Fetch full user profile to retrieve banner data from Discord API
        try:
            full_user = await self.bot.fetch_user(target.id)
        except discord.HTTPException:
            full_user = target

        # Check for Server Banner vs Global Banner
        banner_url = None
        title_type = "Banner"

        if server and isinstance(target, discord.Member) and getattr(target, "guild_banner", None):
            banner_url = target.guild_banner.url
            title_type = "Server Banner"
        elif full_user.banner:
            banner_url = full_user.banner.url

        if not banner_url:
            return await ctx.reply(f"❌ **{target.display_name}** does not have a banner set.", mention_author=False)

        embed = discord.Embed(
            title=f"{target.display_name}'s {title_type}",
            color=0x5865F2
        )
        embed.set_image(url=banner_url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Default(bot))
