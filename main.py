import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot_admin import build_admin_application
from app.config import settings
from app.db.init_db import init_db
from app.logger import setup_logger
from app.pipeline_runner import run_pipeline_once

logger = setup_logger()


async def scheduled_pipeline_job() -> None:
    try:
        await run_pipeline_once()
    except Exception as error:
        logger.exception("Scheduled pipeline job failed: %s", error)


async def start_admin_bot() -> None:
    application = build_admin_application()

    await application.initialize()
    await application.start()

    if application.updater is None:
        raise RuntimeError("Telegram updater is not available.")

    logger.info("Starting admin bot polling...")
    await application.updater.start_polling()

    try:
        await asyncio.Event().wait()
    finally:
        logger.info("Stopping admin bot polling...")

        if application.updater is not None:
            await application.updater.stop()

        await application.stop()
        await application.shutdown()


async def main() -> None:
    await init_db()

    await run_pipeline_once()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_pipeline_job,
        trigger="interval",
        minutes=settings.pipeline_run_interval_minutes,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    logger.info(
        "Scheduler started. Pipeline will run every %s minutes.",
        settings.pipeline_run_interval_minutes,
    )

    try:
        await start_admin_bot()
    except Exception as error:
        logger.exception("Admin bot failed to start: %s", error)
        logger.info("Pipeline scheduler will continue running without admin bot.")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())