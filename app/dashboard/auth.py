# app/dashboard/auth.py
"""
Вход в дашборд по одноразовой ссылке (magic-link) из Telegram-бота:
без пароля — только владелец бота может её получить, т.к. ссылку
присылает сам бот в личный чат.
"""
import secrets
from typing import Optional

from app.database.crud import cache_crud
from app.config import settings

TOKEN_TTL_SECONDS = 300  # ссылка живёт 5 минут и одноразовая
CACHE_TYPE = "dashboard_auth"


def _cache_key(token: str) -> str:
    return f"dashboard_token:{token}"


async def create_login_link(telegram_id: int) -> str:
    """Генерирует одноразовый токен и возвращает готовую ссылку для входа"""
    token = secrets.token_urlsafe(32)
    await cache_crud.set_cache(
        cache_key=_cache_key(token),
        cache_type=CACHE_TYPE,
        data={"telegram_id": telegram_id},
        expires_in_seconds=TOKEN_TTL_SECONDS,
    )
    return f"{settings.DASHBOARD_BASE_URL}/login?token={token}"


async def consume_login_token(token: str) -> Optional[int]:
    """
    Проверяет токен и сразу удаляет его (одноразовый). Возвращает
    telegram_id владельца ссылки, либо None, если токен неверный/истёк
    """
    data = await cache_crud.get_cache(_cache_key(token))
    if not data:
        return None
    await cache_crud.delete_cache(_cache_key(token))
    return data.get("telegram_id")
