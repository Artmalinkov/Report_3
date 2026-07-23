# app/database/models/cache.py
"""
Модель кеша для данных из API
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from datetime import datetime
from app.database.base import Base, BaseModel


class Cache(Base, BaseModel):
    """Модель кеширования данных из API"""

    __tablename__ = "cache"

    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(255), unique=True, index=True, nullable=False)
    cache_type = Column(String(50), nullable=False)  # fns, ionet

    # Данные кеша
    data = Column(Text, nullable=False)  # JSON строка
    expires_at = Column(DateTime, nullable=True)

    # Метаданные
    inn = Column(String(12), index=True, nullable=True)
    request_count = Column(Integer, default=0)

    # Индексы
    __table_args__ = (
        Index('ix_cache_type_key', 'cache_type', 'cache_key'),
        Index('ix_cache_expires', 'expires_at'),
        Index('ix_cache_inn_type', 'inn', 'cache_type'),
    )

    def __repr__(self):
        return f"<Cache(id={self.id}, key={self.cache_key}, type={self.cache_type})>"

    def is_expired(self) -> bool:
        """Проверка истек ли кеш"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Проверка валидности кеша"""
        return not self.is_expired()