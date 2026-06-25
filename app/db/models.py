from datetime import datetime

from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Временная тестовая таблица.
# Можно оставить ее на время разработки, она не мешает.
class Healthcheck(Base):
    __tablename__ = "healthcheck"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# Основная таблица новостей для MVP.
# Здесь уже есть поля как для сырых данных статьи,
# так и для дальнейшей AI и Telegram обработки.
class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Устойчивый ключ статьи для дедупликации между запусками.
    content_signature: Mapped[str | None] = mapped_column(nullable=True, index=True)


    # Уникальный slug новости внутри F1 Cosmos.
    slug: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)

    # URL страницы новости на F1 Cosmos.
    f1cosmos_url: Mapped[str] = mapped_column(nullable=False, unique=True)

    # Заголовок статьи на английском.
    title: Mapped[str] = mapped_column(nullable=False)

    # Краткое summary на английском.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Основной текст статьи на английском.
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Оригинальная ссылка на первоисточник.
    original_url: Mapped[str | None] = mapped_column(nullable=True)

    # Название источника как оно распарсилось.
    source_name: Mapped[str | None] = mapped_column(nullable=True)

    # Ссылка на логотип источника.
    source_logo_url: Mapped[str | None] = mapped_column(nullable=True)

    # Главная картинка статьи.
    main_image_url: Mapped[str | None] = mapped_column(nullable=True)

    # Человекочитаемое время публикации с сайта.
    published_at_text: Mapped[str | None] = mapped_column(nullable=True)

    # Категория статьи, например Analysis / Breaking / Reactions.
    category: Mapped[str | None] = mapped_column(nullable=True)

    # Заголовок после перевода/обработки ИИ.
    title_ru: Mapped[str | None] = mapped_column(nullable=True)

    # Краткое summary на русском.
    summary_ru: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Готовый текст для публикации в Telegram.
    telegram_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Статус AI-обработки.
    ai_status: Mapped[str] = mapped_column(nullable=False, default="pending")

    # Статус Telegram-публикации.
    telegram_status: Mapped[str] = mapped_column(nullable=False, default="pending")

    # Текст последней ошибки Telegram-отправки.
    telegram_error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Краткая тема статьи для Telegram и фильтрации.
    topic: Mapped[str | None] = mapped_column(nullable=True)

    # Время, когда статья была обработана ИИ.
    ai_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Время, когда статья была отправлена в Telegram.
    telegram_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Когда мы впервые увидели и сохранили статью в своей системе.
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )