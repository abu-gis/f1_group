from datetime import date, datetime

from pydantic import BaseModel


# Схема одной карточки новости из списка новостей.
# Это еще не полная статья, а только краткие данные с overview-страницы.
class NewsListItem(BaseModel):
    title: str
    url: str
    slug: str
    preview_image_url: str | None = None
    source_name: str | None = None
    category: str | None = None
    published_date: date | None = None
    relative_time_text: str | None = None


# Схема полной новости с детальной страницы.
# Именно ее мы позже будем сохранять в БД и отправлять в ИИ.
class NewsDetail(BaseModel):
    title: str
    slug: str
    f1cosmos_url: str
    summary: str | None = None
    body_text: str | None = None
    original_url: str | None = None
    source_name: str | None = None
    source_logo_url: str | None = None
    main_image_url: str | None = None
    published_at: datetime | None = None
    published_at_text: str | None = None
    category: str | None = None