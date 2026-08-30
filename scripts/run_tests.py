# scripts/run_tests.py
"""
Запуск всех тестов
"""

import sys
import asyncio
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.tests.test_fns_api import TestFNSAPI
from app.tests.test_validators import test_inn_validator
from app.tests.test_ionet_api import TestIONETAPI
from app.tests.test_report_generator import TestReportGenerator
from app.tests.test_integration import TestIntegration
from app.config import settings


async def run_all_tests():
    """Запуск всех тестов"""

    print("\n" + "=" * 70)
    print("🚀 ЗАПУСК ВСЕХ ТЕСТОВ")
    print("=" * 70)
    print(f"📊 Режим: {'DEBUG (мок-данные)' if settings.DEBUG else 'PRODUCTION'}")
    print("=" * 70)

    tests = [
        ("Валидация ИНН", test_inn_validator),
        ("API ФНС", TestFNSAPI().run_tests),
        ("API IO_NET", TestIONETAPI().run_tests),
        ("Генератор отчетов", TestReportGenerator().run_tests),
        ("Интеграционный тест", TestIntegration().run_tests),
    ]

    results = {}

    for name, test_func in tests:
        print("\n" + "=" * 70)
        print(f"📋 ТЕСТ: {name}")
        print("=" * 70)

        try:
            if name == "Валидация ИНН":
                test_func()
                results[name] = "✅ Пройден"
            else:
                await test_func()
                results[name] = "✅ Пройден"
        except Exception as e:
            print(f"\n❌ Ошибка в тесте '{name}': {e}")
            results[name] = f"❌ Ошибка: {e}"

    # Итоги
    print("\n" + "=" * 70)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 70)
    for name, result in results.items():
        print(f"{result} - {name}")
    print("=" * 70)


async def run_test(test_name: str = None):
    """Запуск конкретного теста"""

    tests_map = {
        "validators": ("Валидация ИНН", test_inn_validator),
        "fns": ("API ФНС", TestFNSAPI().run_tests),
        "ionet": ("API IO_NET", TestIONETAPI().run_tests),
        "report": ("Генератор отчетов", TestReportGenerator().run_tests),
        "integration": ("Интеграционный тест", TestIntegration().run_tests),
    }

    if test_name and test_name in tests_map:
        name, test_func = tests_map[test_name]
        print("\n" + "=" * 70)
        print(f"🚀 ЗАПУСК ТЕСТА: {name}")
        print("=" * 70)
        print(f"📊 Режим: {'DEBUG (мок-данные)' if settings.DEBUG else 'PRODUCTION'}")
        print("=" * 70)

        if name == "Валидация ИНН":
            test_func()
        else:
            await test_func()
    else:
        print(f"❌ Тест '{test_name}' не найден")
        print("\nДоступные тесты:")
        for key, (name, _) in tests_map.items():
            print(f"  - {key}: {name}")
        print("  - all: Все тесты")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Запуск тестов Deep Finance Report")
    parser.add_argument(
        "--test",
        type=str,
        choices=["validators", "fns", "ionet", "report", "integration", "all"],
        default="all",
        help="Название теста для запуска"
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Запуск в production режиме (без мок-данных)"
    )

    args = parser.parse_args()

    # Временно меняем DEBUG для production тестов
    if args.prod:
        print("⚠️  Запуск в PRODUCTION режиме (реальные API)")
        settings.DEBUG = False

    try:
        if args.test == "all":
            asyncio.run(run_all_tests())
        else:
            asyncio.run(run_test(args.test))
    except KeyboardInterrupt:
        print("\n👋 Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)

    # Восстанавливаем DEBUG
    settings.DEBUG = True