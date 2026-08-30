# 📊 Report_v_4 — Финансовый анализ компаний через Telegram

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

Telegram-бот: присылаете ИНН компании или ИП — получаете HTML/PDF-отчёт с данными из ФНС России и ИИ-анализом финансового состояния (риски, ключевые показатели, рекомендации).

Личный учебный проект.

---

## Оглавление

- [Возможности](#возможности)
- [Архитектура](#архитектура)
- [Установка и запуск](#установка-и-запуск)
- [Конфигурация](#конфигурация)
- [Команды бота](#команды-бота)
- [База данных](#база-данных)
- [Технологии](#технологии)
- [Тесты](#тесты)

---

## Возможности

**Данные из ФНС** (методы `egr`/`bo`/`check`/`stat` api-fns.ru):
- Реквизиты: статус, дата регистрации, юридический адрес, уставной капитал, ОКВЭД + доп. виды деятельности, счётчики лицензий/филиалов/участий в других организациях
- Бухотчётность за последние 3 года: баланс, отчёт о прибылях и убытках, движение денежных средств (форма №4), коэффициент текущей ликвидности
- Флаги риска (массовый адрес, блокировка счёта, реестр МСП и т.д.)
- Отдельный разбор банковской отчётности (формы 0409806/807)

**ИИ-анализ** (IO.net, OpenAI-совместимый API):
- Структурированный JSON-ответ по строгой схеме — без хрупкого парсинга свободного текста
- Автоматический fallback на резервные модели, если основная недоступна
- Честная пометка в отчёте, если анализ выполнен в офлайн-режиме

**Отчёты:**
- Самостоятельный HTML-файл с графиками (Chart.js), открывается без интернета
- Экспорт в PDF (Playwright, headless Chromium)
- Сравнение до 5 компаний в одном отчёте

**Бот:** история запросов, повторное скачивание отчётов, статистика, rate-limiting для защиты платных API.

**Админ-панель:** веб-дашборд (FastAPI) с пользователями, топом запрашиваемых компаний и расходом платных API; вход через Telegram (magic-link), доступ только через SSH-туннель.

---

## Архитектура

```
Telegram ──▶ aiogram-бот ──▶ ФНС API (реквизиты + отчётность)
                          ──▶ IO.net (ИИ-анализ)
                          ──▶ Генератор отчёта (Jinja2 + Playwright)
                          ──▶ PostgreSQL (история, кэш)

Админ ──▶ SSH-туннель ──▶ FastAPI-дашборд ──▶ PostgreSQL
```

### Структура проекта

```
app/
├── bot/            # Обработчики команд, клавиатуры, FSM
├── dashboard/       # Админ-панель (FastAPI)
├── database/         # Модели SQLAlchemy, CRUD, сессия
├── services/         # fns_client.py, ionet_client.py, report_generator.py
├── tests/            # pytest
├── utils/            # Валидация ИНН и т.п.
├── config.py
└── main.py
migrations/           # Alembic
templates/             # HTML-шаблоны отчётов
reports/                # Сгенерированные отчёты (не в git)
docker-compose.yml
Dockerfile
```

---

## Установка и запуск

### Требования
- Python 3.11+
- PostgreSQL 16
- Docker (опционально)

### Локально

```bash
git clone https://github.com/Artmalinkov/Report_3.git
cd Report_3

python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

python -m pip install -r requirements.txt
playwright install chromium   # для рендера PDF

cp .env.example .env
# заполните .env — см. таблицу ниже

alembic upgrade head          # применить миграции БД
python -m app.main
```

### Docker

```bash
docker compose up -d --build
docker compose logs -f bot
```

Поднимает три контейнера: `postgres`, `bot`, `dashboard`. Дашборд публикуется только на `127.0.0.1:8080` сервера — доступ снаружи только через SSH-туннель.

---

## Конфигурация

Полный список — в `app/config.py`. Обязательные переменные:

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен Telegram-бота |
| `DB_PASS` | Пароль PostgreSQL |
| `FNS_API_KEY` | Ключ API ФНС (api-fns.ru) |
| `IONET_API_KEY` | Ключ API IO.net |

Опциональные (с рабочими значениями по умолчанию): `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `IONET_API_URL`, `IONET_MODEL`, `DEBUG`, `RATE_LIMIT_COOLDOWN_SECONDS`, `RATE_LIMIT_DAILY_MAX`, `LOG_LEVEL`, `LOG_FORMAT`, `DASHBOARD_SECRET_KEY`, `DASHBOARD_PORT`, `DASHBOARD_BASE_URL`.

---

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/help` | Справка по использованию |
| `/history` | История запросов, выбор компаний для сравнения |
| `/stats` | Личная статистика |
| `/dashboard` | Ссылка на админ-панель (для администраторов) |

Отправка ИНН (10 или 12 цифр) → отчёт по одной компании. Несколько ИНН через запятую или пробел (до 5) → сравнительный отчёт.

---

## База данных

PostgreSQL, миграции через Alembic (`migrations/`). Основные таблицы:

- **`users`** — пользователи Telegram (статистика запросов, права администратора)
- **`reports`** — сгенерированные отчёты (HTML, резюме анализа, уровень риска)
- **`cache`** — кэш ответов ФНС/IO.net и токены magic-link дашборда

Точные поля — в `app/database/models/`.

---

## Технологии

| | |
|---|---|
| **Язык** | Python 3.11+ |
| **Бот** | aiogram 3 |
| **Админ-панель** | FastAPI |
| **БД** | PostgreSQL 16 + SQLAlchemy 2 + Alembic |
| **Отчёты** | Jinja2 + Chart.js + Playwright (PDF) |
| **ИИ** | IO.net (OpenAI-совместимый клиент) |
| **HTTP** | aiohttp |
| **Логи** | Loguru |

---

## Тесты

```bash
python -m pytest app/tests/ -q
```
