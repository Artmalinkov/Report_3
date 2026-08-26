# app/dashboard/main.py
"""
Внутренний дашборд (FastAPI + Jinja2) — метрики по боту для администратора.

Не предназначен для публичного доступа: без домена/TLS ссылка отдаётся
только через SSH-туннель на сервере (см. ROADMAP). Вход — по одноразовой
ссылке из Telegram-бота (app/dashboard/auth.py), без пароля.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.dashboard.auth import consume_login_token
from app.database.crud import user_crud

_DASHBOARD_DIR = Path(__file__).parent

app = FastAPI(title="Report_v_4 Dashboard", docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=settings.DASHBOARD_SECRET_KEY)
app.mount("/static", StaticFiles(directory=str(_DASHBOARD_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(_DASHBOARD_DIR / "templates"))


@app.get("/login")
async def login(request: Request, token: str):
    telegram_id = await consume_login_token(token)
    if telegram_id is None:
        return HTMLResponse(
            "<p>Ссылка недействительна или уже использована. "
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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    telegram_id = request.session.get("telegram_id")
    if not telegram_id:
        return templates.TemplateResponse(
            request, "unauthorized.html", {}
        )

    stats = await user_crud.get_dashboard_stats()
    return templates.TemplateResponse(
        request, "index.html", {"stats": stats}
    )
