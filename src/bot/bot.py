import logging

import discord

from src.config import settings

logger = logging.getLogger(__name__)

COMMAND_EXTENSIONS = [
    "src.bot.commands.summary",
    "src.bot.commands.nutrition",
    "src.bot.commands.status",
]


def _get_guild_ids() -> list[int] | None:
    """Return guild IDs for instant slash command sync, or None for global."""
    if settings.discord_guild_id:
        return [int(settings.discord_guild_id)]
    return None


def create_bot() -> discord.Bot:
    """Create and configure the Discord bot with all command cogs."""
    intents = discord.Intents.default()

    guild_ids = _get_guild_ids()
    bot = discord.Bot(intents=intents, debug_guilds=guild_ids)  # type: ignore[no-untyped-call]

    @bot.event
    async def on_ready() -> None:
        logger.info("Bot connected as %s (ID: %s)", bot.user, bot.user.id if bot.user else "?")

    for extension in COMMAND_EXTENSIONS:
        try:
            bot.load_extension(extension)
            logger.info("Loaded extension: %s", extension)
        except Exception:
            logger.exception("Failed to load extension: %s", extension)

    return bot
