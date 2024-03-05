from datetime import timedelta
import random
import time
import psutil
import platform
import wmi
import discord
from discord import app_commands
from discord.ext import commands


intents = discord.Intents.default()
intents.message_content = True
intents.typing = False
intents.presences = False
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)



def get_battery_info():
    battery = psutil.sensors_battery()
    percent = battery.percent
    charging = battery.power_plugged

    return percent, charging

# There's some unused response code since it doesn't work or something, but you could make it work or just customize it. You can laugh at me now.
# Below are old, OLD technique of making responses. I heard there was a new way to make one, but I have to REWRITE all of the bot's code. Have fun customizing it!!!

def get_response(message: str) -> str:
    p_message = message.lower()

    if p_message == '.test embed':
        embed = discord.Embed(title='Title', description='Desc', color=discord.Color.random())
        embed.add_field(name="Name", value="Value", inline=False)
        return embed

    if message == '.roll':
        return str(random.randint(1, 6))

    if p_message == '.help':
        return "## Available Commands\n```Default Commands: .help, .roll, .test, .echo, .tags *.ping\n\nSystem (PC Host) Commands: .battery, .uptime, .status, .winfetch\n\nMedia Commands: cantaloupe, probably cort, nerd, brick, 🧱, !barn, **:pomni::pomni::pomni:\n\nMedia commands doesn't use the bot's prefix. Instead, it directly responses to the user's message without needing to use a prefix.```\n```*Doesn't function properly\n**Only available to some servers```"

    if p_message == 'probably cort':
        return "https://media.discordapp.net/attachments/763430451217432589/793847564045647872/unknown.png?width=130&height=177"

    if p_message == 'cantaloupe':
        return 'https://cdn.discordapp.com/attachments/1079702225774972958/1148636977265123500/lv_0_20230804133527.mp4'

    if p_message == 'nerd':
        return "https://tenor.com/view/nerd-meme-funny-idk-cool-gif-15925381156197121154"
    
    if p_message == 'brick':
        return ":bricks:"
    
    if p_message == '🧱':
        return "🧱"

    if p_message == ':bricks:':
        return "🧱"

    if p_message == '<:pomni:1164212247866912889><:pomni:1164212247866912889><:pomni:1164212247866912889>':
        return "https://tenor.com/view/pomni-digitalcircus-digital-circus-the-amazing-digital-circus-tadc-gif-87641691478271811"
    
    if p_message == '<:pomni:1164212247866912889> <:pomni:1164212247866912889> <:pomni:1164212247866912889>':
        return "https://tenor.com/view/pomni-digitalcircus-digital-circus-the-amazing-digital-circus-tadc-gif-87641691478271811"

    if p_message == '!barn':
        return "https://tenor.com/view/barn-gif-19719443"
    
    if p_message == '.test':
        return "`This is a test message. Beep Boop!`"

    if p_message == '<@1156595433397825728>':
        return '## Hello there!\nMy default prefix is `.` and cannot be changed. If you want to see commands that I can provide you with, do the `.help` command.\n\nHowever, if you want to do my commands in DMs, please do `?` in front of all of my commands (example: **?**.help), and on my DMs you can perform my commands normally.'

    # Tags Commands Below

    if p_message == '.tags':
        return "## Available Tags\nUse tags by doing `.tag [AVAILABLE_TAGS]`. All tags must be created **MANUALLY**, no fancy UI or anything. So if you want your own tag, reach out @ProbablyCort for one!\n```test, cort```"
    
    if p_message == '.tag test':
        return "The tag command is working properly! arrrrrrrrrrrrrrrrrrrggggggggghhhhhhhhhh 🧱🧱🧱🧱🧱🧱🧱"
    
    if p_message == '.tag cort':
        return "the cort siri googl man!!1!1"

    # Advanced Commands Below

    if message == '.ping':
        if not client.latency or client.latency != client.latency:
            return "Aw, missed it. (Latency infomation not available, please try again later.)"
        else:
            latency = round(client.latency, 1)
            return "🏓 Pong! **`{latency}ms`**"
    
    if p_message == '.uptime':
        uptime = round(time.time() - psutil.boot_time())
        return(f'This PC bot host has been up for {uptime // 3600} hours, {(uptime % 3600) // 60} minutes and counting.')

    if p_message == '.status':
        percent, charging = get_battery_info()

        if charging:
            status = "charging"
        else:
            status = "not charging"
        
        uptime = round(time.time() - psutil.boot_time())
        return(f'```System Uptime: {uptime // 3600} hours, {(uptime % 3600) // 60} minutes (and counting...)``````Battery Percentage: {percent}%, currently {status}.```')

    if p_message == '.battery':
        percent, charging = get_battery_info()

        if charging:
            status = "charging"
        else:
            status = "not charging"

        return(f'The battery percentage of this bot\'s host PC is currently at **`{percent}%`**, and it is currently **`{status}`**. ***Please let us know if it\'s full while charging or low on battery. Thanks.***')
    
    if p_message == '.winfetch':

        percent, charging = get_battery_info()

        if charging:
            status = "charging"
        else:
            status = "not charging"

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
        return(f'```Operating System: {os_info}\nDevice Host Name: {os_info.node}\nKernel: {kernel_info}\nUptime: {uptime // 3600} hours, {(uptime % 3600) // 60} minutes\nCPU: {cpu_info}\nGPU: {gpu_info}\nMemory: Available {memory_info.available / (1024 ** 3):.2f} GB / Total {memory_info.total / (1024 ** 3):.2f} GB\nBattery: At {percent}% / Currently {status}```')
    


    if p_message.startswith('.echo'):
        message_content = p_message[6:].strip()
        return message_content
    else:
        return None


def get_system_uptime():
    uptime_seconds = psutil.boot_time()
    uptime = str(timedelta(seconds=uptime_seconds))
    return uptime


def get_battery_status():
    battery = psutil.sensors_battery()
    if battery is not None:
        percent = battery.percent
        charging = battery.power_plugged
        return percent, charging
    else:
        return None
