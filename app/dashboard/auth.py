# app/dashboard/auth.py
"""
Вход в дашборд по временной ссылке (magic-link) из Telegram-бота: без
пароля — только владелец бота может её получить, т.к. ссылку присылает
сам бот в личный чат.
"""
import secrets
from typing import Optional

from app.database.crud import cache_crud
from app.config import settings

# Ссылка не одноразовая, а просто временная: чтобы её открыть, сначала
# нужно поднять SSH-туннель до сервера — это может занять больше, чем
# несколько минут, особенно с первого раза. Строгая одноразовость к тому
# же ломается, если Telegram (или антивирус на стороне получателя)
# сам предварительно открывает ссылку — тогда легитимный клик находит
# токен уже "использованным". Риск от повторного использования в этом
# окне минимален: доступ и так закрыт SSH-туннелем на конкретный сервер
TOKEN_TTL_SECONDS = 900  # 15 минут
CACHE_TYPE = "dashboard_auth"


def _cache_key(token: str) -> str:
    return f"dashboard_token:{token}"


async def create_login_link(telegram_id: int) -> str:
    """Генерирует временный токен и возвращает готовую ссылку для входа"""
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
    Проверяет токен. Возвращает telegram_id владельца ссылки, либо None,
    если токен неверный/истёк (сама ссылка остаётся рабочей до истечения
    TTL — см. комментарий выше про отказ от строгой одноразовости)
    """
    data = await cache_crud.get_cache(_cache_key(token))
    if not data:
        return None
    return data.get("telegram_id")
