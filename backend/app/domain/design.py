"""Параметрическая модель шкафа → спецификация деталей.

Модель учебная и прозрачная: корпус из двух боковин, крыши и дна между боковинами,
полок, накладных дверей и задней стенки из тонкой плиты. Все размеры — целые миллиметры.
"""

from dataclasses import dataclass, field

# Допустимые пределы. Вымышленные, но правдоподобные для мастерской.
WIDTH_RANGE = (300, 2400)
HEIGHT_RANGE = (300, 2700)
DEPTH_RANGE = (250, 700)
THICKNESSES = (16, 18)
MAX_SHELVES = 10
MAX_DOORS = 4
DOOR_WIDTH_RANGE = (250, 700)
SHEET_MM = (2800, 2070)  # формат листа плиты: деталь должна в него помещаться

SHELF_GAP_MM = 2  # зазор полки в проёме, чтобы встала без усилия
SHELF_BACK_OFFSET_MM = 20  # полка короче глубины корпуса на отступ от задней стенки
MIN_SHELF_SPACING_MM = 180  # минимальный просвет между полками
DOOR_OUTER_GAP_MM = 2  # зазор фасада по краю корпуса, с каждой стороны
DOOR_BETWEEN_GAP_MM = 3  # зазор между соседними фасадами
BACK_GAP_MM = 2  # задняя стенка меньше корпуса на 2 мм с каждой стороны

HINGE_CODE = "HW-HINGE"
CONFIRMAT_CODE = "HW-CONFIRMAT"
SHELF_PIN_CODE = "HW-SHELF-PIN"


@dataclass(frozen=True)
class CabinetParams:
    width_mm: int
    height_mm: int
    depth_mm: int
    thickness_mm: int = 16
    shelves: int = 0
    doors: int = 0
    back_panel: bool = True
    board_code: str = "LDSP16-WHITE"
    edge_code: str = "EDGE04-WHITE"
    back_code: str = "HDF3-WHITE"
    handle_code: str = "HW-HANDLE"

    @property
    def inner_width_mm(self) -> int:
        """Внутренний проём между боковинами."""
        return self.width_mm - 2 * self.thickness_mm

    @property
    def inner_height_mm(self) -> int:
        return self.height_mm - 2 * self.thickness_mm


@dataclass(frozen=True)
class Part:
    code: str
    name: str
    length_mm: int
    width_mm: int
    qty: int
    material_code: str
    # Кромка: сколько длинных и сколько коротких сторон детали оклеиваются (0–2).
    edge_long: int = 0
    edge_short: int = 0

    @property
    def area_mm2(self) -> int:
        return self.length_mm * self.width_mm * self.qty

    @property
    def edge_mm(self) -> int:
        return (self.edge_long * self.length_mm + self.edge_short * self.width_mm) * self.qty


@dataclass(frozen=True)
class HardwareItem:
    material_code: str
    name: str
    qty: int


@dataclass(frozen=True)
class Specification:
    parts: list[Part]
    hardware: list[HardwareItem]
    edge_code: str


@dataclass
class DesignError(Exception):
    problems: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return "; ".join(self.problems)


def _in(value: int, bounds: tuple[int, int]) -> bool:
    return bounds[0] <= value <= bounds[1]


def door_width_mm(p: CabinetParams) -> int:
    if p.doors == 0:
        return 0
    free = p.width_mm - 2 * DOOR_OUTER_GAP_MM - (p.doors - 1) * DOOR_BETWEEN_GAP_MM
    return free // p.doors


def hinges_per_door(door_height_mm: int) -> int:
    if door_height_mm <= 900:
        return 2
    if door_height_mm <= 1600:
        return 3
    if door_height_mm <= 2000:
        return 4
    return 5


