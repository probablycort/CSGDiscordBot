from __future__ import annotations

import discord
from discord.ext import commands

import time
import platform
import psutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import CSGDiscordBot


class Linux(commands.Cog):
    def __init__(self, bot):
        self.bot: CSGDiscordBot = bot

    @staticmethod
    def get_battery_info():
        battery = psutil.sensors_battery()
        if battery is None:
            return None, None
        return battery.percent, battery.power_plugged

    @commands.hybrid_command()
    async def battery(self, ctx: commands.Context):
        percent, charging = self.get_battery_info()

        if percent is None:
            embed = discord.Embed(
                title="CortDB Host Battery Status",
                description="No battery detected on this host system (likely running on a desktop or server).",
                color=0xE06C75,
            )
            embed.set_footer(text="the battery is... lost media???")
            return await ctx.send(embed=embed)

        status = "charging" if charging else "not charging"

        embed = discord.Embed(
            title="CortDB Host Battery Status",
            description=f"The battery percentage of this bot's host system is currently at **`{percent}%`**, and it is currently **`{status}`**.",
            color=0x40A02B,
        )
        if percent == 100:
            embed.set_footer(text="We know the battery is full. Just shut the fuck up.")
        else:
            embed.set_footer(text="Yes, if the battery is full, we know. Just shut up.")
        await ctx.send(embed=embed)


    @commands.hybrid_command(
        description="Get CortDB Host Info (linux)"
    )
    async def neofetch(self, ctx: commands.Context):
        # THIS COMMAND IS FOR LINUX ONLY!!!
        os_info = platform.uname()

        # OS / Distro info
        try:
            os_release = platform.freedesktop_os_release()
            os_name = os_release.get("PRETTY_NAME", "Linux")
        except Exception:
            os_name = "Linux"

        kernel_info = platform.release()

        # CPU info from /proc/cpuinfo for accurate neofetch-style naming
        cpu_info = "N/A"
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu_info = line.split(":")[1].strip()
                        break
        except Exception:
            cpu_info = platform.processor() or "N/A"

        # GPU info using lspci
        gpu_info = "N/A"
        try:
            lspci_out = subprocess.check_output("lspci", text=True)
            for line in lspci_out.splitlines():
                if "VGA compatible controller" in line or "3D controller" in line:
                    gpu_info = line.split(":", 2)[-1].strip()
                    break
        except Exception:
            pass

        memory_info = psutil.virtual_memory()
        uptime = round(time.time() - psutil.boot_time())

        embed = discord.Embed(
            title="CortDB Host Info",
            description=f"""```
Operating System: {os_name}
Kernel: {kernel_info} ({os_info.version})
Device Host Name: {os_info.node}
Uptime: {uptime // 3600} hours, {(uptime % 3600) // 60} minutes
CPU: {cpu_info} ({os_info.machine})
GPU: {gpu_info}
Memory: Available {memory_info.available / (1024 ** 3):.2f} GB / Total {memory_info.total / (1024 ** 3):.2f} GB
```""",
            color=0xE95420,  # Classic Linux orange
        )
        embed.set_footer(
            text="To see battery info, do /battery."
        )
        await ctx.reply(embed=embed, mention_author=False)

async def setup(bot: CSGDiscordBot):
    await bot.add_cog(Linux(bot))