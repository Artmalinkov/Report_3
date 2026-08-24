FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Chromium для рендеринга PDF-версий отчетов (app/services/report_generator.py).
# --with-deps ставит системные библиотеки, которых нет в minimal-образе
RUN playwright install --with-deps chromium

COPY app ./app
COPY migrations ./migrations
COPY templates ./templates
COPY alembic.ini .

RUN mkdir -p /app/reports /app/logs

CMD ["sh", "-c", "alembic upgrade head && python -m app.main"]
