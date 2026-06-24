import httpx

from app.config import settings


# Collector отвечает только за сетевой запрос.
# Он ничего не парсит, а просто скачивает HTML страницы.
class F1CosmosCollector:
    def __init__(self) -> None:
        self.base_url = settings.source_base_url.rstrip("/")
        self.news_path = settings.source_news_path
        self.timeout = settings.source_timeout
        self.proxy_url = settings.source_proxy_url.strip() or None
        self.user_agent = settings.request_user_agent

    # Возвращает полный URL страницы списка новостей.
    def get_news_url(self) -> str:
        return f"{self.base_url}{self.news_path}"

    # Скачивает HTML страницы списка новостей.
    async def fetch_news_list_html(self) -> str:
        headers = {
            "User-Agent": self.user_agent,
        }

        client_kwargs = {
            "timeout": self.timeout,
            "headers": headers,
            "follow_redirects": True,
        }

        # Прокси подключаем только если он задан в .env.
        if self.proxy_url:
            client_kwargs["proxy"] = self.proxy_url

        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.get(self.get_news_url())
            response.raise_for_status()
            return response.text

    # Скачивает HTML детальной страницы конкретной новости.
    async def fetch_news_detail_html(self, url: str) -> str:
        headers = {
            "User-Agent": self.user_agent,
        }

        client_kwargs = {
            "timeout": self.timeout,
            "headers": headers,
            "follow_redirects": True,
        }

        if self.proxy_url:
            client_kwargs["proxy"] = self.proxy_url

        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text