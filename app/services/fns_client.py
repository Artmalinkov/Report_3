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
                # Пробуем альтернативный метод
                logger.info(f"Пробуем альтернативный метод получения данных для {inn}")
                company_info = await self._get_company_info_alternative(inn)

                if not company_info:
                    raise ValueError(f"Компания с ИНН {inn} не найдена в ФНС")

            # 2. Получаем финансовые показатели
            financial_data = await self._get_financial_data(inn)

            # 3. Объединяем данные
            result = {
                "inn": inn,
                "company_name": company_info.get("name") or company_info.get("full_name") or "Неизвестно",
                "ogrn": company_info.get("ogrn", ""),
                "period": financial_data.get("period", "2024"),
                "balance": financial_data.get("balance", {}),
                "profit_loss": financial_data.get("profit_loss", {}),
                "status": company_info.get("status", "Активна"),
                "legal_address": company_info.get("address") or company_info.get("legal_address", ""),
                "updated_at": datetime.utcnow().isoformat()
            }

            logger.info(f"Данные для ИНН {inn} успешно получены: {result.get('company_name')}")
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
        # Пробуем разные эндпоинты
        endpoints = [
            f"{self.base_url}/company",
            f"{self.base_url}/api/company",
            f"{self.base_url}/v1/company",
        ]

        params = {"inn": inn}
        session = await self._get_session()

        for url in endpoints:
            try:
                logger.debug(f"Пробуем эндпоинт: {url}")
                async with session.get(url, params=params) as response:
                    logger.debug(f"Статус ответа: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Ответ API: {json.dumps(data, ensure_ascii=False)[:500]}")

                        # Пробуем разные структуры ответа
                        company = data.get("data", {}).get("company", {})
                        if company:
                            return company

                        # Альтернативная структура
                        company = data.get("company", {})
                        if company:
                            return company

                        # Если это список
                        if isinstance(data, list) and data:
                            return data[0]

                        # Если есть suggestions (как в DaData)
                        if "suggestions" in data and data["suggestions"]:
                            return data["suggestions"][0].get("data", {})

                    elif response.status == 404:
                        logger.warning(f"Компания с ИНН {inn} не найдена (404)")
                        continue
                    else:
                        error_text = await response.text()
                        logger.warning(f"Ошибка {response.status}: {error_text[:200]}")
                        continue

            except asyncio.TimeoutError:
                logger.warning(f"Таймаут при запросе к {url}")
                continue
            except Exception as e:
                logger.warning(f"Ошибка при запросе к {url}: {e}")
                continue

        return {}

    async def _get_company_info_alternative(self, inn: str) -> Dict[str, Any]:
        """
        Альтернативный метод получения информации о компании (например, через DaData)
        """
        try:
            # Если у вас есть ключ DaData, можно использовать его
            # https://dadata.ru/api/find-party/

            dadata_url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
            dadata_key = settings.FNS_API_KEY  # или отдельный ключ для DaData

            headers = {
                "Authorization": f"Token {dadata_key}",
                "Content-Type": "application/json"
            }

            payload = {"query": inn}

            session = await self._get_session()
            async with session.post(dadata_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    suggestions = data.get("suggestions", [])
                    if suggestions:
                        company_data = suggestions[0].get("data", {})
                        return {
                            "name": company_data.get("name", {}).get("full", ""),
                            "ogrn": company_data.get("ogrn", ""),
                            "status": "Активна" if company_data.get("state", {}).get(
                                "status") == "ACTIVE" else "Неактивна",
                            "address": company_data.get("address", {}).get("value", ""),
                        }
        except Exception as e:
            logger.warning(f"Ошибка при запросе к DaData: {e}")

        return {}

    async def _get_financial_data(self, inn: str) -> Dict[str, Any]:
        """
        Получение финансовых показателей компании
        """
        # Пробуем разные эндпоинты
        endpoints = [
            f"{self.base_url}/financial",
            f"{self.base_url}/api/financial",
            f"{self.base_url}/v1/financial",
        ]

        params = {"inn": inn, "period": "2024"}
        session = await self._get_session()

        for url in endpoints:
            try:
                logger.debug(f"Пробуем финансовый эндпоинт: {url}")
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        parsed = self._parse_financial_data(data)
                        if parsed.get("balance") or parsed.get("profit_loss"):
                            return parsed
                    else:
                        logger.debug(f"Финансовый эндпоинт {url} вернул {response.status}")
            except Exception as e:
                logger.warning(f"Ошибка при получении финансовых данных: {e}")
                continue

        # Если не нашли финансовые данные, возвращаем пустой словарь
        logger.warning(f"Нет финансовых данных для ИНН {inn}")
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
            # Пробуем разные структуры данных
            financial = data.get("data", {}).get("financial", {})
            if not financial:
                financial = data.get("financial", {})

            balance = financial.get("balance", {})
            profit_loss = financial.get("profit_loss", {})

            # Если данные пустые, пробуем альтернативную структуру
            if not balance and not profit_loss:
                balance = data.get("balance", {})
                profit_loss = data.get("profit_loss", {})

            return {
                "period": financial.get("period") or data.get("period") or "2024",
                "balance": {
                    "assets": balance.get("assets") or balance.get("Активы") or "0",
                    "liabilities": balance.get("liabilities") or balance.get("Обязательства") or "0",
                    "capital": balance.get("capital") or balance.get("Капитал") or "0",
                    "non_current_assets": balance.get("non_current_assets") or balance.get(
                        "Внеоборотные_активы") or "0",
                    "current_assets": balance.get("current_assets") or balance.get("Оборотные_активы") or "0",
                    "long_term_liabilities": balance.get("long_term_liabilities") or balance.get(
                        "Долгосрочные_обязательства") or "0",
                    "short_term_liabilities": balance.get("short_term_liabilities") or balance.get(
                        "Краткосрочные_обязательства") or "0",
                },
                "profit_loss": {
                    "revenue": profit_loss.get("revenue") or profit_loss.get("Выручка") or "0",
                    "profit": profit_loss.get("profit") or profit_loss.get("Прибыль") or "0",
                    "loss": profit_loss.get("loss") or profit_loss.get("Убыток") or "0",
                    "gross_profit": profit_loss.get("gross_profit") or profit_loss.get("Валовая_прибыль") or "0",
                    "operating_expenses": profit_loss.get("operating_expenses") or profit_loss.get(
                        "Операционные_расходы") or "0",
                    "net_profit": profit_loss.get("net_profit") or profit_loss.get("Чистая_прибыль") or "0",
                    "ebitda": profit_loss.get("ebitda") or "0",
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
        """Получение компании по ОГРН"""
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