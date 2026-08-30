# app/services/mock_data.py
"""
Мок-данные для тестирования без реальных API
"""

MOCK_COMPANIES = {
    "7707083893": {
        "name": "ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО \"СБЕРБАНК РОССИИ\"",
        "short_name": "ПАО СБЕРБАНК",
        "ogrn": "1027700132195",
        "status": "Действующее",
        "registration_date": "1991-06-20",
        "charter_capital": "67760844000",
        "staff_count": "",
        # Реальный ответ метода check (проверен live-запросом 30.08.2026)
        "risk_flags": {
            "positive_text": "Есть лицензии (15 шт.); Есть филиалы (88 шт.); Уставный капитал 67760844 тыс. руб.",
            "negative_text": "В реестре массовых адресов (13 юрлиц, в БД найдено - 17 юрлиц)",
        },
        "address": "г. Москва, ул. Вавилова, д. 19",
        "period": "2024",
        "balance": {
            "assets": "45000000000",
            "liabilities": "30000000000",
            "capital": "15000000000",
            "non_current_assets": "25000000000",
            "current_assets": "20000000000",
            "long_term_liabilities": "18000000000",
            "short_term_liabilities": "12000000000",
        },
        "profit_loss": {
            "revenue": "12000000000",
            "profit": "3500000000",
            "loss": "0",
            "gross_profit": "5000000000",
            "operating_expenses": "1500000000",
            "net_profit": "2800000000",
            "ebitda": "4200000000",
        }
    },
    "7702070139": {
        "name": "ПАО Газпром",
        "short_name": "",
        "ogrn": "1027700070518",
        "status": "Действующее",
        "registration_date": "1993-02-25",
        "charter_capital": "",
        "staff_count": "",
        "address": "г. Москва, ул. Наметкина, д. 16",
        "period": "2024",
        "balance": {
            "assets": "28000000000",
            "liabilities": "18000000000",
            "capital": "10000000000",
            "non_current_assets": "18000000000",
            "current_assets": "10000000000",
            "long_term_liabilities": "12000000000",
            "short_term_liabilities": "6000000000",
        },
        "profit_loss": {
            "revenue": "8500000000",
            "profit": "2100000000",
            "loss": "0",
            "gross_profit": "3800000000",
            "operating_expenses": "1700000000",
            "net_profit": "1800000000",
            "ebitda": "3000000000",
        }
    },
    "7736207543": {
        "name": "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ \"ТЕСТОВАЯ КОМПАНИЯ\"",
        "short_name": "ООО ТЕСТОВАЯ КОМПАНИЯ",
        "ogrn": "1037739345678",
        "status": "Ликвидировано",
        "registration_date": "2003-05-14",
        "termination_date": "2025-11-03",
        "charter_capital": "1000000",
        "staff_count": "42",
        "address": "г. Москва, ул. Тестовая, д. 1",
        "period": "2024",
        "balance": {
            "assets": "5000000000",
            "liabilities": "3000000000",
            "capital": "2000000000",
            "non_current_assets": "3000000000",
            "current_assets": "2000000000",
            "long_term_liabilities": "1500000000",
            "short_term_liabilities": "1500000000",
        },
        "profit_loss": {
            "revenue": "2500000000",
            "profit": "500000000",
            "loss": "0",
            "gross_profit": "1200000000",
            "operating_expenses": "700000000",
            "net_profit": "400000000",
            "ebitda": "800000000",
        }
    },
    # Реальная компания (проверена live-запросом к api-fns.ru 26.08.2026),
    # исключена из ЕГРЮЛ как недействующее юрлицо (ст. 21.1 129-ФЗ) — для
    # таких компаний бухотчетность в ФНС обычно отсутствует, поэтому здесь
    # намеренно пустые balance/profit_loss (без разбивки по годам) — заодно
    # проверяет отображение "Н/Д" одновременно с датой ликвидации
    "9110032185": {
        "name": "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ \"УПРАВЛЯЮЩАЯ КОМПАНИЯ КОМФОРТ-СЕРВИС\"",
        "short_name": "ООО \"УК КОМФОРТ-СЕРВИС\"",
        "ogrn": "1239100007244",
        "status": "Ликвидировано по 129-ФЗ",
        "registration_date": "2023-06-07",
        "termination_date": "2025-03-14",
        "charter_capital": "10000",
        "staff_count": "",
        # Реальный ответ метода check (проверен live-запросом 30.08.2026)
        "risk_flags": {
            "positive_text": "",
            "negative_text": (
                "Ликвидировано по 129-ФЗ (14.03.2025); Исключена из реестра МСП; "
                "Недостоверный адрес; Блокировка счета (от 27.01.2025, РНКБ БАНК (ПАО))"
            ),
        },
        "address": "",
        "period": "",
        "balance": {},
        "profit_loss": {},
    }
}

def _generate_recent_years(latest_year: str, balance: dict, profit_loss: dict, yearly_growth: float = 0.10) -> dict:
    """
    Синтетическая генерация данных за 2 предыдущих года на основе
    последнего года и примерного темпа роста — только для мок-режима,
    чтобы локально тестировать разбивку отчета по годам без реального API
    """
    years = {}
    latest = int(latest_year)
    for offset in (2, 1, 0):  # от старого к новому
        year = str(latest - offset)
        factor = (1 - yearly_growth) ** offset
        years[year] = {
            "balance": {k: str(round(int(v) * factor)) for k, v in balance.items()},
            "profit_loss": {k: str(round(int(v) * factor)) for k, v in profit_loss.items()},
        }
    return years


def get_mock_financial_data(inn: str):
    """Получение мок-финансовых данных"""
    company = MOCK_COMPANIES.get(inn)
    if company:
        return {
            "inn": inn,
            "company_name": company["name"],
            "short_name": company.get("short_name", ""),
            "ogrn": company["ogrn"],
            "period": company["period"],
            "balance": company["balance"],
            "profit_loss": company["profit_loss"],
            "status": company["status"],
            "registration_date": company["registration_date"],
            "termination_date": company.get("termination_date", ""),
            "charter_capital": company.get("charter_capital", ""),
            "staff_count": company.get("staff_count", ""),
            "risk_flags": company.get("risk_flags", {"positive_text": "", "negative_text": ""}),
            "legal_address": company["address"],
            "updated_at": "2026-07-26T18:00:00",
            "years": (
                _generate_recent_years(company["period"], company["balance"], company["profit_loss"])
                if company["period"] else {}
            ),
        }
    return None