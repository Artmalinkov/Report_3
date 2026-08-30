# app/services/ionet_client.py
"""
Клиент для работы с API IO_NET
"""

import aiohttp
import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from loguru import logger

from app.config import settings

# Метки секций структурированного ответа ИИ. Ключ — вариант написания
# заголовка, значение — канонический ключ секции в возвращаемом словаре;
# несколько вариантов могут схлопываться в один ключ (например, модель
# иногда пишет просто "Финансовое" без "состояние").
SINGLE_ANALYSIS_LABELS = {
    "ФИНАНСОВОЕ СОСТОЯНИЕ": "ФИНАНСОВОЕ СОСТОЯНИЕ",
    "ФИНАНСОВОЕ": "ФИНАНСОВОЕ СОСТОЯНИЕ",
    "КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ": "КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ",
    "ПОКАЗАТЕЛИ": "КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ",
    "ДИНАМИКА": "ДИНАМИКА",
    "РИСКИ": "РИСКИ",
    "РЕКОМЕНДАЦИИ": "РЕКОМЕНДАЦИИ",
    "УРОВЕНЬ РИСКА": "УРОВЕНЬ РИСКА",
}

COMPARISON_LABELS = {
    "ОБЩИЙ ВЫВОД": "ОБЩИЙ ВЫВОД",
    "ЛИДЕР": "ЛИДЕР",
    "РАЗЛИЧИЯ И РИСКИ": "РАЗЛИЧИЯ И РИСКИ",
    "РАЗЛИЧИЯ": "РАЗЛИЧИЯ И РИСКИ",
    "РЕКОМЕНДАЦИЯ": "РЕКОМЕНДАЦИЯ",
}


