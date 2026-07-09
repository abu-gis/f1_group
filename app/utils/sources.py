from urllib.parse import urlparse

SOURCE_DOMAIN_MAP = {
    "f1i.com": "F1i",
    "racingnews365.com": "Racingnews365",
    "the-race.com": "The Race",
    "planetf1.com": "PlanetF1",
    "motorsport.com": "Motorsport",
    "gpblog.com": "GPblog",
    "speedcafe.com": "Speedcafe",
    "skysports.com": "Sky Sports",
    "fia.com": "FIA",
    "blackbookmotorsport.com": "BlackBook Motorsport",
    "f1-insider.com": "F1-Insider",
    "espn.com": "ESPN",
    "f1oversteer.com": "F1 Oversteer",
}

KNOWN_SOURCES = [
    "F1i",
    "Racingnews365",
    "The Race",
    "PlanetF1",
    "Motorsport",
    "GPblog",
    "Speedcafe",
    "Sky Sports",
    "FIA",
    "BlackBook Motorsport",
    "F1-Insider",
    "ESPN",
    "F1 Oversteer",
]


def get_known_sources() -> list[str]:
    return KNOWN_SOURCES.copy()


def normalize_source_name(source_name: str | None) -> str | None:
    if not source_name:
        return None

    cleaned = source_name.strip()
    if not cleaned:
        return None

    lowered = cleaned.lower()

    for domain, label in SOURCE_DOMAIN_MAP.items():
        if domain in lowered:
            return label

    compact_map = {
        "f1i": "F1i",
        "racingnews365": "Racingnews365",
        "the race": "The Race",
        "planetf1": "PlanetF1",
        "motorsport": "Motorsport",
        "gpblog": "GPblog",
        "gp blog": "GPblog",
        "speedcafe": "Speedcafe",
        "sky sports": "Sky Sports",
        "fia": "FIA",
        "blackbook motorsport": "BlackBook Motorsport",
        "f1-insider": "F1-Insider",
        "espn": "ESPN",
        "f1 oversteer": "F1 Oversteer",
    }

    for key, label in compact_map.items():
        if key == lowered:
            return label

    return None


def detect_source_name_from_url(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlparse(url)
    hostname = (parsed.netloc or "").lower().strip()

    if hostname.startswith("www."):
        hostname = hostname[4:]

    for domain, label in SOURCE_DOMAIN_MAP.items():
        if hostname == domain or hostname.endswith(f".{domain}"):
            return label

    return None