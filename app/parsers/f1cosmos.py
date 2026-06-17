from datetime import date
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from app.config import settings
from app.schemas.article import NewsListItem


# Парсер списка новостей.
# На вход получает HTML страницы /dashboard/news
# На выходе возвращает список карточек новостей в виде NewsListItem.
def parse_news_list(html: str) -> list[NewsListItem]:
    tree = HTMLParser(html)
    items: list[NewsListItem] = []

    # Ищем ссылки на детальные страницы новостей.
    # Нас интересуют только ссылки формата /dashboard/news/<slug>
    links = tree.css('a[href^="/dashboard/news/"]')

    for link in links:
        href = link.attributes.get("href")
        title = link.attributes.get("title")

        if not href or not title:
            continue

        # Превращаем относительный путь в полный URL.
        full_url = urljoin(settings.source_base_url, href)

        # Последняя часть URL обычно и есть slug новости.
        slug = href.rstrip("/").split("/")[-1]

        # Пытаемся найти картинку внутри карточки.
        # Берем первую осмысленную картинку в ссылке.
        preview_image_url = None
        for image_node in link.css("img"):
            image_src = image_node.attributes.get("src")
            image_alt = (image_node.attributes.get("alt") or "").strip().lower()

            # Логотип источника нам не нужен как preview image.
            if image_src and image_alt != "logo":
                preview_image_url = image_src
                break

        # Пытаемся найти дату публикации из атрибута datetime.
        time_node = link.css_first("time")
        published_date = None
        relative_time_text = None
        if time_node:
            datetime_value = time_node.attributes.get("datetime")
            relative_time_text = time_node.text(strip=True)

            if datetime_value:
                try:
                    published_date = date.fromisoformat(datetime_value)
                except ValueError:
                    published_date = None

        # Собираем все span-тексты внутри карточки.
        # Потом отделяем источник от категории.
        span_texts: list[str] = []
        for span_node in link.css("span"):
            text = span_node.text(strip=True)
            if text:
                span_texts.append(text)

        source_name = None
        category = None

        for text in span_texts:
            normalized = text.strip()

            # Категория обычно короткая: Analysis, Breaking, Opinion и т.д.
            # Источник чаще выглядит как имя медиа: Racingnews365, Autosport, PlanetF1.
            if normalized.lower() in {"analysis", "breaking", "opinion", "report", "rumor", "news"}:
                category = normalized
            elif normalized.lower() != "logo":
                source_name = normalized

        items.append(
            NewsListItem(
                title=title.strip(),
                url=full_url,
                slug=slug,
                preview_image_url=preview_image_url,
                source_name=source_name,
                category=category,
                published_date=published_date,
                relative_time_text=relative_time_text,
            )
        )

    return items