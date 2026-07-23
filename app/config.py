# app/config.py
'''
Файл основных конфигураций
'''
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Bot
    BOT_TOKEN: str

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "report3"
    DB_USER: str = "postgres"
    DB_PASS: str

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # API Keys
    FNS_API_KEY: str
    IONET_API_KEY: str
    IONET_API_URL: str = "https://api.ionet.ai/v1"
    IONET_MODEL: str = "gpt-4o-mini"

    # App
    DEBUG: bool = False

    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        case_sensitive = True


settings = Settings()