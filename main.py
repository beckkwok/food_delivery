from __future__ import annotations

import asyncio
import logging
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.bot import build_app
from config.settings import TELEGRAM_BOT_TOKEN
from scheduler.daily import send_daily_summary, ask_feedback_for_yesterday

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set. Create a .env file from .env.example")
        sys.exit(1)

    logger.info("Starting food delivery bot...")
    app = build_app()

    scheduler.add_job(
        send_daily_summary,
        trigger="cron",
        hour=10,
        minute=30,
        args=[app],
        id="daily_summary",
        replace_existing=True,
    )

    scheduler.add_job(
        ask_feedback_for_yesterday,
        trigger="cron",
        hour=20,
        minute=0,
        args=[app],
        id="feedback_request",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started — daily summary at 10:30, feedback requests at 20:00")

    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received...")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    try:
        await app.initialize()
        await app.start()
        logger.info("Bot started polling...")
        await app.updater.start_polling()

        await shutdown_event.wait()

    finally:
        logger.info("Shutting down...")
        scheduler.shutdown(wait=False)
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
