import discord
from discord.ext import commands
import responses
import asyncio
import psutil
import os
from discord.ext import tasks

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix='!', intents=intents)

def get_battery_info():
    global percent
    battery = psutil.sensors_battery()
    percent = battery.percent
    charging = battery.power_plugged

    return percent, charging
        

def run_discord_bot():
    token = 'YOUR_TOKEN_HERE'
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    
    @client.event
    async def on_ready():
        check_battery_status.start()
        print(f'{client.user} is now running!')
    
    @tasks.loop()
    async def check_battery_status():
        battery_percentage = psutil.sensors_battery().percent

        if battery_percentage < 20:
            if status_task.is_running() + full_battery.is_running() + shut_down_task.is_running():
                status_task.stop()
                full_battery.stop()
                shut_down_task.stop()
            if not low_battery.is_running():
                print("Showing statuses low bat %")
                low_battery.start()
        elif battery_percentage == 100:
            if status_task.is_running() + low_battery.is_running() + shut_down_task.is_running():
                status_task.stop()
                low_battery.stop()
                shut_down_task.stop()
            if not full_battery.is_running():
                print("Showing statuses full bat %")
                full_battery.start()
        elif battery_percentage < 10:
            if status_task.is_running() + low_battery.is_running() + full_battery.is_running():
                status_task.stop()
                low_battery.stop()
                full_battery.stop()
            if not shut_down_task.is_running():
                print("Showing statuses of shutting down")
                shut_down_task.start()
        else:
            if low_battery.is_running() + full_battery.is_running() + shut_down_task.is_running():
                low_battery.stop()
                full_battery.stop()
                shut_down_task.stop()
            if not status_task.is_running():
                print("Showing statuses normally")
                status_task.start()

    @tasks.loop()
    async def status_task() -> None:
        await client.change_presence(activity=discord.Game('bit.ly/CSGDiscordBot'))
        await asyncio.sleep(15)
        await client.change_presence(activity=discord.Game('Do .help for commands!'))
        await asyncio.sleep(15)
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=str(len(client.guilds)) + " servers."))
        await asyncio.sleep(5)
        percent, charging = get_battery_info()

        if charging:
            status = "battery: Charging"
        else:
            status = "battery: Not charging"

        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=(str(status))))
        await asyncio.sleep(5)
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=(str((percent)) + '% of battery')))
        await asyncio.sleep(10)

    @tasks.loop()
    async def full_battery() -> None:
        await client.change_presence(activity=discord.Game('bit.ly/CSGDiscordBot'))
        await asyncio.sleep(15)
        await client.change_presence(activity=discord.Game('Do .help for commands!'))
        await asyncio.sleep(15)
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=str(len(client.guilds)) + " servers."))
        await asyncio.sleep(5)
        percent, charging = get_battery_info()
        if charging:
            status = "BATTERY'S FULL!"
        else:
            status = "battery: Not charging"
          
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=(str(status))))
        await asyncio.sleep(5)
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=(str((percent)) + '% of battery')))
        await asyncio.sleep(10)

    @tasks.loop()
    async def low_battery() -> None:
        await client.change_presence(activity=discord.Game('bit.ly/CSGDiscordBot'))
        await asyncio.sleep(15)
        await client.change_presence(activity=discord.Game('Do .help for commands!'))
        await asyncio.sleep(15)
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=str(len(client.guilds)) + " servers."))
        await asyncio.sleep(5)
        percent, charging = get_battery_info()
        if charging:
            status = "battery: Charging"
        else:
            status = "LOW BATTERY!"
 
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=(str(status))))
        await asyncio.sleep(15)
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=(str((percent)) + '% of battery')))
        await asyncio.sleep(10)

    @tasks.loop()
    async def shut_down_task() -> None:
        percent, charging = get_battery_info()

        if charging:
            status = "battery: Charging"
        else:
            status = "going down in a few min."

        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=(str(status))))
        await asyncio.sleep(20)
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=(str((percent)) + '% of battery')))
        await asyncio.sleep(20)

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        username = str(message.author)
        user_message = str(message.content)
        channel = str(message.channel)

        print(f'{username} said: "{user_message}" (channel{channel})')

        if user_message and user_message[0] == '?':
            try:
                user_message = user_message[1:]
                await send_message(message, user_message, is_private=True)
            except IndexError:
                print("Embed/file message cannot be responded, ignored")
        else:
            await send_message(message, user_message, is_private=False)


    new_func(token, client)

def new_func(token, client):
    client.run(token)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    response = responses.get_response(message.content)
    
    if response:
        bot.send_message(message.channel, response)

    if message.content.startswith('?'):
        user_message = message.content[1:]
        await send_message(message, user_message, is_private=True)
    else:
        await send_message(message, message.content, is_private=False)

    await bot.process_commands(message)

# Define any other bot-related functions or classes here

async def send_message(message, user_message, is_private):
    try:
        response = responses.get_response(user_message)
        await message.author.send(response) if is_private else await message.channel.send(response)

    except Exception as e:
        print(e)
