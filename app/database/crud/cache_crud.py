# app/database/crud/cache_crud.py

"""
CRUD операции для модели Cache
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base_crud import BaseCRUD
from app.database.models import Cache
from app.database.session import AsyncSessionLocal
import json


class CacheCRUD(BaseCRUD[Cache]):
    """CRUD операции для кеша"""

    def __init__(self):
        super().__init__(Cache)

    async def set_cache(
            self,
            cache_key: str,
            cache_type: str,
            data: Any,
            expires_in_seconds: int = 3600,
            inn: Optional[str] = None
    ) -> Cache:
        """Сохранение данных в кеш"""
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)

        # Преобразуем данные в JSON
        data_json = json.dumps(data, ensure_ascii=False, default=str)

        async with AsyncSessionLocal() as session:
            # Проверяем существование
            result = await session.execute(
                select(Cache).where(Cache.cache_key == cache_key)
            )
            cache_entry = result.scalar_one_or_none()

            if cache_entry:
                # Обновляем существующий
                cache_entry.data = data_json
                cache_entry.expires_at = expires_at
                cache_entry.request_count += 1
                if inn:
                    cache_entry.inn = inn
            else:
                # Создаем новый
                cache_entry = Cache(
                    cache_key=cache_key,
                    cache_type=cache_type,
                    data=data_json,
                    expires_at=expires_at,
                    inn=inn,
                    request_count=1
                )
                session.add(cache_entry)

            await session.commit()
            await session.refresh(cache_entry)
            return cache_entry

    async def get_cache(self, cache_key: str) -> Optional[Any]:
        """Получение данных из кеша"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Cache).where(Cache.cache_key == cache_key)
            )
            cache_entry = result.scalar_one_or_none()

            if not cache_entry:
                return None

            # Проверяем срок годности
            if cache_entry.is_expired():
                await session.execute(
                    delete(Cache).where(Cache.cache_key == cache_key)
                )
                await session.commit()
                return None

            # Обновляем счетчик
            cache_entry.request_count += 1
            await session.commit()

            # Парсим JSON
            try:
                return json.loads(cache_entry.data)
            except json.JSONDecodeError:
                return cache_entry.data

    async def delete_expired(self) -> int:
        """Удаление просроченного кеша"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(Cache).where(Cache.expires_at < datetime.utcnow())
            )
            await session.commit()
            return result.rowcount

    async def delete_by_type(self, cache_type: str) -> int:
        """Удаление кеша по типу"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(Cache).where(Cache.cache_type == cache_type)
            )
            await session.commit()
            return result.rowcount

    async def delete_by_inn(self, inn: str) -> int:
        """Удаление кеша по ИНН"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(Cache).where(Cache.inn == inn)
            )
            await session.commit()
            return result.rowcount

    async def get_stats(self) -> Dict[str, Any]:
        """Статистика кеша"""
        async with AsyncSessionLocal() as session:
            # Всего записей
            result = await session.execute(
                select(func.count()).select_from(Cache)
            )
            total = result.scalar() or 0

            # Просроченных
            result = await session.execute(
                select(func.count())
                .select_from(Cache)
                .where(Cache.expires_at < datetime.utcnow())
            )
            expired = result.scalar() or 0

            # По типам
            result = await session.execute(
                select(Cache.cache_type, func.count())
                .group_by(Cache.cache_type)
            )
            by_type = {row[0]: row[1] for row in result}

            return {
                "total": total,
                "expired": expired,
                "valid": total - expired,
                "by_type": by_type
            }


# Создаем экземпляр для удобства
cache_crud = CacheCRUD()