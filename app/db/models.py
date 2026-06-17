from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Временная тестовая таблица.
# Нужна только для проверки, что SQLAlchemy и PostgreSQL связаны правильно.
class Healthcheck(Base):
    __tablename__ = "healthcheck"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Простое текстовое поле, чтобы было что сохранить.
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Время создания записи.
    # server_default=func.now() означает, что дату поставит сама БД.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )