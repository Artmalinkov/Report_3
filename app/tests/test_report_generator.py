# app/tests/test_report_generator.py
"""
Тестирование генератора отчетов
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.report_generator import ReportGenerator
from app.services.mock_data import get_mock_financial_data
from app.services.ionet_client import IONETClient


class TestReportGenerator:
    """Тестирование генератора отчетов"""

    def __init__(self):
        self.generator = ReportGenerator()
        self.ionet_client = IONETClient()

    async def test_generate_report(self, inn: str):
        """Тест генерации отчета"""

        print(f"\n🔍 Тестирование генерации отчета для ИНН: {inn}")
        print("-" * 40)

        try:
            # Получаем данные
            financial_data = get_mock_financial_data(inn)
            if not financial_data:
                print(f"❌ Нет данных для ИНН {inn}")
                return False

            # Выполняем анализ
            analysis = await self.ionet_client.analyze_financial_data(financial_data)

            # Генерируем отчет
            filepath, html_content = await self.generator.generate_report(
                inn=inn,
                financial_data=financial_data,
                analysis=analysis
            )

            # Проверяем
            assert filepath and Path(filepath).exists(), "Файл не создан"
            assert html_content, "HTML контент пустой"
            assert len(html_content) > 100, "HTML контент слишком короткий"

            print(f"✅ Отчет создан успешно!")
            print(f"   Путь: {filepath}")
            print(f"   Размер: {len(html_content)} символов")

            # Показываем первые несколько строк
            lines = html_content.split('\n')[:10]
            print(f"\n   Первые строки:")
            for line in lines[:5]:
                if line.strip():
                    print(f"   {line.strip()[:100]}...")

            return True

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

    async def run_tests(self):
        """Запуск всех тестов"""

        print("=" * 60)
        print("🧪 ТЕСТИРОВАНИЕ ГЕНЕРАТОРА ОТЧЕТОВ")
        print("=" * 60)

        test_inns = ["7707083893", "7702070139"]

        results = {}
        for inn in test_inns:
            success = await self.test_generate_report(inn)
            results[inn] = success

        # Итоги
        print("\n" + "=" * 60)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 60)

        for inn, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} ИНН {inn}: {'Успешно' if success else 'Ошибка'}")

        await self.ionet_client.close()
        print("=" * 60)


async def main():
    tester = TestReportGenerator()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())