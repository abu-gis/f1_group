from app.db.repositories import ArticleRepository
from app.db.session import AsyncSessionLocal
from app.logger import setup_logger
from app.services.pipeline_service import PipelineService

logger = setup_logger()

is_pipeline_running = False


# Один полный прогон пайплайна:
# 1. собираем статьи
# 2. вырабатываем AI-очередь
# 3. вырабатываем Telegram-очередь
async def run_pipeline_once() -> None:
    global is_pipeline_running

    if is_pipeline_running:
        logger.warning("Pipeline is already running. Skipping this start.")
        return

    is_pipeline_running = True

    try:
        async with AsyncSessionLocal() as session:
            repository = ArticleRepository(session)
            pipeline = PipelineService(repository)

            logger.info("STEP 1: Collecting new articles...")
            collect_result = await pipeline.collect_new_articles()
            logger.info("Collect result: %s", collect_result)

            logger.info("STEP 2: Processing AI queue...")
            total_ai_processed = 0
            total_ai_failed = 0

            while True:
                ai_result = await pipeline.process_ai_batch(limit=10)
                logger.info("AI batch result: %s", ai_result)

                total_ai_processed += ai_result["processed"]
                total_ai_failed += ai_result["failed"]

                if ai_result["pending_found"] == 0:
                    break

                if ai_result["processed"] == 0 and ai_result["failed"] == 0:
                    break

            logger.info("AI queue finished.")
            logger.info("Total AI processed: %s", total_ai_processed)
            logger.info("Total AI failed: %s", total_ai_failed)

            logger.info("STEP 3: Sending Telegram queue...")
            total_tg_sent = 0
            total_tg_skipped = 0
            total_tg_failed = 0

            while True:
                telegram_result = await pipeline.send_telegram_batch(limit=10)
                logger.info("Telegram batch result: %s", telegram_result)

                total_tg_sent += telegram_result["sent"]
                total_tg_skipped += telegram_result.get("skipped", 0)
                total_tg_failed += telegram_result["failed"]

                if telegram_result["pending_found"] == 0:
                    break

                if (
                    telegram_result["sent"] == 0
                    and telegram_result.get("skipped", 0) == 0
                    and telegram_result["failed"] == 0
                ):
                    break

            logger.info("Telegram queue finished.")
            logger.info("Total Telegram sent: %s", total_tg_sent)
            logger.info("Total Telegram skipped: %s", total_tg_skipped)
            logger.info("Total Telegram failed: %s", total_tg_failed)

            logger.info("Pipeline run finished.")

    except Exception as error:
        logger.exception("Pipeline run crashed: %s", error)

    finally:
        is_pipeline_running = False