import httpx

from app.config import settings


class CalendarCollector:
    def __init__(self) -> None:
        self.base_url = settings.calendar_base_url.rstrip("/")
        self.list_path = settings.calendar_list_path
        self.timeout = settings.source_timeout
        self.proxy_url = settings.source_proxy_url.strip() or None
        self.user_agent = settings.request_user_agent

    def get_calendar_url(self) -> str:
        return f"{self.base_url}{self.list_path}"

    def build_client_kwargs(self, headers: dict[str, str]) -> dict:
        client_kwargs = {
            "timeout": self.timeout,
            "headers": headers,
            "follow_redirects": True,
        }

        if self.proxy_url:
            client_kwargs["proxy"] = self.proxy_url

        return client_kwargs

    async def fetch_calendar_html(self) -> str:
        headers = {"User-Agent": self.user_agent}

        async with httpx.AsyncClient(**self.build_client_kwargs(headers)) as client:
            response = await client.get(self.get_calendar_url())
            response.raise_for_status()
            return response.text

    async def fetch_calendar_rsc(self) -> str:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/x-component, */*;q=0.1",
            "RSC": "1",
            "Next-Url": settings.calendar_next_url,
            "Referer": f"{self.base_url}{settings.calendar_referer_path}",
        }

        if settings.calendar_router_state_tree.strip():
            headers["Next-Router-State-Tree"] = settings.calendar_router_state_tree.strip()

        async with httpx.AsyncClient(**self.build_client_kwargs(headers)) as client:
            response = await client.get(
                self.get_calendar_url(),
                params={"_rsc": "1"},
            )
            response.raise_for_status()
            return response.text