# app/services/report_generator.py
"""
Генератор HTML отчетов
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime
from loguru import logger
from jinja2 import Template


class ReportGenerator:
    """Генератор HTML-отчетов"""

    def __init__(self):
        self.report_dir = Path(__file__).parent.parent.parent / "reports"
        self.template_dir = Path(__file__).parent.parent.parent / "templates"
        self.report_dir.mkdir(exist_ok=True)

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

        return {
            "company_name": financial_data.get("company_name", "Неизвестно"),
            "inn": inn,
            "ogrn": financial_data.get("ogrn", ""),
            "period": financial_data.get("period", "2024"),
            "report_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "status": financial_data.get("status", "Активна"),
            "legal_address": financial_data.get("legal_address", ""),

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
            "analysis_summary": analysis.get("summary", "Анализ не выполнен"),
            "key_metrics": analysis.get("key_metrics", ""),
            "risks": analysis.get("risks", ""),
            "recommendations": analysis.get("recommendations", ""),
            "risk_level": risk_level,
            "risk_color": risk_color,
            "risk_emoji": risk_emoji,

            # Дополнительные метаданные
            "full_response": analysis.get("full_response", "")
        }

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
            # Если value уже строка с форматированием, возвращаем как есть
            if isinstance(value, str) and not value.replace(" ", "").replace(",", ".").strip().isdigit():
                return value

            num = ReportGenerator._safe_float(value)

            if num >= 1_000_000_000:
                return f"{num / 1_000_000_000:.2f} млрд"
            elif num >= 1_000_000:
                return f"{num / 1_000_000:.2f} млн"
            elif num >= 1_000:
                return f"{num / 1_000:.2f} тыс"
            else:
                return f"{num:.0f}"
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
