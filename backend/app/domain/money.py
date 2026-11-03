"""Деньги: целые копейки, количества — Decimal. Float в расчётах не участвует (ADR-0003)."""

from decimal import ROUND_HALF_UP, Decimal

KOPECKS_IN_RUBLE = 100


def amount_kop(quantity: Decimal, price_kop: int) -> int:
    """Сумма строки сметы в копейках: количество × цена за единицу, округление до копейки
    по правилу «половина вверх»."""
    if not isinstance(quantity, Decimal):
        raise TypeError("количество должно быть Decimal, float в денежных расчётах запрещён")
    return int((quantity * price_kop).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def rub_to_kop(rub: str) -> int:
    """'1234.56' → 123456. Принимает только строку, чтобы не протащить float."""
    value = Decimal(rub).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(value * KOPECKS_IN_RUBLE)


def format_kop(kop: int) -> str:
    """123456 → '1 234,56'."""
    sign = "-" if kop < 0 else ""
    rub, k = divmod(abs(kop), KOPECKS_IN_RUBLE)
    return f"{sign}{rub:,}".replace(",", " ") + f",{k:02d}"
