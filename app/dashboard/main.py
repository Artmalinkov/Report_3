# app/dashboard/main.py
"""
Внутренний дашборд (FastAPI + Jinja2) — метрики по боту для администратора.

Не предназначен для публичного доступа: без домена/TLS ссылка отдаётся
только через SSH-туннель на сервере (см. ROADMAP). Вход — по одноразовой
ссылке из Telegram-бота (app/dashboard/auth.py), без пароля.
"""
from pathlib import Path
from typing import Any, Dict

from loguru import logger
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.dashboard.auth import consume_login_token
from app.database.crud import user_crud, report_crud, cache_crud
from app.services.fns_client import FNSClient

_DASHBOARD_DIR = Path(__file__).parent
_FNS_STAT_CACHE_KEY = "dashboard:fns_stat"
_FNS_STAT_TTL_SECONDS = 3600  # раз в час — не тратить лишние запросы к ФНС на каждое обновление страницы
_FNS_METHODS_OF_INTEREST = ("egr", "bo")  # только то, чем реально пользуется бот

fns_client = FNSClient()

app = FastAPI(title="Report_v_4 Dashboard", docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=settings.DASHBOARD_SECRET_KEY)
app.mount("/static", StaticFiles(directory=str(_DASHBOARD_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(_DASHBOARD_DIR / "templates"))


@app.get("/login")
async def login(request: Request, token: str):
    telegram_id = await consume_login_token(token)
    if telegram_id is None:
        return HTMLResponse(
            "<p>Ссылка недействительна или истекла (15 минут). "
            "Отправьте боту команду /dashboard ещё раз.</p>",
            status_code=403,
        )

    user = await user_crud.get_by_telegram_id(telegram_id)
    if not user or not user.is_admin:
        return HTMLResponse("<p>Доступ запрещён.</p>", status_code=403)

    request.session["telegram_id"] = telegram_id
    return RedirectResponse(url="/")


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


async def _get_fns_usage() -> Dict[str, Any]:
    """
    Точный расход платного тарифа ФНС (метод stat) по методам, которые
    реально использует бот (egr, bo) — вместо грубой оценки по кэшу.
    Кэшируется на час, чтобы не тратить лишний запрос к ФНС на каждое
    открытие страницы. При ошибке — отдаёт то, что было в кэше (пусть
    даже устаревшее), а не ломает всю страницу дашборда.
    """
    cached = await cache_crud.get_cache(_FNS_STAT_CACHE_KEY)
    if cached is not None:
        return cached

    try:
        raw = await fns_client.get_usage_stats()
    except Exception as e:
        logger.warning(f"Не удалось получить статистику ФНС (stat): {e}")
        return {method: None for method in _FNS_METHODS_OF_INTEREST}

    methods = raw.get("Методы", {})
    usage = {}
    for method in _FNS_METHODS_OF_INTEREST:
        info = methods.get(method)
        usage[method] = {
            "limit": info.get("Лимит"),
            "used": info.get("Истрачено"),
        } if info else None

    await cache_crud.set_cache(
        cache_key=_FNS_STAT_CACHE_KEY,
        cache_type="dashboard",
        data=usage,
        expires_in_seconds=_FNS_STAT_TTL_SECONDS,
    )
    return usage


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    telegram_id = request.session.get("telegram_id")
    if not telegram_id:
        return templates.TemplateResponse(
            request, "unauthorized.html", {}
        )

    stats = await user_crud.get_dashboard_stats()
    top_companies = await report_crud.get_top_companies(limit=5)
    cache_stats = await cache_crud.get_stats()
    api_usage = {
        "fns": await _get_fns_usage(),
        # У IO_NET нет метода вроде stat — оставляем прежнюю грубую оценку
        # по количеству живых записей в кэше (~24ч)
        "ionet": cache_stats["by_type"].get("ionet", 0),
    }
    return templates.TemplateResponse(
        request, "index.html", {
            "stats": stats,
            "top_companies": top_companies,
            "api_usage": api_usage,
        }
    )
