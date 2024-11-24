import discord
from discord.ext import commands
from discord import app_commands

class defaultcmds(commands.cog):
    def __init__(self, client: commands.Bot):
        self.client = client

