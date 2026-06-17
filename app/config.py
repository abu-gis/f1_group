from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    log_level: str = "INFO"

    database_url: str

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    source_base_url: str
    source_news_path: str
    source_proxy_url: str = ""
    source_timeout: int = 30
    source_poll_interval_seconds: int = 180

    request_user_agent: str = "Mozilla/5.0"
    media_dir: str = "./storage/media"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
