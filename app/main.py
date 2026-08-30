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
from aiogram.types import BotCommand
from loguru import logger

from app.config import settings
from app.bot.handlers import router
from app.database.session import init_db, close_db


async def main():
    """Главная функция запуска бота"""
    # Настройка логирования. LOG_FORMAT=json включает структурированные
    # логи (по одному JSON-объекту на строку) для агрегаторов вроде
    # Loki/ELK на проде; text — читаемый цветной вывод для разработки
    logger.remove()
    is_json = settings.LOG_FORMAT.lower() == "json"
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        serialize=is_json,
    )
    logger.add(
        "logs/report_v_4.log",
        rotation="500 MB",
        retention="10 days",
        level=settings.LOG_LEVEL,
        serialize=is_json,
    )

    logger.info("🚀 Запуск Deep Finance Report бота...")
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

        # Кнопка "Меню" рядом с полем ввода — список команд по умолчанию
        # (без /dashboard: он не для всех, добавляется отдельно только в
        # чат с администратором — см. cmd_start)
        await bot.set_my_commands([
            BotCommand(command="start", description="Начать общение"),
            BotCommand(command="help", description="Справка"),
            BotCommand(command="history", description="История запросов"),
            BotCommand(command="stats", description="Моя статистика"),
        ])

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