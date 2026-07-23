# app/main.py

"""
Точка входа в приложение
"""
import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from app.config import settings
from app.bot.handlers import router
from app.database.session import init_db, close_db


async def main():
    """Главная функция запуска бота"""
    # Настройка логирования
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else "INFO"
    )
    logger.add(
        "logs/report3.log",
        rotation="500 MB",
        retention="10 days",
        level=settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else "INFO"
    )

    logger.info("🚀 Запуск Report_3 бота...")
    logger.info(f"📊 Режим: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")

    try:
        # Инициализация БД
        await init_db()
        logger.info("✅ База данных инициализирована")

        # Создание бота
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        # Создание диспетчера
        dp = Dispatcher()
        dp.include_router(router)

        # Информация о боте
        bot_info = await bot.get_me()
        logger.info(f"✅ Бот запущен: @{bot_info.username}")
        logger.info(f"🔗 Ссылка: https://t.me/{bot_info.username}")

        # Запуск поллинга
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        await close_db()
        logger.info("🔒 Соединение с БД закрыто")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        sys.exit(1)