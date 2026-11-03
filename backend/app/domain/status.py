"""Статусы заявки и допустимые переходы. Переход проверяет сервер, клиент только просит."""

from enum import StrEnum


class RequestStatus(StrEnum):
    NEW = "new"
    PARSED = "parsed"
    DESIGNED = "designed"
    ESTIMATED = "estimated"
    SENT = "sent"


STATUS_LABELS: dict[RequestStatus, str] = {
    RequestStatus.NEW: "новая",
    RequestStatus.PARSED: "разобрана",
    RequestStatus.DESIGNED: "конструкция готова",
    RequestStatus.ESTIMATED: "смета готова",
    RequestStatus.SENT: "отправлена клиенту",
}

# Откат назад разрешён только туда, где правка имеет смысл: изменили конструкцию —
# смета устарела и пересчитывается.
ALLOWED: dict[RequestStatus, frozenset[RequestStatus]] = {
    RequestStatus.NEW: frozenset({RequestStatus.PARSED}),
    RequestStatus.PARSED: frozenset({RequestStatus.DESIGNED}),
    RequestStatus.DESIGNED: frozenset({RequestStatus.DESIGNED, RequestStatus.ESTIMATED}),
    RequestStatus.ESTIMATED: frozenset(
        {RequestStatus.DESIGNED, RequestStatus.ESTIMATED, RequestStatus.SENT}
    ),
    RequestStatus.SENT: frozenset(),
}


class TransitionError(Exception):
    def __init__(self, current: RequestStatus, target: RequestStatus, reason: str = "") -> None:
        self.current = current
        self.target = target
        self.reason = reason or (
            f"переход «{STATUS_LABELS[current]}» → «{STATUS_LABELS[target]}» не разрешён"
        )
        super().__init__(self.reason)


def check_transition(current: RequestStatus, target: RequestStatus) -> None:
    if target not in ALLOWED[current]:
        raise TransitionError(current, target)
