# app/bot/states.py

"""
Состояния FSM для бота
"""
from aiogram.fsm.state import State, StatesGroup


class ReportStates(StatesGroup):
    """Состояния для процесса генерации отчета"""
    waiting_inn = State()  # Ожидание ввода ИНН
