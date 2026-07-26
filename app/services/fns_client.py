# app/services/fns_client.py
"""
Клиент для работы с API ФНС
"""

import aiohttp
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.config import settings
from app.services.mock_data import get_mock_financial_data


class FNSClient:
    """Клиент для API ФНС"""

    def __init__(self):
        self.api_key = settings.FNS_API_KEY
        self.base_url = "https://api-fns.ru/api/v1"
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получение или создание сессии"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
        return self.session

    async def close(self):
        """Закрытие сессии"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_financial_report(self, inn: str) -> Dict[str, Any]:
        """
        Получение финансовой отчетности по ИНН

        Args:
            inn: ИНН компании

        Returns:
            Dict с данными финансовой отчетности
        """
        logger.info(f"Запрос данных ФНС для ИНН: {inn}")

        # РЕЖИМ РАЗРАБОТКИ: используем мок-данные если DEBUG=True
        if settings.DEBUG:
            mock_data = get_mock_financial_data(inn)
            if mock_data:
                logger.info(f"Использованы мок-данные для ИНН {inn}")
                return mock_data
            else:
                logger.warning(f"Мок-данные для ИНН {inn} не найдены")

        try:
            # 1. Получаем основную информацию о компании
            company_info = await self._get_company_info(inn)

            if not company_info:
                raise ValueError(f"Компания с ИНН {inn} не найдена")

            # 2. Получаем финансовые показатели
            financial_data = await self._get_financial_data(inn)

            # 3. Объединяем данные
            result = {
                "inn": inn,
                "company_name": company_info.get("name", "Неизвестно"),
                "ogrn": company_info.get("ogrn", ""),
                "period": financial_data.get("period", "2024"),
                "balance": financial_data.get("balance", {}),
                "profit_loss": financial_data.get("profit_loss", {}),
                "status": company_info.get("status", "Активна"),
                "legal_address": company_info.get("address", ""),
                "updated_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Данные для ИНН {inn} успешно получены")
            return result

        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при запросе к ФНС: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при получении данных ФНС для {inn}: {e}")
            raise

    async def _get_company_info(self, inn: str) -> Dict[str, Any]:
        """
        Получение основной информации о компании
        """
        url = f"{self.base_url}/company"
        params = {"inn": inn}

        session = await self._get_session()

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {}).get("company", {})
                elif response.status == 404:
                    logger.warning(f"Компания с ИНН {inn} не найдена")
                    return {}
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка ФНС API: {response.status} - {error_text}")
                    raise Exception(f"Ошибка API ФНС: {response.status}")

        except asyncio.TimeoutError:
            logger.error(f"Таймаут при запросе к ФНС для {inn}")
            raise TimeoutError("Превышено время ожидания ответа от ФНС")

    async def _get_financial_data(self, inn: str) -> Dict[str, Any]:
        """
        Получение финансовых показателей компании
        """
        url = f"{self.base_url}/financial"
        params = {"inn": inn, "period": "2024"}

        session = await self._get_session()

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_financial_data(data)
                else:
                    # Если нет финансовых данных, возвращаем пустой словарь
                    logger.warning(f"Нет финансовых данных для ИНН {inn}")
                    return {
                        "period": "2024",
                        "balance": {},
                        "profit_loss": {}
                    }

        except Exception as e:
            logger.error(f"Ошибка при получении финансовых данных: {e}")
            return {
                "period": "2024",
                "balance": {},
                "profit_loss": {}
            }

    def _parse_financial_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Парсинг финансовых данных из ответа API
        """
        try:
            # Пример структуры данных (зависит от реального API)
            financial = data.get("data", {}).get("financial", {})

            balance = financial.get("balance", {})
            profit_loss = financial.get("profit_loss", {})

            return {
                "period": financial.get("period", "2024"),
                "balance": {
                    "assets": balance.get("assets", "0"),
                    "liabilities": balance.get("liabilities", "0"),
                    "capital": balance.get("capital", "0"),
                    "non_current_assets": balance.get("non_current_assets", "0"),
                    "current_assets": balance.get("current_assets", "0"),
                    "long_term_liabilities": balance.get("long_term_liabilities", "0"),
                    "short_term_liabilities": balance.get("short_term_liabilities", "0"),
                },
                "profit_loss": {
                    "revenue": profit_loss.get("revenue", "0"),
                    "profit": profit_loss.get("profit", "0"),
                    "loss": profit_loss.get("loss", "0"),
                    "gross_profit": profit_loss.get("gross_profit", "0"),
                    "operating_expenses": profit_loss.get("operating_expenses", "0"),
                    "net_profit": profit_loss.get("net_profit", "0"),
                    "ebitda": profit_loss.get("ebitda", "0"),
                }
            }
        except Exception as e:
            logger.error(f"Ошибка парсинга финансовых данных: {e}")
            return {
                "period": "2024",
                "balance": {},
                "profit_loss": {}
            }

    async def get_company_by_ogrn(self, ogrn: str) -> Dict[str, Any]:
        """
        Получение компании по ОГРН
        """
        url = f"{self.base_url}/company"
        params = {"ogrn": ogrn}

        session = await self._get_session()

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {}).get("company", {})
                return {}
        except Exception as e:
            logger.error(f"Ошибка при получении компании по ОГРН {ogrn}: {e}")
            return {}