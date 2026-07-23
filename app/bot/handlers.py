# app/bot/handlers.py

"""
Обработчики команд Telegram бота
"""
import os
from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    ReplyKeyboardRemove
)
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from app.bot.states import ReportStates
from app.bot.keyboards import (
    main_keyboard,
    get_report_actions_keyboard,
    get_history_keyboard,
    get_cancel_keyboard,
    quick_actions
)
from app.database.crud import user_crud, report_crud, cache_crud
from app.services.fns_client import FNSClient
from app.services.ionet_client import IONETClient
from app.services.report_generator import ReportGenerator
from app.utils.validators import validate_inn
from app.config import settings

# Создаем роутер
router = Router()

# Инициализация сервисов
fns_client = FNSClient()
ionet_client = IONETClient()
report_generator = ReportGenerator()


# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()

    # Сохраняем пользователя
    user = await user_crud.create_or_update(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )

    logger.info(f"Пользователь {user.telegram_id} запустил бота")

    await message.answer(
        "🏢 <b>Добро пожаловать в Report_3!</b>\n\n"
        "Я помогу вам проанализировать финансовую отчетность компании по ИНН.\n\n"
        "📌 <b>Как использовать:</b>\n"
        "Просто отправьте мне ИНН (10 или 12 цифр)\n\n"
        "📋 <b>Команды:</b>\n"
        "/help - Получить справку\n"
        "/history - История запросов\n"
        "/stats - Моя статистика",
        reply_markup=main_keyboard
    )


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    """Обработчик команды /help"""
    await state.clear()

    await message.answer(
        "📋 <b>Инструкция по использованию:</b>\n\n"
        "1️⃣ Отправьте ИНН юридического лица или ИП\n"
        "2️⃣ Бот получит данные из ФНС\n"
        "3️⃣ ИИ проанализирует финансовую отчетность\n"
        "4️⃣ Вы получите HTML-отчет с результатами\n\n"
        "✅ <b>Пример ИНН:</b> 7707083893\n\n"
        "📊 <b>Команды:</b>\n"
        "/start - Приветствие\n"
        "/help - Эта справка\n"
        "/history - История запросов (последние 10)\n"
        "/stats - Ваша статистика\n\n"
        "🔍 <b>Дополнительно:</b>\n"
        "• Отчеты сохраняются в вашей истории\n"
        "• Можно скачать отчет повторно\n"
        "• Анализ занимает 10-30 секунд",
        reply_markup=main_keyboard
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext):
    """Обработчик команды /stats - статистика пользователя"""
    await state.clear()

    stats = await user_crud.get_statistics(message.from_user.id)
    if not stats:
        await message.answer(
            "❌ Не удалось получить статистику",
            reply_markup=main_keyboard
        )
        return

    await message.answer(
        "📊 <b>Ваша статистика:</b>\n\n"
        f"📄 Всего запросов: <b>{stats.get('total_requests', 0)}</b>\n"
        f"📊 Всего отчетов: <b>{stats.get('total_reports', 0)}</b>\n"
        f"🏢 Уникальных компаний: <b>{stats.get('unique_companies', 0)}</b>\n"
        f"📅 За последнюю неделю: <b>{stats.get('last_week', 0)}</b>\n\n"
        f"👤 Статус: {'✅ Активен' if stats.get('is_active') else '❌ Неактивен'}\n"
        f"🛡 Администратор: {'✅ Да' if stats.get('is_admin') else '❌ Нет'}",
        reply_markup=main_keyboard
    )


@router.message(Command("history"))
async def cmd_history(message: Message, state: FSMContext):
    """Обработчик команды /history - история запросов"""
    await state.clear()

    reports = await report_crud.get_user_reports(
        user_id=message.from_user.id,
        limit=10
    )

    if not reports:
        await message.answer(
            "📭 У вас пока нет запросов.\n\n"
            "Отправьте ИНН для получения первого отчета!",
            reply_markup=main_keyboard
        )
        return

    text = "📚 <b>Ваша история запросов:</b>\n\n"
    for i, report in enumerate(reports, 1):
        company = report.company_name or "Неизвестно"
        date = report.created_at.strftime('%d.%m.%Y %H:%M')
        risk_emoji = "🟢" if report.risk_level == "Низкий" else "🟡" if report.risk_level == "Средний" else "🔴"
        text += f"{i}. {company}\n"
        text += f"   ИНН: <code>{report.inn}</code>\n"
        text += f"   📅 {date} | {risk_emoji} {report.risk_level or 'Н/Д'}\n\n"

    await message.answer(
        text,
        reply_markup=main_keyboard
    )


