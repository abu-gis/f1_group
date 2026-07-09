import asyncio
import html

from telegram import Bot
from telegram.request import HTTPXRequest

from app.config import settings
from app.db.models import Article


class TelegramService:
    def __init__(self) -> None:
        proxy_url = settings.telegram_proxy_url.strip() or None

        request = HTTPXRequest(
            proxy=proxy_url,
            connect_timeout=30,
            read_timeout=60,
            write_timeout=60,
            pool_timeout=30,
        )

        self.bot = Bot(
            token=settings.telegram_bot_token,
            request=request,
        )
        self.chat_id = settings.telegram_chat_id

    def get_topic_emoji(self, topic: str | None) -> str:
        topic_map = {
            "пилоты": "🏎️",
            "команды": "🏁",
            "болиды": "🏎️",
            "регламент": "📜",
            "погода": "🌦️",
            "гонка": "🏆",
            "инциденты": "⚠️",
            "рынок": "💼",
            "медиа": "🎙️",
            "другое": "📘",
        }

        if not topic:
            return "🏁"

        return topic_map.get(topic.lower(), "🏁")

    def build_topic_hashtag(self, topic: str) -> str:
        cleaned = topic.strip().replace(" ", "")
        cleaned = cleaned.replace("-", "")
        cleaned = cleaned.replace("#", "")
        return f"#{cleaned}"

    def build_hashtags_text(self, article: Article) -> str:
        hashtags = ["#f1", "#formula1"]
        topic = (article.topic or "").strip()

        if topic:
            hashtags.append(self.build_topic_hashtag(topic))

        return " ".join(hashtags)

    def build_message_text(self, article: Article) -> str:
        title = article.title_ru or article.title
        body = article.telegram_text or article.summary_ru or article.summary or ""
        topic = (article.topic or "").strip()
        emoji = self.get_topic_emoji(topic)

        safe_title = html.escape(title)
        safe_body = html.escape(body)
        hashtags_text = self.build_hashtags_text(article)

        return (
            f"{emoji} <b>{safe_title}</b>\n\n"
            f"{safe_body}\n\n"
            f"{hashtags_text}"
        )

    def build_photo_caption(self, article: Article, limit: int = 1024) -> str:
        title = article.title_ru or article.title
        body = article.telegram_text or article.summary_ru or article.summary or ""
        topic = (article.topic or "").strip()
        emoji = self.get_topic_emoji(topic)

        safe_title = html.escape(title)
        safe_body = html.escape(body)
        hashtags_text = self.build_hashtags_text(article)

        prefix = f"{emoji} <b>{safe_title}</b>\n\n"
        suffix = f"\n\n{hashtags_text}"

        available_body_length = limit - len(prefix) - len(suffix)

        if available_body_length < 0:
            return (prefix + suffix)[:limit]

        trimmed_body = safe_body
        if len(trimmed_body) > available_body_length:
            trimmed_body = trimmed_body[: max(available_body_length - 3, 0)].rstrip()
            if trimmed_body:
                trimmed_body += "..."

        return prefix + trimmed_body + suffix

    async def send_article(self, article: Article) -> None:
        if article.main_image_url:
            await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=article.main_image_url,
                caption=self.build_photo_caption(article),
                parse_mode="HTML",
            )
            return

        await self.bot.send_message(
            chat_id=self.chat_id,
            text=self.build_message_text(article),
            parse_mode="HTML",
        )

    async def send_article_with_retry(
        self,
        article: Article,
        retry_count: int = 2,
        retry_delay_seconds: int = 2,
    ) -> None:
        last_error: Exception | None = None

        for attempt in range(1, retry_count + 2):
            try:
                await self.send_article(article)
                return

            except Exception as error:
                last_error = error
                error_text = str(error).lower()
                wait_seconds = retry_delay_seconds

                if "retry in" in error_text:
                    import re

                    match = re.search(r"retry in (\d+)", error_text)
                    if match:
                        wait_seconds = int(match.group(1)) + 1

                if attempt < retry_count + 1:
                    await asyncio.sleep(wait_seconds)

        if last_error is not None:
            raise last_error

        raise RuntimeError("Unknown error while sending Telegram message")