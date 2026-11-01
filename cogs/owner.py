from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

import logging
from typing import TYPE_CHECKING, Optional

import os, sys

import json
import os

if TYPE_CHECKING:
    from bot import CSGDiscordBot


log = logging.getLogger("CSGDiscordBot")


def restart_bot():
    os.execv(sys.executable, ["python"] + sys.argv)


# Helper functions to manage saved settings
def load_settings():
    if not os.path.exists("guild_settings.json"):
        return {}
    with open("guild_settings.json", "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_settings(data):
    with open("guild_settings.json", "w") as f:
        json.dump(data, f, indent=4)

class Core(commands.Cog):
    def __init__(self, bot):
        self.bot: CSGDiscordBot = bot

    async def send_mod_log(self, guild: discord.Guild, title: str, color: int, target, moderator: discord.abc.User, reason: str):
        settings = load_settings()
        log_channel_id = settings.get(str(guild.id))
        if not log_channel_id:
            return
        channel = self.bot.get_channel(log_channel_id)
        if not channel:
            return
        embed = discord.Embed(
            title=f"{title}",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Target", value=f"{target} (`{target.id}`)", inline=False)
        embed.add_field(name="Moderator", value=f"{moderator} (`{moderator.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        if hasattr(target, "avatar") and target.avatar:
            embed.set_thumbnail(url=target.avatar.url)
        await channel.send(embed=embed)


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
        await ctx.reply("Shutting down, goodbye! :wave:")
        await self.bot.change_presence(activity=discord.CustomActivity(name="Shutting down..."))
        await self.bot.close()

    @commands.is_owner()
    @commands.command(hidden=True)
    async def restart(self, ctx: commands.Context):
        msg = await ctx.reply("Restarting, please wait...")
        await self.bot.change_presence(activity=discord.CustomActivity(name="Restarting..."))
        with open("restart.txt", "w") as f:
            f.write(f"{ctx.channel.id}\n{msg.id}")
        restart_bot()


    @commands.has_permissions(manage_emojis=True)
    @commands.command()
    async def dm(self, ctx, user: discord.User, *, content: str):
            try:
                embed = discord.Embed(
                    title=f"Message from {ctx.guild.name}",
                    description=content,
                    color=0xcba6f7
                )
                embed.set_footer(text=f"Sent by {ctx.author.name}")
                await user.send(embed=embed)
                await ctx.send(f"✅ Message successfully sent to **{user}**!")
                log.info("[LOG] %s sent a DM to %s: %s", ctx.author, user, content)
            except discord.Forbidden:
                await ctx.send(f"❌ Unable to DM **{user}**, likely have their DMs disabled.")
            except Exception as e:
                await ctx.send(f"❌ An error occurred: \n{e}")

    @app_commands.checks.has_permissions(administrator=True)
    @commands.hybrid_command(name="setlogchannel", description="Set the moderation log channel for this server")
    @app_commands.describe(channel="The text channel to send moderation logs to")
    async def setlogchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        settings = load_settings()
        
        # Save by guild ID so it works across multiple servers independently
        settings[str(ctx.guild.id)] = channel.id
        save_settings(settings)
        
        await ctx.reply(f"✅ Successfully set the moderation log channel to {channel.mention}!", ephemeral=True)
        log.info("[CONFIG] Moderation log channel set to %s (%d) in guild %s", channel.name, channel.id, ctx.guild.name)

    @app_commands.checks.has_permissions(kick_members=True)
    @commands.hybrid_command(name="warn", description="Issue a warning to a server member")
    @app_commands.describe(member="The member to warn", reason="The reason for the warning")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        try:
            embed = discord.Embed(
                title=f"You have been warned from {ctx.guild.name}",
                description=f"**Reason:** {reason}",
                color=0xFEE75C
            )
            embed.set_footer(text=f"Issued by {ctx.author.name}")
            await member.send(embed=embed)
            dm_status = f"**{member}** has been warned successfully."
        except discord.Forbidden:
            dm_status = "⚠️ Could not DM member (DMs disabled)."
        await ctx.reply(f"{dm_status}")
        log.info("[MOD WARN] %s warned %s: %s", ctx.author, member, reason)
        await self.send_mod_log(ctx.guild, title="Member Warned", color=0xFEE75C, target=member, moderator=ctx.author, reason=reason)

    @app_commands.checks.has_permissions(kick_members=True)
    @commands.hybrid_command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="The reason for the kick")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("❌ You cannot kick someone with an equal or higher role.")
        try:
            embed = discord.Embed(
                title=f"You have been kicked from {ctx.guild.name}",
                description=f"**Reason:** {reason}",
                color=0xED4245
            )
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        try:
            await member.kick(reason=f"{reason} (Issued by {ctx.author})")
            await ctx.reply(f"**{member}** has been kicked from the server!\n**Reason:** {reason}")
            log.info("[MOD KICK] %s kicked %s: %s", ctx.author, member, reason)
            await self.send_mod_log(ctx.guild, title="Member Kicked", color=0xED4245, target=member, moderator=ctx.author, reason=reason)
        except discord.Forbidden:
            await ctx.reply("❌ I do not have permission to kick this member.")

    @app_commands.checks.has_permissions(ban_members=True)
    @commands.hybrid_command(name="ban", description="Ban a user from the server")
    @app_commands.describe(user="The user to ban", reason="The reason for the ban")
    async def ban(self, ctx: commands.Context, user: discord.User, *, reason: str = "No reason provided"):
        # Check hierarchy if target is currently in the guild
        member = ctx.guild.get_member(user.id)
        if member and member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.reply("❌ You cannot ban someone with an equal or higher role.")
        if member:
            try:
                embed = discord.Embed(
                    title=f"You have been banned from {ctx.guild.name}",
                    description=f"**Reason:** {reason}",
                    color=0x992D22
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
        try:
            await ctx.guild.ban(user, reason=f"{reason} (Issued by {ctx.author})")
            await ctx.reply(f"**{user}** has been banned!\n**Reason:** {reason}")
            log.info("[MOD BAN] %s banned %s: %s", ctx.author, user, reason)
            await self.send_mod_log(ctx.guild, title="Member Banned", color=0x992D22, target=user, moderator=ctx.author, reason=reason)
        except discord.Forbidden:
            await ctx.reply("❌ I do not have permission to ban this user.")

async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Core(bot))
