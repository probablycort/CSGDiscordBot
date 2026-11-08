from __future__ import annotations

import sys
import psutil
import discord
from discord import app_commands
from discord.ext import commands

from datetime import datetime, timezone, timedelta
from typing import Optional
from typing import TYPE_CHECKING

from config import VERSION

if TYPE_CHECKING:
    from bot import CSGDiscordBot


class HelpSelect(discord.ui.Select):
    def __init__(self, bot: CSGDiscordBot, prefix: str, os_label: str):
        self.bot = bot
        self.prefix = prefix
        self.os_label = os_label

        options = [
            discord.SelectOption(
                label="🏠 Main Overview",
                description="Return to the main help menu overview",
                value="main"
            )
        ]

        # Populate options for each cog category
        for cog_name in sorted(bot.cogs.keys()):
            cog = bot.get_cog(cog_name)
            if not cog:
                continue
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if cmds:
                # Use cog docstring/description if set, fallback otherwise
                desc = (cog.description or f"View commands under {cog_name}").strip()
                if len(desc) > 100:
                    desc = desc[:97] + "..."

                options.append(
                    discord.SelectOption(
                        label=f"{cog_name} Commands",
                        description=desc,
                        value=cog_name
                    )
                )

        # Check for uncategorized/general commands
        uncategorized = [c for c in bot.commands if c.cog is None and not c.hidden]
        if uncategorized:
            options.append(
                discord.SelectOption(
                    label="General Commands",
                    description="General uncategorized commands",
                    value="General"
                )
            )

        super().__init__(
            placeholder="Select a command category...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected = self.values[0]

        if selected == "main":
            embed = self.view.build_main_embed()
            return await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self.view)

        # Handle category selection
        if selected == "General":
            cmds = [c for c in self.bot.commands if c.cog is None and not c.hidden]
            embed = discord.Embed(
                title="⚙️ General Commands",
                description=f"Current Prefix: `{self.prefix}`",
                color=0x5865F2,
            )
            for cmd in cmds:
                desc = cmd.short_doc or cmd.description or "No description provided."
                embed.add_field(
                    name=f"{self.prefix}{cmd.qualified_name} {cmd.signature}".strip(),
                    value=desc,
                    inline=False,
                )
            embed.set_footer(text=f"v{VERSION} | OS: {self.os_label}")
            return await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self.view)

        cog = self.bot.get_cog(selected)
        if cog:
            embed = discord.Embed(
                title=f"⚙️ {cog.qualified_name} Commands",
                description=f"Current Prefix: `{self.prefix}`\n{cog.description or 'No category description provided.'}",
                color=0x5865F2,
            )
            for cmd in cog.get_commands():
                if cmd.hidden:
                    continue
                if isinstance(cmd, commands.Group):
                    for sub in cmd.commands:
                        if not sub.hidden:
                            desc = sub.short_doc or sub.description or "No description provided."
                            embed.add_field(
                                name=f"{self.prefix}{cmd.qualified_name} {sub.name} {sub.signature}".strip(),
                                value=desc,
                                inline=False,
                            )
                else:
                    desc = cmd.short_doc or cmd.description or "No description provided."
                    embed.add_field(
                        name=f"{self.prefix}{cmd.qualified_name} {cmd.signature}".strip(),
                        value=desc,
                        inline=False,
                    )
            embed.set_footer(text=f"v{VERSION} | OS: {self.os_label}")
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, bot: CSGDiscordBot, prefix: str, os_label: str, author: discord.User | discord.Member):
        super().__init__(timeout=None)  # No timeout as requested
        self.bot = bot
        self.prefix = prefix
        self.os_label = os_label
        self.author = author
        self.message: discord.Message | None = None
        self.add_item(HelpSelect(bot, prefix, os_label))

    def build_main_embed(self) -> discord.Embed:
        """Constructs the unified main overview embed with clean category lists."""
        embed = discord.Embed(
            title="CortDB Command Help",
            description=(
                f"Commands start with `/` or `{self.prefix}` and the prefix can only be changed by the bot host.\n"
                f"This bot is currently hosted on **{self.os_label}**.\n\n"
                f"Select a category from the dropdown menu below to view specific commands."
            ),
            color=0x5865F2,
        )

        categories_summary = []
        for cog_name in sorted(self.bot.cogs.keys()):
            cog = self.bot.get_cog(cog_name)
            if not cog:
                continue
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if cmds:
                categories_summary.append(f"• **{cog_name}** (`{len(cmds)} commands`)")

        uncategorized = [c for c in self.bot.commands if c.cog is None and not c.hidden]
        if uncategorized:
            categories_summary.append(f"• **General** (`{len(uncategorized)} commands`)")

        if categories_summary:
            embed.add_field(
                name="Available Categories",
                value="\n".join(categories_summary),
                inline=False,
            )

        embed.set_footer(
            text=f"v{VERSION} | Total Commands: {len(self.bot.commands)}"
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ Only the person who requested help can use this menu.", ephemeral=True)
            return False
        return True


class Default(commands.Cog):
    """General bot utility commands."""

    def __init__(self, bot: CSGDiscordBot):
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

        if query:
            query = query.strip()
            cog = self.bot.get_cog(query) or self.bot.get_cog(query.title())
            if cog:
                embed = discord.Embed(
                    title=f"⚙️ {cog.qualified_name} Commands",
                    description=f"Current Prefix: `{prefix}`\n{cog.description or 'No category description provided.'}",
                    color=0x5865F2,
                )
                
                for cmd in cog.get_commands():
                    if cmd.hidden:
                        continue
                    if isinstance(cmd, commands.Group):
                        for sub in cmd.commands:
                            if not sub.hidden:
                                desc = sub.short_doc or sub.description or "No description provided."
                                embed.add_field(
                                    name=f"{prefix}{cmd.qualified_name} {sub.name} {sub.signature}".strip(),
                                    value=desc,
                                    inline=False,
                                )
                    else:
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

                embed.set_footer(text=f"v{VERSION}")
                return await ctx.reply(embed=embed, mention_author=False)

            embed = discord.Embed(
                title="❌ Help Error",
                description=f"No command or category named `{query}` was found.",
                color=0xED4245,
            )
            return await ctx.reply(embed=embed, mention_author=False)

        # Initial .help call matches Main Overview embed precisely
        view = HelpView(self.bot, prefix, os_label, ctx.author)
        embed = view.build_main_embed()
        msg = await ctx.reply(embed=embed, view=view, mention_author=False)
        view.message = msg

    @commands.hybrid_command(description="Show bot and host system uptime")
    async def uptime(self, ctx: commands.Context):
        bot_uptime_delta = discord.utils.utcnow() - self.bot.start_time
        bot_human_uptime = self.bot.humanize_timedelta(timedelta=bot_uptime_delta)
        
        bot_start_ts = int(self.bot.start_time.timestamp())
        host_boot_ts = int(psutil.boot_time())
        host_boot_dt = datetime.fromtimestamp(host_boot_ts, tz=timezone.utc)
        host_uptime_delta = discord.utils.utcnow() - host_boot_dt
        host_human_uptime = self.bot.humanize_timedelta(timedelta=host_uptime_delta)

        embed = discord.Embed(
            title="System & Bot Uptime",
            color=0x5865F2,
        )
        
        embed.add_field(
            name="Bot Uptime",
            value=(
                f"**Duration:** {bot_human_uptime}\n"
                f"**Started:** <t:{bot_start_ts}:f> (<t:{bot_start_ts}:R>)"
            ),
            inline=False,
        )
        
        embed.add_field(
            name=f"Host System Uptime ({self.get_os_label()})",
            value=(
                f"**Duration:** {host_human_uptime}\n"
                f"**Booted:** <t:{host_boot_ts}:f> (<t:{host_boot_ts}:R>)"
            ),
            inline=False,
        )
        
        embed.set_footer(text=f"v{VERSION} | Requested by {ctx.author.name}")
        await ctx.reply(embed=embed, mention_author=False)

    # ---------------------------------------------------------
    # ECHO COMMAND GROUP (/echo ...)
    # ---------------------------------------------------------
    @commands.hybrid_group(name="echo", description="Make me say something", fallback="say")
    @app_commands.describe(message="The message you want me to say")
    async def echo_group(self, ctx: commands.Context, *, message: Optional[str] = None):
        """Standard echo command when calling /echo or .echo directly."""
        if ctx.invoked_subcommand is None:
            if message:
                await ctx.send(message)
            else:
                await ctx.send_help(ctx.command)

    @echo_group.command(name="hidden", description="Echoes back your message and deletes your command invocation message")
    @app_commands.describe(message="The message you want me to say secretly")
    async def echo_hidden(self, ctx: commands.Context, *, message: str):
        """Sends your message and removes the command trigger."""
        if ctx.guild:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound, discord.HTTPException):
                pass
        await ctx.send(message)

    @echo_group.command(name="embed", description="Make me say something inside an embed")
    @app_commands.describe(message="The message you want me to say inside an embed")
    async def echo_embed(self, ctx: commands.Context, *, message: str):
        """Makes the bot repeat your message inside an embed."""
        embed = discord.Embed(description=message, color=0x1E66F5)
        await ctx.send(embed=embed)

    @commands.command(name="hecho", aliases=["hiddenecho"], hidden=True)
    async def hecho_alias(self, ctx: commands.Context, *, message: str):
        await self.echo_hidden(ctx, message=message)

    @commands.command(name="embedecho", hidden=True)
    async def embedecho_alias(self, ctx: commands.Context, *, message: str):
        await self.echo_embed(ctx, message=message)

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
        
        if server and isinstance(target, discord.Member) and target.guild_avatar:
            avatar_url = target.guild_avatar.url
            title_type = "Server Avatar"
        else:
            avatar_url = target.display_avatar.url
            title_type = "Avatar"

        embed = discord.Embed(
            title=f"@{target.name}'s {title_type}",
            color=0x5865F2
        )
        embed.set_image(url=avatar_url)
        embed.set_footer(text=f"Requested by @{ctx.author.name}")

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

        try:
            full_user = await self.bot.fetch_user(target.id)
        except discord.HTTPException:
            full_user = target

        banner_url = None
        title_type = "Banner"

        if server and isinstance(target, discord.Member) and getattr(target, "guild_banner", None):
            banner_url = target.guild_banner.url
            title_type = "Server Banner"
        elif full_user.banner:
            banner_url = full_user.banner.url

        if not banner_url:
            return await ctx.reply(f"❌ **@{target.name}** does not have a banner set.", mention_author=False)

        embed = discord.Embed(
            title=f"{target.name}'s {title_type}",
            color=0x5865F2
        )
        embed.set_image(url=banner_url)
        embed.set_footer(text=f"Requested by {ctx.author.name}")

        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Default(bot))