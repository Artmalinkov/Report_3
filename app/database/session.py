# app/database/session.py
"""
Подключение к базе данных
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.config import settings
from app.database.base import Base
import logging

logger = logging.getLogger(__name__)

# Синхронный движок для миграций и скриптов
sync_engine = create_engine(
    settings.DATABASE_URL.replace("+asyncpg", ""),
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10
)

# Асинхронный движок для бота
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Проверка соединения перед использованием
)

# Асинхронная фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncSession:
    """Получение сессии для работы с БД (для Dependency Injection)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка сессии: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """Инициализация БД (создание таблиц)"""

    logger.info("Создание таблиц в базе данных...")
    async with async_engine.begin() as conn:
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✅ Таблицы успешно созданы")


async def drop_db():
    """Удаление всех таблиц (для тестов)"""
    logger.warning("Удаление всех таблиц...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("✅ Таблицы удалены")


async def close_db():
    """Закрытие соединения с БД"""
    await async_engine.dispose()
    sync_engine.dispose()
    logger.info("Соединение с БД закрыто")


def sync_get_session():
    """Синхронная сессия для миграций и скриптов"""
    SessionLocal = sessionmaker(bind=sync_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()