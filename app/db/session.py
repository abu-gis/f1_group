from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


# Engine отвечает за подключение к PostgreSQL.
# create_async_engine нужен потому, что мы строим проект на async-стеке.
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Если поставить True, SQL-запросы будут печататься в консоль.
)


# Фабрика сессий.
# Через AsyncSessionLocal мы позже будем открывать сессии для чтения/записи в БД.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)