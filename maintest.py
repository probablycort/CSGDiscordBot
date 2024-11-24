import discord, time, asyncio, psutil, wmi, platform, random, sys, os # type: ignore
from discord.ext import commands, tasks # type: ignore
from colorama import Back, Fore, Style # type: ignore
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix=".", help_command=None, intents=discord.Intents.all())

def restart_bot(): 
    os.execv(sys.executable, ['python'] + sys.argv)

def get_battery_info():
    battery = psutil.sensors_battery()
    percent = battery.percent
    charging = battery.power_plugged

    return percent, charging


@client.event
async def on_ready():
    prfx = (Back.BLACK + Fore.GREEN + time.strftime("%H:%M:%H UTC+8", time.localtime()) + Back.RESET + Fore.WHITE + Style.BRIGHT)
    print(prfx + " Logged in as " + Fore.YELLOW + client.user.name)
    print(prfx + " Bot ID " + Fore.YELLOW + str(client.user.id))
    print(prfx + " Discord Version " + Fore.YELLOW + discord.__version__)
    synced = await client.tree.sync()
    print(prfx + " Slash commands has been synced! " + Fore.YELLOW + str(len(synced)) + " Commands")
    statuses.start()

@tasks.loop()
async def statuses():
    synced = await client.tree.sync()
    await client.change_presence(activity=discord.Game('synced ' + str(len(synced)) + ' slash commands'))
    await asyncio.sleep(30)
    await client.change_presence(activity=discord.Game('bit.ly/CSGDiscordBot'))
    await asyncio.sleep(30)
    await client.change_presence(activity=discord.Game('cogs enabled - not set up properly'))
    await asyncio.sleep(30)
    await client.change_presence(activity=discord.Game('EXPERIMENTAL v2.2 | BUGS MAY PRESENT'))
    await asyncio.sleep(600)
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=str(len(client.guilds)) + " servers. | .help"))
    await asyncio.sleep(10)

# ------------------------------------------------------------------------------------------------------------------------------------------

@client.event
async def on_message(message):
    # Prevent the bot from responding to its own messages

    if message.author == client.user:
        return
    # Check for a specific phrase and respond

    content = message.content.lower()

# Commands without prefix
    
    if content == 'probably cort':
        await message.channel.send('https://media.discordapp.net/attachments/763430451217432589/793847564045647872/unknown.png?width=130&height=177')
    elif content == 'cantaloupe':
        await message.channel.send("https://cdn.discordapp.com/attachments/1079702225774972958/1148636977265123500/lv_0_20230804133527.mp4")
    elif content == '🧱':
        await message.channel.send("🧱")
    elif content == ':bricks:':
        await message.channel.send("🧱")
    elif content == '<:pomni:1164212247866912889><:pomni:1164212247866912889><:pomni:1164212247866912889>':
        await message.channel.send("https://tenor.com/view/pomni-digitalcircus-digital-circus-the-amazing-digital-circus-tadc-gif-87641691478271811")
    elif content == '<:pomni:1164212247866912889> <:pomni:1164212247866912889> <:pomni:1164212247866912889>':
        await message.channel.send("https://tenor.com/view/pomni-digitalcircus-digital-circus-the-amazing-digital-circus-tadc-gif-87641691478271811")
    elif content == '<@1156595433397825728>':
        await message.channel.send("# Hello there!\nMy default prefix is `.` and cannot be changed. If you want to see commands that I can provide you with, do the `.help` command.\nHowever, if you want to do my commands in DMs, do my commands on my DM!\n-# v2.1 | https://bit.ly/CSGDiscordBot")
    elif content == 'testwithoutprefix':
        await message.channel.send("```Command without prefix is functional.```")
    elif content == 'ping':
        await message.channel.send("Pong")
    elif content == '!barn':
        await message.channel.send("https://tenor.com/view/barn-gif-19719443")

    # Ensure that other commands with prefix still work
    await client.process_commands(message)

#Commands with prefix

