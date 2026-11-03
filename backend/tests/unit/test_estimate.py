"""US-04: смета из спецификации (FR-08…FR-11)."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.design import CabinetParams, HardwareItem, Part, Specification, build_specification
from app.domain.estimate import MaterialPrice, UnknownMaterialError, area_m2, build_estimate
from app.seed import MATERIALS


def price_list() -> dict[str, MaterialPrice]:
    from app.domain.money import rub_to_kop

    return {
        code: MaterialPrice(
            code,
            name,
            kind,
            unit,
            rub_to_kop(price) if price else None,
            price_date,
            Decimal(waste),
        )
        for code, name, kind, unit, _t, price, price_date, waste in MATERIALS
    }


WARDROBE = CabinetParams(width_mm=1200, height_mm=2100, depth_mm=600, shelves=4, doors=2)
# Ожидаемый итог посчитан вручную в docs/05-testing.md и проверяется в e2e.
EXPECTED_TOTAL_KOP = 1_233_196


def test_us04_wardrobe_total() -> None:
    est = build_estimate(build_specification(WARDROBE), price_list())
    assert est.total_kop == EXPECTED_TOTAL_KOP
    assert est.complete
    assert est.warnings == []
    assert est.totals_by_kind == {
        "board": 860_180,
        "back": 85_560,
        "edge": 44_696,
        "hardware": 242_760,
    }


def test_us04_board_line_is_transparent() -> None:
    est = build_estimate(build_specification(WARDROBE), price_list())
    board = next(ln for ln in est.lines if ln.material_code == "LDSP16-WHITE")
    assert board.net_quantity == Decimal("9.125152")
    assert board.waste_factor == Decimal("1.15")
    assert board.quantity == Decimal("10.49")
    assert board.amount_kop == 860_180


def test_bug01_area_is_rounded_once_not_per_part() -> None:
    """BUG-01: площадь детали округлялась до 0,01 м² до суммирования.
    10 деталей 300×350 = 1,05 м²; поштучное округление давало 10 × 0,11 = 1,10 м²."""
    parts = [Part(f"p{i}", "Деталь", 300, 350, 1, "LDSP16-WHITE") for i in range(10)]
    spec = Specification(parts=parts, hardware=[], edge_code="EDGE04-WHITE")
    est = build_estimate(spec, price_list())
    (line,) = est.lines
    assert line.net_quantity == Decimal("1.05")
    assert area_m2(300 * 350) == Decimal("0.105")


def test_missing_price_marks_total_incomplete() -> None:
    p = CabinetParams(
        width_mm=800, height_mm=900, depth_mm=400, doors=2, handle_code="HW-HANDLE-BLACK"
    )
    est = build_estimate(build_specification(p), price_list())
    handle = next(ln for ln in est.lines if ln.material_code == "HW-HANDLE-BLACK")
    assert handle.amount_kop is None
    assert not est.complete
    assert est.warnings == ["итог неполный: нет цены — Ручка-скоба 128 мм, чёрная"]
    assert est.total_kop == sum(ln.amount_kop or 0 for ln in est.lines)


def test_prices_of_different_dates_are_flagged() -> None:
    p = CabinetParams(width_mm=800, height_mm=900, depth_mm=400, board_code="LDSP16-GRAPHITE")
    est = build_estimate(build_specification(p), price_list())
    assert est.complete
    assert est.warnings == ["цены разных дат: 15.09.2026, 01.10.2026"]


def test_hardware_waste_rounds_up_to_whole_piece() -> None:
    prices = price_list()
    prices["HW-CONFIRMAT"] = MaterialPrice(
        "HW-CONFIRMAT", "Конфирмат", "hardware", "pcs", 320, date(2026, 10, 1), Decimal("1.05")
    )
    spec = Specification([], [HardwareItem("HW-CONFIRMAT", "Конфирмат", 8)], "EDGE04-WHITE")
    (line,) = build_estimate(spec, prices).lines
    assert line.quantity == Decimal(9)


def test_unknown_material() -> None:
    spec = Specification([Part("x", "Деталь", 100, 100, 1, "NOPE")], [], "EDGE04-WHITE")
    with pytest.raises(UnknownMaterialError):
        build_estimate(spec, price_list())
