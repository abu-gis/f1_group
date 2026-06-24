from datetime import date, datetime
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from app.config import settings
from app.schemas.article import NewsDetail, NewsListItem


KNOWN_CATEGORIES = {
    "analysis",
    "breaking",
    "opinion",
    "report",
    "rumor",
    "news",
    "reactions",
    "exclusive",
    "live",
    "feature",
    "technical",
}


# Парсер списка новостей.
# На вход получает HTML страницы /dashboard/news
# На выходе возвращает список карточек новостей в виде NewsListItem.
def parse_news_list(html: str) -> list[NewsListItem]:
    tree = HTMLParser(html)
    items: list[NewsListItem] = []

    links = tree.css('a[href^="/dashboard/news/"]')

    for link in links:
        href = link.attributes.get("href")
        title = link.attributes.get("title")

        if not href or not title:
            continue

        full_url = urljoin(settings.source_base_url, href)
        slug = href.rstrip("/").split("/")[-1]

        preview_image_url = None
        for image_node in link.css("img"):
            image_src = image_node.attributes.get("src")
            image_alt = (image_node.attributes.get("alt") or "").strip().lower()

            if image_src and image_alt != "logo":
                preview_image_url = image_src
                break

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

        source_name = None
        category = None

        span_texts: list[str] = []
        for span_node in link.css("span"):
            text = span_node.text(strip=True)
            if text:
                span_texts.append(text)

        for text in span_texts:
            normalized = text.strip()
            normalized_lower = normalized.lower()

            if normalized_lower == "logo":
                continue

            if normalized_lower in KNOWN_CATEGORIES:
                category = normalized
                continue

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


# Парсер полной страницы новости.
# На вход получает HTML detail page и базовые данные из list item.
# На выходе возвращает полную структуру статьи.
def parse_news_detail(html: str, list_item: NewsListItem) -> NewsDetail:
    tree = HTMLParser(html)

    article_node = tree.css_first("article")

    title = list_item.title
    summary = None
    body_text = None
    original_url = None
    source_name = list_item.source_name
    source_logo_url = None
    main_image_url = list_item.preview_image_url
    published_at = None
    published_at_text = None
    category = list_item.category

    if article_node:
        title_node = article_node.css_first("h1")
        if title_node:
            title = title_node.text(strip=True)

        # Главная картинка статьи.
        image_node = article_node.css_first("img")
        if image_node:
            image_src = image_node.attributes.get("src")
            if image_src:
                main_image_url = image_src

        # Ищем Summary по заголовку блока.
        span_nodes = article_node.css("span")
        for span_node in span_nodes:
            if span_node.text(strip=True).lower() == "summary":
                parent = span_node.parent
                if parent:
                    summary_container = parent.parent
                    if summary_container:
                        text_blocks = summary_container.css("div")
                        if len(text_blocks) >= 2:
                            summary_text = text_blocks[-1].text(strip=True)
                            if summary_text:
                                summary = summary_text
                break

        # Основной текст статьи обычно лежит в prose-блоке.
        prose_node = article_node.css_first(".prose")
        if prose_node:
            body_text = prose_node.text(strip=True)

        # Ищем ссылку на оригинальную статью по подписи Original Article.
        for paragraph_node in article_node.css("p"):
            paragraph_text = paragraph_node.text(strip=True).lower()
            if "original article" in paragraph_text:
                original_link = paragraph_node.css_first('a[href^="http"]')
                if original_link:
                    original_url = original_link.attributes.get("href")
                break

    # Ищем время публикации по всей странице, а не только внутри article.
    # На странице detail time часто находится в нижней панели вне article.
    time_nodes = tree.css("time")
    for time_node in time_nodes:
        datetime_value = time_node.attributes.get("datetime")
        text_value = time_node.text(strip=True)

        if text_value:
            published_at_text = text_value

        if datetime_value:
            try:
                published_at = datetime.fromisoformat(datetime_value)
            except ValueError:
                published_at = None

        # Берем первый осмысленный time и выходим.
        if published_at_text or published_at:
            break

    # Ищем логотип источника по всей странице.
    for image_node in tree.css("img"):
        image_alt = (image_node.attributes.get("alt") or "").strip().lower()
        if image_alt == "logo":
            source_logo_url = image_node.attributes.get("src")
            break

    # Пытаемся уточнить источник и категорию по span-элементам страницы.
    # Здесь стараемся не перепутать источник с типом материала.
    page_span_texts: list[str] = []
    for span_node in tree.css("span"):
        text = span_node.text(strip=True)
        if text:
            page_span_texts.append(text)

    for text in page_span_texts:
        normalized = text.strip()
        normalized_lower = normalized.lower()

        if normalized_lower == "logo":
            continue

        if normalized_lower in KNOWN_CATEGORIES:
            category = normalized
            continue

        # Не затираем уже найденный источник словами вроде "Practice report".
        if normalized_lower not in KNOWN_CATEGORIES and normalized != title:
            if source_name is None:
                source_name = normalized

    return NewsDetail(
        title=title,
        slug=list_item.slug,
        f1cosmos_url=list_item.url,
        summary=summary,
        body_text=body_text,
        original_url=original_url,
        source_name=source_name,
        source_logo_url=source_logo_url,
        main_image_url=main_image_url,
        published_at=published_at,
        published_at_text=published_at_text,
        category=category,
    )

# Убирает дубли новостей внутри одного списка.
# Сайт иногда отдает повторяющиеся карточки, поэтому
# перед обработкой полезно оставить только уникальные slug.
def deduplicate_news_list(items: list[NewsListItem]) -> list[NewsListItem]:
    unique_items: list[NewsListItem] = []
    seen_slugs: set[str] = set()

    for item in items:
        if item.slug in seen_slugs:
            continue

        seen_slugs.add(item.slug)
        unique_items.append(item)

    return unique_items