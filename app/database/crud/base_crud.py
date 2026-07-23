# app/database/crud/base_crud.py

"""
Базовый CRUD класс с общими методами для всех моделей
"""
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import AsyncSessionLocal
from app.database.base import Base, BaseModel

# Тип для модели
ModelType = TypeVar("ModelType", bound=Base)
ModelTypeWithBase = TypeVar("ModelTypeWithBase", bound=BaseModel)


class BaseCRUD(Generic[ModelType]):
    """
    Базовый класс CRUD с общими методами
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def create(self, **kwargs) -> ModelType:
        """Создание новой записи"""
        async with AsyncSessionLocal() as session:
            instance = self.model(**kwargs)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """Получение записи по ID"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Получение всех записей с пагинацией"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(self.model)
                .limit(limit)
                .offset(offset)
            )
            return result.scalars().all()

    async def count(self) -> int:
        """Подсчет количества записей"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count()).select_from(self.model)
            )
            return result.scalar() or 0

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """Обновление записи"""
        async with AsyncSessionLocal() as session:
            # Убираем None значения
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            if not update_data:
                return await self.get_by_id(id)

            await session.execute(
                update(self.model)
                .where(self.model.id == id)
                .values(**update_data)
            )
            await session.commit()
            return await self.get_by_id(id)

    async def delete(self, id: int) -> bool:
        """Удаление записи"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(self.model).where(self.model.id == id)
            )
            await session.commit()
            return result.rowcount > 0

    async def delete_all(self) -> int:
        """Удаление всех записей (осторожно!)"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(delete(self.model))
            await session.commit()
            return result.rowcount

    async def exists(self, **filters) -> bool:
        """Проверка существования записи по фильтрам"""
        async with AsyncSessionLocal() as session:
            query = select(self.model)
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            result = await session.execute(query.limit(1))
            return result.scalar_one_or_none() is not None