@client.command()
async def shutdown(ctx):
    id = str(ctx.author.id)
    if id == '496263009958756352':
        await ctx.send('## The bot is shutting down, please wait... <a:loading_2:1309560598048014387>\n-# The bot MUST be ran again from the host PC after it shutdown. To check if it is has been shut down, wait until the bot\'s status is offline.')
        await asyncio.sleep(1)
        await client.close()
    else:
        await ctx.send("## Womp womp.\nYou don't have the sufficient permissions to perform this action!\n-# Please, do not abuse this command. Oh wait, you're unable to run it anyway.")

@client.command()
async def rulestxt(ctx):
    id = str(ctx.author.id)
    if id == '496263009958756352':
        embed = discord.Embed(title="DISCORD SERVER RULES",
                            description="**Welcome to CortSiriGoogle Studios!** While you're here, we'll ask you to follow the following rules:",
                            colour=0x9357b3)
        embed.set_author(name="CortSiriGoogle Studios",
                        icon_url="https://cdn.discordapp.com/emojis/1284567633022156845.webp")
        embed.add_field(name="Treat everyone with respect.",
                        value="- Absolutely no harassment, witch-hunting, racism, or hate speech.",
                        inline=False)
        embed.add_field(name="Swearing is allowed. However...",
                        value="- If it is a slur, used sexually, or towards hate, it's not allowed.\n - If AutoMod *somehow* got your message moderated but it does not break the rules, let us know!",
                        inline=False)
        embed.add_field(name="No spamming or self-promotion.",
                        value="- This includes messaging our members.",
                        inline=False)
        embed.add_field(name="Be friendly to others.",
                        value="- Even though we allow swearing, just be friendly to each other.\n- Seriously, do not harass anyone, please.",
                        inline=False)
        embed.add_field(name="Absolutely NO NSFW or GORE CONTENT.",
                        value="- This includes text, images, and links featuring nudity, sex, hard violence, or other graphically disturbing content.",
                        inline=False)
        embed.add_field(name="Underage members are NOT allowed.",
                        value="- Even though we sound like a server for all ages, we are not allowing underage members that is under the age of 13.\n - Any underage members that is under the age of 13 will be banned and will be reported immediately to Discord.",
                        inline=False)
        embed.add_field(name="Follow Discord's Terms of Service.",
                        value="- We highly recommend you to follow Discord's Terms of Service.",
                        inline=False)
        embed.add_field(name="And please, USE COMMON SENSE.",
                        value="- Don't even try to share your ACTUAL information and identity **anywhere** on this platform.\n - And please, keep yourself safe online.",
                        inline=False)
        embed.add_field(name="WARNING:",
                        value="-# **Please be warned that if you're not following the rules, it can result you of getting warned, muted, kicked, or banned.**",
                        inline=False)
        embed.add_field(name=":white_check_mark: We encourage you to invite anyone!",
                        value="Go ahead, invite your friend who knows all about Roblox Studio, a tech enthusiast that always uses Linux and never Windows, a Visual Studio Code user that works on their project 24/7, or **literally anyone**! Invite them at discord.gg/Nm6fWfjcyh",
                        inline=True)
        embed.add_field(name=":warning: You may need to mute some channels from this server.",
                        value="This is because of the default notification setting is set to all messages. This setting may will be changed in the future.",
                        inline=True)
        embed.add_field(name="Other Information",
                        value="-# :art: CortSiriGoogle Studios server roles are using [Catppuccin](https://catppuccin.com/) color palettes! Check out #roles for more information about it.\n-# :link: Check out our [website](https://bit.ly/CortSiriGoogle) to learn more about us, links to our socials, and more.\n-# :grey_question: Need help/report something? Ping @Moderator or any higher ranked members.\n-# :rolling_eyes: No, the :dognerd: emoji does not affect you if you reacted to it or not.",
                        inline=False)

        await ctx.send(embed=embed)

    else:
        await ctx.send("## Womp womp.\nYou don't have the sufficient permissions to perform this action!\n-# This command is only accessible by the owner of this bot.")

