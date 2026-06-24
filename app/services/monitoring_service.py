from app.collectors.f1cosmos import F1CosmosCollector
from app.db.repositories import ArticleRepository
from app.db.session import AsyncSessionLocal
from app.parsers.f1cosmos import (
    deduplicate_news_list,
    parse_news_detail,
    parse_news_list,
)


# Сервис мониторинга отвечает за полный проход по ленте новостей:
# 1. скачать список новостей
# 2. убрать дубли
# 3. проверить, какие новости уже есть в БД
# 4. скачать detail page для новых новостей
# 5. сохранить новые статьи
class MonitoringService:
    def __init__(self) -> None:
        self.collector = F1CosmosCollector()

    async def run_once(self) -> dict:
        # Скачиваем HTML списка новостей.
        list_html = await self.collector.fetch_news_list_html()

        # Парсим список карточек.
        parsed_items = parse_news_list(list_html)

        # Убираем дубли внутри одного запуска.
        items = deduplicate_news_list(parsed_items)

        new_articles_count = 0
        existing_articles_count = 0
        failed_articles_count = 0
        failed_items: list[tuple[str, str]] = []

        async with AsyncSessionLocal() as session:
            repository = ArticleRepository(session)

            for item in items:
                existing_article = await repository.get_by_slug(item.slug)
                if existing_article:
                    existing_articles_count += 1
                    continue

                try:
                    detail_html = await self.collector.fetch_news_detail_html(item.url)
                    detail = parse_news_detail(detail_html, item)
                    await repository.create_from_detail(detail)
                    new_articles_count += 1

                except Exception as error:
                    failed_articles_count += 1
                    failed_items.append((item.slug, str(error)))

        return {
            "total_parsed_items": len(parsed_items),
            "unique_items": len(items),
            "new_articles_count": new_articles_count,
            "existing_articles_count": existing_articles_count,
            "failed_articles_count": failed_articles_count,
            "failed_items": failed_items,
        }