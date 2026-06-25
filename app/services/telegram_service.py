import asyncio
import html

from telegram import Bot

from app.config import settings
from app.db.models import Article


# Сервис публикации статей в Telegram.
# Если у статьи есть main_image_url, отправляем фото с подписью.
# Иначе отправляем обычное текстовое сообщение.
class TelegramService:
    def __init__(self) -> None:
        self.bot = Bot(token=settings.telegram_bot_token)
        self.chat_id = settings.telegram_chat_id

    # Подбираем эмодзи по теме статьи.
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

    # Формирует красивый текст поста для Telegram в HTML-формате.
    def build_message_text(self, article: Article) -> str:
        title = article.title_ru or article.title
        body = article.telegram_text or article.summary_ru or article.summary or ""
        topic = (article.topic or "").strip()
        emoji = self.get_topic_emoji(topic)

        safe_title = html.escape(title)
        safe_body = html.escape(body)

        if topic:
            safe_topic = html.escape(topic)
            return (
                f"{emoji} <b>{safe_title}</b>\n\n"
                f"{safe_body}\n\n"
                f"<i>Тема: {safe_topic}</i>"
            )

        return (
            f"{emoji} <b>{safe_title}</b>\n\n"
            f"{safe_body}"
        )

    # Отправляет статью в Telegram.
    # Если есть картинка, отправляем фото с caption.
    async def send_article(self, article: Article) -> None:
        message_text = self.build_message_text(article)

        if article.main_image_url:
            await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=article.main_image_url,
                caption=message_text[:1024],
                parse_mode="HTML",
            )
            return

        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message_text,
            parse_mode="HTML",
        )

    # Делает несколько попыток отправки при временной ошибке.
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

    # Превращает тему в хэштег.
    # Убираем пробелы и служебные символы.
    def build_topic_hashtag(self, topic: str) -> str:
        cleaned = topic.strip().replace(" ", "")
        cleaned = cleaned.replace("-", "")
        return f"#{cleaned}"