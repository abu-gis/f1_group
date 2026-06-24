import asyncio

from app.db.init_db import init_db
from app.db.repositories import ArticleRepository
from app.db.session import AsyncSessionLocal
from app.services.pipeline_service import PipelineService


# Единая точка входа:
# 1. собираем новые статьи
# 2. полностью вырабатываем AI-очередь
# 3. полностью вырабатываем Telegram-очередь
async def main() -> None:
    await init_db()

    async with AsyncSessionLocal() as session:
        repository = ArticleRepository(session)
        pipeline = PipelineService(repository)

        print("STEP 1: Collecting new articles...")
        collect_result = await pipeline.collect_new_articles()
        print(collect_result)
        print()

        print("STEP 2: Processing AI queue...")
        total_ai_processed = 0
        total_ai_failed = 0

        while True:
            ai_result = await pipeline.process_ai_batch(limit=10)
            print(ai_result)

            total_ai_processed += ai_result["processed"]
            total_ai_failed += ai_result["failed"]

            if ai_result["pending_found"] == 0:
                break

            if ai_result["processed"] == 0 and ai_result["failed"] == 0:
                break

        print("AI queue finished.")
        print("Total AI processed:", total_ai_processed)
        print("Total AI failed:", total_ai_failed)
        print()

        print("STEP 3: Sending Telegram queue...")
        total_tg_sent = 0
        total_tg_skipped = 0
        total_tg_failed = 0

        while True:
            telegram_result = await pipeline.send_telegram_batch(limit=10)
            print(telegram_result)

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

        print("Telegram queue finished.")
        print("Total Telegram sent:", total_tg_sent)
        print("Total Telegram skipped:", total_tg_skipped)
        print("Total Telegram failed:", total_tg_failed)
        print()

        print("Pipeline run finished.")


if __name__ == "__main__":
    asyncio.run(main())