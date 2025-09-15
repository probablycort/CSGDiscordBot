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

    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename="discord.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,
        backupCount=5,
    )
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    discord.utils.setup_logging(formatter=formatter)

    async with ClientSession():
        extensions = ["owner", "fun", "default"]
        statuses = (
            "bit.ly/CSGDiscordBot",
            "v3.0 | .help",
            "I KNOW THE BATTERY IS FULL, JUST SHUT THE FUCK UP.",
            "[stupid ass status here]",
            "do NOT abuse me. please.",
            "nothing. i'm bored",
            "OneShot",
            "OneShot: World Machine Edition",
            "UNDERTALE",
            "DELTARUNE",
            "Roblox",
            "GitHub Desktop",
            "Visual Studio Code",
            "The Metaverse Experience",
            "Powering Imagination City",
            "ami, i know. the battery is full. i get it.",
            "MiSide",
            "with Cappie",
            "Umamusume: Pretty Derby",
            "Calculator",
            "on a Nintendo Switch 3",
            "Doki Doki Literature Club!",
            "Doki Doki Literature Club! Plus",
            "...",
            "When the metronome is clicking",
            "MIDI clock is ticking",
            "I can feel it in the rhythm"
            "Loving undefinable",
            "A simple human being",
            "Far beyond the meaning",
            "Can you show me how to be?",
            "..."
            "The Ruminations of Adachi Rei",
            "Machine Love",
            "ouuughhh my boaner... Jamie Paige... I love you...",
            "(NOT) an amazing quote (also NOT) by cort himself",
            "Medicine",
            "Mesmerizer",
            "Be Ameteur!",
            "Hymn to the Decadent Life",
            "kyu-kurarin",
            "Radiant Revival",
            "Overlap TOMATO CAN",
            "Shiny Chariot",
            "Manifesto",
            "Clouddrop",
            "WHATCHACALLITSNAME",
            "LOVELY?CAVITY",
            "People Posture Play Pretend",
            "Constant Companions",
            "Constant Companions (Deluxe Edition)",
            "My Darling, My Companion",
            "Dance Delightful",
            "Manifesto",
            "Autumn Every Day",
            "weathergirl",
            "Static",
            "Spoken For",
            "NEWLY HUMAN FEELING",
            "Butcher Vanity",
            "BIRDBRAIN",
            "Blusher",
            "Get Your Wish",
            "Shelter",
            "Everything Goes On",
            "KLY",
            "My bread was Burnt to a Crisp...",
            "Liar Dancer",
            "Heat Abnormal",
            "I Wish That I Could Fall",
            "Let's head to Tougenkyou",
            "Niko and the World Machine",
            "...",
            "Can you feel my heart is beating?,
            "Hear me simply breathing?",
            "It's this strangely human feeling",
            "Oh, I wanna know if you would",
            "Catch me when I'm falling",
            "Hear me when I'm calling",
            "It's this newly human feeling",
            "Oh, I wanna share it with you!",
            "...",
            "Vanishing into our Final Stop",
            "too much statuses.. send .help",
        )

        debug_mode = os.getenv("DEBUG_MODE") == "1"

        intents = discord.Intents.default()
        intents.message_content = True

        async with CSGDiscordBot(
            intents=intents,
            statuses=statuses,
            extensions=extensions,
            testing_guild=os.getenv("TEST_GUILD"),
            debug_mode=debug_mode,
        ) as bot:
            await bot.start(os.getenv("CSGDISCORDBOT_TOKEN"))


if __name__ == "__main__":
    asyncio.run(main())
