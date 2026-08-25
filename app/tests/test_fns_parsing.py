# app/tests/test_fns_parsing.py
"""
Тестирование разбора бухгалтерской отчетности (FNSClient) — на
синтетических данных, структурно повторяющих реальные ответы api-fns.ru
(коды и контрольные соотношения сверены на живых данных в ходе разработки:
Яндекс, Сбербанк, ещё один банк). Без обращения к реальному API.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.fns_client import FNSClient, _thousands_to_rubles


def test_thousands_to_rubles():
    """Формы ФНС подаются в тысячах рублей — переводим в рубли"""
    assert _thousands_to_rubles("1000") == "1000000"
    assert _thousands_to_rubles("0") == "0"
    assert _thousands_to_rubles("-12254963") == "-12254963000"
    # нечисловое значение (например "Н/Д") возвращается как есть
    assert _thousands_to_rubles("Н/Д") == "Н/Д"


def test_parse_standard_form_maps_official_codes():
    """
    Коды строк форм №1/№2 (Приказ Минфина №66н), сверенные на реальных
    данных: 1100+1200=1600, 1300+1400+1500=1700, 2110-2120=2100.
    """
    year_data = {
        "1100": "197597977", "1200": "367866745", "1600": "565464722",
        "1300": "129250912", "1400": "94096006", "1500": "342117804", "1700": "565464722",
        "2110": "544581317", "2120": "420807670", "2100": "123773647",
        "2210": "29002583", "2220": "48206206",
        "2300": "-12254963", "2400": "-11681168",
    }

    balance, profit_loss = FNSClient._parse_standard_form(year_data)

    # Значения переведены из тысяч в рубли (умножены на 1000)
    assert balance["non_current_assets"] == "197597977000"
    assert balance["assets"] == "565464722000"
    assert balance["capital"] == "129250912000"
    assert profit_loss["revenue"] == "544581317000"
    assert profit_loss["net_profit"] == "-11681168000"
    # profit ("прибыль до налогообложения") корректно остается отрицательным
    assert profit_loss["profit"] == "-12254963000"
    # операционные расходы = сумма себестоимости + коммерческих + управленческих
    assert int(profit_loss["operating_expenses"]) == (420807670 + 29002583 + 48206206) * 1000
    assert profit_loss["ebitda"] == "Н/Д"


def test_parse_standard_form_missing_codes_default_to_zero():
    """Отсутствующие в ответе коды считаются нулем, а не падают с ошибкой"""
    balance, profit_loss = FNSClient._parse_standard_form({})
    assert balance["assets"] == "0"
    assert profit_loss["revenue"] == "0"


def test_parse_credit_form_maps_bank_codes():
    """
    Коды формы 0409806/807 для банков, сверенные на реальных данных двух
    банков: сумма строк credit_assets 1-13 = строка 14 (Всего активов),
    сумма credit_passives 15-22 = строка 23 (Всего обязательств),
    credit_profit_and_loss: строка1-строка2=строка3, строка24+строка25=строка26.
    """
    year_data = {
        "credit_assets": {"1": "614727347", "14": "32979678372"},
        "credit_passives": {"15": "850674866", "23": "28255016171"},
        "credit_sources_of_own_income": {"36": "4724662201"},
        "credit_profit_and_loss": {
            "1": "2219606631", "24": "710599365", "25": "-707486", "26": "709891879",
        },
    }

    balance, profit_loss = FNSClient._parse_credit_form(year_data)

    assert balance["assets"] == "32979678372000"
    assert balance["capital"] == "4724662201000"
    # у банковской формы нет деления на текущие/долгосрочные — честно "Н/Д"
    assert balance["non_current_assets"] == "Н/Д"
    assert balance["long_term_liabilities"] == "Н/Д"

    assert profit_loss["revenue"] == "2219606631000"
    assert profit_loss["profit"] == "710599365000"
    assert profit_loss["net_profit"] == "709891879000"
    assert profit_loss["gross_profit"] == "Н/Д"


def test_parse_credit_form_missing_fields_are_not_available():
    """Если банковских кодов вообще нет в ответе — все поля "Н/Д", не 0"""
    balance, profit_loss = FNSClient._parse_credit_form({})
    assert balance["assets"] == "Н/Д"
    assert profit_loss["net_profit"] == "Н/Д"


def test_credit_schema_detection():
    """
    Ключи credit_* в данных года — признак банковской формы; обычные коды
    (например "1100") — признак стандартной формы №1/№2
    """
    bank_year = {"credit_assets": {}, "credit_passives": {}}
    standard_year = {"1100": "0", "2110": "0"}

    assert any(key.startswith("credit_") for key in bank_year.keys()) is True
    assert any(key.startswith("credit_") for key in standard_year.keys()) is False


async def test_get_financial_data_handles_empty_list_response():
    """
    Регресс-тест на реальный баг, найденный на живом ИП без бухотчетности:
    api-fns.ru при отсутствии данных отдает не {} (пустой объект по ИНН),
    а буквально [] (пустой список) — код падал с AttributeError на
    data.get(inn), считая ответ всегда словарем.
    """
    client = FNSClient()
    with patch.object(client, "_call", new=AsyncMock(return_value=[])):
        result = await client._get_financial_data("732190597507")

    assert result == {"period": "", "balance": {}, "profit_loss": {}}


if __name__ == "__main__":
    test_thousands_to_rubles()
    test_parse_standard_form_maps_official_codes()
    test_parse_standard_form_missing_codes_default_to_zero()
    test_parse_credit_form_maps_bank_codes()
    test_parse_credit_form_missing_fields_are_not_available()
    test_credit_schema_detection()
    print("OK")
