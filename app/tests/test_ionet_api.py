# app/tests/test_ionet_api.py
"""
Тестирование API IO_NET
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.ionet_client import IONETClient
from app.services.mock_data import get_mock_financial_data
from app.config import settings


class TestIONETAPI:
    """Тестирование API IO_NET"""

    def __init__(self):
        self.client = None

    async def setup(self):
        """Инициализация клиента"""
        self.client = IONETClient()

    async def teardown(self):
        """Закрытие клиента"""
        if self.client:
            await self.client.close()

    async def test_analyze(self, inn: str):
        """Тест анализа финансовых данных"""

        print(f"\n🔍 Тестирование анализа для ИНН: {inn}")
        print("-" * 40)

        # Получаем данные компании
        financial_data = get_mock_financial_data(inn)

        if not financial_data:
            print(f"❌ Нет данных для ИНН {inn}")
            return False

        try:
            # Выполняем анализ
            analysis = await self.client.analyze_financial_data(financial_data)

            print(f"✅ Анализ выполнен успешно!")
            print(f"   Уровень риска: {analysis.get('risk_level')}")
            print(f"   Резюме: {analysis.get('summary', '')[:100]}...")
            print(f"   Ключевые показатели: {analysis.get('key_metrics', '')[:100]}...")

            # Проверяем структуру ответа
            assert analysis.get('risk_level') in ["Низкий", "Средний", "Высокий"], "Неверный уровень риска"
            assert analysis.get('summary'), "Отсутствует резюме"

            return True

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    async def run_tests(self):
        """Запуск всех тестов"""

        await self.setup()

        print("=" * 60)
        print("🧪 ТЕСТИРОВАНИЕ API IO_NET")
        print("=" * 60)
        print(f"📊 Режим: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
        print(f"🔑 API Key: {settings.IONET_API_KEY[:10]}...")
        print(f"🤖 Модель: {settings.IONET_MODEL}")
        print("=" * 60)

        test_inns = ["7707083893", "7702070139"]

        results = {}
        for inn in test_inns:
            success = await self.test_analyze(inn)
            results[inn] = success

        await self.teardown()

        # Итоги
        print("\n" + "=" * 60)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 60)

        for inn, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} ИНН {inn}: {'Успешно' if success else 'Ошибка'}")

        print("=" * 60)


async def main():
    tester = TestIONETAPI()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())