class IONETClient:
    """Клиент для API IO_NET"""

    def __init__(self):
        self.api_key = settings.IONET_API_KEY
        self.base_url = settings.IONET_API_URL
        self.model = settings.IONET_MODEL
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=60)

    @staticmethod
    def _get_no_data_analysis(financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Честный ответ, когда бухотчетности по компании нет вообще — не выдумываем оценку по нулям"""
        company_name = financial_data.get("company_name", "Компания")
        return {
            "summary": f"По компании {company_name} в ФНС отсутствует бухгалтерская отчетность — "
                       f"оценить финансовое состояние по имеющимся данным невозможно.",
            "key_metrics": "Н/Д",
            "risks": "Невозможно оценить — отсутствуют исходные данные для анализа",
            "recommendations": "Запросить отчетность у компании напрямую или проверить позже, "
                                "когда она будет подана в ФНС",
            "risk_level": "Средний",
            "full_response": "Анализ не выполнялся: отсутствуют финансовые данные по компании",
        }

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

        years = financial_data.get("years", {})
        sorted_years = sorted(years.keys())
        dynamics = ""
        if len(sorted_years) >= 2:
            first_revenue = self._safe_float(years[sorted_years[0]].get("profit_loss", {}).get("revenue", "0"))
            last_revenue = self._safe_float(years[sorted_years[-1]].get("profit_loss", {}).get("revenue", "0"))
            if first_revenue > 0:
                change = (last_revenue - first_revenue) / first_revenue * 100
                trend = "рост" if change > 0 else "снижение" if change < 0 else "без изменений"
                dynamics = (
                    f"Выручка за период {sorted_years[0]}-{sorted_years[-1]}: {trend} "
                    f"({change:+.1f}%). Детальный анализ динамики недоступен в оффлайн-режиме."
                )

        return {
            "summary": summary,
            "key_metrics": f"Рентабельность: {profitability:.1f}% | Автономия: {autonomy:.1f}% | Выручка: {revenue:,.0f} руб.",
            "dynamics": dynamics,
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
        # Если по компании вообще нет бухотчетности (balance и profit_loss
        # пустые — обычная ситуация для новых компаний или ИП), анализировать
        # нечего: пустые словари выглядели бы для модели как нулевые
        # показатели, и она честно, но ошибочно решала бы, что это "высокий
        # риск" — хотя правильный ответ "данных недостаточно". Не тратим на
        # это платный запрос к API вообще — если только нет флагов ФНС
        # (метод check): их одних достаточно для содержательного анализа
        # даже без бухотчетности (например, "счет заблокирован" по
        # исключенной из ЕГРЮЛ компании — само по себе весомый вывод)
        risk_flags = financial_data.get("risk_flags") or {}
        has_risk_flags = bool(risk_flags.get("positive_text")) or bool(risk_flags.get("negative_text"))
        if not financial_data.get("balance") and not financial_data.get("profit_loss") and not has_risk_flags:
            logger.info("Нет финансовых данных и флагов ФНС — анализ не выполняется (API не вызывается)")
            return self._get_no_data_analysis(financial_data)

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
        Построение промпта для анализа финансовых данных. Если доступны
        данные за 2+ года (financial_data["years"] — см. fns_client.py),
        промпт просит проанализировать динамику, но дать итоговую оценку
        на текущий момент, а не изолированно по последнему году.
        """
        company_name = financial_data.get("company_name", "Неизвестная компания")
        inn = financial_data.get("inn", "")
        period = financial_data.get("period", "2024")

        balance = financial_data.get("balance", {})
        profit_loss = financial_data.get("profit_loss", {})
        years = financial_data.get("years", {})
        sorted_years = sorted(years.keys())

        # Флаги риска ФНС (метод check) — готовые факты о добросовестности
        # контрагента (лицензии, массовый адрес, блокировка счета и т.д.),
        # передаем модели как дополнительный контекст к цифрам отчетности
        risk_flags = financial_data.get("risk_flags") or {}
        flags_lines = []
        if risk_flags.get("positive_text"):
            flags_lines.append(f"Положительные факторы (данные ФНС): {risk_flags['positive_text']}")
        if risk_flags.get("negative_text"):
            flags_lines.append(f"Отрицательные факторы (данные ФНС): {risk_flags['negative_text']}")
        flags_block = "\n".join(flags_lines)

        if not balance and not profit_loss:
            # Бухотчетности нет вовсе, но есть флаги ФНС (иначе сюда бы не
            # дошли — см. проверку в analyze_financial_data) — отдельный,
            # более простой промпт без цифр, которых не существует
            return f"""
Проведи предварительную оценку компании {company_name} (ИНН: {inn}) на основе официальных данных ФНС России.

Бухгалтерская отчетность по этой компании в ФНС отсутствует, поэтому анализируй только следующие факторы:

{flags_block}

Пожалуйста, предоставь анализ в следующем формате:

1. ФИНАНСОВОЕ СОСТОЯНИЕ (краткая оценка на основе доступных факторов — явно укажи, что бухгалтерская отчетность недоступна)
2. КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ (укажи, что показатели недоступны — нет бухгалтерской отчетности)
3. РИСКИ (на основе перечисленных факторов ФНС)
4. РЕКОМЕНДАЦИИ
5. УРОВЕНЬ РИСКА (Низкий/Средний/Высокий)

Будь объективен. Не выдумывай числовые финансовые показатели, которых нет в данных.
"""

        current_year_block = f"""Подробные данные за последний отчетный год ({period}):

Бухгалтерский баланс:
- Активы: {balance.get('assets', '0')} руб.
- Внеоборотные активы: {balance.get('non_current_assets', '0')} руб.
- Оборотные активы: {balance.get('current_assets', '0')} руб.
- Собственный капитал: {balance.get('capital', '0')} руб.
- Долгосрочные обязательства: {balance.get('long_term_liabilities', '0')} руб.
- Краткосрочные обязательства: {balance.get('short_term_liabilities', '0')} руб.

Отчет о финансовых результатах:
- Выручка: {profit_loss.get('revenue', '0')} руб.
- Валовая прибыль: {profit_loss.get('gross_profit', '0')} руб.
- Прибыль до налогообложения: {profit_loss.get('profit', '0')} руб.
- Чистая прибыль: {profit_loss.get('net_profit', '0')} руб.
- EBITDA: {profit_loss.get('ebitda', '0')} руб."""

        if flags_block:
            current_year_block += f"\n\nДополнительные факторы ФНС (реестры, не бухотчетность):\n{flags_block}"

        if len(sorted_years) >= 2:
            year_blocks = []
            for year in sorted_years:
                yb = years[year].get("balance", {})
                ypl = years[year].get("profit_loss", {})
                year_blocks.append(
                    f"### {year} год\n"
                    f"- Активы: {yb.get('assets', '0')} руб.\n"
                    f"- Собственный капитал: {yb.get('capital', '0')} руб.\n"
                    f"- Выручка: {ypl.get('revenue', '0')} руб.\n"
                    f"- Чистая прибыль: {ypl.get('net_profit', '0')} руб."
                )
            years_block = "\n\n".join(year_blocks)

            prompt = f"""
Проведи финансовый анализ компании {company_name} (ИНН: {inn}) на основе отчетности за {len(sorted_years)} года ({sorted_years[0]}-{sorted_years[-1]}):

{years_block}

{current_year_block}

Пожалуйста, предоставь анализ в следующем формате:

1. ФИНАНСОВОЕ СОСТОЯНИЕ (краткая оценка на текущий момент, с учетом истории)
2. КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ (рентабельность, ликвидность, финансовая устойчивость на последний год)
3. ДИНАМИКА (как менялись показатели за {sorted_years[0]}-{sorted_years[-1]} годы — рост, спад или стабильность, с конкретными цифрами)
4. РИСКИ (выявленные риски и проблемы, включая риски, видимые из динамики и из дополнительных факторов ФНС, если они указаны)
5. РЕКОМЕНДАЦИИ (практические рекомендации)
6. УРОВЕНЬ РИСКА (Низкий/Средний/Высокий)

Пункты 1, 2 и 6 должны отражать текущее состояние компании, но с учетом тренда за все {len(sorted_years)} года — не только последний год в отрыве от истории.

Будь объективен, используй профессиональную терминологию, но объясняй доступно.
"""
        else:
            prompt = f"""
Проведи финансовый анализ компании {company_name} (ИНН: {inn}) за {period} год.

{current_year_block}

Пожалуйста, предоставь анализ в следующем формате:

1. ФИНАНСОВОЕ СОСТОЯНИЕ (краткая оценка)
2. КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ (рентабельность, ликвидность, финансовая устойчивость)
3. РИСКИ (выявленные риски и проблемы, включая дополнительные факторы ФНС, если они указаны)
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
            sections = self._parse_sections(content, SINGLE_ANALYSIS_LABELS)

            # Определяем уровень риска
            risk_level = self._determine_risk_level(content, sections)

            return {
                "summary": sections.get("ФИНАНСОВОЕ СОСТОЯНИЕ", "Анализ не выполнен"),
                "key_metrics": sections.get("КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ", ""),
                "dynamics": sections.get("ДИНАМИКА", ""),
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
                "dynamics": "",
                "risks": "",
                "recommendations": "",
                "risk_level": "Средний",
                "full_response": str(response)
            }

    @staticmethod
    def _clean_heading_line(line: str) -> str:
        """
        Снимает markdown-декорации ("**", "###", нумерацию "1.", ":") с начала
        строки, чтобы отличить настоящий заголовок секции от обычного
        предложения, которое просто упоминает слово вроде "риски" не в начале.
        Регистр не меняет — см. _heading_candidate (для сравнения с картой
        меток) и _parse_sections (где нужен оригинальный регистр остатка
        строки после заголовка).
        """
        cleaned = re.sub(r'^[#*\s]+', '', line.strip())
        cleaned = re.sub(r'^\d+[.)]\s*', '', cleaned)
        return cleaned.strip('*: \t')

    @classmethod
    def _heading_candidate(cls, line: str) -> str:
        """Верхний регистр _clean_heading_line — для сравнения с картой меток (там все ключи в верхнем регистре)"""
        return cls._clean_heading_line(line).upper()

    def _parse_sections(self, content: str, label_map: Dict[str, str]) -> Dict[str, str]:
        """
        Разбиение текста на секции по карте меток {вариант_заголовка: канонический_ключ}.

        Заголовком считается только строка, которая НАЧИНАЕТСЯ с одного из
        вариантов (после очистки от markdown/нумерации в _heading_candidate)
        — иначе обычное предложение вида "...могут возникать риски в
        случае..." само обрывает текущую секцию, едва начавшись. Варианты
        сравниваются от самого длинного к самому короткому, чтобы более
        специфичный ("ФИНАНСОВОЕ СОСТОЯНИЕ") матчился раньше своего же
        префикса ("ФИНАНСОВОЕ"), если оба есть в карте.

        Модель не всегда переносит текст секции на новую строку — иногда
        пишет "1. **РИСКИ**: <весь текст секции сразу>" одной строкой. Без
        учета остатка строки после заголовка такой текст терялся бы
        полностью (вся строка потреблялась как заголовок, а следующая
        строка уже могла быть заголовком следующей секции — реальный баг,
        воспроизведен на ответе модели для компании без бухотчетности,
        где секции "финансовое состояние"/"рекомендации" были однострочными,
        а "риски" — списком на отдельных строках и потому не терялись).
        """
        variants = sorted(label_map.keys(), key=len, reverse=True)
        sections = {}
        current_key = None
        current_content = []

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue

            cleaned = self._clean_heading_line(line)
            heading = cleaned.upper()
            matched = next((v for v in variants if heading.startswith(v)), None)
            if matched:
                if current_key and current_content:
                    sections[current_key] = '\n'.join(current_content).strip()
                current_key = label_map[matched]
                current_content = []
                remainder = cleaned[len(matched):].strip('*: \t')
                if remainder:
                    current_content.append(remainder)
            elif current_key:
                current_content.append(line)

        if current_key and current_content:
            sections[current_key] = '\n'.join(current_content).strip()

        return sections

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

    def _get_mock_comparison(self, companies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Оффлайн-сравнение при недоступности IO_NET"""

        def revenue_of(c: Dict[str, Any]) -> float:
            return self._safe_float(c.get("profit_loss", {}).get("revenue", "0"))

        leader = max(companies, key=revenue_of)
        names = ", ".join(c.get("company_name", "?") for c in companies)

        return {
            "summary": f"Сравнение выполнено по базовым метрикам (режим оффлайн) для: {names}.",
            "leader": f"{leader.get('company_name', '?')} — наибольшая выручка среди сравниваемых компаний.",
            "differences": "Детальное сравнение рисков недоступно в оффлайн-режиме.",
            "recommendation": "Для полноценного AI-сравнения повторите запрос позже.",
            "full_response": "Сравнение выполнено на основе базовых метрик (режим оффлайн)",
        }

    def _build_comparison_prompt(self, companies: List[Dict[str, Any]]) -> str:
        """Построение промпта для сравнения нескольких компаний"""
        blocks = []
        for c in companies:
            balance = c.get("balance", {})
            profit_loss = c.get("profit_loss", {})
            blocks.append(
                f"### {c.get('company_name', 'Неизвестная компания')} "
                f"(ИНН: {c.get('inn', '')}, период: {c.get('period', '')})\n"
                f"- Активы: {balance.get('assets', '0')} руб.\n"
                f"- Собственный капитал: {balance.get('capital', '0')} руб.\n"
                f"- Выручка: {profit_loss.get('revenue', '0')} руб.\n"
                f"- Прибыль до налогообложения: {profit_loss.get('profit', '0')} руб.\n"
                f"- Чистая прибыль: {profit_loss.get('net_profit', '0')} руб."
            )
        companies_block = "\n\n".join(blocks)

        return f"""
Сравни финансовое состояние следующих {len(companies)} компаний по данным бухгалтерской отчетности:

{companies_block}

Предоставь сравнительный анализ в следующем формате:

1. ОБЩИЙ ВЫВОД (краткое резюме сравнения)
2. ЛИДЕР (какая компания выглядит финансово сильнее и почему, или отметь, что явного лидера нет)
3. РАЗЛИЧИЯ И РИСКИ (ключевые различия между компаниями и риски каждой)
4. РЕКОМЕНДАЦИЯ (практический вывод для того, кто сравнивает эти компании)

Будь объективен, используй профессиональную терминологию, но объясняй доступно.
"""

    def _parse_comparison_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Парсинг ответа ИИ на сравнительный запрос"""
        try:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            sections = self._parse_sections(content, COMPARISON_LABELS)

            return {
                "summary": sections.get("ОБЩИЙ ВЫВОД", "Сравнение не выполнено"),
                "leader": sections.get("ЛИДЕР", ""),
                "differences": sections.get("РАЗЛИЧИЯ И РИСКИ", ""),
                "recommendation": sections.get("РЕКОМЕНДАЦИЯ", ""),
                "full_response": content,
            }
        except Exception as e:
            logger.error(f"Ошибка парсинга сравнительного ответа IO_NET: {e}")
            return {
                "summary": "Ошибка при сравнении данных",
                "leader": "",
                "differences": "",
                "recommendation": "",
                "full_response": str(response),
            }

    async def analyze_comparison(self, companies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Сравнительный анализ нескольких компаний с помощью ИИ
        """
        logger.info(f"Начало сравнительного анализа {len(companies)} компаний через IO_NET")

        try:
            prompt = self._build_comparison_prompt(companies)
            response = await self._send_request(prompt)
            analysis = self._parse_comparison_response(response)

            logger.info("Сравнительный анализ успешно завершен")
            return analysis

        except (aiohttp.ClientError, asyncio.TimeoutError, Exception) as e:
            logger.error(f"Ошибка при сравнительном анализе через IO_NET: {e}")
            logger.info("Использовано оффлайн-сравнение")
            return self._get_mock_comparison(companies)

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