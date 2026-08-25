# app/tests/test_rate_limiter.py
"""
Тестирование check_rate_limit — на реальной локальной БД (не мок): тест
создает тестового пользователя с заведомо нереальным telegram_id, гоняет
проверки и чистит за собой данные (пользователя и ratelimit-кеш) в finally,
даже если сам тест упал. Платных внешних API не касается — только
локальный Postgres, поэтому в отличие от test_fns_api.py/test_ionet_api.py
пригоден для автоматического запуска через pytest.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import delete, update

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import settings
from app.database.crud import user_crud, cache_crud
from app.database.models import User
from app.database.session import AsyncSessionLocal
from app.bot.handlers import check_rate_limit

TEST_TELEGRAM_ID = 999999999


async def _cleanup():
    async with AsyncSessionLocal() as session:
        await session.execute(delete(User).where(User.telegram_id == TEST_TELEGRAM_ID))
        await session.commit()
    await cache_crud.delete_by_type("ratelimit")


async def _age_last_request(seconds_ago: int):
    """Отодвигает last_request_at в прошлое, чтобы обойти cooldown в тесте"""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.telegram_id == TEST_TELEGRAM_ID)
            .values(last_request_at=datetime.utcnow() - timedelta(seconds=seconds_ago))
        )
        await session.commit()


@pytest.fixture
async def rate_limit_test_user():
    await _cleanup()
    await user_crud.create_or_update(telegram_id=TEST_TELEGRAM_ID, username="test_rate_limit")
    yield TEST_TELEGRAM_ID
    await _cleanup()


async def test_first_request_is_allowed(rate_limit_test_user):
    result = await check_rate_limit(TEST_TELEGRAM_ID)
    assert result is None


async def test_immediate_second_request_blocked_by_cooldown(rate_limit_test_user):
    await check_rate_limit(TEST_TELEGRAM_ID)
    result = await check_rate_limit(TEST_TELEGRAM_ID)
    assert result is not None
    assert "часто" in result or "сек" in result


async def test_request_allowed_after_cooldown_elapses(rate_limit_test_user):
    await check_rate_limit(TEST_TELEGRAM_ID)
    await _age_last_request(settings.RATE_LIMIT_COOLDOWN_SECONDS + 5)
    result = await check_rate_limit(TEST_TELEGRAM_ID)
    assert result is None


async def test_daily_limit_blocks_after_max_requests(rate_limit_test_user):
    for _ in range(settings.RATE_LIMIT_DAILY_MAX):
        await _age_last_request(settings.RATE_LIMIT_COOLDOWN_SECONDS + 5)
        result = await check_rate_limit(TEST_TELEGRAM_ID)
        assert result is None

    await _age_last_request(settings.RATE_LIMIT_COOLDOWN_SECONDS + 5)
    blocked = await check_rate_limit(TEST_TELEGRAM_ID)
    assert blocked is not None
    assert "лимит" in blocked.lower()


async def test_comparison_weight_counts_multiple_requests(rate_limit_test_user):
    """Сравнение N компаний должно расходовать дневной лимит как N запросов, а не 1"""
    weight = settings.RATE_LIMIT_DAILY_MAX  # сразу выбираем весь лимит одним вызовом
    result = await check_rate_limit(TEST_TELEGRAM_ID, weight=weight)
    assert result is None

    await _age_last_request(settings.RATE_LIMIT_COOLDOWN_SECONDS + 5)
    blocked = await check_rate_limit(TEST_TELEGRAM_ID, weight=1)
    assert blocked is not None


async def test_banned_user_is_blocked(rate_limit_test_user):
    await user_crud.ban_user(TEST_TELEGRAM_ID)
    result = await check_rate_limit(TEST_TELEGRAM_ID)
    assert result is not None
    assert "ограничен" in result.lower()
