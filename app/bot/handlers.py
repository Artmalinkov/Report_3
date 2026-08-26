# app/bot/handlers.py

"""
Обработчики команд Telegram бота
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    FSInputFile,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from app.bot.states import ReportStates
from app.bot.keyboards import (
    main_keyboard,
    get_main_keyboard,
    get_report_actions_keyboard,
    get_history_keyboard,
    get_cancel_keyboard,
    quick_actions
)
from app.database.crud import user_crud, report_crud, cache_crud
from app.dashboard.auth import create_login_link
from app.services.fns_client import FNSClient
from app.services.ionet_client import IONETClient
from app.services.report_generator import ReportGenerator
from app.utils.validators import validate_inn, extract_inns
from app.config import settings

# Ограничения для сравнения компаний
MAX_COMPARE_COMPANIES = 5
HISTORY_PAGE_SIZE = 5

# Известные ИНН для тестирования
TEST_INNS = {
    "7707083893": "ПАО Сбербанк",
    "7702070139": "ПАО Газпром",
    "7736207543": "ООО Тестовая Компания",
}

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

    mode_text = "🔧 <b>Режим:</b> РАЗРАБОТКА (мок-данные)\n" if settings.DEBUG else ""

    await message.answer(
        f"🏢 <b>Добро пожаловать в Report_v_4!</b>\n\n"
        f"{mode_text}"
        "Я помогу вам проанализировать финансовую отчетность компании по ИНН.\n\n"
        "📌 <b>Как использовать:</b>\n"
        "Просто отправьте мне ИНН (10 или 12 цифр)\n\n"
        "📋 <b>Команды:</b>\n"
        "/help - Получить справку\n"
        "/history - История запросов\n"
        "/stats - Моя статистика",
        reply_markup=get_main_keyboard(user.is_admin)
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
        "🔀 <b>Сравнение компаний:</b>\n"
        "Отправьте несколько ИНН через запятую или пробел\n"
        "(например: <code>7707083893, 7702070139</code>) — до "
        f"{MAX_COMPARE_COMPANIES} компаний за раз.\n"
        "Также можно отметить компании прямо в /history.\n\n"
        "📊 <b>Команды:</b>\n"
        "/start - Приветствие\n"
        "/help - Эта справка\n"
        "/history - История запросов и выбор для сравнения\n"
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


@router.message(Command("dashboard"))
async def cmd_dashboard(message: Message, state: FSMContext):
    """Обработчик команды /dashboard — одноразовая ссылка для входа в админ-дашборд"""
    await state.clear()

    user = await user_crud.get_by_telegram_id(message.from_user.id)
    if not user or not user.is_admin:
        await message.answer("🚫 Доступ ограничен.", reply_markup=main_keyboard)
        return

    link = await create_login_link(message.from_user.id)
    await message.answer(
        "🔐 <b>Вход в дашборд</b>\n\n"
        f'<a href="{link}">Открыть дашборд</a>\n\n'
        "Ссылка одноразовая и действует 5 минут.",
        reply_markup=main_keyboard
    )


async def _render_history(
        user_id: int,
        state: FSMContext,
        page: int = 0
) -> Optional[Tuple[str, InlineKeyboardMarkup]]:
    """
    Готовит текст и клавиатуру для страницы истории (с чекбоксами выбора
    компаний для сравнения). Возвращает None, если у пользователя вообще
    нет отчетов.
    """
    total = await report_crud.get_user_reports_count(user_id)
    if total == 0:
        return None

    total_pages = max(1, -(-total // HISTORY_PAGE_SIZE))  # деление с округлением вверх
    page = max(0, min(page, total_pages - 1))
    reports = await report_crud.get_user_reports(
        user_id=user_id,
        limit=HISTORY_PAGE_SIZE,
        offset=page * HISTORY_PAGE_SIZE
    )

    data = await state.get_data()
    selected = set(data.get("compare_selection", []))

    text = f"📚 <b>Ваша история запросов</b> (стр. {page + 1}/{total_pages}):\n\n"
    for i, report in enumerate(reports, start=page * HISTORY_PAGE_SIZE + 1):
        company = report.company_name or "Неизвестно"
        date = report.created_at.strftime('%d.%m.%Y %H:%M')
        risk_emoji = "🟢" if report.risk_level == "Низкий" else "🟡" if report.risk_level == "Средний" else "🔴"
        text += f"{i}. {company}\n"
        text += f"   ИНН: <code>{report.inn}</code>\n"
        text += f"   📅 {date} | {risk_emoji} {report.risk_level or 'Н/Д'}\n\n"

    text += (
        f"☑️ Выбрано для сравнения: {len(selected)}\n\n" if selected else "\n"
    )
    text += "Отметьте компании ниже, чтобы сравнить их между собой (нужно минимум 2)."

    keyboard = get_history_keyboard(reports, selected, page, total_pages)
    return text, keyboard


@router.message(Command("history"))
async def cmd_history(message: Message, state: FSMContext):
    """Обработчик команды /history - история запросов"""
    await state.clear()  # свежий вход в историю сбрасывает и FSM, и выбор для сравнения

    rendered = await _render_history(message.from_user.id, state, page=0)
    if not rendered:
        await message.answer(
            "📭 У вас пока нет запросов.\n\n"
            "Отправьте ИНН для получения первого отчета!",
            reply_markup=main_keyboard
        )
        return

    text, keyboard = rendered
    await message.answer(text, reply_markup=keyboard)


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
        "ℹ️ <b>О боте Report_v_4</b>\n\n"
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
        "• Сравнение нескольких компаний\n"
        "• Генерация HTML-отчетов\n"
        "• Сохранение истории запросов\n\n"
        "💡 <b>Идеи для улучшения:</b>\n"
        "• Графики и диаграммы\n"
        "• PDF-отчеты",
        reply_markup=main_keyboard
    )


@router.message(F.text == "🖥 Дашборд")
async def btn_dashboard(message: Message, state: FSMContext):
    """Кнопка дашборда (видна только администраторам)"""
    await cmd_dashboard(message, state)


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

async def _fetch_financial_data(inn: str) -> Dict[str, Any]:
    """
    Получение финансовых данных по ИНН с проверкой кеша (24 часа).
    Общая логика для одиночного отчета и для сравнения компаний.
    """
    cache_key = f"fns:{inn}"
    cached_data = await cache_crud.get_cache(cache_key)

    if cached_data:
        logger.info(f"Данные для ИНН {inn} получены из кеша")
        return cached_data

    financial_data = await fns_client.get_financial_report(inn)
    await cache_crud.set_cache(
        cache_key=cache_key,
        cache_type="fns",
        data=financial_data,
        expires_in_seconds=86400,  # 24 часа
        inn=inn
    )
    return financial_data


async def check_rate_limit(user_id: int, weight: int = 1) -> Optional[str]:
    """
    Проверяет, можно ли пользователю выполнить запрос к платным API
    (ФНС, IO_NET), и если да — сразу его регистрирует (обновляет
    last_request_at/total_requests и дневной счетчик), чтобы проверка и
    учет не расходились. Возвращает текст отказа, если запрос нужно
    отклонить, иначе None.

    weight — во сколько "запросов" засчитывать обращение в дневном лимите:
    сравнение нескольких компаний тратит API кратно числу компаний, а не
    как один обычный запрос.
    """
    user = await user_crud.get_by_telegram_id(user_id)

    if user and user.is_banned:
        return "🚫 Доступ ограничен администратором."

    if user and user.last_request_at:
        elapsed = (datetime.utcnow() - user.last_request_at).total_seconds()
        if elapsed < settings.RATE_LIMIT_COOLDOWN_SECONDS:
            wait = int(settings.RATE_LIMIT_COOLDOWN_SECONDS - elapsed) + 1
            return f"⏳ Слишком много запросов подряд. Подождите {wait} сек. и попробуйте снова."

    today = datetime.utcnow().strftime("%Y-%m-%d")
    cache_key = f"ratelimit:{user_id}:{today}"
    cached = await cache_crud.get_cache(cache_key)
    used = int(cached.get("count", 0)) if cached else 0

    if used + weight > settings.RATE_LIMIT_DAILY_MAX:
        return (
            f"📛 Достигнут дневной лимит запросов ({settings.RATE_LIMIT_DAILY_MAX} в сутки). "
            "Попробуйте завтра."
        )

    await user_crud.increment_requests(user_id)
    await cache_crud.set_cache(
        cache_key=cache_key,
        cache_type="ratelimit",
        data={"count": used + weight},
        expires_in_seconds=90000,  # чуть больше суток — ключ сам "сгорает" на следующий день
    )
    return None


@router.message(StateFilter(default_state), F.text)
async def handle_inn(message: Message, state: FSMContext):
    """Обработка текстовых сообщений (ИНН или несколько ИНН для сравнения)"""
    text = message.text.strip()

    # Несколько ИНН в одном сообщении (через запятую/пробел/перенос строки) -
    # запрос на сравнение компаний
    inns = extract_inns(text)
    if len(inns) >= 2:
        await run_comparison(message, state, message.from_user.id, inns)
        return

    inn = text

    # Валидация ИНН
    if not validate_inn(inn):
        await message.answer(
            "❌ <b>Неверный ИНН</b>\n\n"
            "ИНН должен содержать 10 или 12 цифр.\n"
            "Пример: 7707083893\n\n"
            "Чтобы сравнить несколько компаний, отправьте их ИНН через запятую\n"
            "или пробел, например: <code>7707083893, 7702070139</code>\n\n"
            "📋 <b>Тестовые ИНН:</b>\n"
            "• 7707083893 - Сбербанк\n"
            "• 7702070139 - Газпром\n"
            "• 7736207543 - Тестовая"
        )
        return

    user_id = message.from_user.id

    rate_limit_error = await check_rate_limit(user_id)
    if rate_limit_error:
        await message.answer(rate_limit_error, reply_markup=main_keyboard)
        return

    # Отправляем статус
    status_msg = await message.answer(
        "🔍 <i>Получаю данные ФНС...</i>\n"
        "⏳ Обычно это занимает 10-30 секунд",
        reply_markup=get_cancel_keyboard()
    )

    try:
        financial_data = await _fetch_financial_data(inn)

        # Пытаемся обновить сообщение, если оно еще существует
        try:
            await status_msg.edit_text(
                "🧠 <i>Анализирую данные с помощью AI...</i>\n"
                "⏳ Это может занять несколько секунд"
            )
        except Exception:
            # Если не удалось отредактировать, отправляем новое
            status_msg = await message.answer(
                "🧠 <i>Анализирую данные с помощью AI...</i>\n"
                "⏳ Это может занять несколько секунд"
            )

        # 3. Анализ через IO_NET
        analysis = await ionet_client.analyze_financial_data(financial_data)

        try:
            await status_msg.edit_text(
                "📄 <i>Генерирую HTML-отчет...</i>"
            )
        except Exception:
            status_msg = await message.answer(
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
        try:
            await status_msg.delete()
        except Exception:
            pass  # Игнорируем ошибку удаления

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
                f"📅 Период: {report_generator.format_period_range(financial_data)}\n"
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

    except ValueError as e:
        # Ошибка валидации (компания не найдена)
        logger.error(f"Ошибка валидации для ИНН {inn}: {e}")
        try:
            await status_msg.delete()
        except Exception:
            pass
        await message.answer(
            f"❌ <b>Компания не найдена</b>\n\n"
            f"Проверьте правильность ИНН: <code>{inn}</code>\n"
            f"Возможно, компания не существует или данные отсутствуют в ФНС.",
            reply_markup=main_keyboard
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке ИНН {inn}: {e}")
        try:
            await status_msg.edit_text(
                f"❌ <b>Произошла ошибка:</b>\n\n{str(e)}\n\n"
                "Попробуйте позже или обратитесь к администратору."
            )
        except Exception:
            await message.answer(
                f"❌ <b>Произошла ошибка:</b>\n\n{str(e)}\n\n"
                "Попробуйте позже или обратитесь к администратору.",
                reply_markup=main_keyboard
            )

    await state.clear()


# ============================================
# СРАВНЕНИЕ КОМПАНИЙ
# ============================================

async def run_comparison(message: Message, state: FSMContext, user_id: int, inns: List[str]):
    """
    Сравнение нескольких компаний: получение данных по каждому ИНН,
    сравнительный AI-анализ и единый HTML-отчет. Используется и из
    текстового ввода (несколько ИНН в одном сообщении), и из выбора
    компаний в /history.

    user_id передается явно, а не берется из message.from_user: при вызове
    из callback-обработчика message — это сообщение бота (с историей), и
    message.from_user там оказался бы самим ботом, а не человеком, нажавшим
    кнопку.
    """
    if len(inns) > MAX_COMPARE_COMPANIES:
        await message.answer(
            f"ℹ️ Указано {len(inns)} ИНН, для сравнения беру первые {MAX_COMPARE_COMPANIES}."
        )
        inns = inns[:MAX_COMPARE_COMPANIES]

    valid_inns = [inn for inn in inns if validate_inn(inn)]
    invalid_inns = [inn for inn in inns if inn not in valid_inns]

    if invalid_inns:
        await message.answer(
            "⚠️ Пропущены некорректные ИНН: " + ", ".join(f"<code>{i}</code>" for i in invalid_inns)
        )

    if len(valid_inns) < 2:
        await message.answer(
            "❌ <b>Недостаточно компаний для сравнения</b>\n\n"
            "Нужно минимум 2 корректных ИНН.",
            reply_markup=main_keyboard
        )
        return

    rate_limit_error = await check_rate_limit(user_id, weight=len(valid_inns))
    if rate_limit_error:
        await message.answer(rate_limit_error, reply_markup=main_keyboard)
        return

    status_msg = await message.answer(
        f"🔍 <i>Получаю данные ФНС по {len(valid_inns)} компаниям...</i>\n"
        "⏳ Это может занять до минуты",
        reply_markup=get_cancel_keyboard()
    )

    companies: List[Dict[str, Any]] = []
    failed: List[str] = []

    for inn in valid_inns:
        try:
            companies.append(await _fetch_financial_data(inn))
        except ValueError:
            failed.append(f"{inn} — компания не найдена в ФНС")
        except Exception as e:
            logger.error(f"Ошибка при получении данных для сравнения (ИНН {inn}): {e}")
            failed.append(f"{inn} — ошибка получения данных")

    if len(companies) < 2:
        try:
            await status_msg.delete()
        except Exception:
            pass
        text = "❌ <b>Не удалось собрать данные для сравнения</b>\n\n"
        if failed:
            text += "\n".join(failed)
        await message.answer(text, reply_markup=main_keyboard)
        return

    try:
        try:
            await status_msg.edit_text("🧠 <i>Сравниваю компании с помощью AI...</i>")
        except Exception:
            status_msg = await message.answer("🧠 <i>Сравниваю компании с помощью AI...</i>")

        comparison = await ionet_client.analyze_comparison(companies)

        try:
            await status_msg.edit_text("📄 <i>Формирую сравнительный отчет...</i>")
        except Exception:
            status_msg = await message.answer("📄 <i>Формирую сравнительный отчет...</i>")

        html_path, html_content = await report_generator.generate_comparison_report(
            companies=companies,
            comparison=comparison
        )

        # Сравнительные отчеты не хранятся в БД (нет report_id для кнопки
        # "Скачать PDF" позднее), поэтому PDF рендерится сразу и отправляется
        # вторым файлом рядом с HTML
        pdf_bytes = None
        try:
            pdf_bytes = await report_generator.render_pdf(html_content)
        except Exception as e:
            logger.warning(f"Не удалось сформировать PDF для сравнения: {e}")

        try:
            await status_msg.delete()
        except Exception:
            pass

        names = ", ".join(c.get("company_name", "?") for c in companies)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        document = FSInputFile(
            path=html_path,
            filename=f"comparison_{timestamp}.html"
        )

        caption = f"✅ <b>Сравнение готово!</b>\n\n🏢 {names}\n\n"
        if failed:
            caption += "⚠️ Не удалось получить: " + "; ".join(failed) + "\n\n"
        caption += "💾 Полный текст сравнения — в отчете и следующем сообщении"

        await message.answer_document(document, caption=caption, reply_markup=main_keyboard)

        if pdf_bytes:
            await message.answer_document(
                BufferedInputFile(pdf_bytes, filename=f"comparison_{timestamp}.pdf"),
                caption="📑 Тот же отчет в PDF",
                reply_markup=main_keyboard
            )

        leader = comparison.get("leader", "")
        summary = comparison.get("summary", "")
        await message.answer(
            f"📊 <b>Итог сравнения:</b>\n\n{summary}\n\n🏆 <b>Лидер:</b> {leader}",
            reply_markup=main_keyboard
        )

        logger.info(f"Сравнительный отчет для {[c.get('inn') for c in companies]} создан пользователем {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при сравнении компаний {valid_inns}: {e}")
        try:
            await status_msg.edit_text(
                f"❌ <b>Произошла ошибка при сравнении:</b>\n\n{str(e)}"
            )
        except Exception:
            await message.answer(
                f"❌ <b>Произошла ошибка при сравнении:</b>\n\n{str(e)}",
                reply_markup=main_keyboard
            )

    finally:
        await state.update_data(compare_selection=[])
        await state.set_state(None)


# ============================================
# ОБРАБОТКА CALLBACK
# ============================================

@router.callback_query(F.data.startswith("download_report:"))
async def callback_download_report(callback: CallbackQuery):
    """Скачивание отчета (HTML)"""
    report_id = int(callback.data.split(":")[1])

    report = await report_crud.get_by_id(report_id)
    if not report:
        await callback.answer("❌ Отчет не найден", show_alert=True)
        return

    # Проверяем, что отчет принадлежит пользователю
    if report.user_id != callback.from_user.id:
        await callback.answer("❌ У вас нет доступа к этому отчету", show_alert=True)
        return

    document = BufferedInputFile(
        report.html_content.encode('utf-8'),
        filename=f"report_{report.inn}_{report.created_at.strftime('%Y%m%d')}.html"
    )

    await callback.message.answer_document(
        document,
        caption=f"📄 Отчет для ИНН: <code>{report.inn}</code>"
    )

    await callback.answer("✅ Отчет отправлен")


@router.callback_query(F.data.startswith("download_pdf:"))
async def callback_download_pdf(callback: CallbackQuery):
    """Скачивание отчета в PDF (рендерится по запросу через headless Chromium)"""
    report_id = int(callback.data.split(":")[1])

    report = await report_crud.get_by_id(report_id)
    if not report:
        await callback.answer("❌ Отчет не найден", show_alert=True)
        return

    if report.user_id != callback.from_user.id:
        await callback.answer("❌ У вас нет доступа к этому отчету", show_alert=True)
        return

    await callback.answer("⏳ Готовлю PDF...")

    try:
        pdf_bytes = await report_generator.render_pdf(report.html_content)
    except Exception as e:
        logger.error(f"Ошибка при рендеринге PDF для отчета {report_id}: {e}")
        await callback.message.answer("❌ Не удалось сформировать PDF, попробуйте позже")
        return

    document = BufferedInputFile(
        pdf_bytes,
        filename=f"report_{report.inn}_{report.created_at.strftime('%Y%m%d')}.pdf"
    )

    await callback.message.answer_document(
        document,
        caption=f"📑 Отчет (PDF) для ИНН: <code>{report.inn}</code>"
    )


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


async def _update_history_message(callback: CallbackQuery, state: FSMContext, page: int):
    """Перерисовывает сообщение с историей на месте (без спама новыми сообщениями)"""
    rendered = await _render_history(callback.from_user.id, state, page)
    if not rendered:
        await callback.message.edit_text(
            "📭 У вас пока нет запросов.\n\nОтправьте ИНН для получения первого отчета!"
        )
        return
    text, keyboard = rendered
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass  # текст не изменился — Telegram не даст отредактировать тем же содержимым


@router.callback_query(F.data.startswith("history_page:"))
async def callback_history_page(callback: CallbackQuery, state: FSMContext):
    """Переход на другую страницу истории"""
    page = int(callback.data.split(":")[1])
    await _update_history_message(callback, state, page)
    await callback.answer()


@router.callback_query(F.data.startswith("history_refresh:"))
async def callback_history_refresh(callback: CallbackQuery, state: FSMContext):
    """Обновление текущей страницы истории"""
    page = int(callback.data.split(":")[1])
    await _update_history_message(callback, state, page)
    await callback.answer("✅ История обновлена")


@router.callback_query(F.data.startswith("toggle_compare:"))
async def callback_toggle_compare(callback: CallbackQuery, state: FSMContext):
    """Отметить/снять компанию для сравнения"""
    _, inn, page = callback.data.split(":")
    page = int(page)

    data = await state.get_data()
    selected = set(data.get("compare_selection", []))
    if inn in selected:
        selected.discard(inn)
    else:
        if len(selected) >= MAX_COMPARE_COMPANIES:
            await callback.answer(
                f"Максимум {MAX_COMPARE_COMPANIES} компаний для сравнения", show_alert=True
            )
            return
        selected.add(inn)
    await state.update_data(compare_selection=list(selected))

    await _update_history_message(callback, state, page)
    await callback.answer()


@router.callback_query(F.data == "clear_compare")
async def callback_clear_compare(callback: CallbackQuery, state: FSMContext):
    """Сбросить выбор компаний для сравнения"""
    await state.update_data(compare_selection=[])
    await _update_history_message(callback, state, page=0)
    await callback.answer("Выбор сброшен")


@router.callback_query(F.data == "run_compare")
async def callback_run_compare(callback: CallbackQuery, state: FSMContext):
    """Запуск сравнения выбранных в истории компаний"""
    data = await state.get_data()
    selected = list(data.get("compare_selection", []))

    if len(selected) < 2:
        await callback.answer("Выберите минимум 2 компании", show_alert=True)
        return

    await callback.answer()
    await run_comparison(callback.message, state, callback.from_user.id, selected)


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