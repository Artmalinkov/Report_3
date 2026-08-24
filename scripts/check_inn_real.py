# scripts/check_inn_real.py
"""
Проверка реального API ФНС (api-fns.ru) по конкретному ИНН
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.fns_client import FNSClient


async def main():
    """Главная функция"""
    inn = "7701285928"

    print("=" * 60)
    print("🔍 ПРОВЕРКА ИНН ЧЕРЕЗ РЕАЛЬНЫЙ API ФНС (api-fns.ru)")
    print("=" * 60)
    print(f"📋 ИНН: {inn}")
    print("=" * 60)

    original_debug = settings.DEBUG
    settings.DEBUG = False  # тест должен ходить в реальный API, а не в мок-данные

    client = FNSClient()
    try:
        data = await client.get_financial_report(inn)

        print("\n✅ Компания найдена!")
        print(f"   Название: {data.get('company_name')}")
        print(f"   ОГРН: {data.get('ogrn')}")
        print(f"   Статус: {data.get('status')}")
        print(f"   Адрес: {data.get('legal_address')}")

        balance = data.get("balance", {})
        profit_loss = data.get("profit_loss", {})
        if balance or profit_loss:
            print(f"\n📊 Отчетность за {data.get('period')} год:")
            print(f"   Выручка: {profit_loss.get('revenue', 'н/д')}")
            print(f"   Чистая прибыль: {profit_loss.get('net_profit', 'н/д')}")
            print(f"   Активы: {balance.get('assets', 'н/д')}")
        else:
            print("\n⚠️  Бухгалтерская отчетность не найдена (нормально для ИП/банков)")

    except ValueError as e:
        print(f"\n❌ Компания не найдена: {e}")
    except Exception as e:
        print(f"\n❌ Ошибка запроса: {e}")
    finally:
        await client.close()
        settings.DEBUG = original_debug

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
