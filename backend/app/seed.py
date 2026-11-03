"""Справочник материалов демо. Все цены вымышленные."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.money import rub_to_kop
from app.models import Material

_OCT = date(2026, 10, 1)
_SEP = date(2026, 9, 15)

# code, name, kind, unit, thickness, price (руб., строкой), date, waste
MATERIALS: list[tuple[str, str, str, str, int | None, str | None, date | None, str]] = [
    ("LDSP16-WHITE", "ЛДСП 16 мм, белая", "board", "m2", 16, "820.00", _OCT, "1.15"),
    ("LDSP16-GRAPHITE", "ЛДСП 16 мм, графит", "board", "m2", 16, "905.50", _SEP, "1.15"),
    ("LDSP18-OAK", "ЛДСП 18 мм, дуб светлый", "board", "m2", 18, "1040.00", _OCT, "1.15"),
    ("HDF3-WHITE", "ХДФ 3 мм, белая", "back", "m2", 3, "310.00", _OCT, "1.10"),
    ("EDGE04-WHITE", "Кромка ПВХ 0,4 мм, белая", "edge", "m", None, "18.50", _OCT, "1.10"),
    ("EDGE2-WHITE", "Кромка ПВХ 2 мм, белая", "edge", "m", None, "42.00", _OCT, "1.10"),
    ("HW-CONFIRMAT", "Конфирмат 7×50", "hardware", "pcs", None, "3.20", _OCT, "1.00"),
    ("HW-SHELF-PIN", "Полкодержатель", "hardware", "pcs", None, "4.50", _OCT, "1.00"),
    ("HW-HINGE", "Петля накладная с доводчиком", "hardware", "pcs", None, "185.00", _OCT, "1.00"),
    ("HW-HANDLE", "Ручка-скоба 128 мм", "hardware", "pcs", None, "240.00", _OCT, "1.00"),
    ("HW-HANDLE-BLACK", "Ручка-скоба 128 мм, чёрная", "hardware", "pcs", None, None, None, "1.00"),
]


def seed_materials(session: Session) -> int:
    existing = set(session.scalars(select(Material.code)))
    added = 0
    for code, name, kind, unit, thick, price, price_date, waste in MATERIALS:
        if code in existing:
            continue
        session.add(
            Material(
                code=code,
                name=name,
                kind=kind,
                unit=unit,
                thickness_mm=thick,
                price_kop=rub_to_kop(price) if price is not None else None,
                price_date=price_date,
                waste_factor=Decimal(waste),
            )
        )
        added += 1
    session.commit()
    return added


if __name__ == "__main__":
    from sqlalchemy.orm import sessionmaker

    from app.db import get_engine

    with sessionmaker(bind=get_engine())() as s:
        print(f"материалов добавлено: {seed_materials(s)}")
