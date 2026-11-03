"""US-05: статусы заявки (FR-12)."""

import itertools

import pytest

from app.domain.status import RequestStatus as S
from app.domain.status import TransitionError, check_transition

HAPPY_PATH = [S.NEW, S.PARSED, S.DESIGNED, S.ESTIMATED, S.SENT]


def test_happy_path_is_allowed() -> None:
    for a, b in itertools.pairwise(HAPPY_PATH):
        check_transition(a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [(S.NEW, S.ESTIMATED), (S.NEW, S.SENT), (S.PARSED, S.SENT), (S.SENT, S.DESIGNED)],
)
def test_us05_skipping_steps_is_rejected(a: S, b: S) -> None:
    with pytest.raises(TransitionError, match="не разрешён"):
        check_transition(a, b)


def test_redesign_after_estimate_goes_back() -> None:
    check_transition(S.ESTIMATED, S.DESIGNED)
