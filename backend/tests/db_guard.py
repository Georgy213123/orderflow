"""Защита от запуска разрушающих фикстур на рабочей базе.

Интеграционные фикстуры делают `downgrade base` и `TRUNCATE`. Запускаем их только на базе,
имя которой оканчивается на `_test`.
"""

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
