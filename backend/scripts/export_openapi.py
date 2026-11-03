"""Выгрузить контракт API в docs/03-design/openapi.yaml."""

import sys
from pathlib import Path

import yaml

from app.main import app

TARGET = Path(__file__).resolve().parents[2] / "docs" / "03-design" / "openapi.yaml"


def render() -> str:
    return yaml.safe_dump(app.openapi(), allow_unicode=True, sort_keys=False, width=100)


if __name__ == "__main__":
    TARGET.write_text(render(), encoding="utf-8")
    sys.stdout.write(f"записано: {TARGET}\n")
