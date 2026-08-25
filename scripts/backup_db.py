# scripts/backup_db.py
"""
Резервное копирование базы данных PostgreSQL через pg_dump
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

BACKUP_DIR = Path(__file__).parent.parent / "backups"


def backup_database() -> Path:
    """Создает SQL-дамп текущей БД в backups/, возвращает путь к файлу"""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = BACKUP_DIR / f"{settings.DB_NAME}_{timestamp}.sql"

    cmd = [
        "pg_dump",
        "-h", settings.DB_HOST,
        "-p", str(settings.DB_PORT),
        "-U", settings.DB_USER,
        "-d", settings.DB_NAME,
        "-f", str(out_path),
        "--no-owner",
        "--no-privileges",
    ]
    env = {**os.environ, "PGPASSWORD": settings.DB_PASS}

    print(f"Создаю бэкап {settings.DB_NAME} -> {out_path}...")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Ошибка pg_dump:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"Готово: {out_path.name} ({size_mb:.2f} МБ)")
    return out_path


def cleanup_old_backups(keep: int = 10) -> None:
    """Удаляет старые бэкапы, оставляя только keep последних по дате изменения"""
    backups = sorted(
        BACKUP_DIR.glob(f"{settings.DB_NAME}_*.sql"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for old in backups[keep:]:
        old.unlink()
        print(f"Удален старый бэкап: {old.name}")


if __name__ == "__main__":
    backup_database()
    cleanup_old_backups()
