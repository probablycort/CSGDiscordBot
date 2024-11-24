import discord, time, asyncio, psutil, wmi, platform, random, sys, os
from discord.ext import commands

def restart_bot(): 
    os.execv(sys.executable, ['python'] + sys.argv)

def get_battery_info():
    battery = psutil.sensors_battery()
    percent = battery.percent
    charging = battery.power_plugged

    return percent, charging

class slashcmds(commands.Cog):
    def __init__(self, client):
        self.client = client 

    @commands.Cog.listener()
    async def on_ready(self):
        print("Slash cog loaded")   

    @commands.tree.command(name="shutdown", description="Completely shuts down the bot. Only \"the superusers\" could do this command...")
    async def slashshutdown(self, Interaction: discord.Interaction):
        id = str(Interaction.user.id)
        if id == '496263009958756352':
            await Interaction.response.send_message('## The bot is shutting down, please wait... <a:loading_2:1309560598048014387>\n-# The bot MUST be ran again from the host PC after it shutdown. To check if it is has been shut down, wait until the bot\'s status is offline.')
            await asyncio.sleep(1)
            await Interaction.client.close()
        else:
            await Interaction.response.send_message("## Womp womp.\nYou don't have the sufficient permissions to perform this action!\n-# Please, do not abuse this command. Oh wait, you're unable to run it anyway.", ephemeral=True)

    @commands.tree.command(name="restart", description="Completely restarts the bot. Only \"the superusers\" could do this command...")
    async def slashrestart(Interaction: discord.Interaction):
        id = str(Interaction.user.id)
        if id == '496263009958756352':
            await Interaction.response.send_message('## The bot is restarting. <a:loading_2:1309560598048014387>\n-# Check the bot\'s status to confirm that it has restarted! The bot\'s status starts off with `bit.ly/CSGDiscordBot`.')
            await asyncio.sleep(1)
            restart_bot()
        else:
            await Interaction.response.send_message("## Womp womp.\nYou don't have the sufficient permissions to perform this action!\n-# Please, do not abuse this command. Oh wait, you're unable to run it anyway.", ephemeral=True)

    @commands.tree.command(name="help", description="Shows the list of commands of this bot.")
    async def slashhelp(Interaction: discord.Interaction):
        embed=discord.Embed(title="CortSiriGoogle Help", description="Get to see the list of CortSiriGoogle's commands.\n-# *Currently not available\n-# **May have issues or doesn't function properly\n-# ***Only available to some servers", color=0x1e66f5)
        embed.add_field(name="Slash Commands", value="```/help (shows this command), /ping, /uptime, /status, /battery, /winfetch, /restart, /shutdown```", inline=True)
        embed.add_field(name="Default Commands", value="```.help (shows this command), **.guess, .choose, .roll, .echo, *.tags, .ping, .restart, .shutdown```", inline=True)
        embed.add_field(name="System (PC Host) Commands", value="```.battery, .uptime, .status, .winfetch```", inline=False)
        embed.add_field(name="Media Commands", value="-# Media commands doesn't use the bot's prefix. Instead, it directly responses to the user's message without needing to use a prefix.\n```cantaloupe, probably cort, nerd, brick, 🧱, !barn, **:pomni::pomni::pomni:```", inline=True)
        embed.add_field(name="Test Commands", value="-# For debugging purposes\n```testwithoutprefix, .test, /test```", inline=True)
        embed.set_footer(text="[INFO] The commands with the battery info may not be available depending on the bot's PC host.")
        await Interaction.response.send_message(embed=embed)

    @commands.tree.command(name="test", description="Test command.")
    async def slashtest(Interaction: discord.Interaction):
        await Interaction.response.send_message(content="```Slash Command is functional.```")

    @commands.tree.command(name="ping", description="Shows the bot's latency.")
    async def slashping(Interaction: discord.Interaction):
        await Interaction.response.send_message('🏓 Pong! `{0}ms`'.format(round(commands.latency * 1000)))

    @commands.tree.command(name="uptime", description="Shows the bot's uptime.")
    async def slashuptime(Interaction: discord.Interaction):
        uptime = round(time.time() - psutil.boot_time())
        embed=discord.Embed(title="CortSiriGoogle PC Host Uptime", description=f'This PC bot host has been up for `{uptime // 3600} hours, {(uptime % 3600) // 60} minutes` (and counting.)', color=discord.Color.dark_blue())
        await Interaction.response.send_message(embed=embed)

    @commands.tree.command(name="status", description="Shows the bot's current status (uptime and battery if available).")
    async def slashstatus(Interaction: discord.Interaction):
        percent, charging = get_battery_info()

        if charging:
            status = "charging"
        else:
            status = "not charging"

        uptime = round(time.time() - psutil.boot_time())
        embed=discord.Embed(title="CortSiriGoogle PC Host Status", description="Shows the battery status and uptime status.", color=0x66abc6)
        embed.add_field(name="System Uptime", value=f"{uptime // 3600} hours, {(uptime % 3600) // 60} minutes (and counting.)", inline=True)
        embed.add_field(name="Battery", value=f"{percent}%, currently {status}.", inline=True)
        await Interaction.response.send_message(embed=embed)

    @commands.tree.command(name="battery", description="Shows the bot's battery (if available).")
    async def slashbattery(Interaction: discord.Interaction):
        percent, charging = get_battery_info()

        if charging:
            status = "charging"
        else:
            status = "not charging"
        
        embed=discord.Embed(title="PC Host Battery Status", description=f"The battery percentage of this bot\'s host PC is currently at **`{percent}%`**, and it is currently **`{status}`**.", color=0x40a02b)
        embed.set_footer(text="Yes, if the battery is full, we know. Just shut up.")
        await Interaction.response.send_message(embed=embed)

    @commands.tree.command(name="winfetch", description="Neofetch, but on Windows. Shows the bot's client info.")
    async def slashwinfetch(Interaction: discord.Interaction):
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

        embed=discord.Embed(title="CortSiriGoogle PC Client Info", description=f"```Operating System: {os_info.system}\nKernel: {kernel_info} ({os_info.version})\nDevice Host Name: {os_info.node}\nUptime: {uptime // 3600} hours, {(uptime % 3600) // 60} minutes\nCPU: {cpu_info} ({os_info.machine})\nGPU: {gpu_info}\nMemory: Available {memory_info.available / (1024 ** 3):.2f} GB / Total {memory_info.total / (1024 ** 3):.2f} GB```", color=0x66abc6)
        embed.set_footer(text="To see battery info, do /battery. The battery command may not respond if the bot's PC host doesn\'t have one.")
        await Interaction.response.send_message(embed=embed)

async def setup(client):
    await client.add_cog(slashcmds(client))