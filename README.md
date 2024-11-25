# CSGDiscordBotPrivate
 CSGDiscord Bot - Private

# Quick Setup

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