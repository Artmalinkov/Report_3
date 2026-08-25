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

# Коды форм 0409806 "Бухгалтерский баланс (публикуемая форма)" и 0409807
# "Отчет о финансовых результатах" для кредитных организаций (банков).
# У api-fns.ru эти показатели, в отличие от обычных компаний, сгруппированы
# по разделам (credit_assets, credit_passives и т.д.), а не лежат плоско.
# Сопоставление кодов проверено арифметически на двух реальных банках:
# сумма строк 1-13 credit_assets = строка 14 (Всего активов);
# сумма строк 15-22 credit_passives = строка 23 (Всего обязательств);
# строка14 - строка23 = credit_sources_of_own_income.36 (капитал, сходится
# и как отдельная строка баланса, и как остаток по балансовому равенству);
# credit_profit_and_loss: строка1 - строка2 = строка3 (проценты получены
# минус проценты уплачены = чистый процентный доход), строка24 + строка25
# = строка26 (прибыль за период после итоговой корректировки).
# У банковской формы нет деления активов/обязательств на текущие и
# долгосрочные (это отраслевой признак промышленных форм) — такие поля
# оставляем недоступными, а не подменяем угаданной разбивкой.
CREDIT_ASSETS_TOTAL = ("credit_assets", "14")
CREDIT_EQUITY_TOTAL = ("credit_sources_of_own_income", "36")
CREDIT_INTEREST_INCOME = ("credit_profit_and_loss", "1")  # ближайший аналог "выручки" для банка
CREDIT_PROFIT_BEFORE_ADJ = ("credit_profit_and_loss", "24")
CREDIT_NET_PROFIT = ("credit_profit_and_loss", "26")

NOT_AVAILABLE = "Н/Д"


def _thousands_to_rubles(value: str) -> str:
    """
    Бухгалтерская отчетность в РФ подается "в тысячах рублей" (изредка — "в
    миллионах" для очень крупных организаций, но эту оговорку сам API никак
    не помечает — единицы измерения в ответе не отдаются). Сверено на
    реальных числах: активы банка из примера ИНН 7707083893 = 32 979 678 372
    в сырых данных — это правдоподобно как ~33 трлн руб. (тыс.), но не как
    33 млрд (если бы значение уже было в рублях). Домножаем на 1000, считая
    это доминирующим случаем для целевой аудитории бота (малый/средний
    бизнес).
    """
    try:
        return str(int(round(float(value) * 1000)))
    except (TypeError, ValueError):
        return value


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

        # При отсутствии отчетности (обычная ситуация для ИП) api-fns.ru
        # отдает не {} (пустой объект по ИНН), а буквально [] (пустой
        # список) — проверено на реальном ИП без бухотчетности
        if not isinstance(data, dict):
            logger.info(f"Бухгалтерская отчетность для ИНН {inn} не найдена (например, это ИП)")
            return empty

        company_block = data.get(inn)
        if not company_block:
            logger.info(f"Бухгалтерская отчетность для ИНН {inn} не найдена (например, это ИП)")
            return empty

        latest_year = sorted(company_block.keys())[-1]
        year_data = company_block[latest_year]

        if any(key.startswith("credit_") for key in year_data.keys()):
            logger.info(f"ИНН {inn}: отчетность кредитной организации (форма 0409806/807)")
            balance, profit_loss = self._parse_credit_form(year_data)
            return {"period": latest_year, "balance": balance, "profit_loss": profit_loss}

        balance, profit_loss = self._parse_standard_form(year_data)
        return {"period": latest_year, "balance": balance, "profit_loss": profit_loss}

    @staticmethod
    def _parse_standard_form(year_data: Dict[str, Any]) -> tuple[Dict[str, str], Dict[str, str]]:
        """Формы №1 и №2 (Приказ Минфина №66н) — обычные компании"""

        def get(code: str) -> str:
            return _thousands_to_rubles(str(year_data.get(code, "0")))

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
        profit_loss["ebitda"] = NOT_AVAILABLE

        return balance, profit_loss

    @staticmethod
    def _parse_credit_form(year_data: Dict[str, Any]) -> tuple[Dict[str, str], Dict[str, str]]:
        """Формы 0409806/0409807 — кредитные организации (банки)"""

        def get(section_code: tuple[str, str]) -> Optional[str]:
            section, code = section_code
            value = (year_data.get(section) or {}).get(code)
            return _thousands_to_rubles(str(value)) if value is not None else None

        assets = get(CREDIT_ASSETS_TOTAL)
        equity = get(CREDIT_EQUITY_TOTAL)
        revenue = get(CREDIT_INTEREST_INCOME)
        profit = get(CREDIT_PROFIT_BEFORE_ADJ)
        net_profit = get(CREDIT_NET_PROFIT)

        balance = {
            "non_current_assets": NOT_AVAILABLE,
            "current_assets": NOT_AVAILABLE,
            "assets": assets or NOT_AVAILABLE,
            "capital": equity or NOT_AVAILABLE,
            "long_term_liabilities": NOT_AVAILABLE,
            "short_term_liabilities": NOT_AVAILABLE,
        }
        profit_loss = {
            "revenue": revenue or NOT_AVAILABLE,
            "cost_of_sales": NOT_AVAILABLE,
            "gross_profit": NOT_AVAILABLE,
            "profit_from_sales": NOT_AVAILABLE,
            "profit": profit or NOT_AVAILABLE,
            "net_profit": net_profit or NOT_AVAILABLE,
            "loss": "0",
            "operating_expenses": NOT_AVAILABLE,
            "ebitda": NOT_AVAILABLE,
        }

        return balance, profit_loss
