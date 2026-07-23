# app/database/models/base.py
"""
Базовые классы для моделей SQLAlchemy
"""
from sqlalchemy.orm import declarative_base, declared_attr
from sqlalchemy import Column, DateTime, func
from datetime import datetime

# Создаем базовый класс
Base = declarative_base()


class BaseModel:
    """
    Абстрактный базовый класс с общими полями для всех моделей
    """

    # Автоматическое создание имени таблицы из имени класса
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + 's'

    # Общие поля для всех моделей
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        """Преобразование модели в словарь"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result