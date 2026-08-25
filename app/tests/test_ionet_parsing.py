# app/tests/test_ionet_parsing.py
"""
Тестирование разбора текстового ответа ИИ (IONETClient) — без обращения
к реальному API, только на синтетических примерах текста.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.ionet_client import IONETClient, SINGLE_ANALYSIS_LABELS, COMPARISON_LABELS

client = IONETClient()


def test_heading_candidate_strips_decorations():
    """Заголовок очищается от markdown-жирного, нумерации и двоеточия"""
    assert client._heading_candidate("**1. РИСКИ**") == "РИСКИ"
    assert client._heading_candidate("### Риски:") == "РИСКИ"
    assert client._heading_candidate("Риски") == "РИСКИ"
    assert client._heading_candidate("  2) Ключевые показатели  ") == "КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ"


def test_parse_sections_does_not_break_on_word_inside_sentence():
    """
    Регресс-тест на реальный баг: раньше секция обрывалась при любом
    упоминании ключевого слова ГДЕ УГОДНО в строке, а не только в
    заголовке. Обычное предложение внутри "ФИНАНСОВОЕ СОСТОЯНИЕ",
    упоминающее слово "риски" не в начале строки, не должно создавать
    новую секцию.
    """
    content = (
        "**1. ФИНАНСОВОЕ СОСТОЯНИЕ**\n\n"
        "Компания демонстрирует стабильное состояние, однако наблюдается "
        "зависимость от заемных средств, что может создавать определенные "
        "риски в случае изменения рыночной конъюнктуры.\n\n"
        "**2. КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ**\n\n"
        "Рентабельность 32%.\n\n"
        "**3. РИСКИ**\n\n"
        "Основной риск — концентрация на одном рынке.\n\n"
        "**4. РЕКОМЕНДАЦИИ**\n\n"
        "Рекомендуется диверсификация активов.\n\n"
        "**5. УРОВЕНЬ РИСКА**\n"
        "Средний\n"
    )

    sections = client._parse_sections(content, SINGLE_ANALYSIS_LABELS)

    assert "ФИНАНСОВОЕ СОСТОЯНИЕ" in sections
    assert "риски" in sections["ФИНАНСОВОЕ СОСТОЯНИЕ"]
    assert sections["КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ"] == "Рентабельность 32%."
    assert sections["РИСКИ"] == "Основной риск — концентрация на одном рынке."
    assert sections["РЕКОМЕНДАЦИИ"] == "Рекомендуется диверсификация активов."
    assert sections["УРОВЕНЬ РИСКА"] == "Средний"


def test_parse_analysis_response_extracts_risk_level():
    """Полный путь: choices -> секции -> уровень риска"""
    content = (
        "1. ФИНАНСОВОЕ СОСТОЯНИЕ\nВсе стабильно.\n\n"
        "2. КЛЮЧЕВЫЕ ПОКАЗАТЕЛИ\nРентабельность высокая.\n\n"
        "3. РИСКИ\nМинимальные.\n\n"
        "4. РЕКОМЕНДАЦИИ\nПродолжать.\n\n"
        "5. УРОВЕНЬ РИСКА\nНизкий\n"
    )
    response = {"choices": [{"message": {"content": content}}]}

    result = client._parse_analysis_response(response)

    assert result["summary"] == "Все стабильно."
    assert result["risk_level"] == "Низкий"
    assert result["risks"] == "Минимальные."


def test_parse_comparison_response():
    """Сравнительный ответ парсится своей картой меток, не конфликтует с одиночной"""
    content = (
        "1. ОБЩИЙ ВЫВОД\nОбе компании устойчивы.\n\n"
        "2. ЛИДЕР\nСбербанк опережает по всем показателям.\n\n"
        "3. РАЗЛИЧИЯ И РИСКИ\nГазпром зависит от внешней конъюнктуры.\n\n"
        "4. РЕКОМЕНДАЦИЯ\nРассмотреть Сбербанк.\n"
    )
    response = {"choices": [{"message": {"content": content}}]}

    result = client._parse_comparison_response(response)

    assert result["summary"] == "Обе компании устойчивы."
    assert result["leader"] == "Сбербанк опережает по всем показателям."
    assert "Газпром" in result["differences"]
    assert result["recommendation"] == "Рассмотреть Сбербанк."


def test_parse_sections_handles_missing_sections_gracefully():
    """Если модель не написала часть секций — просто нет соответствующих ключей, не падаем"""
    sections = client._parse_sections("Просто текст без заголовков вообще.", SINGLE_ANALYSIS_LABELS)
    assert sections == {}


def test_determine_risk_level_fallback_to_content_scan():
    """Если секция УРОВЕНЬ РИСКА не найдена, ищем слово в общем тексте"""
    content = "Какой-то текст. Общий уровень риска: высокий."
    level = client._determine_risk_level(content, {})
    assert level == "Высокий"


async def test_analyze_financial_data_skips_api_when_no_data():
    """
    Регресс-тест на реальный баг: у компании без бухотчетности (balance и
    profit_loss пустые) модель раньше получала фиктивные нули и делала
    вывод вроде "высокий риск" по несуществующим данным. Теперь для
    пустых данных запрос к API вообще не отправляется — сразу честный
    ответ "данных недостаточно".
    """
    financial_data = {
        "company_name": "ООО Без отчетности",
        "balance": {},
        "profit_loss": {},
    }

    result = await client.analyze_financial_data(financial_data)

    assert result["risk_level"] == "Средний"
    assert "отсутствует" in result["summary"]


if __name__ == "__main__":
    test_heading_candidate_strips_decorations()
    test_parse_sections_does_not_break_on_word_inside_sentence()
    test_parse_analysis_response_extracts_risk_level()
    test_parse_comparison_response()
    test_parse_sections_handles_missing_sections_gracefully()
    test_determine_risk_level_fallback_to_content_scan()
    print("OK")
