# scripts/check_inn_real.py
"""
Проверка ИНН через различные API
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


async def check_inn_dadata(inn: str, api_key: str) -> dict:
    """Проверка ИНН через DaData"""
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    payload = {"query": inn}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    suggestions = data.get("suggestions", [])
                    if suggestions:
                        company = suggestions[0].get("data", {})
                        return {
                            "source": "DaData",
                            "found": True,
                            "name": company.get("name", {}).get("full", ""),
                            "ogrn": company.get("ogrn", ""),
                            "inn": company.get("inn", ""),
                            "address": company.get("address", {}).get("value", ""),
                            "status": company.get("state", {}).get("status", ""),
                        }
                return {"source": "DaData", "found": False, "status": response.status}
    except Exception as e:
        return {"source": "DaData", "found": False, "error": str(e)}


async def check_inn_fns(inn: str, api_key: str) -> dict:
    """Проверка ИНН через API ФНС"""
    # Пробуем разные эндпоинты
    endpoints = [
        f"https://api-fns.ru/api/v1/company",
        f"https://api-fns.ru/api/company",
        f"https://api-fns.ru/v1/company",
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    for url in endpoints:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params={"inn": inn}, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        company = data.get("data", {}).get("company", {})
                        if company:
                            return {
                                "source": "FNS",
                                "found": True,
                                "name": company.get("name", ""),
                                "ogrn": company.get("ogrn", ""),
                                "inn": company.get("inn", ""),
                            }
                    elif response.status == 404:
                        continue
        except Exception as e:
            continue

    return {"source": "FNS", "found": False}


async def check_inn_nalog_ru(inn: str) -> dict:
    """Проверка ИНН через официальный сайт налоговой (парсинг)"""
    # Это упрощенный вариант, для реальной работы нужен парсинг
    url = f"https://egrul.nalog.ru/search"
    params = {"query": inn}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    # Здесь нужна обработка HTML
                    return {"source": "nalog.ru", "found": True, "message": "Требуется парсинг HTML"}
                return {"source": "nalog.ru", "found": False, "status": response.status}
    except Exception as e:
        return {"source": "nalog.ru", "found": False, "error": str(e)}


async def main():
    """Главная функция"""
    inn = "7701285928"

    print("=" * 60)
    print("🔍 ПРОВЕРКА ИНН ЧЕРЕЗ РАЗЛИЧНЫЕ API")
    print("=" * 60)
    print(f"📋 ИНН: {inn}")
    print("=" * 60)

    # Проверка через DaData
    print("\n1️⃣ DaData API...")
    result = await check_inn_dadata(inn, settings.FNS_API_KEY)
    if result.get("found"):
        print(f"   ✅ Компания найдена!")
        print(f"   Название: {result.get('name')}")
        print(f"   ОГРН: {result.get('ogrn')}")
        print(f"   Статус: {result.get('status')}")
    else:
        print(f"   ❌ Компания не найдена")
        print(f"   Статус: {result.get('status', 'N/A')}")

    # Проверка через API ФНС
    print("\n2️⃣ API ФНС...")
    result = await check_inn_fns(inn, settings.FNS_API_KEY)
    if result.get("found"):
        print(f"   ✅ Компания найдена!")
        print(f"   Название: {result.get('name')}")
    else:
        print(f"   ❌ Компания не найдена")

    print("\n" + "=" * 60)
    print("💡 Рекомендации:")
    print("   - Если DaData нашел компанию, используйте DaData API")
    print("   - Если оба API не нашли, проверьте правильность ИНН")
    print("   - Возможно, компания не публикует отчетность")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())