"""Настройки приложения. Всё берётся из переменных окружения."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres@localhost:55301/orderflow"
    # Разбор текста заявки: "rules" — правила и регулярные выражения (по умолчанию),
    # "llm" — адаптер к языковой модели (в демо не подключён).
    request_parser: str = "rules"
    llm_api_url: str = ""
    llm_api_key: str = ""
    cors_origins: str = "http://localhost:5301"


@lru_cache
def get_settings() -> Settings:
    return Settings()
