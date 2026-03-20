import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv


def _load_env() -> None:
    env_file = os.getenv("ENV_FILE", ".env")
    # python-dotenv: при отсутствии файла не падаем — переменные могут быть заданы окружением
    load_dotenv(dotenv_path=env_file, override=False)


_load_env()


def _get_int(name: str, default: Optional[int] = None) -> Optional[int]:
    val = os.getenv(name, None)
    if val is None or val == "":
        return default
    return int(val)


def _parse_admin_ids() -> List[int]:
    raw = os.getenv("ADMIN_ID", "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    return [int(p) for p in parts]


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: List[int]
    subscription_channel_id: int
    db_type: str
    database_url: str
    sqlite_path: str
    log_level: str


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set (check your .env)")

    admin_ids = _parse_admin_ids()

    # На некоторых хостингах переменные окружения/файлы .env могут не подхватываться.
    # Чтобы бот не падал на старте, делаем значение необязательным и валидируем позже по бизнес-логике.
    # 0 = "не настроено"
    subscription_channel_id = _get_int("SUBSCRIPTION_CHANNEL_ID", 0) or 0

    db_type = os.getenv("DB_TYPE", "sqlite").strip().lower()
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    sqlite_path = os.getenv("SQLITE_PATH", "data.sqlite").strip()
    # SQLAlchemy async URL for SQLite
    sqlite_url = f"sqlite+aiosqlite:///{sqlite_path}"

    database_url = os.getenv("DATABASE_URL", "").strip()
    if db_type == "sqlite":
        database_url = database_url or sqlite_url
    else:
        if not database_url:
            # Для PostgreSQL ожидаем готовый DATABASE_URL (sqlalchemy async dialect)
            # например: postgresql+asyncpg://user:pass@host:5432/dbname
            raise RuntimeError("DATABASE_URL is required when DB_TYPE is not sqlite")

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        subscription_channel_id=subscription_channel_id,
        db_type=db_type,
        database_url=database_url,
        sqlite_path=sqlite_path,
        log_level=log_level,
    )


settings = get_settings()

