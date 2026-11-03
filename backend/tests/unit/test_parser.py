"""US-01: разбор свободного текста заявки (FR-02)."""

import pytest

from app.domain.fields import FieldKey
from app.domain.parser import LlmRequestParser, RuleBasedParser, build_parser, to_mm

SAMPLE = (
    "Здравствуйте! Нужен шкаф в прихожую 1200х2100х600 мм, 4 полки, две двери. "
    "Меня зовут Анна Смирнова, телефон +7 (900) 123-45-67, почта anna@example.com"
)


def values(text: str) -> dict[FieldKey, str]:
    return {k: v.value for k, v in RuleBasedParser().parse(text).items()}


def test_us01_sample_request_is_fully_parsed() -> None:
    assert values(SAMPLE) == {
        FieldKey.PRODUCT_TYPE: "шкаф",
        FieldKey.WIDTH_MM: "1200",
        FieldKey.HEIGHT_MM: "2100",
        FieldKey.DEPTH_MM: "600",
        FieldKey.SHELVES: "4",
        FieldKey.DOORS: "2",
        FieldKey.CLIENT_NAME: "Анна Смирнова",
        FieldKey.PHONE: "+79001234567",
        FieldKey.EMAIL: "anna@example.com",
    }


def test_fragment_points_to_source_text() -> None:
    parsed = RuleBasedParser().parse(SAMPLE)
    assert parsed[FieldKey.WIDTH_MM].fragment == "1200х2100х600 мм"
    assert parsed[FieldKey.PHONE].fragment in SAMPLE


@pytest.mark.parametrize(
    ("text", "width"),
    [
        ("ширина 80 см", "800"),
        ("ширина 800 мм", "800"),
        ("ширина: 0,8 м", "800"),
        ("ширина 80см", "800"),
    ],
)
def test_bug03_units_are_respected(text: str, width: str) -> None:
    """BUG-03: «80 см» превращалось в 80 мм, единица отбрасывалась."""
    assert values(f"шкаф, {text}")[FieldKey.WIDTH_MM] == width


def test_triple_without_unit_guesses_by_magnitude() -> None:
    assert values("шкаф 120x210x60")[FieldKey.WIDTH_MM] == "1200"
    assert values("шкаф 1200x2100x600")[FieldKey.DEPTH_MM] == "600"
    assert values("шкаф 1,2x2,1x0,6 м")[FieldKey.HEIGHT_MM] == "2100"


def test_to_mm_does_not_mix_units() -> None:
    assert to_mm("80", "см") == 800
    assert to_mm("800", "мм") == 800
    assert to_mm("2", "м") == 2000


def test_separate_dimensions_and_words() -> None:
    v = values("Стеллаж высота 2 м, глубина 35 см, ширина 900 мм, три полки. 8 900 000 11 22")
    assert v[FieldKey.PRODUCT_TYPE] == "стеллаж"
    assert (v[FieldKey.WIDTH_MM], v[FieldKey.HEIGHT_MM], v[FieldKey.DEPTH_MM]) == (
        "900",
        "2000",
        "350",
    )
    assert v[FieldKey.SHELVES] == "3"
    assert v[FieldKey.PHONE] == "+79000001122"


def test_nothing_found_in_unrelated_text() -> None:
    assert values("Добрый день, перезвоните, пожалуйста") == {}


def test_llm_parser_without_config_falls_back_to_rules() -> None:
    parser = build_parser("llm")
    assert isinstance(parser, LlmRequestParser)
    assert {k: v.value for k, v in parser.parse(SAMPLE).items()} == values(SAMPLE)


def test_fragment_keeps_whole_word() -> None:
    parsed = RuleBasedParser().parse(SAMPLE)
    assert parsed[FieldKey.SHELVES].fragment == "4 полки"
    assert parsed[FieldKey.DOORS].fragment == "две двери"
