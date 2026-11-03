"""Поля заявки и их источник.

Каждое поле знает, откуда пришло значение: «найдено в тексте» (text) или «ввёл человек»
(human). Значение из текста — предположение разбора: оно не считается заполненным, пока
человек его не подтвердил.
"""

from dataclasses import dataclass
from enum import StrEnum


class FieldSource(StrEnum):
    TEXT = "text"
    HUMAN = "human"


class FieldKey(StrEnum):
    PRODUCT_TYPE = "product_type"
    WIDTH_MM = "width_mm"
    HEIGHT_MM = "height_mm"
    DEPTH_MM = "depth_mm"
    SHELVES = "shelves"
    DOORS = "doors"
    CLIENT_NAME = "client_name"
    PHONE = "phone"
    EMAIL = "email"


FIELD_LABELS: dict[FieldKey, str] = {
    FieldKey.PRODUCT_TYPE: "Изделие",
    FieldKey.WIDTH_MM: "Ширина, мм",
    FieldKey.HEIGHT_MM: "Высота, мм",
    FieldKey.DEPTH_MM: "Глубина, мм",
    FieldKey.SHELVES: "Полок",
    FieldKey.DOORS: "Дверей",
    FieldKey.CLIENT_NAME: "Клиент",
    FieldKey.PHONE: "Телефон",
    FieldKey.EMAIL: "Почта",
}

REQUIRED_FIELDS: frozenset[FieldKey] = frozenset(
    {
        FieldKey.PRODUCT_TYPE,
        FieldKey.WIDTH_MM,
        FieldKey.HEIGHT_MM,
        FieldKey.DEPTH_MM,
        FieldKey.CLIENT_NAME,
        FieldKey.PHONE,
    }
)

INT_FIELDS: frozenset[FieldKey] = frozenset(
    {FieldKey.WIDTH_MM, FieldKey.HEIGHT_MM, FieldKey.DEPTH_MM, FieldKey.SHELVES, FieldKey.DOORS}
)


@dataclass(frozen=True)
class FieldState:
    value: str
    source: FieldSource
    confirmed: bool
    fragment: str | None = None


def apply_human_input(current: FieldState | None, new_value: str) -> FieldState:
    """Человек подтвердил или поправил поле.

    Значение не изменилось — это подтверждение: источник остаётся прежним, поле становится
    подтверждённым. Значение изменилось — источник «ввёл человек».
    Баг BUG-04: раньше повторное подтверждение всегда ставило источник «human», и
    источник «найдено в тексте» терялся.
    """
    value = new_value.strip()
    if current is not None and current.value == value:
        return FieldState(value, current.source, True, current.fragment)
    return FieldState(value, FieldSource.HUMAN, True, None)


def missing_for_parsed(fields: dict[FieldKey, FieldState]) -> list[str]:
    """Что мешает перевести заявку в «разобрана». Пустой список — можно."""
    problems: list[str] = []
    for key in FieldKey:
        state = fields.get(key)
        label = FIELD_LABELS[key]
        if state is None or not state.value:
            if key in REQUIRED_FIELDS:
                problems.append(f"{label}: не заполнено")
            continue
        if not state.confirmed:
            problems.append(f"{label}: найдено в тексте, но не подтверждено")
    return problems
