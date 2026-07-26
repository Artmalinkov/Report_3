# app/tests/test_integration.py
"""
Интеграционное тестирование всего процесса
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.fns_client import FNSClient
from app.services.ionet_client import IONETClient
from app.services.report_generator import ReportGenerator
from app.config import settings


class TestIntegration:
    """Интеграционное тестирование"""

    def __init__(self):
        self.fns_client = FNSClient()
        self.ionet_client = IONETClient()
        self.generator = ReportGenerator()

    async def test_full_flow(self, inn: str):
        """Тест полного цикла: ИНН → ФНС → AI → Отчет"""

        print(f"\n🔍 Тестирование полного цикла для ИНН: {inn}")
        print("-" * 40)

        try:
            # 1. Получаем данные из ФНС
            print("  1️⃣ Получение данных из ФНС...")
            financial_data = await self.fns_client.get_financial_report(inn)
            print(f"     ✅ Компания: {financial_data.get('company_name')}")

            # 2. Анализ через AI
            print("  2️⃣ Анализ через AI...")
            analysis = await self.ionet_client.analyze_financial_data(financial_data)
            print(f"     ✅ Риск: {analysis.get('risk_level')}")

            # 3. Генерация отчета
            print("  3️⃣ Генерация отчета...")
            filepath, html_content = await self.generator.generate_report(
                inn=inn,
                financial_data=financial_data,
                analysis=analysis
            )
            print(f"     ✅ Отчет создан: {filepath}")

            print(f"\n✅ Полный цикл успешно завершен!")
            return True

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    async def teardown(self):
        """Закрытие клиентов"""
        await self.fns_client.close()
        await self.ionet_client.close()

    async def run_tests(self):
        """Запуск всех тестов"""

        print("=" * 60)
        print("🧪 ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ")
        print("=" * 60)
        print(f"📊 Режим: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
        print("=" * 60)

        test_inns = ["7707083893"]

        results = {}
        for inn in test_inns:
            success = await self.test_full_flow(inn)
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
    tester = TestIntegration()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())