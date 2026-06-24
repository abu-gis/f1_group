import asyncio

from app.db.init_db import init_db
from app.db.repositories import ArticleRepository
from app.db.session import AsyncSessionLocal
from app.services.ai_service import AIService


# На этом шаге мы не мониторим сайт,
# а проверяем первый проход AI-обработки статьи из БД.
async def main() -> None:
    await init_db()

    ai_service = AIService()

    async with AsyncSessionLocal() as session:
        repository = ArticleRepository(session)

        # Берем первую статью, которая еще не обработана ИИ.
        article = await repository.get_first_pending_ai_article()

        if article is None:
            print("No pending AI articles found.")
            return

        print("Processing article:")
        print("id:", article.id)
        print("slug:", article.slug)
        print("title:", article.title)
        print()

        try:
            ai_result = ai_service.process_article(article)

            updated_article = await repository.update_ai_result(
                article=article,
                title_ru=ai_result["title_ru"],
                summary_ru=ai_result["summary_ru"],
                telegram_text=ai_result["telegram_text"],
            )

            print("AI processing completed successfully.")
            print("title_ru:", updated_article.title_ru)
            print("summary_ru:", updated_article.summary_ru)
            print("telegram_text:", updated_article.telegram_text)
            print("ai_status:", updated_article.ai_status)
            print("ai_processed_at:", updated_article.ai_processed_at)

        except Exception as error:
            await repository.mark_ai_failed(article)
            print("AI processing failed:", error)


if __name__ == "__main__":
    asyncio.run(main())