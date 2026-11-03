"""Отправка сметы клиенту. В демо — заглушка: запись в журнал, без сети."""

import logging
from typing import Protocol

log = logging.getLogger("orderflow.notifier")


class ClientNotifier(Protocol):
    def send_estimate(self, request_id: int, contact: str, total_kop: int) -> str: ...


class LogNotifier:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str, int]] = []

    def send_estimate(self, request_id: int, contact: str, total_kop: int) -> str:
        self.sent.append((request_id, contact, total_kop))
        log.info("смета по заявке %s отправлена на %s", request_id, contact)
        return f"log-{request_id}"
