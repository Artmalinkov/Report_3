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
    IONET_API_URL: str = "https://api.intelligence.io.solutions/api/v1"
    IONET_MODEL: str = "meta-llama/Llama-3.3-70B-Instruct"

    # App
    DEBUG: bool = False

    # Rate limiting — защита платных API (ФНС, IO_NET) от спама/злоупотреблений
    RATE_LIMIT_COOLDOWN_SECONDS: int = 15
    RATE_LIMIT_DAILY_MAX: int = 20

    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"  # "text" — читаемо для разработки, "json" — для прод/агрегаторов логов

    # Дашборд (внутренняя админ-панель, без публичного доступа — см. ROADMAP)
    DASHBOARD_SECRET_KEY: str = "change-me-in-env"  # для подписи сессионной cookie
    DASHBOARD_PORT: int = 8080
    # Адрес, который бот подставляет в magic-link — с точки зрения браузера
    # админа (для прод-сервера открывается через SSH-туннель на этот же порт)
    DASHBOARD_BASE_URL: str = "http://localhost:8080"

    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        case_sensitive = True


settings = Settings()