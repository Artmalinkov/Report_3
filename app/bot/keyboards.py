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


def get_history_keyboard(page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    """Клавиатура для пагинации истории"""
    builder = InlineKeyboardBuilder()

    if page > 0:
        builder.button(text="◀️ Назад", callback_data=f"history_page:{page - 1}")
    if page < total_pages - 1:
        builder.button(text="Вперед ▶️", callback_data=f"history_page:{page + 1}")

    builder.button(text="🔄 Обновить", callback_data="history_refresh")
    builder.adjust(2, 1)
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
