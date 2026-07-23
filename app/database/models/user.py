# app/database/models/user.py
"""
Модель пользователя Telegram
"""
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, Index
from app.database.base import Base, BaseModel


class User(Base, BaseModel):
    """Модель пользователя Telegram"""

    __tablename__ = "users"

    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)

    # Информация о пользователе
    username = Column(String(64), nullable=True)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    language_code = Column(String(5), default="ru")

    # Статусы
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)

    # Статистика
    total_requests = Column(Integer, default=0)
    last_request_at = Column(DateTime, nullable=True)

    # Дополнительно
    notes = Column(String(500), nullable=True)

    # Индексы для быстрого поиска
    __table_args__ = (
        Index('ix_users_telegram_username', 'telegram_id', 'username'),
        Index('ix_users_active', 'is_active', 'telegram_id'),
    )

    # Связи (будет добавлено позже)
    # reports = relationship("Report", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"

    def get_full_name(self) -> str:
        """Получение полного имени"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.username or str(self.telegram_id)

    def to_dict(self) -> dict:
        """Преобразование в словарь для API"""
        data = super().to_dict()
        # Добавляем дополнительные поля
        data['full_name'] = self.get_full_name()
        return data