# app/services/fns_client.py
"""
Клиент для работы с API ФНС (api-fns.ru)
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp
from loguru import logger

from app.config import settings
from app.services.mock_data import get_mock_financial_data

# Коды строк бухгалтерской отчетности (Приказ Минфина РФ №66н от 02.07.2010).
# Проверены сверкой контрольных соотношений на реальных ответах api-fns.ru
# (1100+1200=1600, 1300+1400+1500=1700, 2110-2120=2100 и т.д.).
BALANCE_CODES = {
    "non_current_assets": "1100",
    "current_assets": "1200",
    "assets": "1600",
    "capital": "1300",
    "long_term_liabilities": "1400",
    "short_term_liabilities": "1500",
}

PROFIT_LOSS_CODES = {
    "revenue": "2110",
    "cost_of_sales": "2120",
    "gross_profit": "2100",
    "profit_from_sales": "2200",
    "profit": "2300",  # прибыль (убыток) до налогообложения
    "net_profit": "2400",
}


class FNSClient:
    """Клиент для API api-fns.ru"""

    BASE_URL = "https://api-fns.ru/api"

    def __init__(self):
        self.api_key = settings.FNS_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        # 30с не всегда хватает: у компаний с большой историей в ЕГРЮЛ
        # (например, у Сбербанка — десятки филиалов, сотни исторических записей)
        # api-fns.ru может отвечать дольше
        self.timeout = aiohttp.ClientTimeout(total=45)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получение или создание сессии"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def close(self):
        """Закрытие сессии"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _call(self, method: str, inn: str, **extra_params) -> Any:
        """
        Низкоуровневый вызов метода api-fns.ru.
        Авторизация — параметром key в query string (не Bearer-заголовком):
        именно так сервис принимает ключ (см. api-fns.ru/api_help).
        """
        session = await self._get_session()
        params = {"req": inn, "key": self.api_key, **extra_params}

        try:
            async with session.get(f"{self.BASE_URL}/{method}", params=params) as response:
                text = await response.text()
                if response.status != 200:
                    # api-fns.ru отдает ошибки простым текстом (например,
                    # "Ошибка: Исчерпано количество запросов"), а не JSON
                    raise RuntimeError(f"API ФНС ({method}) вернул {response.status}: {text[:300]}")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    raise RuntimeError(f"API ФНС ({method}) вернул не-JSON ответ: {text[:300]}")
        except asyncio.TimeoutError:
            raise TimeoutError(f"Превышено время ожидания ответа от API ФНС ({method})")

    async def get_financial_report(self, inn: str) -> Dict[str, Any]:
        """
        Получение сводных данных о компании/ИП и его отчетности по ИНН
        """
        logger.info(f"Запрос данных ФНС для ИНН: {inn}")

        if settings.DEBUG:
            mock_data = get_mock_financial_data(inn)
            if mock_data:
                logger.info(f"Использованы мок-данные для ИНН {inn}")
                return mock_data
            logger.warning(f"Мок-данные для ИНН {inn} не найдены, идем в реальный API")

        company_info = await self._get_company_info(inn)
        if company_info is None:
            raise ValueError(f"Компания с ИНН {inn} не найдена в ФНС")

        financial = await self._get_financial_data(inn)

        result = {
            "inn": inn,
            "company_name": company_info["name"],
            "ogrn": company_info["ogrn"],
            "period": financial.get("period", ""),
            "balance": financial.get("balance", {}),
            "profit_loss": financial.get("profit_loss", {}),
            "status": company_info["status"],
            "legal_address": company_info["address"],
            "updated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Данные для ИНН {inn} получены: {result['company_name']}")
        return result

    async def _get_company_info(self, inn: str) -> Optional[Dict[str, Any]]:
        """
        Реквизиты компании/ИП по данным ЕГРЮЛ/ЕГРИП (метод egr)
        """
        data = await self._call("egr", inn)
        items = data.get("items") or []
        if not items:
            return None

        entry = items[0]

        if "ЮЛ" in entry:
            ul = entry["ЮЛ"]
            return {
                "name": ul.get("НаимПолнЮЛ") or ul.get("НаимСокрЮЛ") or "Неизвестно",
                "ogrn": ul.get("ОГРН", ""),
                "status": ul.get("Статус", "Неизвестно"),
                "address": (ul.get("Адрес") or {}).get("АдресПолн", ""),
            }

        if "ИП" in entry:
            ip = entry["ИП"]
            return {
                "name": ip.get("ФИОПолн", "Неизвестно"),
                "ogrn": ip.get("ОГРНИП", ""),
                "status": ip.get("Статус", "Неизвестно"),
                "address": (ip.get("Адрес") or {}).get("АдресПолн", ""),
            }

        return None

    async def _get_financial_data(self, inn: str) -> Dict[str, Any]:
        """
        Бухгалтерская отчетность по данным ФНС (метод bo).
        Отдает показатели по годам с кодами строк форм №1 и №2.
        ИП такую отчетность, как правило, не сдают (работают по декларациям) —
        для них метод вернет пустой результат, это ожидаемое поведение.
        """
        empty = {"period": "", "balance": {}, "profit_loss": {}}

        try:
            data = await self._call("bo", inn)
        except RuntimeError as e:
            logger.warning(f"Бухгалтерская отчетность для {inn} недоступна: {e}")
            return empty

        company_block = data.get(inn)
        if not company_block:
            logger.info(f"Бухгалтерская отчетность для ИНН {inn} не найдена (например, это ИП)")
            return empty

        latest_year = sorted(company_block.keys())[-1]
        year_data = company_block[latest_year]

        if any(key.startswith("credit_") for key in year_data.keys()):
            # Кредитные организации (банки) отчитываются по форме 0409806/807
            # с другой нумерацией строк — она здесь не размечена, чтобы не
            # выдавать угаданные подписи за реальные показатели
            logger.warning(
                f"ИНН {inn}: отчетность в формате кредитной организации, "
                f"показатели по стандартным кодам не извлечены"
            )
            return {"period": latest_year, "balance": {}, "profit_loss": {}}

        def get(code: str) -> str:
            return str(year_data.get(code, "0"))

        balance = {key: get(code) for key, code in BALANCE_CODES.items()}
        profit_loss = {key: get(code) for key, code in PROFIT_LOSS_CODES.items()}
        profit_loss["loss"] = "0"
        # В формах нет отдельной строки "операционные расходы" — это сумма
        # себестоимости, коммерческих и управленческих расходов (2120+2210+2220)
        profit_loss["operating_expenses"] = str(
            int(get("2120")) + int(get("2210")) + int(get("2220"))
        )
        # EBITDA не входит в состав официальной отчетности — не подменяем
        # отсутствующий показатель угаданным числом
        profit_loss["ebitda"] = "Н/Д"

        return {"period": latest_year, "balance": balance, "profit_loss": profit_loss}
