# database/crud/__init__.py

"""
Инициализация CRUD модулей
"""
from app.database.crud.user_crud import UserCRUD, user_crud
from app.database.crud.report_crud import ReportCRUD, report_crud
from app.database.crud.cache_crud import CacheCRUD, cache_crud
from app.database.crud.base_crud import BaseCRUD

__all__ = [
    "UserCRUD",
    "user_crud",
    "ReportCRUD",
    "report_crud",
    "CacheCRUD",
    "cache_crud",
    "BaseCRUD",
]