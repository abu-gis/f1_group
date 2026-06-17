from datetime import date
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