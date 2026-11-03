"""Смета из спецификации и справочника материалов.

Порядок счёта (учебно-прозрачный):
1. Плита и задняя стенка: площадь по материалу суммируется в мм² целыми числами,
   переводится в м², умножается на коэффициент запаса и округляется до 0,01 м² один раз.
2. Кромка: погонные мм по всем деталям → м × коэффициент запаса → округление до 0,01 м.
3. Фурнитура: штуки × коэффициент запаса, округление вверх до целой штуки.
4. Сумма строки = количество × цена за единицу (в копейках), до копейки, половина вверх.

Строка без цены не даёт суммы: итог помечается неполным. Если в смете цены разных дат,
это тоже предупреждение.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from app.domain.design import Specification
from app.domain.money import amount_kop

MM2_IN_M2 = Decimal(1_000_000)
MM_IN_M = Decimal(1000)
CENT = Decimal("0.01")


@dataclass(frozen=True)
class MaterialPrice:
    code: str
    name: str
    kind: str  # board | back | edge | hardware
    unit: str  # m2 | m | pcs
    price_kop: int | None
    price_date: date | None
    waste_factor: Decimal


@dataclass(frozen=True)
class EstimateLine:
    kind: str
    material_code: str
    name: str
    unit: str
    net_quantity: Decimal
    waste_factor: Decimal
    quantity: Decimal
    price_kop: int | None
    price_date: date | None
    amount_kop: int | None


@dataclass(frozen=True)
class Estimate:
    lines: list[EstimateLine]
    totals_by_kind: dict[str, int]
    total_kop: int
    complete: bool
    warnings: list[str]


class UnknownMaterialError(Exception):
    pass


def area_m2(area_mm2: int) -> Decimal:
    """Точная площадь в м². Округлять здесь нельзя (BUG-01)."""
    return Decimal(area_mm2) / MM2_IN_M2


def _line(kind: str, m: MaterialPrice, net: Decimal) -> EstimateLine:
    if m.unit == "pcs":
        qty = (net * m.waste_factor).quantize(Decimal(1), rounding=ROUND_CEILING)
    else:
        qty = (net * m.waste_factor).quantize(CENT, rounding=ROUND_HALF_UP)
    amount = amount_kop(qty, m.price_kop) if m.price_kop is not None else None
    return EstimateLine(
        kind, m.code, m.name, m.unit, net, m.waste_factor, qty, m.price_kop, m.price_date, amount
    )


def build_estimate(spec: Specification, prices: dict[str, MaterialPrice]) -> Estimate:
    def material(code: str) -> MaterialPrice:
        try:
            return prices[code]
        except KeyError:
            raise UnknownMaterialError(f"материала {code} нет в справочнике") from None

    area_by_code: dict[str, int] = defaultdict(int)
    edge_mm = 0
    for part in spec.parts:
        area_by_code[part.material_code] += part.area_mm2
        edge_mm += part.edge_mm

    lines: list[EstimateLine] = []
    for code, mm2 in area_by_code.items():
        m = material(code)
        lines.append(_line(m.kind, m, area_m2(mm2)))
    if edge_mm:
        m = material(spec.edge_code)
        lines.append(_line("edge", m, Decimal(edge_mm) / MM_IN_M))
    for item in spec.hardware:
        m = material(item.material_code)
        lines.append(_line("hardware", m, Decimal(item.qty)))

    totals: dict[str, int] = defaultdict(int)
    warnings: list[str] = []
    missing = [ln.name for ln in lines if ln.amount_kop is None]
    for ln in lines:
        if ln.amount_kop is not None:
            totals[ln.kind] += ln.amount_kop
    if missing:
        warnings.append("итог неполный: нет цены — " + ", ".join(missing))
    dates = sorted({ln.price_date for ln in lines if ln.price_date is not None})
    if len(dates) > 1:
        warnings.append("цены разных дат: " + ", ".join(d.strftime("%d.%m.%Y") for d in dates))
    return Estimate(
        lines=lines,
        totals_by_kind=dict(totals),
        total_kop=sum(totals.values()),
        complete=not missing,
        warnings=warnings,
    )
