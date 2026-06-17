from app.db.base import Base
from app.db.session import engine
from app.db import models


# Эта функция создает таблицы, которые описаны в models.py.
# Импорт models нужен, чтобы metadata знала о существующих моделях.
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)