"""Разбор свободного текста заявки.

`RequestParser` — интерфейс. По умолчанию работает `RuleBasedParser`: правила и регулярные
выражения, без сети и ключей. `LlmRequestParser` — точка подключения языковой модели,
в демо не реализован (ADR-0002).

Результат разбора — предположения: каждое поле помечается источником «найдено в тексте»
и считается неподтверждённым, пока его не подтвердит человек.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.domain.fields import FieldKey


@dataclass(frozen=True)
class ParsedField:
    value: str
    fragment: str


class RequestParser(Protocol):
    name: str

    def parse(self, text: str) -> dict[FieldKey, ParsedField]: ...


# Длина чисел ограничена: размер — до 5 цифр, количество — до 2 (R-07 ревью).
_NUM = r"(?<![\d.,])(\d{1,5}(?:[.,]\d{1,3})?)(?![\d.,]*\d)"
_UNIT = r"(мм|см|м)?"
_UNIT_MM: dict[str, int] = {"мм": 1, "см": 10, "м": 1000}

_TRIPLE = re.compile(
    rf"{_NUM}\s*[x×хX*]\s*{_NUM}\s*[x×хX*]\s*{_NUM}\s*{_UNIT}(?![а-яё])", re.IGNORECASE
)
_SINGLE = {
    FieldKey.WIDTH_MM: re.compile(rf"ширин\w*\s*[:\-–—]?\s*{_NUM}\s*{_UNIT}(?![а-яё])", re.I),
    FieldKey.HEIGHT_MM: re.compile(rf"высот\w*\s*[:\-–—]?\s*{_NUM}\s*{_UNIT}(?![а-яё])", re.I),
    FieldKey.DEPTH_MM: re.compile(rf"глубин\w*\s*[:\-–—]?\s*{_NUM}\s*{_UNIT}(?![а-яё])", re.I),
}

_WORD_NUMBERS = {
    "одна": 1, "одну": 1, "один": 1, "одно": 1,
    "две": 2, "два": 2, "двух": 2,
    "три": 3, "трёх": 3, "трех": 3,
    "четыре": 4, "четырёх": 4, "четырех": 4,
    "пять": 5, "шесть": 6, "семь": 7, "восемь": 8,
}  # fmt: skip
_COUNT = r"((?<!\d)\d{1,2}(?!\d)|" + "|".join(_WORD_NUMBERS) + r")"
_SHELVES = [
    re.compile(rf"{_COUNT}\s+пол(?:к[а-яё]*|ок)", re.I),
    re.compile(r"пол(?:ок|ки)\s*[:\-–—]\s*(\d{1,2})(?!\d)", re.I),
]
_DOORS = [
    re.compile(rf"{_COUNT}\s+двер[а-яё]*", re.I),
    re.compile(r"двер\w*\s*[:\-–—]\s*(\d{1,2})(?!\d)", re.I),
    re.compile(r"(одно|двух|трёх|трех|четырёх|четырех)створчат|(одно|двух|трёх|трех)дверн", re.I),
]
_PRODUCTS = [
    (re.compile(r"шкаф", re.I), "шкаф"),
    (re.compile(r"стеллаж", re.I), "стеллаж"),
    (re.compile(r"тумб", re.I), "тумба"),
]
_PHONE = re.compile(r"(?:\+7|(?<!\d)8)[\s\-(]*\d{3}[\s\-)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_NAME = re.compile(
    r"(?i:меня\s+зовут|зовут|с\s+уважением,?|это)\s+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)"
)


def to_mm(number: str, unit: str | None, *, hint_max: Decimal | None = None) -> int:
    """Перевести число с единицей в миллиметры.

    Единица указана — берём её. Баг BUG-03: раньше единица отбрасывалась, и «80 см»
    превращалось в 80 мм. Единица не указана — угадываем по величине: до 10 — метры,
    до 300 — сантиметры, иначе миллиметры. Догадку человек всё равно подтверждает.
    """
    value = Decimal(number.replace(",", "."))
    if unit:
        return int(value * _UNIT_MM[unit.lower()])
    probe = hint_max if hint_max is not None else value
    if probe <= 10:
        return int(value * 1000)
    if probe <= 300:
        return int(value * 10)
    return int(value)


def _count(token: str) -> int:
    token = token.lower()
    return int(token) if token.isdigit() else _WORD_NUMBERS[token]


class RuleBasedParser:
    """Правила и регулярные выражения. Работает без сети."""

    name = "rules"

    def parse(self, text: str) -> dict[FieldKey, ParsedField]:
        found: dict[FieldKey, ParsedField] = {}

        for pattern, product in _PRODUCTS:
            if m := pattern.search(text):
                found[FieldKey.PRODUCT_TYPE] = ParsedField(product, m.group(0))
                break

        if m := _TRIPLE.search(text):
            nums = [m.group(i) for i in (1, 2, 3)]
            hint = max(Decimal(n.replace(",", ".")) for n in nums)
            for key, num in zip(
                (FieldKey.WIDTH_MM, FieldKey.HEIGHT_MM, FieldKey.DEPTH_MM), nums, strict=True
            ):
                found[key] = ParsedField(str(to_mm(num, m.group(4), hint_max=hint)), m.group(0))
        for key, pattern in _SINGLE.items():
            if key in found:
                continue
            if m := pattern.search(text):
                found[key] = ParsedField(str(to_mm(m.group(1), m.group(2))), m.group(0))

        for pattern in _SHELVES:
            if m := pattern.search(text):
                token = next(g for g in m.groups() if g)
                found[FieldKey.SHELVES] = ParsedField(str(_count(token)), m.group(0))
                break
        for pattern in _DOORS:
            if m := pattern.search(text):
                token = next(g for g in m.groups() if g)
                found[FieldKey.DOORS] = ParsedField(str(_count(token)), m.group(0))
                break

        if m := _PHONE.search(text):
            digits = re.sub(r"\D", "", m.group(0))
            found[FieldKey.PHONE] = ParsedField("+7" + digits[-10:], m.group(0))
        if m := _EMAIL.search(text):
            found[FieldKey.EMAIL] = ParsedField(m.group(0).lower(), m.group(0))
        if m := _NAME.search(text):
            found[FieldKey.CLIENT_NAME] = ParsedField(m.group(1), m.group(0))
        return found


class LlmRequestParser:
    """Адаптер к языковой модели. Точка расширения, в демо не подключён.

    TODO: запрос к модели со строгой JSON-схемой ответа (те же FieldKey), таймаут,
    повтор, при любой ошибке — откат на RuleBasedParser. Адрес и ключ — только из
    переменных окружения LLM_API_URL / LLM_API_KEY.
    """

    name = "llm"

    def __init__(self, api_url: str, api_key: str, fallback: RequestParser) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._fallback = fallback

    def parse(self, text: str) -> dict[FieldKey, ParsedField]:
        # Без настроенного адреса работаем правилами: демо не зависит от сети.
        return self._fallback.parse(text)


def build_parser(kind: str, api_url: str = "", api_key: str = "") -> RequestParser:
    rules = RuleBasedParser()
    if kind == "llm":
        return LlmRequestParser(api_url, api_key, fallback=rules)
    return rules
