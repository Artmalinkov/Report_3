# app/utils/validators.py
'''
Валидация ИНН
'''


def validate_inn(inn: str) -> bool:
    """
    Проверка корректности ИНН (10 или 12 цифр)

    Args:
        inn: Строка с ИНН

    Returns:
        True если ИНН валидный, иначе False
    """
    if not inn or not isinstance(inn, str):
        return False

    # Удаляем пробелы и другие символы
    inn = inn.strip()

    # Проверяем длину
    if len(inn) not in [10, 12]:
        return False

    # Проверяем что все символы - цифры
    if not inn.isdigit():
        return False

    # Для 10-значного ИНН
    if len(inn) == 10:
        return validate_inn_10(inn)

    # Для 12-значного ИНН
    if len(inn) == 12:
        return validate_inn_12(inn)

    return False


def validate_inn_10(inn: str) -> bool:
    """
    Проверка контрольной суммы для 10-значного ИНН
    """
    coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    control_sum = sum(int(inn[i]) * coefficients[i] for i in range(9))
    control_digit = control_sum % 11 % 10
    return control_digit == int(inn[9])


def validate_inn_12(inn: str) -> bool:
    """
    Проверка контрольных сумм для 12-значного ИНН
    """
    # Первая контрольная сумма
    coefficients_1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    control_sum_1 = sum(int(inn[i]) * coefficients_1[i] for i in range(10))
    control_digit_1 = control_sum_1 % 11 % 10

    if control_digit_1 != int(inn[10]):
        return False

    # Вторая контрольная сумма
    coefficients_2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    control_sum_2 = sum(int(inn[i]) * coefficients_2[i] for i in range(11))
    control_digit_2 = control_sum_2 % 11 % 10

    return control_digit_2 == int(inn[11])


def format_inn(inn: str) -> str:
    """
    Форматирование ИНН для отображения
    """
    inn = inn.strip()
    if len(inn) == 10:
        return f"{inn[:4]} {inn[4:]}"
    elif len(inn) == 12:
        return f"{inn[:4]} {inn[4:6]} {inn[6:8]} {inn[8:]}"
    return inn
