import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot_admin import build_admin_application
from app.config import settings
from app.db.init_db import init_db
from app.logger import setup_logger
from app.pipeline_runner import run_pipeline_once
from telegram import Update
import httpx

logger = setup_logger()


async def scheduled_pipeline_job() -> None:
    try:
        await run_pipeline_once()
    except Exception as error:
        logger.exception("Scheduled pipeline job failed: %s", error)


async def start_admin_bot():
    application = build_admin_application()

    await application.initialize()
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.start()

    logger.info("Starting admin bot polling...")

    try:
        await poll_admin_updates(application)
    finally:
        logger.info("Stopping admin bot polling...")
        await application.stop()
        await application.shutdown()


async def poll_admin_updates(application) -> None:
    token = settings.telegram_bot_token
    proxy = settings.telegram_proxy_url.strip() or None
    offset = None

    async with httpx.AsyncClient(proxy=proxy, timeout=60) as client:
        while True:
            params = {
                "timeout": 30,
                "allowed_updates": '["message","callback_query","my_chat_member"]',
            }

            if offset is not None:
                params["offset"] = offset

            response = await client.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params=params,
            )
            response.raise_for_status()

            payload = response.json()
            updates = payload.get("result", [])

            for raw_update in updates:
                update = Update.de_json(raw_update, application.bot)
                offset = update.update_id + 1
                await application.process_update(update)

            await asyncio.sleep(1))


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