@client.command()
async def restart(ctx):
    id = str(ctx.author.id)
    if id == '496263009958756352':
        await ctx.send('## The bot is restarting. <a:loading_2:1309560598048014387>\n-# Check the bot\'s status to confirm that it has restarted! The bot\'s status starts off with `bit.ly/CSGDiscordBot`.')
        restart_bot()
    else:
        await ctx.send("## Womp womp.\nYou don't have the sufficient permissions to perform this action!\n-# Please, do not abuse this command. Oh wait, you're unable to run it anyway.")

@client.command()
async def hello(ctx):
    await ctx.send("hello world!")

@client.command()
async def embed(ctx):
    embed=discord.Embed(title="CortSiriGoogle Help", description="Get to see the list of CortSiriGoogle's commands.\n-# *Currently not available\n-# **May have issues or doesn't function properly\n-# ***Only available to some servers", color=0x1e66f5)
    embed.add_field(name="Slash Commands", value="```/help (shows this command), /ping, /uptime, /status, /battery, /winfetch```", inline=True)
    embed.add_field(name="Default Commands", value="```.help (shows this command), **.guess, .choose, .roll,, .echo, *.tags, .ping```", inline=True)
    embed.add_field(name="System (PC Host) Commands", value="```.battery, .uptime, .status, .winfetch```", inline=True)
    embed.add_field(name="Media Commands", value="-# Media commands doesn't use the bot's prefix. Instead, it directly responses to the user's message without needing to use a prefix.\n```cantaloupe, probably cort, nerd, brick, 🧱, !barn, **:pomni::pomni::pomni:, testwithoutprefix```", inline=True)
    embed.add_field(name="Test Commands", value="-# For debugging purposes\n```testwithoutprefix, .test, /test```", inline=True)
    embed.set_footer(text="[INFO] The commands with the battery info may not be available depending on the bot's PC host.")
    await ctx.send(embed=embed)

@client.command(aliases=['dice'])
async def roll(ctx, max:int=6):
    number = random.randint(1,max)
    await ctx.send(f"You have rolled a **{number}**.")

@client.command(aliases=['guessinggame', 'startgame'])
async def guess(ctx, max:int=100):
    MAX_GUESSES = 15
    number = random.randint(1,max)
    await ctx.send(f"## Guessing game has been started!\nPlease guess a number between **1-{max}.**\nYou have **{MAX_GUESSES}** guesses.\n-# This command is currently marked as [**], which is [May have issues or doesn't function properly]. We encourage you to NOT WIN the game as even after winning the game, you will be spammed and notified with the 'Please send a number.' message. *I would* like to fix the code but I'm just a rookie at Python coding and just too lazy. -Cort")
    def check(m):
        return m.author == ctx.author and m.channel == ctx.message.channel
    for i in range(MAX_GUESSES):
        guess = await client.wait_for('message', check=check)
        try:
            int(guess.content)
            if guess.content == str(number):
                await ctx.send(f"Congrats, you guessed it correctly! It took you **{i+1}** tries.")
            elif guess.content >= str(number):
                await ctx.send(f"Lower!")
            elif guess.content <= str(number):
                await ctx.send(f"Higher!")
        except:
            await ctx.send("Please send a number.\n-# If you've already won the game and this message still being posted, please immediately let us know to restart the bot.")
    else:
        await ctx.send(f"Game over! You have ran out of tries.\n-# Remember, you only get **{MAX_GUESSES}** guesses!")


@client.command(aliases=['choice'])
async def choose(ctx, *, args):
    arguements = args.split(" ")
    choice = random.choice(arguements)
    thinking = await ctx.send(":clock1: Thinking, please wait...")
    await asyncio.sleep(0.2)
    for i in range(4):
        await thinking.edit(content=f":clock{i+1}: Thinking, please wait...")
        await asyncio.sleep(0.2)
    await ctx.send(choice)

@client.command()
async def test(ctx):
    await ctx.send("```Command with prefix is functional.```")

@client.command()
async def ping(ctx):
    await ctx.send('🏓 Pong! `{0}ms`'.format(round(client.latency * 1000)))

