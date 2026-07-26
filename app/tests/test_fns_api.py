# app/tests/test_fns_api.py
"""
Тестирование API ФНС
"""

import asyncio
import sys
from pathlib import Path
import json
from typing import Dict, Any

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.fns_client import FNSClient
from app.config import settings
from loguru import logger


class TestFNSAPI:
    """Тестирование API ФНС"""

    def __init__(self):
        self.client = None
        self.results = {}

    async def setup(self):
        """Инициализация клиента"""
        self.client = FNSClient()

    async def teardown(self):
        """Закрытие клиента"""
        if self.client:
            await self.client.close()

    async def test_get_company_info(self, inn: str) -> Dict[str, Any]:
        """
        Тест получения информации о компании по ИНН
        """
        print(f"\n🔍 Тестирование ИНН: {inn}")
        print("-" * 40)

        try:
            data = await self.client.get_financial_report(inn)

            # Проверяем структуру данных
            assert data.get('inn') == inn, "ИНН не совпадает"
            assert data.get('company_name'), "Отсутствует название компании"

            print(f"✅ Данные получены успешно!")
            print(f"   Компания: {data.get('company_name')}")
            print(f"   ОГРН: {data.get('ogrn')}")
            print(f"   Период: {data.get('period')}")
            print(f"   Статус: {data.get('status')}")

            # Показываем финансовые данные
            balance = data.get('balance', {})
            profit_loss = data.get('profit_loss', {})

            if balance:
                print(f"\n   📊 Баланс:")
                print(f"      Активы: {balance.get('assets', '0')}")
                print(f"      Капитал: {balance.get('capital', '0')}")

            if profit_loss:
                print(f"\n   📈 Прибыли и убытки:")
                print(f"      Выручка: {profit_loss.get('revenue', '0')}")
                print(f"      Прибыль: {profit_loss.get('profit', '0')}")

            return {
                "success": True,
                "inn": inn,
                "company": data.get('company_name'),
                "data": data
            }

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return {
                "success": False,
                "inn": inn,
                "error": str(e)
            }

    async def run_tests(self, inns: list = None):
        """
        Запуск всех тестов
        """
        if inns is None:
            inns = [
                "7707083893",  # Сбербанк
                "7702070139",  # Газпром
                "7736207543",  # Тестовая (может не существовать)
            ]

        await self.setup()

        print("=" * 60)
        print("🧪 ТЕСТИРОВАНИЕ API ФНС")
        print("=" * 60)
        print(f"📊 Режим: {'DEBUG (мок-данные)' if settings.DEBUG else 'PRODUCTION (реальный API)'}")
        print(
            f"🔑 API Key: {settings.FNS_API_KEY[:10]}...{settings.FNS_API_KEY[-4:] if len(settings.FNS_API_KEY) > 14 else '***'}")
        print("=" * 60)

        for inn in inns:
            result = await self.test_get_company_info(inn)
            self.results[inn] = result

        await self.teardown()
        self.print_summary()

    def print_summary(self):
        """Вывод итогов тестирования"""
        print("\n" + "=" * 60)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 60)

        success_count = sum(1 for r in self.results.values() if r["success"])
        total_count = len(self.results)

        for inn, result in self.results.items():
            status = "✅" if result["success"] else "❌"
            company = result.get("company", result.get("error", "Ошибка"))
            print(f"{status} ИНН {inn}: {company}")

        print(f"\n📈 Успешно: {success_count}/{total_count}")
        print("=" * 60)

    def save_results(self, filename: str = "fns_test_result.json"):
        """Сохранение результатов в файл"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n📁 Результат сохранен в {filename}")


async def test_without_mock():
    """Тестирование API ФНС без мок-данных"""

    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ API ФНС (БЕЗ МОК-ДАННЫХ)")
    print("=" * 60)
    print("⚠️  ВНИМАНИЕ: Временно отключаем мок-данные для теста")
    print("=" * 60)

    # Сохраняем текущее состояние DEBUG
    original_debug = settings.DEBUG

    try:
        # Временно отключаем мок-данные
        settings.DEBUG = False
        print(f"📊 Режим: PRODUCTION (реальный API)")

        tester = TestFNSAPI()
        await tester.run_tests(["7707083893"])
        tester.save_results("fns_test_real_result.json")

    finally:
        # Возвращаем DEBUG в исходное состояние
        settings.DEBUG = original_debug
        print(f"\n🔄 Режим DEBUG восстановлен: {settings.DEBUG}")

    print("=" * 60)


async def main():
    """Главная функция"""
    print("\nВыберите режим тестирования:")
    print("1. Тест с мок-данными (текущий DEBUG режим)")
    print("2. Тест без мок-данных (реальный API)")
    print("3. Все тесты")

    choice = input("\nВаш выбор (1/2/3): ").strip()

    tester = TestFNSAPI()

    if choice == "1":
        await tester.run_tests()
        tester.save_results()
    elif choice == "2":
        await test_without_mock()
    elif choice == "3":
        await tester.run_tests()
        tester.save_results("fns_test_mock_result.json")
        await test_without_mock()
    else:
        print("❌ Неверный выбор")


if __name__ == "__main__":
    asyncio.run(main())