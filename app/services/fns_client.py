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

# Сколько последних лет отчетности запрашивать для разбивки по годам в
# отчете (может быть меньше, если у компании нет данных за столько лет)
RECENT_YEARS_COUNT = 3


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
        risk_flags = await self._get_risk_flags(inn)

        staff_count = company_info["staff_count"]
        if not staff_count and risk_flags.get("staff_count"):
            # ССЧР (среднесписочная численность) внутри check.Позитив.РеестрМСП
            # оказалась более надежным источником, чем ОткрСведения.КолРаб —
            # см. комментарий в _get_company_info про непроверенность последнего
            staff_count = risk_flags["staff_count"]

        result = {
            "inn": inn,
            "company_name": company_info["name"],
            "short_name": company_info["short_name"],
            "ogrn": company_info["ogrn"],
            "period": financial.get("period", ""),
            "balance": financial.get("balance", {}),
            "profit_loss": financial.get("profit_loss", {}),
            "status": company_info["status"],
            "registration_date": company_info["registration_date"],
            "termination_date": company_info["termination_date"],
            "charter_capital": company_info["charter_capital"],
            "staff_count": staff_count,
            "okved": company_info["okved"],
            "egr_extra": company_info["egr_extra"],
            "legal_address": company_info["address"],
            "updated_at": datetime.utcnow().isoformat(),
            # {год: {"balance": ..., "profit_loss": ...}} за последние (до)
            # 3 года, от старого к новому; для ИП или при недоступности
            # отчетности — пустой словарь
            "years": financial.get("years", {}),
            # Флаги риска ФНС (метод check) — см. _get_risk_flags
            "risk_flags": risk_flags,
        }

        logger.info(f"Данные для ИНН {inn} получены: {result['company_name']}")
        return result

    @staticmethod
    def _summarize_egr_extra(block: Dict[str, Any]) -> str:
        """
        Сжатая сводка по Лицензиям/ДопВидДеят/Филиалам/Участиям/СПВЗ/Истории
        из egr — для промпта ИИ-анализа, не для отображения в отчете (см.
        ROADMAP). Эти блоки могут быть огромными (у Сбербанка, например,
        341 запись СПВЗ и 88 филиалов) — целиком в промпт не поместится и
        не нужно, модели достаточно сводки и нескольких свежих событий.
        Работает одинаково для ЮЛ и ИП (передаем блок целиком) — просто
        для ИП большинство списков обычно пустые, .get() это переживает
        без ошибок.
        """
        lines = []

        licenses = block.get("Лицензии") or []
        if licenses:
            types = sorted({l.get("ВидДеятельности", "") for l in licenses if l.get("ВидДеятельности")})
            preview = "; ".join(types[:3])
            if len(types) > 3:
                preview += f" и еще {len(types) - 3}"
            lines.append(f"Лицензии: {len(licenses)} шт. ({preview})")

        extra_okved = block.get("ДопВидДеят") or []
        if extra_okved:
            texts = [f"{d.get('Код', '')} — {d.get('Текст', '')}" for d in extra_okved if d.get("Текст")]
            if texts:
                lines.append("Дополнительные виды деятельности: " + "; ".join(texts))

        branches = block.get("Филиалы") or []
        if branches:
            lines.append(f"Филиалы: {len(branches)} шт.")

        participations = block.get("Участия") or []
        if participations:
            names = [p.get("НаимСокрЮЛ", "") for p in participations if p.get("НаимСокрЮЛ")][:3]
            preview = "; ".join(names)
            if len(participations) > len(names):
                preview += f" и еще {len(participations) - len(names)}"
            lines.append(f"Участие в других организациях: {len(participations)} шт. ({preview})")

        spvz = block.get("СПВЗ") or []
        if spvz:
            recent = sorted(spvz, key=lambda x: x.get("Дата", ""), reverse=True)[:3]
            recent_text = "; ".join(f"{r.get('Дата', '')}: {r.get('Текст', '')}" for r in recent)
            lines.append(f"Регистрационные действия: {len(spvz)} записей за все время, последние — {recent_text}")

        history = block.get("История") or {}
        if history:
            parts = [f"{key}: {len(sub)} изм." for key, sub in history.items() if isinstance(sub, (dict, list))]
            if parts:
                lines.append("История изменений сведений: " + ", ".join(parts))

        return "\n".join(lines)

    async def _get_company_info(self, inn: str) -> Optional[Dict[str, Any]]:
        """
        Реквизиты компании/ИП по данным ЕГРЮЛ/ЕГРИП (метод egr)
        """
        data = await self._call("egr", inn)
        items = data.get("items") or []
        if not items:
            return None

        entry = items[0]

        def _format_okved(block: Dict[str, Any]) -> str:
            """
            Основной вид деятельности (ОКВЭД) — проверено на реальных
            данных для ЮЛ (Сбербанк: "64.19 — Денежное посредничество
            прочее") и для ИП (Мингараев: "13.92 — Производство готовых
            текстильных изделий, кроме одежды"), структура ОснВидДеят
            одинакова для обоих типов
            """
            osn = block.get("ОснВидДеят") or {}
            code = osn.get("Код", "")
            text = osn.get("Текст", "")
            if code and text:
                return f"{code} — {text}"
            return code or text

        if "ЮЛ" in entry:
            ul = entry["ЮЛ"]
            full_name = ul.get("НаимПолнЮЛ") or ""
            short_name = ul.get("НаимСокрЮЛ") or ""
            name = full_name or short_name or "Неизвестно"
            return {
                "name": name,
                # показываем сокращенное наименование отдельной строкой,
                # только если оно реально отличается от того, что уже
                # показано как основное имя компании
                "short_name": short_name if short_name and short_name != name else "",
                "ogrn": ul.get("ОГРН", ""),
                "status": ul.get("Статус", "Неизвестно"),
                "registration_date": ul.get("ДатаРег", ""),
                # Проверено на реальной ликвидированной компании (ИНН
                # 9110032185): ДатаПрекр = дата исключения из ЕГРЮЛ,
                # совпадает с СтатусДата
                "termination_date": ul.get("ДатаПрекр", ""),
                # Капитал.СумКап подтвержден на реальных данных (Сбербанк:
                # 67 760 844 000 руб. — сходится с известным реальным
                # уставным капиталом), значение уже в рублях (не в тысячах,
                # в отличие от бухотчетности методом bo)
                "charter_capital": (ul.get("Капитал") or {}).get("СумКап", ""),
                # НЕ ПОДТВЕРЖДЕНО на реальных данных: по документации
                # api-fns.ru поле должно быть ОткрСведения.КолРаб, но ни в
                # одном из проверенных живых ответов (Сбербанк, ликвидированная
                # компания, ИП) оно не встретилось заполненным — либо не все
                # компании его раскрывают, либо название неточное. .get() —
                # если поля нет, строка просто не покажется в отчете
                "staff_count": (ul.get("ОткрСведения") or {}).get("КолРаб", ""),
                "okved": _format_okved(ul),
                # Сжатая сводка Лицензии/ДопВидДеят/Филиалы/Участия/СПВЗ/
                # История — только для промпта ИИ, в отчете не показываем
                # (см. ROADMAP: возможен отдельный раздел "справка о компании")
                "egr_extra": self._summarize_egr_extra(ul),
                "address": (ul.get("Адрес") or {}).get("АдресПолн", ""),
            }

        if "ИП" in entry:
            ip = entry["ИП"]
            return {
                "name": ip.get("ФИОПолн", "Неизвестно"),
                "short_name": "",
                # У ИП нет уставного капитала как правовой категории
                "charter_capital": "",
                "staff_count": (ip.get("ОткрСведения") or {}).get("КолРаб", ""),
                "okved": _format_okved(ip),
                "egr_extra": self._summarize_egr_extra(ip),
                "ogrn": ip.get("ОГРНИП", ""),
                "status": ip.get("Статус", "Неизвестно"),
                "registration_date": ip.get("ДатаРег", ""),
                "termination_date": ip.get("ДатаПрекр", ""),  # см. пояснение выше для ЮЛ
                "address": (ip.get("Адрес") or {}).get("АдресПолн", ""),
            }

        return None

    async def _get_risk_flags(self, inn: str) -> Dict[str, Any]:
        """
        Флаги риска ФНС (метод check) — готовые признаки добросовестности/
        неблагонадежности контрагента. Проверено на 4 реальных примерах
        (крупный банк, ликвидированная компания, малое предприятие, ИП):
        Позитив: Лицензии, Филиалы, КапБолее50тыс, РеестрМСП{...}, ПоддержкаМСП[...]
        Негатив: РеестрМассАдрес, МассАдрес, Статус, ИсклИзРеестраМСП,
        НедостоверАдрес, БлокСчета, РискНалогПроверки. Оба блока всегда
        содержат готовый текст в "Текст" — используем как есть, без
        собственного форматирования отдельных флагов.

        check — не критичный для отчета источник: при ошибке отчет должен
        собраться и без него, поэтому исключение наружу не пробрасываем.
        """
        empty = {"positive_text": "", "negative_text": "", "positive": {}, "negative": {}, "staff_count": ""}
        try:
            data = await self._call("check", inn)
        except Exception as e:
            logger.warning(f"Не удалось получить флаги ФНС (check) для {inn}: {e}")
            return empty

        items = data.get("items") or []
        if not items:
            return empty

        entry = items[0]
        block = entry.get("ЮЛ") or entry.get("ИП") or {}
        positive = block.get("Позитив") or {}
        negative = block.get("Негатив") or {}

        # ССЧР (среднесписочная численность) лежит внутри Позитив.РеестрМСП —
        # более надежный источник staff_count, чем ОткрСведения.КолРаб (см.
        # комментарий в _get_company_info)
        staff_count = (positive.get("РеестрМСП") or {}).get("ССЧР", "")

        return {
            "positive_text": positive.get("Текст", ""),
            "negative_text": negative.get("Текст", ""),
            "positive": positive,
            "negative": negative,
            "staff_count": staff_count,
        }

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

        available_years = sorted(company_block.keys())
        recent_years = available_years[-RECENT_YEARS_COUNT:]
        latest_year = recent_years[-1]

        # Тип формы определяем по последнему году — банк не меняет форму
        # отчетности от года к году, одного year_data достаточно
        is_credit = any(key.startswith("credit_") for key in company_block[latest_year].keys())
        parse = self._parse_credit_form if is_credit else self._parse_standard_form
        if is_credit:
            logger.info(f"ИНН {inn}: отчетность кредитной организации (форма 0409806/807)")

        years: Dict[str, Dict[str, Any]] = {}
        for year in recent_years:
            balance, profit_loss = parse(company_block[year])
            years[year] = {"balance": balance, "profit_loss": profit_loss}

        return {
            "period": latest_year,
            "balance": years[latest_year]["balance"],
            "profit_loss": years[latest_year]["profit_loss"],
            # Данные за последние (до) 3 года, от старого к новому, для
            # отчета с разбивкой по годам и AI-анализа динамики
            "years": years,
        }

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
