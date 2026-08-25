# app/tests/test_report_formatting.py
"""
Тестирование форматирования данных для HTML-отчетов (ReportGenerator) —
без обращения к API и без рендеринга шаблонов, только чистые функции.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.report_generator import ReportGenerator


def test_render_text_converts_markdown_bold():
    """
    Регресс-тест: модель форматирует ответ markdown-ом (**жирный**), а
    Jinja2-шаблон раньше вставлял текст как есть — в HTML показывались
    буквальные звездочки вместо жирного начертания.
    """
    result = ReportGenerator._render_text("- **Больший объем активов**: Сбербанк лидирует")
    assert "<strong>Больший объем активов</strong>" in result
    assert "**" not in result


def test_render_text_escapes_html_special_chars():
    """Сырой текст (включая имена компаний из ФНС) не должен превращаться в HTML-разметку"""
    result = ReportGenerator._render_text('ООО «Ромашка & Ко» <script>alert(1)</script>')
    assert "&amp;" in result
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


def test_render_text_handles_empty_and_none():
    assert ReportGenerator._render_text("") == ""
    assert ReportGenerator._render_text(None) is None


def test_format_number_negative_values():
    """
    Регресс-тест: отрицательные числа (компания в убытке) раньше не
    форматировались — str.isdigit() возвращает False для "-123", и функция
    отдавала сырую строку вместо "млн"/"млрд".
    """
    result = ReportGenerator._format_number(-12_254_963)
    assert result.startswith("-")
    assert "млн" in result


def test_format_number_scale_thresholds():
    assert "тыс" in ReportGenerator._format_number(5_000)
    assert "млн" in ReportGenerator._format_number(5_000_000)
    assert "млрд" in ReportGenerator._format_number(5_000_000_000)
    assert "трлн" in ReportGenerator._format_number(5_000_000_000_000)
    assert ReportGenerator._format_number(500) == "500"


def test_format_number_passes_through_not_available_label():
    assert ReportGenerator._format_number("Н/Д") == "Н/Д"


def test_chart_point_distinguishes_missing_from_real_zero():
    """
    Регресс-тест: "недоступно" (banковские "Н/Д" поля) не должно рисоваться
    на графике как настоящий ноль — это два разных состояния.
    """
    assert ReportGenerator._chart_point("Н/Д") is None
    assert ReportGenerator._chart_point(None) is None
    assert ReportGenerator._chart_point("") is None
    assert ReportGenerator._chart_point("0") == 0.0
    assert ReportGenerator._chart_point("-500") == -500.0
    assert ReportGenerator._chart_point("12345") == 12345.0


def test_pick_scale_selects_matching_unit():
    assert ReportGenerator._pick_scale([500]) == (1, "₽")
    assert ReportGenerator._pick_scale([5_000]) == (1_000, "тыс ₽")
    assert ReportGenerator._pick_scale([5_000_000]) == (1_000_000, "млн ₽")
    assert ReportGenerator._pick_scale([5_000_000_000]) == (1_000_000_000, "млрд ₽")
    assert ReportGenerator._pick_scale([5_000_000_000_000]) == (1_000_000_000_000, "трлн ₽")
    # масштаб определяется по максимальному значению в наборе
    assert ReportGenerator._pick_scale([100, 5_000_000_000]) == (1_000_000_000, "млрд ₽")
    assert ReportGenerator._pick_scale([]) == (1, "₽")


if __name__ == "__main__":
    test_render_text_converts_markdown_bold()
    test_render_text_escapes_html_special_chars()
    test_render_text_handles_empty_and_none()
    test_format_number_negative_values()
    test_format_number_scale_thresholds()
    test_format_number_passes_through_not_available_label()
    test_chart_point_distinguishes_missing_from_real_zero()
    test_pick_scale_selects_matching_unit()
    print("OK")
