# CortSiriGoogle Discord Bot
CortSiriGoogle, also known as CSGDiscordBot, is an experimental Discord bot based on Python, specifically made for the CortSiriGoogle Studios Discord server. It is currently part of a side project made by [CortSiriGoogle Studios](https://cortstudios.carrd.co/). The bot has some unique commands, statuses and more. The default prefix of this bot is `.`, and do `.help` for commands.

Developed by [@probablycort](https://github.com/probablycort/) and rewritten by [@searinminecraft](https://github.com/searinminecraft/)

## Quick Setup
Make a virtual enviroment, then install the requirements at `requirements.txt`:

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Enter info in `.env`:

```
CSGDISCORDBOT_TOKEN="TOKEN_HERE"

# For debugging purposes, for slash commands for now
DEBUG_MODE=0
TEST_GUILD=123412432134312341234
```

Run bot:
```
python start.py
```

Then sync app commands globally for them to show up:
```
.sync global
```
## Configuring the bot
### Prefix
Configure the prefix of the bot at `bot.py`, on line 32.

### Statuses
Configure the bot's statuses by going to `start.py`, under line 40. 

### Commands
While commands (with prefix) and app commands are located under the `cogs` folder, the commands without prefix is located at `bot.py`, under line 162.

#### CSGDiscordBot before v3.0 has been archived. Go to https://github.com/probablycort/CSGArchivedDiscordBot.