@router.message(F.text == "📊 Моя статистика")
async def btn_stats(message: Message, state: FSMContext):
    """Кнопка статистики"""
    await cmd_stats(message, state)


@router.message(F.text == "📚 История")
async def btn_history(message: Message, state: FSMContext):
    """Кнопка истории"""
    await cmd_history(message, state)


@router.message(F.text == "❓ Помощь")
async def btn_help(message: Message, state: FSMContext):
    """Кнопка помощи"""
    await cmd_help(message, state)


@router.message(F.text == "ℹ️ О боте")
async def btn_about(message: Message, state: FSMContext):
    """Кнопка 'О боте'"""
    await state.clear()

    await message.answer(
        "ℹ️ <b>О боте Report_3</b>\n\n"
        "🤖 <b>Версия:</b> 1.0.0\n"
        "📅 <b>Разработан:</b> 2024\n\n"
        "🔧 <b>Технологии:</b>\n"
        "• Python 3.11+\n"
        "• Aiogram 3.x\n"
        "• PostgreSQL 15+\n"
        "• SQLAlchemy 2.x\n"
        "• IO_NET AI\n\n"
        "📊 <b>Функции:</b>\n"
        "• Анализ финансовой отчетности\n"
        "• ИИ-анализ финансовых показателей\n"
        "• Генерация HTML-отчетов\n"
        "• Сохранение истории запросов\n\n"
        "💡 <b>Идеи для улучшения:</b>\n"
        "• Сравнение компаний\n"
        "• Графики и диаграммы\n"
        "• PDF-отчеты",
        reply_markup=main_keyboard
    )


@router.message(F.text == "❌ Отмена")
async def btn_cancel(message: Message, state: FSMContext):
    """Кнопка отмены"""
    await state.clear()
    await message.answer(
        "✅ Действие отменено",
        reply_markup=main_keyboard
    )


# ============================================
# ОБРАБОТКА ИНН
# ============================================

@router.message(StateFilter(default_state), F.text)
async def handle_inn(message: Message, state: FSMContext):
    """Обработка текстовых сообщений (ИНН)"""
    inn = message.text.strip()

    # Валидация ИНН
    if not validate_inn(inn):
        await message.answer(
            "❌ <b>Неверный ИНН</b>\n\n"
            "ИНН должен содержать 10 или 12 цифр.\n"
            "Пример: 7707083893"
        )
        return

    user_id = message.from_user.id

    # Увеличиваем счетчик запросов
    await user_crud.increment_requests(user_id)

    # Отправляем статус
    status_msg = await message.answer(
        "🔍 <i>Получаю данные из ФНС...</i>\n"
        "⏳ Обычно это занимает 10-30 секунд",
        reply_markup=get_cancel_keyboard()
    )

    try:
        # 1. Проверяем кеш
        cache_key = f"fns:{inn}"
        cached_data = await cache_crud.get_cache(cache_key)

        if cached_data:
            logger.info(f"Данные для ИНН {inn} получены из кеша")
            financial_data = cached_data
        else:
            # 2. Получение данных из ФНС
            financial_data = await fns_client.get_financial_report(inn)
            # Сохраняем в кеш на 24 часа
            await cache_crud.set_cache(
                cache_key=cache_key,
                cache_type="fns",
                data=financial_data,
                expires_in_seconds=86400,  # 24 часа
                inn=inn
            )

        await status_msg.edit_text(
            "🧠 <i>Анализирую данные с помощью AI...</i>\n"
            "⏳ Это может занять несколько секунд"
        )

        # 3. Анализ через IO_NET
        analysis = await ionet_client.analyze_financial_data(financial_data)

        await status_msg.edit_text(
            "📄 <i>Генерирую HTML-отчет...</i>"
        )

        # 4. Генерация HTML
        html_path, html_content = await report_generator.generate_report(
            inn=inn,
            financial_data=financial_data,
            analysis=analysis
        )

        # 5. Сохранение в БД
        report = await report_crud.create_report(
            user_id=user_id,
            inn=inn,
            html_content=html_content,
            analysis_summary=analysis.get('summary', ''),
            company_name=financial_data.get('company_name'),
            ogrn=financial_data.get('ogrn'),
            period=financial_data.get('period'),
            risk_level=analysis.get('risk_level'),
            revenue=financial_data.get('profit_loss', {}).get('revenue'),
            profit=financial_data.get('profit_loss', {}).get('profit'),
            assets=financial_data.get('balance', {}).get('assets')
        )

        # 6. Отправка отчета
        await status_msg.delete()

        document = FSInputFile(
            path=html_path,
            filename=f"report_{inn}_{datetime.now().strftime('%Y%m%d')}.html"
        )

        risk_emoji = "🟢" if analysis.get('risk_level') == "Низкий" else "🟡" if analysis.get(
            'risk_level') == "Средний" else "🔴"

        await message.answer_document(
            document,
            caption=(
                f"✅ <b>Отчет готов!</b>\n\n"
                f"🏢 {financial_data.get('company_name', 'Неизвестно')}\n"
                f"📋 ИНН: <code>{inn}</code>\n"
                f"📅 Период: {financial_data.get('period', 'Н/Д')}\n"
                f"{risk_emoji} Риск: {analysis.get('risk_level', 'Н/Д')}\n\n"
                f"💾 Отчет сохранен в истории"
            ),
            reply_markup=get_report_actions_keyboard(report.id)
        )

        # 7. Отправка краткой выжимки
        summary = analysis.get('summary', '')
        if len(summary) > 500:
            summary = summary[:500] + "..."

        await message.answer(
            f"📊 <b>Краткий анализ:</b>\n\n{summary}",
            reply_markup=main_keyboard
        )

        logger.info(f"Отчет для ИНН {inn} успешно создан пользователем {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке ИНН {inn}: {e}")
        await status_msg.edit_text(
            f"❌ <b>Произошла ошибка:</b>\n\n{str(e)}\n\n"
            "Попробуйте позже или обратитесь к администратору."
        )

    await state.clear()


