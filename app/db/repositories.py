from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Article, SchedulePost, SourceSetting
from app.schemas.article import NewsDetail
from app.utils.signature import build_article_signature
from app.utils.sources import normalize_source_name


class ArticleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_slug(self, slug: str) -> Article | None:
        result = await self.session.execute(
            select(Article).where(Article.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_first_pending_ai_article(self) -> Article | None:
        result = await self.session.execute(
            select(Article)
            .where(Article.ai_status == "pending")
            .order_by(Article.id.asc())
        )
        return result.scalars().first()

    async def create_from_detail(self, detail: NewsDetail) -> Article:
        content_signature = build_article_signature(
            title=detail.title,
            source_name=detail.source_name,
            original_url=detail.original_url,
        )

        article = Article(
            slug=detail.slug,
            f1cosmos_url=detail.f1cosmos_url,
            title=detail.title,
            summary=detail.summary,
            body_text=detail.body_text,
            original_url=detail.original_url,
            source_name=normalize_source_name(detail.source_name),
            source_logo_url=detail.source_logo_url,
            main_image_url=detail.main_image_url,
            published_at_text=detail.published_at_text,
            category=detail.category,
            content_signature=content_signature,
        )

        self.session.add(article)
        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def update_ai_result(
        self,
        article: Article,
        title_ru: str,
        summary_ru: str,
        telegram_text: str,
        topic: str | None,
    ) -> Article:
        article.title_ru = title_ru
        article.summary_ru = summary_ru
        article.telegram_text = telegram_text
        article.topic = topic
        article.ai_status = "done"
        article.ai_processed_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def mark_ai_failed(self, article: Article) -> Article:
        article.ai_status = "failed"

        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def get_pending_ai_articles(self, limit: int = 10) -> list[Article]:
        result = await self.session.execute(
            select(Article)
            .where(Article.ai_status == "pending")
            .order_by(Article.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_telegram_articles(self, limit: int = 10) -> list[Article]:
        result = await self.session.execute(
            select(Article)
            .where(Article.ai_status == "done")
            .where(Article.telegram_status == "pending")
            .order_by(Article.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_failed_telegram_articles(self, limit: int = 10) -> list[Article]:
        result = await self.session.execute(
            select(Article)
            .where(Article.ai_status == "done")
            .where(Article.telegram_status == "failed")
            .order_by(Article.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_telegram_sent(self, article: Article) -> Article:
        article.telegram_status = "sent"
        article.telegram_sent_at = datetime.now(timezone.utc)
        article.telegram_error_text = None

        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def mark_telegram_failed(self, article: Article, error_text: str) -> Article:
        article.telegram_status = "failed"
        article.telegram_error_text = error_text

        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def get_by_title(self, title: str) -> Article | None:
        result = await self.session.execute(
            select(Article).where(Article.title == title)
        )
        return result.scalars().first()

    async def get_by_original_url(self, original_url: str) -> Article | None:
        result = await self.session.execute(
            select(Article).where(Article.original_url == original_url)
        )
        return result.scalars().first()

    async def get_by_normalized_title(self, normalized_title: str) -> Article | None:
        result = await self.session.execute(select(Article))
        articles = result.scalars().all()

        from app.utils.text import normalize_title

        for article in articles:
            if normalize_title(article.title) == normalized_title:
                return article

        return None

    async def has_sent_article_with_original_url(self, original_url: str) -> bool:
        if not original_url:
            return False

        result = await self.session.execute(
            select(Article).where(
                Article.original_url == original_url,
                Article.telegram_status == "sent",
            )
        )
        return result.scalars().first() is not None

    async def mark_telegram_skipped(
        self,
        article: Article,
        reason: str = "Skipped as duplicate",
    ) -> Article:
        article.telegram_status = "skipped"
        article.telegram_error_text = reason

        await self.session.commit()
        await self.session.refresh(article)
        return article

    async def get_by_normalized_title_ru(self, normalized_title_ru: str) -> Article | None:
        result = await self.session.execute(select(Article))
        articles = result.scalars().all()

        from app.utils.text import normalize_title

        for article in articles:
            if not article.title_ru:
                continue

            if normalize_title(article.title_ru) == normalized_title_ru:
                return article

        return None

    async def get_by_content_signature(self, content_signature: str) -> Article | None:
        result = await self.session.execute(
            select(Article).where(Article.content_signature == content_signature)
        )
        return result.scalars().first()

    async def has_sent_article_with_title_ru(self, title_ru: str) -> bool:
        if not title_ru:
            return False

        result = await self.session.execute(select(Article))
        articles = result.scalars().all()

        from app.utils.text import normalize_title

        normalized_title_ru = normalize_title(title_ru)

        for article in articles:
            if article.telegram_status != "sent":
                continue
            if not article.title_ru:
                continue
            if normalize_title(article.title_ru) == normalized_title_ru:
                return True

        return False

    async def mark_ai_skipped(self, article: Article) -> Article:
        article.ai_status = "done"
        article.telegram_status = "skipped"
        article.telegram_error_text = "Skipped as duplicate after AI normalization"
        article.ai_processed_at = datetime.now(timezone.utc)

        await self.session.commit()
        await self.session.refresh(article)
        return article


class SchedulePostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, schedule_post_id: int) -> SchedulePost | None:
        result = await self.session.execute(
            select(SchedulePost).where(SchedulePost.id == schedule_post_id)
        )
        return result.scalar_one_or_none()

    async def get_by_round_key(self, round_key: str) -> SchedulePost | None:
        result = await self.session.execute(
            select(SchedulePost).where(SchedulePost.round_key == round_key)
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        *,
        round_key: str,
        round_number: str,
        grand_prix_title: str,
        country: str,
        city: str,
        circuit_name: str,
        start_date: str,
        end_date: str,
        original_text: str,
        track_text: str,
        source_payload_json: str | None,
    ) -> SchedulePost:
        schedule_post = await self.get_by_round_key(round_key)

        if schedule_post is None:
            schedule_post = SchedulePost(
                round_key=round_key,
                round_number=round_number,
                grand_prix_title=grand_prix_title,
                country=country,
                city=city,
                circuit_name=circuit_name,
                start_date=start_date,
                end_date=end_date,
                original_text=original_text,
                track_text=track_text,
                source_payload_json=source_payload_json,
            )
            self.session.add(schedule_post)
        else:
            schedule_post.round_number = round_number
            schedule_post.grand_prix_title = grand_prix_title
            schedule_post.country = country
            schedule_post.city = city
            schedule_post.circuit_name = circuit_name
            schedule_post.start_date = start_date
            schedule_post.end_date = end_date
            schedule_post.original_text = original_text
            schedule_post.track_text = track_text
            schedule_post.source_payload_json = source_payload_json

        await self.session.commit()
        await self.session.refresh(schedule_post)
        return schedule_post

    async def save_edited_text(self, schedule_post: SchedulePost, edited_text: str) -> SchedulePost:
        schedule_post.edited_text = edited_text
        await self.session.commit()
        await self.session.refresh(schedule_post)
        return schedule_post

    async def mark_original_sent(self, schedule_post: SchedulePost) -> SchedulePost:
        schedule_post.original_sent_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(schedule_post)
        return schedule_post

    async def mark_edited_sent(self, schedule_post: SchedulePost) -> SchedulePost:
        schedule_post.edited_sent_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(schedule_post)
        return schedule_post


class SourceSettingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_source_name(self, source_name: str) -> SourceSetting | None:
        normalized_source_name = normalize_source_name(source_name)
        if not normalized_source_name:
            return None

        result = await self.session.execute(
            select(SourceSetting).where(SourceSetting.source_name == normalized_source_name)
        )
        return result.scalar_one_or_none()

    async def is_source_enabled(self, source_name: str | None) -> bool:
        normalized_source_name = normalize_source_name(source_name)
        if not normalized_source_name:
            return True

        setting = await self.get_by_source_name(normalized_source_name)
        if setting is None:
            return True

        return setting.is_enabled

    async def set_source_enabled(self, source_name: str, is_enabled: bool) -> SourceSetting:
        normalized_source_name = normalize_source_name(source_name)
        if not normalized_source_name:
            raise ValueError("Source name is empty after normalization")

        setting = await self.get_by_source_name(normalized_source_name)

        if setting is None:
            setting = SourceSetting(
                source_name=normalized_source_name,
                is_enabled=is_enabled,
            )
            self.session.add(setting)
        else:
            setting.is_enabled = is_enabled

        await self.session.commit()
        await self.session.refresh(setting)
        return setting

    async def toggle_source(self, source_name: str) -> SourceSetting:
        normalized_source_name = normalize_source_name(source_name)
        if not normalized_source_name:
            raise ValueError("Source name is empty after normalization")

        current_enabled = await self.is_source_enabled(normalized_source_name)
        return await self.set_source_enabled(normalized_source_name, not current_enabled)

    async def list_sources_with_status(self) -> list[tuple[str, bool]]:
        article_result = await self.session.execute(
            select(Article.source_name)
            .where(Article.source_name.is_not(None))
            .distinct()
            .order_by(Article.source_name.asc())
        )
        article_sources = [
            normalize_source_name(row[0])
            for row in article_result.all()
            if row[0] and normalize_source_name(row[0])
        ]

        settings_result = await self.session.execute(
            select(SourceSetting).order_by(SourceSetting.source_name.asc())
        )
        settings = list(settings_result.scalars().all())

        settings_map = {item.source_name: item.is_enabled for item in settings}
        all_sources = sorted(set(article_sources) | set(settings_map.keys()))

        result: list[tuple[str, bool]] = []
        for source_name in all_sources:
            result.append((source_name, settings_map.get(source_name, True)))

        return result