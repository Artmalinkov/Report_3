# app/bot/keyboards.py

"""
Клавиатуры для бота
"""
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Основная клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📊 Моя статистика"),
            KeyboardButton(text="📚 История")
        ],
        [
            KeyboardButton(text="❓ Помощь"),
            KeyboardButton(text="ℹ️ О боте")
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)


def get_report_actions_keyboard(report_id: int) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура для действий с отчетом"""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📄 Скачать отчет",
        callback_data=f"download_report:{report_id}"
    )
    builder.button(
        text="🔄 Повторить анализ",
        callback_data=f"repeat_analysis:{report_id}"
    )
    builder.button(
        text="🗑 Удалить отчет",
        callback_data=f"delete_report:{report_id}"
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def get_history_keyboard(
        reports,
        selected_inns: set,
        page: int = 0,
        total_pages: int = 1
) -> InlineKeyboardMarkup:
    """
    Клавиатура истории: пагинация + отметка компаний для сравнения.
    По кнопке-строке на каждый отчет (чекбокс + название), затем навигация
    и, если что-то выбрано, кнопки запуска/сброса сравнения.
    """
    builder = InlineKeyboardBuilder()

    for report in reports:
        checked = "✅" if report.inn in selected_inns else "⬜"
        label = f"{checked} {report.company_name or report.inn}"
        builder.row(InlineKeyboardButton(
            text=label[:60],
            callback_data=f"toggle_compare:{report.inn}:{page}"
        ))

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"history_page:{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"history_page:{page + 1}"))
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data=f"history_refresh:{page}"))

    if selected_inns:
        builder.row(InlineKeyboardButton(
            text=f"🔀 Сравнить выбранные ({len(selected_inns)})",
            callback_data="run_compare"
        ))
        builder.row(InlineKeyboardButton(text="❌ Сбросить выбор", callback_data="clear_compare"))

    return builder.as_markup()


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )


# Кнопки для быстрых действий
quick_actions = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="📚 История", callback_data="history")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ]
)
