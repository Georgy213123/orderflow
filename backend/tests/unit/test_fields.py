"""US-02: подтверждение полей и их источник (FR-03, FR-04)."""

from app.domain.fields import (
    FieldKey,
    FieldSource,
    FieldState,
    apply_human_input,
    missing_for_parsed,
)

FROM_TEXT = FieldState("1200", FieldSource.TEXT, confirmed=False, fragment="1200х2100х600 мм")


def test_us02_confirming_keeps_text_source() -> None:
    confirmed = apply_human_input(FROM_TEXT, "1200")
    assert confirmed == FieldState("1200", FieldSource.TEXT, True, "1200х2100х600 мм")


def test_bug04_second_confirmation_keeps_source() -> None:
    """BUG-04: повторное подтверждение сбрасывало источник на «ввёл человек»."""
    once = apply_human_input(FROM_TEXT, "1200")
    twice = apply_human_input(once, " 1200 ")
    assert twice.source is FieldSource.TEXT
    assert twice.confirmed


def test_us02_editing_makes_source_human() -> None:
    edited = apply_human_input(FROM_TEXT, "1250")
    assert edited == FieldState("1250", FieldSource.HUMAN, True, None)


def test_new_field_from_human() -> None:
    assert apply_human_input(None, "Пётр").source is FieldSource.HUMAN


def test_unconfirmed_guess_blocks_parsed_status() -> None:
    fields = {k: FieldState("1", FieldSource.HUMAN, True) for k in FieldKey}
    assert missing_for_parsed(fields) == []
    fields[FieldKey.WIDTH_MM] = FROM_TEXT
    assert missing_for_parsed(fields) == ["Ширина, мм: найдено в тексте, но не подтверждено"]


def test_required_fields_reported() -> None:
    problems = missing_for_parsed({})
    assert "Телефон: не заполнено" in problems
    assert not any(p.startswith("Почта") for p in problems)  # почта необязательна
