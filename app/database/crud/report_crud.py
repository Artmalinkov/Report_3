# database/crud/report_crud.py

"""
CRUD операции для модели Report
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base_crud import BaseCRUD
from app.database.models import Report
from app.database.session import AsyncSessionLocal


class ReportCRUD(BaseCRUD[Report]):
    """CRUD операции для отчетов"""

    def __init__(self):
        super().__init__(Report)

    async def create_report(
            self,
            user_id: int,
            inn: str,
            html_content: str,
            analysis_summary: Optional[str] = None,
            company_name: Optional[str] = None,
            ogrn: Optional[str] = None,
            period: Optional[str] = None,
            risk_level: Optional[str] = None,
            status: str = "completed",
            revenue: Optional[str] = None,
            profit: Optional[str] = None,
            assets: Optional[str] = None
    ) -> Report:
        """Создание нового отчета"""
        return await self.create(
            user_id=user_id,
            inn=inn,
            html_content=html_content,
            analysis_summary=analysis_summary,
            company_name=company_name,
            ogrn=ogrn,
            period=period,
            risk_level=risk_level,
            status=status,
            revenue=revenue,
            profit=profit,
            assets=assets
        )

    async def get_by_inn(self, inn: str, limit: int = 10) -> List[Report]:
        """Получение отчетов по ИНН"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Report)
                .where(Report.inn == inn)
                .order_by(desc(Report.created_at))
                .limit(limit)
            )
            return result.scalars().all()

    async def get_user_reports(
            self,
            user_id: int,
            limit: int = 10,
            offset: int = 0
    ) -> List[Report]:
        """Получение отчетов пользователя"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Report)
                .where(Report.user_id == user_id)
                .order_by(desc(Report.created_at))
                .offset(offset)
                .limit(limit)
            )
            return result.scalars().all()

    async def get_user_reports_count(self, user_id: int) -> int:
        """Количество отчетов пользователя"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count()).select_from(Report)
                .where(Report.user_id == user_id)
            )
            return result.scalar() or 0

    async def get_by_date_range(
            self,
            start_date: datetime,
            end_date: datetime,
            user_id: Optional[int] = None
    ) -> List[Report]:
        """Получение отчетов за период"""
        async with AsyncSessionLocal() as session:
            query = select(Report).where(
                and_(
                    Report.created_at >= start_date,
                    Report.created_at <= end_date
                )
            )
            if user_id:
                query = query.where(Report.user_id == user_id)

            result = await session.execute(
                query.order_by(desc(Report.created_at))
            )
            return result.scalars().all()

    async def get_by_risk_level(self, risk_level: str, limit: int = 100) -> List[Report]:
        """Получение отчетов по уровню риска"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Report)
                .where(Report.risk_level == risk_level)
                .order_by(desc(Report.created_at))
                .limit(limit)
            )
            return result.scalars().all()

    async def get_high_risk_reports(self, limit: int = 50) -> List[Report]:
        """Получение отчетов с высоким риском"""
        return await self.get_by_risk_level("Высокий", limit)

    async def update_status(self, report_id: int, status: str) -> Optional[Report]:
        """Обновление статуса отчета"""
        return await self.update(report_id, status=status)

    async def update_risk_level(self, report_id: int, risk_level: str) -> Optional[Report]:
        """Обновление уровня риска"""
        return await self.update(report_id, risk_level=risk_level)

    async def get_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Получение статистики по отчетам"""
        async with AsyncSessionLocal() as session:
            query = select(Report)
            if user_id:
                query = query.where(Report.user_id == user_id)

            # Общее количество
            result = await session.execute(
                select(func.count()).select_from(query.subquery())
            )
            total = result.scalar() or 0

            # Уникальные ИНН
            if user_id:
                result = await session.execute(
                    select(func.count(func.distinct(Report.inn)))
                    .where(Report.user_id == user_id)
                )
            else:
                result = await session.execute(
                    select(func.count(func.distinct(Report.inn)))
                )
            unique_inns = result.scalar() or 0

            # По уровням риска
            for level in ["Низкий", "Средний", "Высокий"]:
                query_level = select(Report).where(Report.risk_level == level)
                if user_id:
                    query_level = query_level.where(Report.user_id == user_id)
                result = await session.execute(
                    select(func.count()).select_from(query_level.subquery())
                )
                setattr(self, f"risk_{level.lower()}_count", result.scalar() or 0)

            # За последнюю неделю
            week_ago = datetime.utcnow() - timedelta(days=7)
            query_week = select(Report).where(Report.created_at >= week_ago)
            if user_id:
                query_week = query_week.where(Report.user_id == user_id)
            result = await session.execute(
                select(func.count()).select_from(query_week.subquery())
            )
            last_week = result.scalar() or 0

            return {
                "total": total,
                "unique_inns": unique_inns,
                "risk_low": getattr(self, "risk_низкий_count", 0),
                "risk_medium": getattr(self, "risk_средний_count", 0),
                "risk_high": getattr(self, "risk_высокий_count", 0),
                "last_week": last_week
            }


# Создаем экземпляр для удобства
report_crud = ReportCRUD()