@client.command()
async def pign(ctx):
    await ctx.send('pogn!!1 {0}ms🏓🏓'.format(round(client.latency * 10000)))

@client.command()
async def uptime(ctx):
    uptime = round(time.time() - psutil.boot_time())
    embed=discord.Embed(title="CortSiriGoogle PC Host Uptime", description=f'This PC bot host has been up for `{uptime // 3600} hours, {(uptime % 3600) // 60} minutes` (and counting.)', color=discord.Color.dark_blue())
    await ctx.send(embed=embed)

@client.command()
async def status(ctx):
    percent, charging = get_battery_info()

    if charging:
        status = "charging"
    else:
        status = "not charging"

    uptime = round(time.time() - psutil.boot_time())
    embed=discord.Embed(title="CortSiriGoogle PC Host Status", description="Shows the battery status and uptime status.", color=0x66abc6)
    embed.add_field(name="System Uptime", value=f"{uptime // 3600} hours, {(uptime % 3600) // 60} minutes (and counting.)", inline=True)
    embed.add_field(name="Battery", value=f"{percent}%, currently {status}.", inline=True)
    await ctx.send(embed=embed)

@client.command()
async def battery(ctx):
    percent, charging = get_battery_info()

    if charging:
        status = "charging"
    else:
        status = "not charging"
    
    embed=discord.Embed(title="CortSiriGoogle PC Host Battery Status", description=f"The battery percentage of this bot\'s host PC is currently at **`{percent}%`**, and it is currently **`{status}`**.", color=0x40a02b)
    embed.set_footer(text="Yes, if the battery is full, we know. Just shut up.")
    await ctx.send(embed=embed)

@client.command()
async def winfetch(ctx):
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
    await ctx.send(embed=embed)

@client.command()
async def echo(ctx, *args):
    await ctx.send(" ".join(args))

@client.command()
async def embedecho(ctx, *args):
    embed=discord.Embed(description=" ".join(args), color=0x1e66f5)
    await ctx.send(embed=embed)

@client.command()
async def help(ctx):
    embed=discord.Embed(title="CortSiriGoogle Help", description="Get to see the list of CortSiriGoogle's commands.\n-# *Currently not available\n-# **May have issues or doesn't function properly\n-# ***Only available to some servers", color=0x1e66f5)
    embed.add_field(name="Slash Commands", value="```/help (shows this command), /test, /ping, /uptime, /status, /battery, /winfetch, /restart, /shutdown```", inline=True)
    embed.add_field(name="Default Commands", value="```.help (shows this command), **.guess, .choose, .roll, .test, .echo, *.tags, .ping, .restart, .shutdown```", inline=True)
    embed.add_field(name="System (PC Host) Commands", value="```.battery, .uptime, .status, .winfetch```", inline=False)
    embed.add_field(name="Media Commands", value="-# Media commands doesn't use the bot's prefix. Instead, it directly responses to the user's message without needing to use a prefix.\n```cantaloupe, probably cort, nerd, brick, 🧱, !barn, **:pomni::pomni::pomni:, testwithoutprefix```", inline=True)
    embed.set_footer(text="[INFO] The commands with the battery info may not be available depending on the bot's PC host.")
    await ctx.send(embed=embed)

# Slash Commands --------------------------------------------------------------------------
    
@client.tree.command(name="shutdown", description="Completely shuts down the bot. Only \"the superusers\" could do this command...")
async def slashshutdown(Interaction: discord.Interaction):
    id = str(Interaction.user.id)
    if id == '496263009958756352':
        await Interaction.response.send_message('## The bot is shutting down, please wait... <a:loading_2:1309560598048014387>\n-# The bot MUST be ran again from the host PC after it shutdown. To check if it is has been shut down, wait until the bot\'s status is offline.')
        await asyncio.sleep(1)
        await Interaction.client.close()
    else:
        await Interaction.response.send_message("## Womp womp.\nYou don't have the sufficient permissions to perform this action!\n-# Please, do not abuse this command. Oh wait, you're unable to run it anyway.", ephemeral=True)

