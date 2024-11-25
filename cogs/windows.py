from __future__ import annotations

import discord
from discord.ext import commands

import platform
import psutil
import wmi
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from bot import CSGDiscordBot


class Windows(commands.Cog):
    def __init__(self, bot):
        self.bot: CSGDiscordBot = bot

    def get_battery_info():
        battery = psutil.sensors_battery()
        percent = battery.percent
        charging = battery.power_plugged

        return percent, charging

    @commands.hybrid_command()
    async def battery(self, ctx: commands.Context):
        percent, charging = get_battery_info()

        if charging:
            status = "charging"
        else:
            status = "not charging"

        embed = discord.Embed(
            title="CortSiriGoogle PC Host Battery Status",
            description=f"The battery percentage of this bot's host PC is currently at **`{percent}%`**, and it is currently **`{status}`**.",
            color=0x40A02B,
        )
        embed.set_footer(text="Yes, if the battery is full, we know. Just shut up.")
        await ctx.send(embed=embed)

    @commands.hybrid_command(description="Get CortSiriGoogle PC Client Info (this may or may not work depending on OS the host runs on)")
    async def winfetch(self, ctx: commands.Context):
        # THIS COMMAND IS FOR WINDOWS ONLY!!!

        os_info = platform.uname()
        cpu_info = platform.processor()

        # Retrieve GPU info using wmi
        c = wmi.WMI()
        gpu_info = "N/A"
        for gpu in c.Win32_VideoController():
            gpu_info = gpu.Caption
            break

        memory_info = psutil.virtual_memory()
        uptime = round(time.time() - psutil.boot_time())
        kernel_info = platform.release()

        embed = discord.Embed(
            title="CortSiriGoogle PC Client Info",
            description=f"""
```
Operating System: {os_info.system}
Kernel: {kernel_info} ({os_info.version})
Device Host Name: {os_info.node}
Uptime: {uptime // 3600} hours, {(uptime % 3600) // 60} minutes
CPU: {cpu_info} ({os_info.machine})
GPU: {gpu_info}
Memory: Available {memory_info.available / (1024 ** 3):.2f} GB / Total {memory_info.total / (1024 ** 3):.2f} GB
```""",
            color=0x66ABC6,
        )
        embed.set_footer(
            text="To see battery info, do /battery. The battery command may not respond if the bot's PC host doesn't have one."
        )
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Windows(bot))
