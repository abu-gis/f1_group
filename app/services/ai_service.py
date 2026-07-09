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
            "You are a professional Formula 1 editor writing for a Russian Telegram audience. "
            "Your job is to translate and adapt F1 news into clear, natural, accurate Russian. "
            "Never invent facts, quotes, motives, or context. "
            "Preserve names, teams, circuits, dates, penalties, standings context, and numbers exactly. "
            "Prefer concise editorial Russian over literal translation. "
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

            "Required JSON fields:\n"
            "- title_ru\n"
            "- summary_ru\n"
            "- telegram_text\n"
            "- topic\n\n"

            "Task:\n"
            "You are preparing a Russian-language Formula 1 news post for Telegram.\n"
            "Translate and adapt the article into clear, natural, modern Russian.\n"
            "Write like an F1 editor, not like a literal translator.\n\n"

            "Hard rules:\n"
            "- Do not invent facts, quotes, context, or conclusions.\n"
            "- Do not add information that is missing from the article input.\n"
            "- Preserve all driver names, team names, track names, dates, positions, penalties, and numbers accurately.\n"
            "- If the article is speculative, keep that uncertainty in Russian.\n"
            "- Do not include source link.\n"
            "- Do not include source name.\n"
            "- Do not repeat the headline inside telegram_text.\n\n"

            "Field rules:\n"
            "- title_ru: a short, strong, natural Russian headline in media style.\n"
            "- title_ru should sound like a Telegram/news headline, not a word-for-word translation.\n"
            "- summary_ru: 3-5 informative sentences in Russian summarizing the key point, context, and consequence.\n"
            "- telegram_text: a ready-to-publish Russian Telegram post body without headline.\n"
            "- telegram_text must be split into 2 or 3 readable paragraphs.\n"
            "- Total length: usually 4 to 6 sentences.\n"
            "- Each paragraph should contain 1 to 3 sentences.\n"
            "- The post should explain what happened, why it matters, and what it may affect next.\n"
            "- Avoid one long solid block of text.\n"
            "- Keep the style informative, readable, and slightly more detailed than a short alert.\n"
            "- telegram_text should feel like a polished F1 channel post, not like raw translation.\n"
            "- topic: choose exactly one label from this list: "
            "[Пилоты, Команды, Болиды, Регламент, Погода, Гонка, Инциденты, Рынок, Медиа, Другое]\n\n"

            "Topic selection hints:\n"
            "- Пилоты: driver performance, quotes, rivalry, career, contract, personal form.\n"
            "- Команды: team strategy, management, team decisions, internal dynamics.\n"
            "- Болиды: technical changes, upgrades, car performance, aerodynamics.\n"
            "- Регламент: FIA rules, penalties framework, regulation changes.\n"
            "- Погода: forecast, rain, temperature, track conditions.\n"
            "- Гонка: race weekend action, sessions, qualifying, sprint, race results.\n"
            "- Инциденты: crashes, collisions, investigations, steward decisions.\n"
            "- Рынок: transfers, contracts, rumors, seat market.\n"
            "- Медиа: interviews, public reactions, broadcasts, off-track media stories.\n"
            "- Другое: use only if none of the above fits.\n\n"

            "Style requirements:\n"
            "- Use simple, confident, editorial Russian.\n"
            "- Avoid bureaucratic wording and awkward literal translation.\n"
            "- Avoid clichés, filler, and generic phrases.\n"
            "- Prefer clarity over drama.\n"
            "- Keep the tone engaging for Formula 1 fans.\n\n"

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