# CortSiriGoogle Discord Bot
CortDB, also known as CSGDiscordBot, is an experimental Python-based Discord bot created for the CortSiriGoogle Discord server as part of a [CortSiriGoogle Development](https://cortstudios.carrd.co/) side project. It features unique commands, custom statuses, and more. The default prefix is `.`. Type `.help` to view available commands.

> [!NOTE]
> CSGDiscordBot below v3.0 and statuses has been archived and can be found at https://github.com/probablycort/CSGArchivedDiscordBot.

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
You can now configure the prefix, statuses, and commands (without prefixes) of the bot in config.py!
