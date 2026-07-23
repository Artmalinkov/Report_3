# for_dev/check_db.py

"""
Проверка состояния базы данных
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from app.database.session import AsyncSessionLocal
from sqlalchemy import text


async def check_tables():
    """Проверка существующих таблиц"""
    async with AsyncSessionLocal() as session:
        # Получаем список таблиц
        result = await session.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
        )
        tables = result.fetchall()

        print("=" * 50)
        print("📊 TABLES IN DATABASE report3")
        print("=" * 50)

        if tables:
            for table in tables:
                print(f"  ✅ {table[0]}")
        else:
            print("  ❌ No tables found")

        print("=" * 50)

        # Check alembic_version
        result = await session.execute(
            text("SELECT * FROM alembic_version")
        )
        version = result.fetchone()
        if version:
            print(f"📌 Alembic version: {version[0]}")

        # Statistics
        print("\n📊 Statistics:")
        for table in tables:
            table_name = table[0]
            if table_name != 'alembic_version':
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                )
                count = result.fetchone()[0]
                print(f"  📄 {table_name}: {count} records")


async def check_users():
    """Проверка пользователей"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM users")
        )
        count = result.fetchone()[0]
        print(f"👥 Users in database: {count}")


if __name__ == "__main__":
    asyncio.run(check_tables())