import json

import openai

from app.config import settings
from app.db.models import Article


# Сервис AI-обработки статьи через OpenAI-совместимый API.
# Здесь используется chat.completions.create и кастомный base_url.
class AIService:
    def __init__(self) -> None:
        self.client = openai.OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.openai_model

    # Готовит входные данные статьи для модели.
    def build_article_input(self, article: Article) -> dict[str, str]:
        return {
            "title": article.title,
            "summary": article.summary or "",
            "body_text": (article.body_text or "")[:12000],
            "source_name": article.source_name or "",
            "category": article.category or "",
            "original_url": article.original_url or "",
        }

    # Формирует системный промпт.
    def build_system_prompt(self) -> str:
        return (
            "You are a professional Formula 1 news editor. "
            "Translate articles into natural Russian. "
            "Do not invent facts. "
            "Preserve names, teams, dates, and competitive context accurately. "
            "Return valid JSON only with fields: "
            "title_ru, summary_ru, telegram_text, topic."
        )

    # Формирует пользовательский промпт.
    def build_user_prompt(self, article: Article) -> str:
        article_input = self.build_article_input(article)

        payload = {
            "title": article_input["title"],
            "summary": article_input["summary"],
            "body_text": article_input["body_text"],
            "source_name": article_input["source_name"],
            "category": article_input["category"],
            "original_url": article_input["original_url"],
        }

        return (
            "Return ONLY valid JSON.\n"
            "No markdown.\n"
            "No explanation.\n"
            "No code fences.\n\n"
            "Required fields:\n"
            "- title_ru\n"
            "- summary_ru\n"
            "- telegram_text\n"
            "- topic\n\n"
            "Rules:\n"
            "- title_ru: short natural Russian headline\n"
            "- summary_ru: 3-5 informative sentences in Russian\n"
            "- telegram_text: ready-to-publish Russian Telegram post body without headline\n"
            "- telegram_text must be split into 2 or 3 short paragraphs\n"
            "- Each paragraph should contain 1 or 2 sentences\n"
            "- Avoid one long solid block of text\n"
            "- Keep the style concise, informative, and readable for Telegram\n"
            "- topic: choose exactly one Russian label from this list: "
            "[Пилоты, Команды, Болиды, Регламент, Погода, Гонка, Инциденты, Рынок, Медиа, Другое]\n"
            "- Do not include source link\n"
            "- Do not include source name\n\n"
            f"Article input:\n{json.dumps(payload, ensure_ascii=False)}"
        )

    # Если модель вернула JSON внутри ```json ... ```,
    # вырезаем только содержимое блока.
    def extract_json_text(self, content: str) -> str:
        cleaned = content.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned.removeprefix("```json").strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```").strip()

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        return cleaned

    # Вызывает внешний API и возвращает результат обработки.
    def process_article(self, article: Article) -> dict[str, str]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.build_system_prompt()},
                {"role": "user", "content": self.build_user_prompt(article)},
            ],
            temperature=0.3,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Model returned empty content")

        json_text = self.extract_json_text(content)
        parsed = json.loads(json_text)

        title_ru = parsed.get("title_ru", "").strip()
        summary_ru = parsed.get("summary_ru", "").strip()
        telegram_text = parsed.get("telegram_text", "").strip()
        topic = parsed.get("topic", "").strip()

        if not title_ru or not summary_ru or not telegram_text:
            raise ValueError("Model returned incomplete JSON fields")

        return {
            "title_ru": title_ru,
            "summary_ru": summary_ru,
            "telegram_text": telegram_text,
            "topic": topic,
        }