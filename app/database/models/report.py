# app/database/models/report.py
"""
Модель финансового отчета
"""
from sqlalchemy import Column, Integer, BigInteger, String, Text, Index
from app.database.base import Base, BaseModel


class Report(Base, BaseModel):
    """Модель финансового отчета"""

    __tablename__ = "reports"

    # Основные поля
    id = Column(Integer, primary_key=True, index=True)

    # Связь с пользователем
    user_id = Column(BigInteger, index=True, nullable=False)
    # user = relationship("User", back_populates="reports")

    # Данные компании
    inn = Column(String(12), index=True, nullable=False)
    company_name = Column(String(255), nullable=True)
    ogrn = Column(String(15), nullable=True)
    period = Column(String(20), nullable=True)  # Год отчетности

    # Содержимое отчета
    html_content = Column(Text, nullable=False)
    analysis_summary = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=True)  # Низкий, Средний, Высокий

    # Статус отчета
    status = Column(String(20), default="completed")  # processing, completed, error

    # Финансовые данные (для быстрого доступа)
    revenue = Column(String(50), nullable=True)  # Выручка
    profit = Column(String(50), nullable=True)  # Прибыль
    assets = Column(String(50), nullable=True)  # Активы

    # Метаданные
    error_message = Column(Text, nullable=True)

    # Индексы для быстрого поиска
    __table_args__ = (
        Index('ix_reports_user_inn', 'user_id', 'inn'),
        Index('ix_reports_user_created', 'user_id', 'created_at'),
        Index('ix_reports_inn', 'inn'),
        Index('ix_reports_status', 'status'),
    )

    def __repr__(self):
        return f"<Report(id={self.id}, inn={self.inn}, user_id={self.user_id})>"

    def to_dict(self) -> dict:
        """Преобразование в словарь для API"""
        data = super().to_dict()
        # Добавляем краткую информацию
        data['summary'] = self.analysis_summary[:200] + "..." if self.analysis_summary else None
        return data

    def is_high_risk(self) -> bool:
        """Проверка высокого риска"""
        return self.risk_level == "Высокий"
