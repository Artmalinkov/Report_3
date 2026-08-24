# app/services/report_generator.py
"""
Генератор HTML отчетов
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from loguru import logger
from jinja2 import Template


class ReportGenerator:
    """Генератор HTML-отчетов"""

    def __init__(self):
        self.report_dir = Path(__file__).parent.parent.parent / "reports"
        self.template_dir = Path(__file__).parent.parent.parent / "templates"
        self.report_dir.mkdir(exist_ok=True)
        self._chartjs_lib = self._load_chartjs()

    def _load_chartjs(self) -> str:
        """
        Загружает вендоренную библиотеку Chart.js (templates/vendor/) один
        раз и вставляет её содержимое в каждый отчет целиком — отчеты
        рассылаются как самостоятельные HTML-файлы и должны открываться
        без интернета, поэтому графики не тянутся с CDN
        """
        path = self.template_dir / "vendor" / "chart.umd.min.js"
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("templates/vendor/chart.umd.min.js не найден — графики в отчетах не будут работать")
            return ""

    async def generate_report(
            self,
            inn: str,
            financial_data: Dict[str, Any],
            analysis: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Генерация HTML-отчета

        Args:
            inn: ИНН компании
            financial_data: Данные финансовой отчетности
            analysis: Результаты анализа ИИ

        Returns:
            Tuple[str, str]: (путь к файлу, HTML содержимое)
        """
        logger.info(f"Генерация отчета для ИНН {inn}")

        try:
            # Загружаем шаблон
            template_path = self.template_dir / "report_template.html"
            if not template_path.exists():
                logger.warning("Шаблон не найден, создаем базовый шаблон")
                template_content = self._create_default_template()
            else:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()

            # Подготавливаем данные для шаблона
            context = self._prepare_template_context(inn, financial_data, analysis)

            # Генерируем HTML
            template = Template(template_content)
            html_content = template.render(**context)

            # Сохраняем файл
            filename = f"report_{inn}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath = self.report_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"Отчет сохранен: {filepath}")
            return str(filepath), html_content

        except Exception as e:
            logger.error(f"Ошибка при генерации отчета: {e}")
            raise

    async def generate_comparison_report(
            self,
            companies: List[Dict[str, Any]],
            comparison: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Генерация HTML-отчета сравнения нескольких компаний

        Args:
            companies: Список financial_data по каждой компании
            comparison: Результат IONETClient.analyze_comparison

        Returns:
            Tuple[str, str]: (путь к файлу, HTML содержимое)
        """
        inns = "_".join(c.get("inn", "") for c in companies)
        logger.info(f"Генерация сравнительного отчета для ИНН: {inns}")

        try:
            template_path = self.template_dir / "comparison_report_template.html"
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            context = self._prepare_comparison_context(companies, comparison)

            template = Template(template_content)
            html_content = template.render(**context)

            filename = f"comparison_{inns}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath = self.report_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"Сравнительный отчет сохранен: {filepath}")
            return str(filepath), html_content

        except Exception as e:
            logger.error(f"Ошибка при генерации сравнительного отчета: {e}")
            raise

    def _prepare_comparison_context(
            self,
            companies: List[Dict[str, Any]],
            comparison: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Подготовка данных для шаблона сравнения"""
        rows = []
        for c in companies:
            balance = c.get("balance", {})
            profit_loss = c.get("profit_loss", {})
            rows.append({
                "company_name": self._render_text(c.get("company_name", "Неизвестно")),
                "inn": c.get("inn", ""),
                "period": c.get("period", ""),
                "status": self._render_text(c.get("status", "")),
                "revenue": self._format_number(profit_loss.get("revenue", "0")),
                "net_profit": self._format_number(profit_loss.get("net_profit", "0")),
                "assets": self._format_number(balance.get("assets", "0")),
                "capital": self._format_number(balance.get("capital", "0")),
            })

        # Данные для графиков Chart.js: те же ряды, что и в таблице выше,
        # но сырыми числами (None для недоступных показателей — не рисуем
        # их нулем, чтобы не выдавать "нет данных" за реальный ноль)
        names = [row["company_name"] for row in rows]
        revenue_points = [self._chart_point(c.get("profit_loss", {}).get("revenue")) for c in companies]
        net_profit_points = [self._chart_point(c.get("profit_loss", {}).get("net_profit")) for c in companies]
        assets_points = [self._chart_point(c.get("balance", {}).get("assets")) for c in companies]
        capital_points = [self._chart_point(c.get("balance", {}).get("capital")) for c in companies]

        def zero_if_none(v: Optional[float]) -> float:
            return v if v is not None else 0.0

        pl_scale, pl_unit = self._pick_scale(
            [zero_if_none(v) for v in revenue_points + net_profit_points]
        )
        balance_scale, balance_unit = self._pick_scale(
            [zero_if_none(v) for v in assets_points + capital_points]
        )

        return {
            "companies": rows,
            "companies_count": len(rows),
            "report_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "summary": self._render_text(comparison.get("summary") or "Сравнение не выполнено"),
            "leader": self._render_text(comparison.get("leader") or "Не определен"),
            "differences": self._render_text(comparison.get("differences") or "Не выявлены"),
            "recommendation": self._render_text(comparison.get("recommendation") or "Нет рекомендаций"),

            # Графики
            "chartjs_lib": self._chartjs_lib,
            "has_pl_chart": any(v is not None for v in revenue_points + net_profit_points),
            "pl_chart_json": json.dumps({
                "labels": names,
                "datasets": [
                    {"label": "Выручка", "data": [round(zero_if_none(v) / pl_scale, 2) for v in revenue_points]},
                    {"label": "Чистая прибыль",
                     "data": [round(zero_if_none(v) / pl_scale, 2) for v in net_profit_points]},
                ],
                "unit": pl_unit,
            }, ensure_ascii=False),
            "has_balance_chart": any(v is not None for v in assets_points + capital_points),
            "balance_chart_json": json.dumps({
                "labels": names,
                "datasets": [
                    {"label": "Активы", "data": [round(zero_if_none(v) / balance_scale, 2) for v in assets_points]},
                    {"label": "Капитал",
                     "data": [round(zero_if_none(v) / balance_scale, 2) for v in capital_points]},
                ],
                "unit": balance_unit,
            }, ensure_ascii=False),
        }

    def _prepare_template_context(
            self,
            inn: str,
            financial_data: Dict[str, Any],
            analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Подготовка данных для шаблона"""
        balance = financial_data.get("balance", {})
        profit_loss = financial_data.get("profit_loss", {})

        # Безопасное получение значений
        def get_safe_value(dict_obj, key, default="0"):
            value = dict_obj.get(key, default)
            if value is None:
                return default
            return value

        revenue = self._safe_float(get_safe_value(profit_loss, "revenue", "0"))
        profit = self._safe_float(get_safe_value(profit_loss, "profit", "0"))
        assets = self._safe_float(get_safe_value(balance, "assets", "0"))
        capital = self._safe_float(get_safe_value(balance, "capital", "0"))

        # Рентабельность
        profitability = (profit / revenue * 100) if revenue > 0 else 0

        # Коэффициент автономии
        autonomy_ratio = (capital / assets * 100) if assets > 0 else 0

        risk_level = analysis.get("risk_level", "Средний")
        risk_color = {
            "Низкий": "#4CAF50",
            "Средний": "#FFC107",
            "Высокий": "#F44336"
        }.get(risk_level, "#FFC107")

        risk_emoji = {
            "Низкий": "🟢",
            "Средний": "🟡",
            "Высокий": "🔴"
        }.get(risk_level, "🟡")

        # Данные для графиков Chart.js. Показатели, которых нет (например,
        # себестоимость у банка — см. fns_client.py), просто не попадают
        # на график вместо того чтобы рисоваться нулем
        balance_points = [
            (label, self._chart_point(get_safe_value(balance, key, "0")))
            for label, key in [
                ("Внеоборотные активы", "non_current_assets"),
                ("Оборотные активы", "current_assets"),
            ]
        ]
        balance_points = [(l, v) for l, v in balance_points if v is not None]

        pl_points = [
            (label, self._chart_point(get_safe_value(profit_loss, key, "0")))
            for label, key in [
                ("Выручка", "revenue"),
                ("Валовая прибыль", "gross_profit"),
                ("Чистая прибыль", "net_profit"),
            ]
        ]
        pl_points = [(l, v) for l, v in pl_points if v is not None]

        balance_scale, balance_unit = self._pick_scale([v for _, v in balance_points])
        pl_scale, pl_unit = self._pick_scale([v for _, v in pl_points])

        return {
            "company_name": self._render_text(financial_data.get("company_name", "Неизвестно")),
            "inn": inn,
            "ogrn": financial_data.get("ogrn", ""),
            "period": financial_data.get("period", "2024"),
            "report_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "status": self._render_text(financial_data.get("status", "Активна")),
            "legal_address": self._render_text(financial_data.get("legal_address", "")),

            # Финансовые показатели (форматированные)
            "revenue": self._format_number(revenue),
            "profit": self._format_number(profit),
            "assets": self._format_number(assets),
            "capital": self._format_number(capital),
            "profitability": f"{profitability:.1f}%",
            "autonomy_ratio": f"{autonomy_ratio:.1f}%",

            # Детальные данные баланса (безопасное получение)
            "non_current_assets": self._format_number(get_safe_value(balance, "non_current_assets", "0")),
            "current_assets": self._format_number(get_safe_value(balance, "current_assets", "0")),
            "long_term_liabilities": self._format_number(get_safe_value(balance, "long_term_liabilities", "0")),
            "short_term_liabilities": self._format_number(get_safe_value(balance, "short_term_liabilities", "0")),
            "gross_profit": self._format_number(get_safe_value(profit_loss, "gross_profit", "0")),
            "operating_expenses": self._format_number(get_safe_value(profit_loss, "operating_expenses", "0")),
            "net_profit": self._format_number(get_safe_value(profit_loss, "net_profit", "0")),
            "ebitda": self._format_number(get_safe_value(profit_loss, "ebitda", "0")),

            # Анализ ИИ
            "analysis_summary": self._render_text(analysis.get("summary", "Анализ не выполнен")),
            "key_metrics": self._render_text(analysis.get("key_metrics", "")),
            "risks": self._render_text(analysis.get("risks", "")),
            "recommendations": self._render_text(analysis.get("recommendations", "")),
            "risk_level": risk_level,
            "risk_color": risk_color,
            "risk_emoji": risk_emoji,

            # Дополнительные метаданные
            "full_response": analysis.get("full_response", ""),

            # Графики
            "chartjs_lib": self._chartjs_lib,
            "has_balance_chart": len(balance_points) >= 2,
            "balance_chart_json": json.dumps({
                "labels": [l for l, _ in balance_points],
                "values": [round(v / balance_scale, 2) for _, v in balance_points],
                "unit": balance_unit,
            }, ensure_ascii=False),
            "has_pl_chart": len(pl_points) >= 2,
            "pl_chart_json": json.dumps({
                "labels": [l for l, _ in pl_points],
                "values": [round(v / pl_scale, 2) for _, v in pl_points],
                "unit": pl_unit,
            }, ensure_ascii=False),
        }

    @staticmethod
    def _render_text(text) -> str:
        """
        Подготовка текста (от ИИ или из данных ФНС) к вставке в HTML:
        экранирует спецсимволы, чтобы сырой текст не превращался в разметку
        страницы, и конвертирует markdown **жирный** в <strong> — модель
        систематически форматирует ответы жирным текстом, а Jinja2-шаблон
        вставляет строку как есть, без интерпретации markdown.
        """
        if not text:
            return text
        text = str(text)
        text = (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        return text

    @staticmethod
    def _chart_point(raw) -> Optional[float]:
        """
        Числовое значение для графика, либо None если показатель недоступен
        ("Н/Д" или пусто). Важно не путать с реальным нулем: отсутствующий
        показатель (например, себестоимость у банка) исключается из графика,
        а настоящий ноль — честно рисуется нулевым столбиком.
        """
        if raw is None:
            return None
        s = str(raw).strip()
        if not s or s.upper() in ("Н/Д", "НЕТ ДАННЫХ"):
            return None
        try:
            return float(s.replace(" ", "").replace(",", "."))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _pick_scale(values: List[float]) -> Tuple[float, str]:
        """
        Единый масштаб (делитель + подпись) для набора значений одного
        графика — чтобы мелкие показатели не терялись рядом с одним
        гигантским, а ось была подписана осмысленно (млн/млрд/трлн)
        """
        max_val = max((abs(v) for v in values), default=0)
        if max_val >= 1_000_000_000_000:
            return 1_000_000_000_000, "трлн ₽"
        if max_val >= 1_000_000_000:
            return 1_000_000_000, "млрд ₽"
        if max_val >= 1_000_000:
            return 1_000_000, "млн ₽"
        if max_val >= 1_000:
            return 1_000, "тыс ₽"
        return 1, "₽"

    @staticmethod
    def _safe_float(value) -> float:
        """Безопасное преобразование в число"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Убираем пробелы, заменяем запятые на точки
                cleaned = value.replace(" ", "").replace(",", ".").strip()
                # Убираем буквенные обозначения (тыс, млн, млрд)
                cleaned = cleaned.replace("тыс", "").replace("млн", "").replace("млрд", "").strip()
                if not cleaned or cleaned == "-":
                    return 0.0
                # Обрабатываем случай с точками как разделителями тысяч
                # Например: "1.000.000" -> "1000000"
                if "." in cleaned and cleaned.count(".") > 1:
                    cleaned = cleaned.replace(".", "")
                return float(cleaned)
            return 0.0
        except (ValueError, TypeError, AttributeError):
            return 0.0

    @staticmethod
    def _format_number(value) -> str:
        """Форматирование числа для отображения"""
        try:
            # Нечисловые метки (например "Н/Д") возвращаем как есть
            if isinstance(value, str) and value.strip().upper() in ("Н/Д", "НЕТ ДАННЫХ", ""):
                return value

            num = ReportGenerator._safe_float(value)
            sign = "-" if num < 0 else ""
            num = abs(num)

            if num >= 1_000_000_000_000:
                return f"{sign}{num / 1_000_000_000_000:.2f} трлн"
            elif num >= 1_000_000_000:
                return f"{sign}{num / 1_000_000_000:.2f} млрд"
            elif num >= 1_000_000:
                return f"{sign}{num / 1_000_000:.2f} млн"
            elif num >= 1_000:
                return f"{sign}{num / 1_000:.2f} тыс"
            else:
                return f"{sign}{num:.0f}"
        except Exception:
            return str(value) if value else "0"

    def _create_default_template(self) -> str:
        """
        Создание базового шаблона, если файл не найден
        """
        return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Финансовый отчет {{ company_name }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f7fa;
            padding: 20px;
            color: #333;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 40px;
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #2c3e50;
            font-size: 28px;
        }
        .header .meta {
            color: #7f8c8d;
            font-size: 14px;
            margin-top: 8px;
        }
        .risk-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: bold;
            color: white;
            background-color: {{ risk_color }};
            margin: 5px 0;
        }
        .section {
            margin: 30px 0;
        }
        .section h2 {
            color: #2c3e50;
            border-left: 4px solid #4CAF50;
            padding-left: 12px;
            margin-bottom: 15px;
            font-size: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }
        .stat {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat .label {
            font-size: 12px;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .stat .value {
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 4px;
        }
        .analysis-text {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            line-height: 1.8;
            margin: 10px 0;
        }
        .analysis-text p {
            margin: 8px 0;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            font-size: 12px;
            color: #95a5a6;
        }
        @media (max-width: 600px) {
            .container { padding: 20px; }
            .grid { grid-template-columns: 1fr 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Финансовый отчет</h1>
            <div class="meta">
                <strong>{{ company_name }}</strong> | ИНН: {{ inn }} | ОГРН: {{ ogrn }}<br>
                Отчетный период: {{ period }} | Дата: {{ report_date }}
            </div>
            <div class="risk-badge">{{ risk_emoji }} {{ risk_level }} риск</div>
        </div>

        <div class="section">
            <h2>📈 Ключевые показатели</h2>
            <div class="grid">
                <div class="stat">
                    <div class="label">Выручка</div>
                    <div class="value">{{ revenue }}</div>
                </div>
                <div class="stat">
                    <div class="label">Прибыль</div>
                    <div class="value">{{ profit }}</div>
                </div>
                <div class="stat">
                    <div class="label">Активы</div>
                    <div class="value">{{ assets }}</div>
                </div>
                <div class="stat">
                    <div class="label">Рентабельность</div>
                    <div class="value">{{ profitability }}</div>
                </div>
                <div class="stat">
                    <div class="label">Собственный капитал</div>
                    <div class="value">{{ capital }}</div>
                </div>
                <div class="stat">
                    <div class="label">Автономия</div>
                    <div class="value">{{ autonomy_ratio }}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🏦 Баланс</h2>
            <div class="grid">
                <div class="stat">
                    <div class="label">Внеоборотные активы</div>
                    <div class="value">{{ non_current_assets }}</div>
                </div>
                <div class="stat">
                    <div class="label">Оборотные активы</div>
                    <div class="value">{{ current_assets }}</div>
                </div>
                <div class="stat">
                    <div class="label">Долгосрочные обязательства</div>
                    <div class="value">{{ long_term_liabilities }}</div>
                </div>
                <div class="stat">
                    <div class="label">Краткосрочные обязательства</div>
                    <div class="value">{{ short_term_liabilities }}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📊 Прибыли и убытки</h2>
            <div class="grid">
                <div class="stat">
                    <div class="label">Валовая прибыль</div>
                    <div class="value">{{ gross_profit }}</div>
                </div>
                <div class="stat">
                    <div class="label">Операционные расходы</div>
                    <div class="value">{{ operating_expenses }}</div>
                </div>
                <div class="stat">
                    <div class="label">Чистая прибыль</div>
                    <div class="value">{{ net_profit }}</div>
                </div>
                <div class="stat">
                    <div class="label">EBITDA</div>
                    <div class="value">{{ ebitda }}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🧠 Анализ ИИ</h2>
            <div class="analysis-text">
                <h3>Финансовое состояние</h3>
                <p>{{ analysis_summary }}</p>

                <h3 style="margin-top:15px;">Ключевые показатели</h3>
                <p>{{ key_metrics or 'Нет данных' }}</p>

                <h3 style="margin-top:15px;">Выявленные риски</h3>
                <p>{{ risks or 'Не выявлены' }}</p>

                <h3 style="margin-top:15px;">Рекомендации</h3>
                <p>{{ recommendations or 'Провести дополнительный анализ' }}</p>
            </div>
        </div>

        <div class="footer">
            Отчет создан автоматически с использованием ИИ Report_v_4<br>
            {{ report_date }}
        </div>
    </div>
</body>
</html>
"""


# Создаем экземпляр для удобства
report_generator = ReportGenerator()
