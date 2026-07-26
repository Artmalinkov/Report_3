# app/services/mock_data.py
"""
Мок-данные для тестирования без реальных API
"""

MOCK_COMPANIES = {
    "7707083893": {
        "name": "ПАО Сбербанк",
        "ogrn": "1027700132195",
        "status": "Активна",
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
        "ogrn": "1027700070518",
        "status": "Активна",
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
        "name": "ООО Тестовая Компания",
        "ogrn": "1037739345678",
        "status": "Активна",
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
    }
}

def get_mock_financial_data(inn: str):
    """Получение мок-финансовых данных"""
    company = MOCK_COMPANIES.get(inn)
    if company:
        return {
            "inn": inn,
            "company_name": company["name"],
            "ogrn": company["ogrn"],
            "period": company["period"],
            "balance": company["balance"],
            "profit_loss": company["profit_loss"],
            "status": company["status"],
            "legal_address": company["address"],
            "updated_at": "2026-07-26T18:00:00"
        }
    return None