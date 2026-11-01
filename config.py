import re

# ---------Bot prefix-----------
PREFIX = "."
VERSION = "4.0a"

# ---------Statuses-----------

NORMAL_STATUSES = (
    "bit.ly/CSGDiscordBot",
    f"v{VERSION} | .help",
    "...",  # Triggers the lyric sequence
)

LYRICS = (
    '"Between the verdant touch of green"',
    '"The dappled sunlight casts a crown on me"',
    '"And though I trip and fall"',
    '"I\'ll face the all and breathe it into me"',
    '"Daydream"',
    '"I\'ll weave it in a wreath"',
    "The clouds, the sky and every sprout and seed",
    '"In colors of acrylic"',
    '"To mix them on my palette"',
    '"The gallery of life yet lived is-"',
)

SONG_INFO = {
    "title": "Clover",
    "artist": "FLAVOR FOLEY",
    "album": "MIRROR MODULATION",
    "release_year": "2026",
    "youtube_url": "https://www.youtube.com/watch?v=cY0qV7q9IC4",
} # Fill out the song info for the current lyrics statuses

# Change the status delay (in seconds)
NORMAL_DELAY = 60
LYRIC_DELAY = 5

# ---------Commands without prefixes-----------

STICKER_TRIGGERS = {
    # "your command": STICKER_ID
    "girlcockx": 1384139430067175495
}

TRACKER_WARNINGS = {
    "?si=": {
        "title": "⚠️ Your YouTube/Spotify link contains a tracking parameter! (`?si=`)",
        "description": "Please edit your message and remove everything starting from `?` onwards.",
        "color": 0xFEE75C 
    },
    "?a=": {
        "title": "⚠️ Your Twitter link contains a tracking parameter! (`?a=`)",
        "description": "Please edit your message and remove everything starting from `?` onwards.",
        "color": 0xFEE75C
    }
}

BATTERY_PATTERN = re.compile(
    r"(?i)The battery is (fu(l|1|i|\||!)*|cort|empty|drained|low|gone)(\.)?"
)

def check_battery_trigger(content: str) -> str | None:
    if BATTERY_PATTERN.search(content):
        return "SHUT THE FUCK UP"
    return None

def get_match_response(content: str, user_mention: str) -> str | None:
    # if "some word" in content:
        # return "bot response"
    # if content.endswith("some word"):
        # return "bot response"
    if "ity" in content:
        return "is that a new verity variant"
    match content:
        # case "your command":
            # return "bot response"
        case "but it refused":
            return "https://i.redd.it/o1efjhddq2x21.jpg"
        case "!barn":
            return "https://tenor.com/view/barn-gif-19719443"
        case "probably cort":
            return "https://media.discordapp.net/attachments/763430451217432589/793847564045647872/unknown.png?width=130&height=177"
        case "cantaloupe":
            return "https://cdn.discordapp.com/attachments/1079702225774972958/1148636977265123500/lv_0_20230804133527.mp4"
        case "🧱":
            return "🧱"
        case ":bricks:":
            return "🧱"
        case "<:pomni:1164212247866912889><:pomni:1164212247866912889><:pomni:1164212247866912889>":
            return "https://tenor.com/view/pomni-digitalcircus-digital-circus-the-amazing-digital-circus-tadc-gif-87641691478271811"
        case "<:pomni:1164212247866912889> <:pomni:1164212247866912889> <:pomni:1164212247866912889>":
            return "https://tenor.com/view/pomni-digitalcircus-digital-circus-the-amazing-digital-circus-tadc-gif-87641691478271811"
        case mention if mention == user_mention:
            return f"""# Hello there!
My default prefix is `{PREFIX}` and cannot be changed. If you want to see commands that I can provide you with, do the `{PREFIX}help` command.
However, if you want to do my commands in DMs, do my commands on my DM!
-# v{VERSION} | https://bit.ly/CSGDiscordBot
"""
        case "testwithoutprefix":
            return "```Command without prefix is functional.```"
        case "ping":
            return "Pong"
        case _:
            return None

STATUSES = NORMAL_STATUSES + LYRICS