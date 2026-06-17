from sqlalchemy.orm import DeclarativeBase

# Базовый класс для всех ORM-моделей.
# Все таблицы проекта будут наследоваться от него.
class Base(DeclarativeBase):
    pass