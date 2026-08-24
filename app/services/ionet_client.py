# app/services/ionet_client.py
"""
Клиент для работы с API IO_NET
"""

import aiohttp
import asyncio
import json
import re
from typing import Dict, Any, Optional
from loguru import logger

from app.config import settings


class IONETClient:
    """Клиент для API IO_NET"""

    def __init__(self):
        self.api_key = settings.IONET_API_KEY
        self.base_url = settings.IONET_API_URL
        self.model = settings.IONET_MODEL
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=60)

    def _get_mock_analysis(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Возвращает мок-анализ при недоступности API"""
        company_name = financial_data.get("company_name", "Компания")
        profit = self._safe_float(financial_data.get("profit_loss", {}).get("profit", "0"))
        revenue = self._safe_float(financial_data.get("profit_loss", {}).get("revenue", "0"))
        assets = self._safe_float(financial_data.get("balance", {}).get("assets", "0"))
        capital = self._safe_float(financial_data.get("balance", {}).get("capital", "0"))

        profitability = (profit / revenue * 100) if revenue > 0 else 0
        autonomy = (capital / assets * 100) if assets > 0 else 0

        # Определяем уровень риска
        if profitability > 10 and autonomy > 50:
            risk_level = "Низкий"
            summary = f"Компания {company_name} демонстрирует хорошие финансовые показатели. Высокая рентабельность ({profitability:.1f}%) и хорошая финансовая устойчивость (автономия {autonomy:.1f}%)."
        elif profitability > 0 and autonomy > 30:
            risk_level = "Средний"
            summary = f"Компания {company_name} имеет средние финансовые показатели. Рентабельность {profitability:.1f}%, автономия {autonomy:.1f}%. Требуется дополнительный анализ."
        else:
            risk_level = "Высокий"
            summary = f"Компания {company_name} показывает низкую рентабельность ({profitability:.1f}%) и недостаточную финансовую устойчивость (автономия {autonomy:.1f}%). Рекомендуется детальный анализ."

        return {
            "summary": summary,
            "key_metrics": f"Рентабельность: {profitability:.1f}% | Автономия: {autonomy:.1f}% | Выручка: {revenue:,.0f} руб.",
            "risks": "Низкая диверсификация источников дохода. Зависимость от экономической ситуации.",
            "recommendations": "1. Увеличить долю собственного капитала\n2. Диверсифицировать источники дохода\n3. Повысить эффективность управления активами",
            "risk_level": risk_level,
            "full_response": f"Анализ выполнен на основе базовых метрик (режим оффлайн)"
        }

    @staticmethod
    def _safe_float(value) -> float:
        """Безопасное преобразование в число"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                cleaned = value.replace(" ", "").replace(",", ".").strip()
                if not cleaned:
                    return 0.0
                return float(cleaned)
            return 0.0
        except (ValueError, TypeError):
            return 0.0

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

    async def analyze_financial_data(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализ финансовых данных с помощью ИИ
        """
        logger.info("Начало анализа финансовых данных через IO_NET")

        try:
            # Подготовка промпта для анализа
            prompt = self._build_analysis_prompt(financial_data)

            # Отправка запроса к IO_NET
            response = await self._send_request(prompt)

            # Парсинг ответа
            analysis = self._parse_analysis_response(response)

            logger.info("Анализ финансовых данных успешно завершен")
            return analysis

        except (aiohttp.ClientError, asyncio.TimeoutError, Exception) as e:
            logger.error(f"Ошибка при анализе через IO_NET: {e}")
            # Возвращаем мок-анализ при недоступности API
            logger.info("Использован мок-анализ (режим оффлайн)")
            return self._get_mock_analysis(financial_data)

    async def _send_request(self, prompt: str) -> Dict[str, Any]:
        """
        Отправка запроса к IO_NET API
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты - эксперт по финансовому анализу. "
                               "Анализируй финансовые данные компаний и давай четкие, структурированные ответы. "
                               "Оценивай финансовое состояние, риски, и давай рекомендации."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }

        session = await self._get_session()

        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка IO_NET API: {response.status} - {error_text}")
                    raise Exception(f"Ошибка API IO_NET: {response.status}")

        except asyncio.TimeoutError:
            logger.error("Таймаут при запросе к IO_NET")
            raise TimeoutError("Превышено время ожидания ответа от IO_NET")

    def _build_analysis_prompt(self, financial_data: Dict[str, Any]) -> str:
        """
        Построение промпта для анализа финансовых данных
        """
        company_name = financial_data.get("company_name", "Неизвестная компания")
        inn = financial_data.get("inn", "")
        period = financial_data.get("period", "2024")

        balance = financial_data.get("balance", {})
        profit_loss = financial_data.get("profit_loss", {})

        prompt = f"""
Проведи финансовый анализ компании {company_name} (ИНН: {inn}) за {period} год.

Данные бухгалтерского баланса:
- Активы: {balance.get('assets', '0')} руб.
- Внеоборотные активы: {balance.get('non_current_assets', '0')} руб.
- Оборотные активы: {balance.get('current_assets', '0')} руб.
- Собственный капитал: {balance.get('capital', '0')} руб.
- Долгосрочные обязательства: {balance.get('long_term_liabilities', '0')} руб.
- Краткосрочные обязательства: {balance.get('short_term_liabilities', '0')} руб.

Данные отчета о финансовых результатах:
- Выручка: {profit_loss.get('revenue', '0')} руб.
- Валовая прибыль: {profit_loss.get('gross_profit', '0')} руб.
- Прибыль до налогообложения: {profit_loss.get('profit', '0')} руб.
- Чистая прибыль: {profit_loss.get('net_profit', '0')} руб.
- EBITDA: {profit_loss.get('ebitda', '0')} руб.

Пожалуйста, предоставь анализ в следующем формате:

1. ФИНАНСОВОЕ СОСТОЯНИЕ (краткая оценка)
2. КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ (рентабельность, ликвидность, финансовая устойчивость)
3. РИСКИ (выявленные риски и проблемы)
4. РЕКОМЕНДАЦИИ (практические рекомендации)
5. УРОВЕНЬ РИСКА (Низкий/Средний/Высокий)

Будь объективен, используй профессиональную терминологию, но объясняй доступно.
"""

        return prompt

    def _parse_analysis_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Парсинг ответа от IO_NET
        """
        try:
            # Получаем текст ответа
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Разбиваем на секции
            sections = self._parse_sections(content)

            # Определяем уровень риска
            risk_level = self._determine_risk_level(content, sections)

            return {
                "summary": sections.get("ФИНАНСОВОЕ СОСТОЯНИЕ", "Анализ не выполнен"),
                "key_metrics": sections.get("КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ", ""),
                "risks": sections.get("РИСКИ", ""),
                "recommendations": sections.get("РЕКОМЕНДАЦИИ", ""),
                "risk_level": risk_level,
                "full_response": content
            }

        except Exception as e:
            logger.error(f"Ошибка парсинга ответа IO_NET: {e}")
            return {
                "summary": "Ошибка при анализе данных",
                "key_metrics": "",
                "risks": "",
                "recommendations": "",
                "risk_level": "Средний",
                "full_response": str(response)
            }

    @staticmethod
    def _heading_candidate(line: str) -> str:
        """
        Снимает markdown-декорации ("**", "###", нумерацию "1.", ":") с начала
        строки, чтобы отличить настоящий заголовок секции от обычного
        предложения, которое просто упоминает слово вроде "риски" не в начале
        """
        cleaned = re.sub(r'^[#*\s]+', '', line.strip())
        cleaned = re.sub(r'^\d+[.)]\s*', '', cleaned)
        cleaned = cleaned.strip('*: \t')
        return cleaned.upper()

    def _parse_sections(self, content: str) -> Dict[str, str]:
        """
        Разбиение текста на секции
        """
        sections = {}
        current_section = None
        current_content = []

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Заголовком считаем только строку, которая НАЧИНАЕТСЯ с одной из
            # меток (после очистки от markdown/нумерации) — иначе обычное
            # предложение вида "...могут возникать риски в случае..." само
            # обрывает текущую секцию, едва начавшись
            heading = self._heading_candidate(line)
            if any(heading.startswith(section) for section in [
                "ФИНАНСОВОЕ СОСТОЯНИЕ", "КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ",
                "РИСКИ", "РЕКОМЕНДАЦИИ", "УРОВЕНЬ РИСКА"
            ]):
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = self._get_section_key(heading)
                current_content = []
            else:
                if current_section:
                    current_content.append(line)

        # Добавляем последнюю секцию
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def _get_section_key(self, heading: str) -> str:
        """
        Определение ключа секции по уже очищенному (см. _heading_candidate)
        заголовку. Порядок проверок важен: "УРОВЕНЬ РИСКА" должен проверяться
        раньше "РИСКИ", иначе строка "Уровень риска" никогда до него не дойдет.
        """
        if heading.startswith("УРОВЕНЬ РИСКА"):
            return "УРОВЕНЬ РИСКА"
        elif heading.startswith("ФИНАНСОВОЕ СОСТОЯНИЕ") or heading.startswith("ФИНАНСОВОЕ"):
            return "ФИНАНСОВОЕ СОСТОЯНИЕ"
        elif heading.startswith("КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ") or heading.startswith("ПОКАЗАТЕЛИ"):
            return "КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ"
        elif heading.startswith("РИСКИ"):
            return "РИСКИ"
        elif heading.startswith("РЕКОМЕНДАЦИИ"):
            return "РЕКОМЕНДАЦИИ"
        return "ДРУГОЕ"

    def _determine_risk_level(self, content: str, sections: Dict[str, str]) -> str:
        """
        Определение уровня риска
        """
        # Проверяем секцию с уровнем риска
        risk_section = sections.get("УРОВЕНЬ РИСКА", "")
        if risk_section:
            if "Низкий" in risk_section or "низкий" in risk_section:
                return "Низкий"
            elif "Высокий" in risk_section or "высокий" in risk_section:
                return "Высокий"
            elif "Средний" in risk_section or "средний" in risk_section:
                return "Средний"

        # Если не нашли в секции, ищем в тексте
        if "Низкий" in content or "низкий" in content:
            return "Низкий"
        elif "Высокий" in content or "высокий" in content:
            return "Высокий"
        else:
            return "Средний"

    def _get_fallback_analysis(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Базовый анализ при ошибке API
        """
        profit = financial_data.get("profit_loss", {}).get("profit", "0")
        try:
            profit_num = float(profit.replace(" ", "").replace(",", "."))
            if profit_num > 0:
                risk_level = "Низкий"
                summary = "Компания показывает положительную финансовую динамику."
            else:
                risk_level = "Высокий"
                summary = "Компания имеет отрицательные финансовые показатели, требуется детальный анализ."
        except:
            risk_level = "Средний"
            summary = "Не удалось провести полный анализ, проверьте финансовые данные."

        return {
            "summary": summary,
            "key_metrics": "Не удалось рассчитать ключевые показатели",
            "risks": "Требуется дополнительный анализ рисков",
            "recommendations": "Рекомендуется провести углубленный финансовый аудит",
            "risk_level": risk_level,
            "full_response": "Анализ выполнен с использованием базовых метрик"
        }

    async def analyze_text(self, text: str) -> str:
        """
        Общий метод для анализа текста
        """
        try:
            response = await self._send_request(text)
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content
        except Exception as e:
            logger.error(f"Ошибка при анализе текста: {e}")
            return f"Не удалось обработать запрос: {str(e)}"