# ============================================
# ОБРАБОТКА CALLBACK
# ============================================

@router.callback_query(F.data.startswith("download_report:"))
async def callback_download_report(callback: CallbackQuery):
    """Скачивание отчета"""
    report_id = int(callback.data.split(":")[1])

    report = await report_crud.get_by_id(report_id)
    if not report:
        await callback.answer("❌ Отчет не найден", show_alert=True)
        return

    # Проверяем, что отчет принадлежит пользователю
    if report.user_id != callback.from_user.id:
        await callback.answer("❌ У вас нет доступа к этому отчету", show_alert=True)
        return

    # Создаем временный файл
    temp_path = f"/tmp/report_{report_id}.html"
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(report.html_content)

    document = FSInputFile(
        path=temp_path,
        filename=f"report_{report.inn}_{report.created_at.strftime('%Y%m%d')}.html"
    )

    await callback.message.answer_document(
        document,
        caption=f"📄 Отчет для ИНН: <code>{report.inn}</code>"
    )

    # Удаляем временный файл
    try:
        os.remove(temp_path)
    except:
        pass

    await callback.answer("✅ Отчет отправлен")


@router.callback_query(F.data.startswith("delete_report:"))
async def callback_delete_report(callback: CallbackQuery):
    """Удаление отчета"""
    report_id = int(callback.data.split(":")[1])

    report = await report_crud.get_by_id(report_id)
    if not report:
        await callback.answer("❌ Отчет не найден", show_alert=True)
        return

    # Проверяем, что отчет принадлежит пользователю
    if report.user_id != callback.from_user.id:
        await callback.answer("❌ У вас нет доступа к этому отчету", show_alert=True)
        return

    # Удаляем
    await report_crud.delete(report_id)

    await callback.message.edit_caption(
        caption=f"🗑 Отчет для ИНН <code>{report.inn}</code> удален",
        reply_markup=None
    )

    await callback.answer("✅ Отчет удален")


@router.callback_query(F.data == "history_refresh")
async def callback_history_refresh(callback: CallbackQuery):
    """Обновление истории"""
    await cmd_history(callback.message, None)
    await callback.answer("✅ История обновлена")


@router.message()
async def handle_unknown(message: Message, state: FSMContext):
    """Обработка неизвестных сообщений"""
    await state.clear()
    await message.answer(
        "❓ Я не понимаю эту команду.\n\n"
        "Пожалуйста, отправьте ИНН (10 или 12 цифр)\n"
        "или используйте /help для справки.",
        reply_markup=main_keyboard
    )