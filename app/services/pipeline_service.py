import asyncio

from app.collectors.f1cosmos import F1CosmosCollector
from app.config import settings
from app.db.repositories import ArticleRepository
from app.parsers.f1cosmos import (
    deduplicate_news_list,
    parse_news_detail,
    parse_news_list,
)
from app.services.ai_service import AIService
from app.services.telegram_service import TelegramService
from app.utils.text import normalize_title


# Пайплайн-сервис объединяет все этапы:
# 1. сбор новых новостей
# 2. AI-обработка
# 3. отправка в Telegram
class PipelineService:
    def __init__(self, repository: ArticleRepository) -> None:
        self.repository = repository
        self.collector = F1CosmosCollector()
        self.ai_service = AIService()
        self.telegram_service = TelegramService()

    # Скачивает список новостей, убирает дубли и сохраняет только новые статьи.
    async def collect_new_articles(self) -> dict[str, int]:
        list_html = await self.collector.fetch_news_list_html()
        parsed_items = parse_news_list(list_html)
        items = deduplicate_news_list(parsed_items)

        from app.utils.text import normalize_title

        new_articles_count = 0
        existing_articles_count = 0
        failed_articles_count = 0

        # Храним нормализованные title, уже встреченные в текущем запуске.
        seen_titles_in_run: set[str] = set()

        for item in items:
            normalized_title = normalize_title(item.title)

            # Если такой заголовок уже встречался в этой же ленте, сразу пропускаем.
            if normalized_title in seen_titles_in_run:
                existing_articles_count += 1
                continue

            seen_titles_in_run.add(normalized_title)

            # Проверяем дубль по slug.
            existing_article = await self.repository.get_by_slug(item.slug)
            if existing_article:
                existing_articles_count += 1
                continue

            # Проверяем дубль по нормализованному title в БД.
            existing_article = await self.repository.get_by_normalized_title(normalized_title)
            if existing_article:
                existing_articles_count += 1
                continue

            try:
                detail_html = await self.fetch_detail_with_retry(item.url)
                detail = parse_news_detail(detail_html, item)

                # После detail page проверяем дубль по original_url.
                if detail.original_url:
                    existing_article = await self.repository.get_by_original_url(detail.original_url)
                    if existing_article:
                        existing_articles_count += 1
                        continue

                await self.repository.create_from_detail(detail)
                new_articles_count += 1

            except Exception:
                failed_articles_count += 1

            await asyncio.sleep(settings.source_between_requests_seconds)

        return {
            "parsed_total": len(parsed_items),
            "unique_total": len(items),
            "new_saved": new_articles_count,
            "already_exists": existing_articles_count,
            "failed": failed_articles_count,
        }

    # Пытается скачать detail page с несколькими попытками.
    async def fetch_detail_with_retry(self, url: str) -> str:
        last_error: Exception | None = None

        for attempt in range(1, settings.source_retry_count + 2):
            try:
                return await self.collector.fetch_news_detail_html(url)

            except Exception as error:
                last_error = error

                if attempt < settings.source_retry_count + 1:
                    await asyncio.sleep(settings.source_retry_delay_seconds)

        if last_error is not None:
            raise last_error

        raise RuntimeError("Unknown error while fetching detail page")

    # Обрабатывает пачку статей через AI.
    async def process_ai_batch(self, limit: int = 10) -> dict[str, int]:
        articles = await self.repository.get_pending_ai_articles(limit=limit)

        processed_count = 0
        failed_count = 0

        for article in articles:
            try:
                ai_result = self.ai_service.process_article(article)

                normalized_title_ru = normalize_title(ai_result["title_ru"])
                existing_article = await self.repository.get_by_normalized_title_ru(
                    normalized_title_ru
                )

                if existing_article and existing_article.id != article.id:
                    await self.repository.mark_telegram_skipped(article)
                    continue

                await self.repository.update_ai_result(
                    article=article,
                    title_ru=ai_result["title_ru"],
                    summary_ru=ai_result["summary_ru"],
                    telegram_text=ai_result["telegram_text"],
                    topic=ai_result.get("topic"),
                )

                processed_count += 1

            except Exception:
                await self.repository.mark_ai_failed(article)
                failed_count += 1

        return {
            "pending_found": len(articles),
            "processed": processed_count,
            "failed": failed_count,
        }

    # Отправляет готовые статьи в Telegram.
    async def send_telegram_batch(self, limit: int = 10) -> dict[str, int]:
        articles = await self.repository.get_pending_telegram_articles(limit=limit)

        sent_count = 0
        failed_count = 0
        skipped_count = 0

        for article in articles:
            try:
                # Если статья с тем же original_url уже была отправлена, пропускаем ее.
                if article.original_url:
                    already_sent = await self.repository.has_sent_article_with_original_url(
                        article.original_url
                    )
                    if already_sent:
                        await self.repository.mark_telegram_skipped(article)
                        skipped_count += 1
                        continue

                await self.telegram_service.send_article_with_retry(article)
                await self.repository.mark_telegram_sent(article)

                sent_count += 1

            except Exception as error:
                await self.repository.mark_telegram_failed(article, str(error))
                failed_count += 1

        return {
            "pending_found": len(articles),
            "sent": sent_count,
            "skipped": skipped_count,
            "failed": failed_count,
        }