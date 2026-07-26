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
            "assets": "45_000_000_000",
            "liabilities": "30_000_000_000",
            "capital": "15_000_000_000",
            "non_current_assets": "25_000_000_000",
            "current_assets": "20_000_000_000",
            "long_term_liabilities": "18_000_000_000",
            "short_term_liabilities": "12_000_000_000",
        },
        "profit_loss": {
            "revenue": "12_000_000_000",
            "profit": "3_500_000_000",
            "loss": "0",
            "gross_profit": "5_000_000_000",
            "operating_expenses": "1_500_000_000",
            "net_profit": "2_800_000_000",
            "ebitda": "4_200_000_000",
        }
    },
    "7702070139": {
        "name": "ПАО Газпром",
        "ogrn": "1027700070518",
        "status": "Активна",
        "address": "г. Москва, ул. Наметкина, д. 16",
        "period": "2024",
        "balance": {
            "assets": "28_000_000_000",
            "liabilities": "18_000_000_000",
            "capital": "10_000_000_000",
            "non_current_assets": "18_000_000_000",
            "current_assets": "10_000_000_000",
            "long_term_liabilities": "12_000_000_000",
            "short_term_liabilities": "6_000_000_000",
        },
        "profit_loss": {
            "revenue": "8_500_000_000",
            "profit": "2_100_000_000",
            "loss": "0",
            "gross_profit": "3_800_000_000",
            "operating_expenses": "1_700_000_000",
            "net_profit": "1_800_000_000",
            "ebitda": "3_000_000_000",
        }
    },
    "7736207543": {
        "name": "ООО Тестовая Компания",
        "ogrn": "1037739345678",
        "status": "Активна",
        "address": "г. Москва, ул. Тестовая, д. 1",
        "period": "2024",
        "balance": {
            "assets": "5_000_000_000",
            "liabilities": "3_000_000_000",
            "capital": "2_000_000_000",
            "non_current_assets": "3_000_000_000",
            "current_assets": "2_000_000_000",
            "long_term_liabilities": "1_500_000_000",
            "short_term_liabilities": "1_500_000_000",
        },
        "profit_loss": {
            "revenue": "2_500_000_000",
            "profit": "500_000_000",
            "loss": "0",
            "gross_profit": "1_200_000_000",
            "operating_expenses": "700_000_000",
            "net_profit": "400_000_000",
            "ebitda": "800_000_000",
        }
    }
}


def get_mock_company(inn: str):
    """Получение мок-данных компании"""
    return MOCK_COMPANIES.get(inn)


def get_mock_financial_data(inn: str):
    """Получение мок-финансовых данных"""
    company = get_mock_company(inn)
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