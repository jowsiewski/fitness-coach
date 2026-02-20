import asyncio
import logging

import uvicorn

from src.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Entry point: starts FastAPI server, Discord bot, and scheduler concurrently."""
    asyncio.run(_run())


async def _run() -> None:
    from src.api.app import create_app
    from src.bot.bot import create_bot
    from src.models.database import init_db
    from src.scheduler.jobs import start_scheduler

    logger.info("Initializing database...")
    await init_db()

    app = create_app()
    bot = create_bot()
    scheduler = start_scheduler()

    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)

    tasks = [asyncio.create_task(server.serve())]

    if settings.discord_bot_token:
        tasks.append(asyncio.create_task(bot.start(settings.discord_bot_token)))
        logger.info("Discord bot starting...")
    else:
        logger.warning("DISCORD_BOT_TOKEN not set — bot disabled")

    logger.info("Fitness Coach started on %s:%s", settings.api_host, settings.api_port)

    try:
        await asyncio.gather(*tasks)
    finally:
        scheduler.shutdown(wait=False)
        if settings.discord_bot_token and not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    main()