def validate_params(p: CabinetParams) -> list[str]:
    problems: list[str] = []
    if not _in(p.width_mm, WIDTH_RANGE):
        problems.append(f"ширина {p.width_mm} мм вне пределов {WIDTH_RANGE[0]}–{WIDTH_RANGE[1]}")
    if not _in(p.height_mm, HEIGHT_RANGE):
        problems.append(f"высота {p.height_mm} мм вне пределов {HEIGHT_RANGE[0]}–{HEIGHT_RANGE[1]}")
    if not _in(p.depth_mm, DEPTH_RANGE):
        problems.append(f"глубина {p.depth_mm} мм вне пределов {DEPTH_RANGE[0]}–{DEPTH_RANGE[1]}")
    if p.thickness_mm not in THICKNESSES:
        problems.append(f"толщина плиты {p.thickness_mm} мм не из списка {THICKNESSES}")
    if not 0 <= p.shelves <= MAX_SHELVES:
        problems.append(f"полок {p.shelves}, допустимо 0–{MAX_SHELVES}")
    if not 0 <= p.doors <= MAX_DOORS:
        problems.append(f"дверей {p.doors}, допустимо 0–{MAX_DOORS}")
    if problems:
        return problems

    need = p.shelves * p.thickness_mm + (p.shelves + 1) * MIN_SHELF_SPACING_MM
    if p.shelves and need > p.inner_height_mm:
        problems.append(
            f"{p.shelves} полок не помещаются по высоте: нужно {need} мм, "
            f"внутри корпуса {p.inner_height_mm} мм"
        )
    if p.doors:
        dw = door_width_mm(p)
        if not _in(dw, DOOR_WIDTH_RANGE):
            problems.append(
                f"ширина двери {dw} мм вне пределов {DOOR_WIDTH_RANGE[0]}–{DOOR_WIDTH_RANGE[1]}: "
                "измените число дверей"
            )
    return problems


def validate_parts(p: CabinetParams, parts: list[Part]) -> list[str]:
    """Инварианты готовой спецификации.

    Баг BUG-02: проверка полки сравнивала её длину с полной шириной корпуса, а не с
    внутренним проёмом (ширина минус две боковины). Полка шире проёма проходила.
    """
    problems: list[str] = []
    long_side, short_side = max(SHEET_MM), min(SHEET_MM)
    for part in parts:
        if part.length_mm <= 0 or part.width_mm <= 0 or part.qty <= 0:
            problems.append(f"{part.name}: неположительный размер или количество")
            continue
        if (
            max(part.length_mm, part.width_mm) > long_side
            or min(part.length_mm, part.width_mm) > short_side
        ):
            problems.append(f"{part.name}: {part.length_mm}×{part.width_mm} больше листа плиты")
        if part.code == "shelf":
            if part.length_mm > p.inner_width_mm:
                problems.append(
                    f"полка {part.length_mm} мм шире внутреннего проёма {p.inner_width_mm} мм"
                )
            if part.width_mm > p.depth_mm:
                problems.append(f"полка глубже корпуса: {part.width_mm} > {p.depth_mm} мм")
    return problems


def build_specification(p: CabinetParams) -> Specification:
    problems = validate_params(p)
    if problems:
        raise DesignError(problems)

    t = p.thickness_mm
    parts: list[Part] = [
        Part("side", "Боковина", p.height_mm, p.depth_mm, 2, p.board_code, edge_long=1),
        Part("top_bottom", "Крыша / дно", p.width_mm - 2 * t, p.depth_mm, 2, p.board_code, 1),
    ]
    if p.shelves:
        parts.append(
            Part(
                "shelf",
                "Полка",
                p.inner_width_mm - SHELF_GAP_MM,
                p.depth_mm - SHELF_BACK_OFFSET_MM,
                p.shelves,
                p.board_code,
                edge_long=1,
            )
        )
    if p.back_panel:
        parts.append(
            Part(
                "back",
                "Задняя стенка",
                p.height_mm - 2 * BACK_GAP_MM,
                p.width_mm - 2 * BACK_GAP_MM,
                1,
                p.back_code,
            )
        )
    door_height = p.height_mm - 2 * DOOR_OUTER_GAP_MM
    if p.doors:
        parts.append(
            Part(
                "door",
                "Фасад (дверь)",
                door_height,
                door_width_mm(p),
                p.doors,
                p.board_code,
                edge_long=2,
                edge_short=2,
            )
        )

    hardware: list[HardwareItem] = [HardwareItem(CONFIRMAT_CODE, "Конфирмат", 8)]
    if p.shelves:
        hardware.append(HardwareItem(SHELF_PIN_CODE, "Полкодержатель", 4 * p.shelves))
    if p.doors:
        hardware.append(
            HardwareItem(HINGE_CODE, "Петля накладная", hinges_per_door(door_height) * p.doors)
        )
        hardware.append(HardwareItem(p.handle_code, "Ручка", p.doors))

    part_problems = validate_parts(p, parts)
    if part_problems:
        raise DesignError(part_problems)
    return Specification(parts=parts, hardware=hardware, edge_code=p.edge_code)
