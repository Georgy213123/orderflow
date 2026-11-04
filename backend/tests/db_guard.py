"""Защита от запуска разрушающих фикстур на рабочей базе.

Интеграционные фикстуры делают `downgrade base` и `TRUNCATE`. Запускаем их только на базе,
имя которой оканчивается на `_test`.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


class UnsafeDatabaseError(RuntimeError):
    pass


def require_test_database(url: str) -> None:
    name = make_url(url).database or ""
    if not name.endswith("_test"):
        raise UnsafeDatabaseError(
            f"интеграционные тесты стирают данные; база «{name}» не похожа на тестовую "
            "(имя должно оканчиваться на _test)"
        )


def reset_public_schema(url: str) -> None:
    """Пересоздать схему `public` тестовой базы: чужая `alembic_version` не должна влиять."""
    require_test_database(url)
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()
