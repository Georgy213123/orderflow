"""Находки ревью Codex: регрессионные тесты без БД (R-01, R-06, R-07, R-09)."""

import pytest
from fastapi.testclient import TestClient

from app.domain.fields import FieldKey
from app.domain.parser import RuleBasedParser
from app.main import app
from tests.db_guard import UnsafeDatabaseError, require_test_database


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://postgres@localhost:55301/orderflow",
        "postgresql+psycopg://postgres@localhost:55301/orderflow_victim",
        "postgresql+psycopg://postgres@localhost:55301/test_orderflow_prod",
    ],
)
def test_r01_destructive_fixture_refuses_non_test_database(url: str) -> None:
    with pytest.raises(UnsafeDatabaseError):
        require_test_database(url)


def test_r01_test_database_is_allowed() -> None:
    require_test_database("postgresql+psycopg://postgres@localhost:55301/orderflow_test")


def test_r07_huge_number_in_text_does_not_crash_parser() -> None:
    parsed = RuleBasedParser().parse("шкаф, полок: " + "9" * 4310)
    assert FieldKey.SHELVES not in parsed


def test_r07_huge_dimension_does_not_crash_parser() -> None:
    parsed = RuleBasedParser().parse("шкаф ширина " + "9" * 4400 + " мм")
    assert FieldKey.WIDTH_MM not in parsed


def test_r06_too_long_manual_field_is_422() -> None:
    r = TestClient(app).post("/api/requests", json={"fields": {"client_name": "я" * 256}})
    assert r.status_code == 422
    assert r.json()["message"] == "неверный запрос"


def test_r09_validation_errors_use_problem_format() -> None:
    client = TestClient(app)
    r = client.get("/api/requests/not-an-int")
    assert r.status_code == 422
    assert set(r.json()) == {"message", "problems"}


def test_r09_contract_declares_problem_for_every_422() -> None:
    spec = app.openapi()
    wrong = [
        f"{method.upper()} {path}"
        for path, ops in spec["paths"].items()
        for method, op in ops.items()
        if "422" in op["responses"]
        and op["responses"]["422"]["content"]["application/json"]["schema"]["$ref"]
        != "#/components/schemas/Problem"
    ]
    assert wrong == []
