from urllib.parse import urlparse

from app.utils.text import normalize_title


# Строит устойчивую сигнатуру статьи.
# Стараемся использовать original_url, а если его нет —
# берем комбинацию нормализованного title и source_name.
def build_article_signature(
    title: str,
    source_name: str | None = None,
    original_url: str | None = None,
) -> str:
    normalized_title = normalize_title(title)
    normalized_source = (source_name or "").strip().lower()

    if original_url:
        parsed = urlparse(original_url)
        url_part = f"{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
        return f"{normalized_title}|{normalized_source}|{url_part}"

    return f"{normalized_title}|{normalized_source}"