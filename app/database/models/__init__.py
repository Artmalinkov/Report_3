# app/database/models/__init__.py
"""
Инициализация моделей
"""
from app.database.models.user import User
from app.database.models.report import Report
from app.database.models.cache import Cache

# Список всех моделей для Alembic
__all__ = [
    "User",
    "Report",
    "Cache",
]

# Словарь моделей для удобства
MODELS = {
    "user": User,
    "report": Report,
    "cache": Cache,
}