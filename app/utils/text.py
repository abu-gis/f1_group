import re


def normalize_title(title: str) -> str:
    normalized = title.strip().lower()

    normalized = normalized.replace("’", "'")
    normalized = normalized.replace("–", " ")
    normalized = normalized.replace("—", " ")
    normalized = normalized.replace("-", " ")

    normalized = re.sub(r"[^a-zа-я0-9\s']", " ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()