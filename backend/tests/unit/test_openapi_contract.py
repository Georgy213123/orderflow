"""Контракт первым: docs/03-design/openapi.yaml совпадает с тем, что отдаёт код."""

from pathlib import Path

import yaml

from app.main import app

CONTRACT = Path(__file__).resolve().parents[3] / "docs" / "03-design" / "openapi.yaml"


def test_openapi_file_matches_code() -> None:
    assert CONTRACT.exists(), "выполните make openapi"
    on_disk = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert on_disk == app.openapi(), "контракт разошёлся с кодом: make openapi"
