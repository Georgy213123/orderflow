"""Отправка сметы клиенту. В демо — заглушка: запись в журнал, без сети."""

import logging
from typing import Protocol

log = logging.getLogger("orderflow.notifier")


class NotifierError(Exception):
    """Отправка не удалась: статус заявки не меняется, повтор разрешён."""


class ClientNotifier(Protocol):
    def send_estimate(
        self, request_id: int, contact: str, total_kop: int, idempotency_key: str
    ) -> str:
        """Повтор с тем же ключом не должен слать второе письмо."""
        ...


class LogNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str, int]] = []
        self._refs: dict[str, str] = {}

    def send_estimate(
        self, request_id: int, contact: str, total_kop: int, idempotency_key: str
    ) -> str:
        if idempotency_key in self._refs:
            return self._refs[idempotency_key]
        self.sent.append((request_id, contact, total_kop))
        log.info("смета по заявке %s отправлена на %s", request_id, contact)
        ref = f"log-{request_id}"
        self._refs[idempotency_key] = ref
        return ref
