# This example requires the 'message_content' privileged intent to function, however your own bot might not.

# This example covers advanced startup options and uses some real world examples for why you may need them.

import asyncio
import logging
import logging.handlers
import os

from typing import List, Optional

import discord
from discord.ext import commands
from aiohttp import ClientSession
from dotenv import load_dotenv

from bot import CSGDiscordBot

async def main():
    load_dotenv()

    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename='discord.log',
        encoding='utf-8',
        maxBytes=32 * 1024 * 1024,
        backupCount=5,
    )
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    discord.utils.setup_logging(formatter=formatter)

    async with ClientSession() as client:
        extensions = ['owner', 'fun', 'default']
        statuses = (
            'bit.ly/CSGDiscordBot',
            'v3.0 | .help',
            'HAPPY NEW YEAR 2025!',
            'my new year resolution will be 1600x720',
            'fart',
            'water.',
            'balls',
            'I KNOW THE BATTERY IS FULL, JUST SHUT THE FUCK UP.',
            '[stupid ass status here]',
            'do NOT abuse me. please.',
            'please give me some song suggestions. i need',
            'nothing. i\'m bored',
            'who is asyncio and why is it sleeping for 60 sec',
            'Find Luigi',
            '\"You know what else is massive?\"',
            'mmgh...',
            'UNDERTALE',
            'DELTARUNE',
            'Bloons TD 6',
            'Slime Rancher',
            'Grand Theft Auto VI',
            'Roblox',
            'GitHub Desktop',
            'Visual Studio Code',
            'The Metaverse Experience',
            'Powering Imagination City',
            'spook (will never be updated until 2077)',
            'cort\'s snowing tps game (prev. known as FPS Game)',
            'ami, i know. the battery is full. i get it.',
            'too much statuses.. send .help',
        )

        debug_mode=os.getenv("DEBUG_MODE") == '1'

        intents = discord.Intents.default()
        intents.message_content = True

        async with CSGDiscordBot(
            intents=intents,
            statuses=statuses,
            extensions=extensions,
            testing_guild=os.getenv("TEST_GUILD"),
            debug_mode=debug_mode
        ) as bot:
            await bot.start(os.getenv("CSGDISCORDBOT_TOKEN"))

asyncio.run(main())