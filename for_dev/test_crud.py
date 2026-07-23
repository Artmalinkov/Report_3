# for_dev/test_crud.py

"""
Тестирование CRUD операций
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from app.database.crud import user_crud, report_crud, cache_crud


async def test_user_crud():
    """Тестирование CRUD пользователей"""
    print("=" * 50)
    print("🧪 Тестирование User CRUD")
    print("=" * 50)

    # Создание пользователя
    user = await user_crud.create_or_update(
        telegram_id=123456789,
        username="test_user",
        first_name="Тест",
        last_name="Пользователь"
    )
    print(f"✅ Создан пользователь: {user.username} (ID: {user.id})")

    # Получение пользователя
    user2 = await user_crud.get_by_telegram_id(123456789)
    print(f"✅ Получен пользователь: {user2.username}")

    # Увеличение счетчика
    await user_crud.increment_requests(123456789)
    user3 = await user_crud.get_by_telegram_id(123456789)
    print(f"✅ Счетчик запросов: {user3.total_requests}")

    # Статистика
    stats = await user_crud.get_statistics(123456789)
    print(f"✅ Статистика: {stats}")


async def test_report_crud():
    """Тестирование CRUD отчетов"""
    print("\n" + "=" * 50)
    print("🧪 Тестирование Report CRUD")
    print("=" * 50)

    # Создание отчета
    report = await report_crud.create_report(
        user_id=123456789,
        inn="7707083893",
        html_content="<html><body>Test Report</body></html>",
        analysis_summary="Тестовый анализ",
        company_name="Тестовая компания",
        risk_level="Низкий"
    )
    print(f"✅ Создан отчет: ID {report.id}, ИНН {report.inn}")

    # Получение отчетов пользователя
    reports = await report_crud.get_user_reports(123456789)
    print(f"✅ Отчетов пользователя: {len(reports)}")

    # Статистика
    stats = await report_crud.get_statistics(123456789)
    print(f"✅ Статистика: {stats}")


async def test_cache_crud():
    """Тестирование CRUD кеша"""
    print("\n" + "=" * 50)
    print("🧪 Тестирование Cache CRUD")
    print("=" * 50)

    # Сохранение в кеш
    await cache_crud.set_cache(
        cache_key="test_key",
        cache_type="test",
        data={"test": "data", "number": 123},
        expires_in_seconds=60
    )
    print("✅ Данные сохранены в кеш")

    # Получение из кеша
    data = await cache_crud.get_cache("test_key")
    print(f"✅ Данные из кеша: {data}")

    # Статистика кеша
    stats = await cache_crud.get_stats()
    print(f"✅ Статистика кеша: {stats}")


async def main():
    """Запуск всех тестов"""
    try:
        await test_user_crud()
        await test_report_crud()
        await test_cache_crud()
        print("\n" + "=" * 50)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())