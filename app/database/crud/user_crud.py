# database/crud/user_crud.py

"""
CRUD операции для модели User
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base_crud import BaseCRUD
from app.database.models import User
from app.database.session import AsyncSessionLocal


class UserCRUD(BaseCRUD[User]):
    """CRUD операции для пользователей"""

    def __init__(self):
        super().__init__(User)

    async def create_or_update(
            self,
            telegram_id: int,
            username: Optional[str] = None,
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
            language_code: str = "ru"
    ) -> User:
        """Создание или обновление пользователя"""
        async with AsyncSessionLocal() as session:
            # Ищем пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if user:
                # Обновляем существующего
                if username:
                    user.username = username
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
                if language_code:
                    user.language_code = language_code
            else:
                # Создаем нового
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code,
                    total_requests=0,
                    is_active=True
                )
                session.add(user)

            await session.commit()
            await session.refresh(user)
            return user

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Получение пользователя по username"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()

    async def increment_requests(self, telegram_id: int) -> None:
        """Увеличение счетчика запросов"""
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    total_requests=User.total_requests + 1,
                    last_request_at=datetime.utcnow()
                )
            )
            await session.commit()

    async def get_active_users(self, limit: int = 100) -> List[User]:
        """Получение активных пользователей"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User)
                .where(User.is_active == True)
                .limit(limit)
            )
            return result.scalars().all()

    async def get_admins(self) -> List[User]:
        """Получение администраторов"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.is_admin == True)
            )
            return result.scalars().all()

    async def get_banned_users(self) -> List[User]:
        """Получение забаненных пользователей"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.is_banned == True)
            )
            return result.scalars().all()

    async def ban_user(self, telegram_id: int) -> bool:
        """Бан пользователя"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(is_banned=True, is_active=False)
            )
            await session.commit()
            return result.rowcount > 0

    async def unban_user(self, telegram_id: int) -> bool:
        """Разбан пользователя"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(is_banned=False, is_active=True)
            )
            await session.commit()
            return result.rowcount > 0

    async def get_statistics(self, telegram_id: int) -> Dict[str, Any]:
        """Получение статистики пользователя"""
        async with AsyncSessionLocal() as session:
            # Получаем пользователя
            user = await self.get_by_telegram_id(telegram_id)
            if not user:
                return {}

            # Считаем отчеты из таблицы reports
            from app.database.models import Report
            result = await session.execute(
                select(Report).where(Report.user_id == telegram_id)
            )
            reports = result.scalars().all()

            # Статистика по ИНН
            inns = set(r.inn for r in reports)

            # За последнюю неделю
            week_ago = datetime.utcnow() - timedelta(days=7)
            last_week = [r for r in reports if r.created_at >= week_ago]

            return {
                "total_requests": user.total_requests,
                "total_reports": len(reports),
                "unique_companies": len(inns),
                "last_week": len(last_week),
                "last_request": user.last_request_at,
                "is_active": user.is_active,
                "is_admin": user.is_admin
            }


# Создаем экземпляр для удобства
user_crud = UserCRUD()