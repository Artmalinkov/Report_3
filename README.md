# 📊 Report_3 — Финансовый анализ компаний через Telegram

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://t.me/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

> 🤖 Telegram-бот для автоматического анализа финансовой отчетности компаний по ИНН с использованием искусственного интеллекта.

---

## 📖 Оглавление

- [✨ Особенности](#-особенности)
- [🚀 Демонстрация](#-демонстрация)
- [🏗 Архитектура](#-архитектура)
- [📦 Установка](#-установка)
- [⚙️ Конфигурация](#️-конфигурация)
- [🚀 Запуск](#-запуск)
- [📱 Использование](#-использование)
- [📊 Команды бота](#-команды-бота)
- [🗄 Структура базы данных](#-структура-базы-данных)
- [🛠 Технологии](#-технологии)
- [🤝 Вклад в проект](#-вклад-в-проект)
- [📄 Лицензия](#-лицензия)

---

## ✨ Особенности

### 🎯 Основной функционал
- ✅ **Получение данных из ФНС** — автоматический запрос финансовой отчетности по ИНН
- 🧠 **ИИ-анализ** — интеллектуальный анализ финансовых показателей через IO_NET
- 📄 **Генерация отчетов** — создание красивых HTML-отчетов с визуализацией данных
- 💾 **Сохранение истории** — все запросы сохраняются в базе данных
- 📊 **Статистика** — отслеживание количества запросов и активности пользователя

### 🌟 Дополнительные возможности
- ⚡ **Асинхронная работа** — высокая производительность и отзывчивость
- 🔒 **Валидация ИНН** — проверка контрольных сумм (10 и 12-значные)
- 📱 **Удобный интерфейс** — интуитивно понятные команды и кнопки
- 🐳 **Docker-поддержка** — легкое развертывание в любом окружении
- 📈 **Масштабируемость** — готовая архитектура для добавления новых функций

---

## 🚀 Демонстрация

### Пример работы бота

```
👤 Пользователь: /start
🤖 Бот: 🏢 Добро пожаловать в Report_3!
      Я помогу вам проанализировать финансовую отчетность компании по ИНН.
      Просто отправьте мне ИНН (10 или 12 цифр)

👤 Пользователь: 7707083893
🤖 Бот: 🔍 Получаю данные из ФНС...
      🧠 Анализирую данные с помощью AI...
      📄 Генерирую HTML-отчет...

      ✅ Отчет готов!
      🏢 Сбербанк России
      ИНН: 7707083893
      📊 Риск: Низкий

      📄 Отчет сохранен в истории.
```

### Пример сгенерированного отчета

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Финансовый отчет 7707083893</title>
    <style>
        /* Стили для красивого отображения */
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Финансовый отчет</h1>
            <div class="meta">
                ИНН: 7707083893 | Компания: Сбербанк России | Период: 2024
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Ключевые показатели</h2>
            <div class="grid">
                <div class="stat">
                    <div class="label">Выручка</div>
                    <div class="value">2 100 000 000</div>
                </div>
                <div class="stat">
                    <div class="label">Прибыль</div>
                    <div class="value">300 000 000</div>
                </div>
                <div class="stat">
                    <div class="label">Рентабельность</div>
                    <div class="value">14.3%</div>
                </div>
            </div>
        </div>
        <!-- ... остальной отчет ... -->
    </div>
</body>
</html>
```

---

## 🏗 Архитектура

### Схема взаимодействия

```
┌─────────────┐
│  Telegram   │
│    User     │
└──────┬──────┘
       │ ИНН
       ▼
┌─────────────┐     ┌─────────────┐
│  Telegram   │────▶│  Валидация  │
│  Bot        │     │    ИНН      │
└──────┬──────┘     └─────────────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│  API ФНС    │────▶│  IO_NET AI  │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └───────┬───────────┘
               ▼
       ┌─────────────┐
       │  Генератор  │
       │  HTML       │
       └──────┬──────┘
              ▼
       ┌─────────────┐     ┌─────────────┐
       │  PostgreSQL │────▶│  Отправка   │
       │             │     │  отчета     │
       └─────────────┘     └─────────────┘
```

### Структура проекта

```
report_3/
├── 📁 app/
│   ├── 📁 bot/              # Обработчики команд и FSM
│   │   ├── handlers.py      # Основные обработчики
│   │   ├── keyboards.py     # Клавиатуры
│   │   └── states.py        # Состояния FSM
│   │
│   ├── 📁 database/         # Работа с БД
│   │   ├── 📁 models/       # Модели SQLAlchemy
│   │   │   ├── report.py
│   │   │   ├── user.py
│   │   │   └── cache.py
│   │   ├── 📁 crud/         # CRUD операции
│   │   │   ├── report_crud.py
│   │   │   └── user_crud.py
│   │   ├── base.py          # Базовый класс
│   │   └── session.py       # Подключение к БД
│   │
│   ├── 📁 services/         # Внешние сервисы
│   │   ├── fns_client.py    # Клиент API ФНС
│   │   ├── ionet_client.py  # Клиент IO_NET
│   │   └── report_generator.py # Генерация HTML
│   │
│   ├── 📁 templates/        # HTML-шаблоны
│   │   └── report_template.html
│   │
│   ├── 📁 utils/            # Вспомогательные функции
│   │   └── validators.py    # Валидация ИНН
│   │
│   ├── config.py            # Конфигурация
│   └── main.py              # Точка входа
│
├── 📁 reports/              # Сгенерированные отчеты
├── 📁 logs/                 # Логи (опционально)
├── 📄 .env                  # Переменные окружения
├── 📄 .env.example          # Пример конфигурации
├── 📄 requirements.txt      # Зависимости
├── 📄 Dockerfile            # Docker образ
├── 📄 docker-compose.yml    # Docker Compose
├── 📄 README.md             # Документация
└── 📄 LICENSE               # Лицензия
```

---

## 📦 Установка

### Требования

- Python 3.11 или выше
- PostgreSQL 15 или выше
- Pip (менеджер пакетов Python)
- Git

### Пошаговая инструкция

#### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/report_3.git
cd report_3
```

#### 2. Создание виртуального окружения

```bash
# Создание
python -m venv venv

# Активация (Windows)
venv\Scripts\activate

# Активация (Linux/Mac)
source venv/bin/activate
```

#### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

#### 4. Настройка базы данных

```bash
# Создание базы данных PostgreSQL
createdb -U postgres report3

# Или через psql
psql -U postgres -c "CREATE DATABASE report3;"
```

#### 5. Конфигурация

Создайте файл `.env` в корне проекта:

```bash
cp .env.example .env
# Отредактируйте .env, указав свои значения
```

---

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | Обязательная | Пример |
|------------|----------|--------------|--------|
| `BOT_TOKEN` | Токен Telegram бота | ✅ | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `DB_HOST` | Хост PostgreSQL | ❌ | `localhost` |
| `DB_PORT` | Порт PostgreSQL | ❌ | `5432` |
| `DB_NAME` | Имя базы данных | ✅ | `report3` |
| `DB_USER` | Пользователь БД | ✅ | `postgres` |
| `DB_PASS` | Пароль БД | ✅ | `secure_password` |
| `FNS_API_KEY` | Ключ API ФНС | ✅ | `your_fns_key` |
| `IONET_API_KEY` | Ключ API IO_NET | ✅ | `your_ionet_key` |
| `IONET_API_URL` | URL API IO_NET | ❌ | `https://api.ionet.ai/v1` |
| `IONET_MODEL` | Модель IO_NET | ❌ | `gpt-4o-mini` |
| `DEBUG` | Режим отладки | ❌ | `True` |

### Пример .env

```env
# Telegram Bot
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=report3
DB_USER=postgres
DB_PASS=my_secure_password

# API Keys
FNS_API_KEY=your_fns_api_key_here
IONET_API_KEY=your_ionet_api_key_here

# App Settings
DEBUG=True
```

---

## 🚀 Запуск

### Локальный запуск

```bash
# Активируйте виртуальное окружение
source venv/bin/activate  # или venv\Scripts\activate

# Запуск бота
python -m app.main
```

### Запуск в Docker

```bash
# Сборка и запуск контейнеров
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f bot

# Проверка статуса
docker-compose ps

# Остановка
docker-compose down
```

### Проверка работы

1. Откройте Telegram
2. Найдите своего бота по имени
3. Отправьте команду `/start`
4. Отправьте ИНН для проверки

---

## 📱 Использование

### Основные команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и начало работы |
| `/help` | Справка по использованию |
| `/history` | История запросов |
| `/stats` | Статистика использования |

### Процесс анализа

1. **Отправка ИНН** — введите 10 или 12-значный ИНН
2. **Валидация** — бот проверяет корректность ИНН
3. **Получение данных** — запрос к API ФНС
4. **ИИ-анализ** — обработка данных через IO_NET
5. **Генерация отчета** — создание HTML-документа
6. **Сохранение** — запись в базу данных
7. **Отправка** — пользователь получает готовый отчет

### Примеры ИНН для тестирования

```text
✅ 7707083893 - Сбербанк
✅ 7702070139 - Газпром
✅ 7702261992 - Лукойл
✅ 7736050003 - Яндекс
✅ 7825700086 - ВТБ
```

---

## 📊 Команды бота

### Команды пользователя

```text
/start      - Приветственное сообщение
/help       - Полная справка по использованию
/history    - Последние 10 запросов
/stats      - Ваша статистика
```

### Примеры использования

```text
Пользователь: /start
Бот: 🏢 Добро пожаловать в Report_3!
     Я помогу вам проанализировать финансовую отчетность...

Пользователь: 7707083893
Бот: 🔍 Получаю данные из ФНС...
     🧠 Анализирую данные с помощью AI...
     📄 Генерирую HTML-отчет...
     ✅ Отчет готов! 📄 report_7707083893.html

Пользователь: /history
Бот: 📚 Ваша история:
     1. Сбербанк России - 7707083893 - 15.01.2024 14:30
     2. Газпром - 7702070139 - 14.01.2024 10:15
```

---

## 🗄 Структура базы данных

### ER-диаграмма

```sql
┌─────────────────┐     ┌─────────────────────┐
│      users       │     │      reports        │
├─────────────────┤     ├─────────────────────┤
│ id (PK)         │────<│ user_id (FK)        │
│ telegram_id     │     │ id (PK)             │
│ username        │     │ inn                 │
│ first_name      │     │ html_content        │
│ last_name       │     │ analysis_summary    │
│ is_active       │     │ company_name        │
│ is_admin        │     │ period              │
│ total_requests  │     │ risk_level          │
│ created_at      │     │ status              │
│ updated_at      │     │ created_at          │
└─────────────────┘     │ updated_at          │
                        └─────────────────────┘

┌─────────────────┐
│      cache      │
├─────────────────┤
│ id (PK)         │
│ cache_key       │
│ cache_type      │
│ data            │
│ expires_at      │
│ inn             │
│ request_count   │
│ created_at      │
└─────────────────┘
```

### Описание таблиц

#### Таблица `users`
Хранит информацию о пользователях Telegram.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `telegram_id` | BigInteger | ID пользователя в Telegram |
| `username` | String(64) | Имя пользователя |
| `first_name` | String(64) | Имя |
| `last_name` | String(64) | Фамилия |
| `is_active` | Boolean | Активен ли пользователь |
| `is_admin` | Boolean | Является ли администратором |
| `total_requests` | Integer | Общее количество запросов |
| `created_at` | DateTime | Дата регистрации |
| `updated_at` | DateTime | Дата обновления |

#### Таблица `reports`
Хранит все сгенерированные отчеты.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `user_id` | BigInteger | ID пользователя |
| `inn` | String(12) | ИНН компании |
| `html_content` | Text | HTML-содержимое отчета |
| `analysis_summary` | Text | Краткое резюме анализа |
| `company_name` | String(255) | Название компании |
| `period` | String(20) | Отчетный период |
| `risk_level` | String(20) | Уровень риска |
| `status` | String(20) | Статус отчета |
| `created_at` | DateTime | Дата создания |
| `updated_at` | DateTime | Дата обновления |

#### Таблица `cache`
Кеш для данных из внешних API.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer | Первичный ключ |
| `cache_key` | String(255) | Уникальный ключ кеша |
| `cache_type` | String(50) | Тип кеша (fns, ionet) |
| `data` | Text | JSON-данные |
| `expires_at` | DateTime | Время истечения |
| `inn` | String(12) | ИНН (для поиска) |
| `request_count` | Integer | Количество обращений |
| `created_at` | DateTime | Дата создания |

### Индексы для производительности

```sql
-- Для быстрого поиска отчетов пользователя
CREATE INDEX ix_reports_user_inn ON reports (user_id, inn);

-- Для поиска по ИНН
CREATE INDEX ix_reports_inn ON reports (inn);

-- Для истории пользователя
CREATE INDEX ix_reports_user_created ON reports (user_id, created_at);

-- Для кеша
CREATE INDEX ix_cache_key ON cache (cache_key);
CREATE INDEX ix_cache_expires ON cache (expires_at);
```

---

## 🛠 Технологии

### Основные

| Технология | Версия | Назначение |
|------------|--------|------------|
| **Python** | 3.11+ | Язык программирования |
| **Aiogram** | 3.x | Фреймворк для Telegram ботов |
| **PostgreSQL** | 15+ | Основная база данных |
| **SQLAlchemy** | 2.x | ORM для работы с БД |
| **Alembic** | 1.x | Миграции базы данных |

### Интеграции

| Сервис | Назначение |
|--------|------------|
| **API ФНС** | Получение финансовой отчетности |
| **IO_NET** | ИИ-анализ финансовых данных |

### Утилиты

| Библиотека | Назначение |
|------------|------------|
| **httpx** | Асинхронные HTTP-запросы |
| **Jinja2** | Генерация HTML-отчетов |
| **Pydantic** | Валидация данных |
| **Loguru** | Логирование |
| **Python-magic** | Определение MIME-типов |
| **Celery** | Асинхронные задачи |
| **Redis** | Кеширование |

### Полный список зависимостей

```txt
aiofiles==25.1.0
aiogram==3.30.0
alembic==1.18.5
asyncpg==0.31.0
celery==5.6.3
httpx==0.28.1
Jinja2==3.1.6
loguru==0.7.3
openai==2.46.0
pydantic==2.13.4
pydantic-settings==2.14.2
python-dotenv==1.2.2
python-magic==0.4.27
redis==8.0.1
SQLAlchemy==2.0.51
```

---

## 🐳 Docker

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание необходимых директорий
RUN mkdir -p /app/reports /tmp/reports

# Запуск бота
CMD ["python", "-m", "app.main"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: report3_db
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASS}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: report3_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  bot:
    build: .
    container_name: report3_bot
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASS=${DB_PASS}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - FNS_API_KEY=${FNS_API_KEY}
      - IONET_API_KEY=${IONET_API_KEY}
      - DEBUG=${DEBUG}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./reports:/app/reports
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

---

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта!

### Как помочь

1. 🐛 **Сообщить об ошибке** — создайте Issue с описанием проблемы
2. 💡 **Предложить улучшение** — расскажите о новых идеях
3. 📝 **Улучшить документацию** — исправьте или дополните README
4. 🔧 **Внести код** — создайте Pull Request с новым функционалом

### Процесс разработки

```bash
# 1. Форк репозитория
# 2. Клонирование форка
git clone https://github.com/yourusername/report_3.git

# 3. Создание ветки
git checkout -b feature/amazing-feature

# 4. Коммит изменений
git add .
git commit -m 'Add some amazing feature'

# 5. Пуш в ветку
git push origin feature/amazing-feature

# 6. Создание Pull Request
```

### Требования к коду

- ✅ Следование PEP 8
- ✅ Добавление комментариев
- ✅ Написание тестов
- ✅ Обновление документации

---

## 📄 Лицензия

Этот проект распространяется под лицензией MIT.

```text
MIT License

Copyright (c) 2024 Report_3

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 📞 Контакты

| Контакт | Ссылка |
|---------|--------|
| 📧 Email | your.email@example.com |
| 💬 Telegram | [@your_username](https://t.me/your_username) |
| 🐛 Issues | [GitHub Issues](https://github.com/yourusername/report_3/issues) |
| 📚 Документация | [Wiki](https://github.com/yourusername/report_3/wiki) |

---

## ⭐ Поддержка проекта

Если вам понравился проект, поставьте звезду ⭐ на GitHub!

<p align="center">
  <a href="https://github.com/yourusername/report_3">
    <img src="https://img.shields.io/github/stars/yourusername/report_3?style=social" alt="GitHub stars">
  </a>
  <a href="https://github.com/yourusername/report_3/network/members">
    <img src="https://img.shields.io/github/forks/yourusername/report_3?style=social" alt="GitHub forks">
  </a>
</p>

---

## 🙏 Благодарности

- [Aiogram](https://docs.aiogram.dev/) — за отличный фреймворк для ботов
- [PostgreSQL](https://www.postgresql.org/) — за надежную базу данных
- [IO_NET](https://ionet.ai/) — за мощный AI-анализ
- [API ФНС](https://api-fns.ru/) — за доступ к финансовым данным

---

<p align="center">
  <b>Сделано с ❤️ для финансового анализа</b>
</p>

<p align="center">
  <i>Report_3 — Ваш надежный помощник в финансовом анализе</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/⭐-Support%20us-brightgreen.svg" alt="Support">
  <img src="https://img.shields.io/badge/📊-Financial%20Analysis-blue.svg" alt="Financial Analysis">
  <img src="https://img.shields.io/badge/🤖-AI%20Powered-purple.svg" alt="AI Powered">
</p>
```

---