@client.tree.command(name="restart", description="Completely restarts the bot. Only \"the superusers\" could do this command...")
async def slashrestart(Interaction: discord.Interaction):
    id = str(Interaction.user.id)
    if id == '496263009958756352':
        await Interaction.response.send_message('## The bot is restarting. <a:loading_2:1309560598048014387>\n-# Check the bot\'s status to confirm that it has restarted! The bot\'s status starts off with `bit.ly/CSGDiscordBot`.')
        await asyncio.sleep(1)
        restart_bot()
    else:
        await Interaction.response.send_message("## Womp womp.\nYou don't have the sufficient permissions to perform this action!\n-# Please, do not abuse this command. Oh wait, you're unable to run it anyway.", ephemeral=True)

@client.tree.command(name="help", description="Shows the list of commands of this bot.")
async def slashhelp(Interaction: discord.Interaction):
    embed=discord.Embed(title="CortSiriGoogle Help", description="Get to see the list of CortSiriGoogle's commands.\n-# *Currently not available\n-# **May have issues or doesn't function properly\n-# ***Only available to some servers", color=0x1e66f5)
    embed.add_field(name="Slash Commands", value="```/help (shows this command), /ping, /uptime, /status, /battery, /winfetch, /restart, /shutdown```", inline=True)
    embed.add_field(name="Default Commands", value="```.help (shows this command), **.guess, .choose, .roll, .echo, *.tags, .ping, .restart, .shutdown```", inline=True)
    embed.add_field(name="System (PC Host) Commands", value="```.battery, .uptime, .status, .winfetch```", inline=False)
    embed.add_field(name="Media Commands", value="-# Media commands doesn't use the bot's prefix. Instead, it directly responses to the user's message without needing to use a prefix.\n```cantaloupe, probably cort, nerd, brick, 🧱, !barn, **:pomni::pomni::pomni:```", inline=True)
    embed.add_field(name="Test Commands", value="-# For debugging purposes\n```testwithoutprefix, .test, /test```", inline=True)
    embed.set_footer(text="[INFO] The commands with the battery info may not be available depending on the bot's PC host.")
    await Interaction.response.send_message(embed=embed)

@client.tree.command(name="test", description="Test command.")
async def slashtest(Interaction: discord.Interaction):
    await Interaction.response.send_message(content="```Slash Command is functional.```")

@client.tree.command(name="ping", description="Shows the bot's latency.")
async def slashping(Interaction: discord.Interaction):
    await Interaction.response.send_message('🏓 Pong! `{0}ms`'.format(round(client.latency * 1000)))

@client.tree.command(name="uptime", description="Shows the bot's uptime.")
async def slashuptime(Interaction: discord.Interaction):
    uptime = round(time.time() - psutil.boot_time())
    embed=discord.Embed(title="CortSiriGoogle PC Host Uptime", description=f'This PC bot host has been up for `{uptime // 3600} hours, {(uptime % 3600) // 60} minutes` (and counting.)', color=discord.Color.dark_blue())
    await Interaction.response.send_message(embed=embed)

@client.tree.command(name="status", description="Shows the bot's current status (uptime and battery if available).")
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

@client.tree.command(name="battery", description="Shows the bot's battery (if available).")
async def slashbattery(Interaction: discord.Interaction):
    percent, charging = get_battery_info()

    if charging:
        status = "charging"
    else:
        status = "not charging"
    
    embed=discord.Embed(title="PC Host Battery Status", description=f"The battery percentage of this bot\'s host PC is currently at **`{percent}%`**, and it is currently **`{status}`**.", color=0x40a02b)
    embed.set_footer(text="Yes, if the battery is full, we know. Just shut up.")
    await Interaction.response.send_message(embed=embed)

@client.tree.command(name="winfetch", description="Neofetch, but on Windows. Shows the bot's client info.")
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

# ------------------------------------------------------------------------------------------------------------------------------------------

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')

load_dotenv()
TOKEN = os.getenv("CSGDISCORDBOT_TOKEN")
client.run(TOKEN)