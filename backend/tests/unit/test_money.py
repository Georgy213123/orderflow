from decimal import Decimal

import pytest

from app.domain.money import amount_kop, format_kop, rub_to_kop


def test_amount_rounds_half_up_to_kopeck() -> None:
    assert amount_kop(Decimal("0.5"), 1) == 1
    assert amount_kop(Decimal("10.49"), 82000) == 860180


def test_bug05_float_lost_a_kopeck() -> None:
    """BUG-05: 1,15 м² × 905,50 руб. Во float выходило 1041,32, верно 1041,33."""
    assert round(1.15 * 905.50, 2) == 1041.32  # так считал старый код
    assert amount_kop(Decimal("1.15"), rub_to_kop("905.50")) == 104133


def test_float_quantity_is_rejected() -> None:
    with pytest.raises(TypeError):
        amount_kop(1.15, 90550)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("rub", "kop"), [("820.00", 82000), ("18.5", 1850), ("0.005", 1), ("1040", 104000)]
)
def test_rub_to_kop(rub: str, kop: int) -> None:
    assert rub_to_kop(rub) == kop


def test_format_kop() -> None:
    assert format_kop(1233196) == "12 331,96"
    assert format_kop(5) == "0,05"
    assert format_kop(-150) == "-1,50"
