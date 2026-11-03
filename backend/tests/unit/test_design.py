"""US-03: конструкция шкафа и спецификация (FR-05…FR-07)."""

import pytest

from app.domain.design import (
    CabinetParams,
    DesignError,
    Part,
    build_specification,
    hinges_per_door,
    validate_parts,
)

WARDROBE = CabinetParams(width_mm=1200, height_mm=2100, depth_mm=600, shelves=4, doors=2)


def parts_by_code(p: CabinetParams) -> dict[str, Part]:
    return {part.code: part for part in build_specification(p).parts}


def test_us03_wardrobe_specification() -> None:
    parts = parts_by_code(WARDROBE)
    assert (parts["side"].length_mm, parts["side"].width_mm, parts["side"].qty) == (2100, 600, 2)
    assert (parts["top_bottom"].length_mm, parts["top_bottom"].qty) == (1168, 2)
    assert (parts["shelf"].length_mm, parts["shelf"].width_mm, parts["shelf"].qty) == (1166, 580, 4)
    assert (parts["back"].length_mm, parts["back"].width_mm) == (2096, 1196)
    assert (parts["door"].length_mm, parts["door"].width_mm, parts["door"].qty) == (2096, 596, 2)
    assert (parts["door"].edge_long, parts["door"].edge_short) == (2, 2)
    assert parts["back"].material_code == "HDF3-WHITE"


def test_us03_hardware_counts() -> None:
    hw = {h.material_code: h.qty for h in build_specification(WARDROBE).hardware}
    assert hw == {"HW-CONFIRMAT": 8, "HW-SHELF-PIN": 16, "HW-HINGE": 10, "HW-HANDLE": 2}


def test_shelf_uses_inner_opening_for_both_thicknesses() -> None:
    for t in (16, 18):
        p = CabinetParams(width_mm=800, height_mm=2000, depth_mm=500, thickness_mm=t, shelves=1)
        assert parts_by_code(p)["shelf"].length_mm == 800 - 2 * t - 2


def test_bug02_shelf_wider_than_inner_opening_is_rejected() -> None:
    """BUG-02: проверка сравнивала полку с полной шириной корпуса (800), а не с проёмом (768)."""
    p = CabinetParams(width_mm=800, height_mm=2000, depth_mm=500, shelves=1)
    too_wide = Part("shelf", "Полка", 790, 480, 1, p.board_code, edge_long=1)
    assert validate_parts(p, [too_wide]) == ["полка 790 мм шире внутреннего проёма 768 мм"]
    fits = Part("shelf", "Полка", 766, 480, 1, p.board_code, edge_long=1)
    assert validate_parts(p, [fits]) == []


@pytest.mark.parametrize(
    ("params", "message"),
    [
        (CabinetParams(width_mm=200, height_mm=2000, depth_mm=500), "ширина 200 мм вне пределов"),
        (CabinetParams(width_mm=800, height_mm=2000, depth_mm=900), "глубина 900 мм"),
        (CabinetParams(width_mm=800, height_mm=2000, depth_mm=500, thickness_mm=10), "толщина"),
        (
            CabinetParams(width_mm=800, height_mm=600, depth_mm=500, shelves=3),
            "3 полок не помещаются по высоте",
        ),
        (
            CabinetParams(width_mm=800, height_mm=2000, depth_mm=500, doors=4),
            "ширина двери 196 мм",
        ),
        (
            CabinetParams(width_mm=1800, height_mm=2000, depth_mm=500, doors=1),
            "ширина двери 1796 мм",
        ),
    ],
)
def test_invariants(params: CabinetParams, message: str) -> None:
    with pytest.raises(DesignError) as exc:
        build_specification(params)
    assert any(message in p for p in exc.value.problems), exc.value.problems


def test_no_back_panel_and_no_doors() -> None:
    p = CabinetParams(width_mm=900, height_mm=1800, depth_mm=350, shelves=3, back_panel=False)
    codes = set(parts_by_code(p))
    assert codes == {"side", "top_bottom", "shelf"}


@pytest.mark.parametrize(("h", "n"), [(700, 2), (900, 2), (1200, 3), (1900, 4), (2096, 5)])
def test_hinges_by_door_height(h: int, n: int) -> None:
    assert hinges_per_door(h) == n
