# app/tests/test_validators.py
"""
Тестирование валидаторов
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.utils.validators import validate_inn, format_inn


def test_inn_validator():
    """Тест валидации ИНН"""

    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ВАЛИДАЦИИ ИНН")
    print("=" * 60)

    test_cases = [
        # (ИНН, ожидаемый результат, описание)
        ("7707083893", True, "Сбербанк (10 цифр)"),
        ("7702070139", True, "Газпром (10 цифр)"),
        ("7736207543", True, "Тестовая (10 цифр)"),
        ("1234567890", False, "Невалидный 10-значный"),
        ("123456789012", False, "Невалидный 12-значный"),
        ("77070838931", False, "11 цифр (неправильная длина)"),
        ("770708389a", False, "Содержит букву"),
        ("", False, "Пустая строка"),
        ("  7707083893  ", True, "С пробелами"),
    ]

    passed = 0
    failed = 0

    for inn, expected, description in test_cases:
        result = validate_inn(inn)
        status = "✅" if result == expected else "❌"

        if result == expected:
            passed += 1
        else:
            failed += 1

        formatted = format_inn(inn) if result else "Н/Д"
        print(f"{status} {description}")
        print(f"   ИНН: '{inn}' -> Валидный: {result} (ожидалось: {expected})")
        print(f"   Формат: {formatted}")
        print()

        assert result == expected, f"{description}: ожидалось {expected}, получено {result}"

    print("=" * 60)
    print(f"📊 ИТОГИ: ✅ {passed} пройдено, ❌ {failed} не пройдено")
    print("=" * 60)


if __name__ == "__main__":
    test_inn_validator()