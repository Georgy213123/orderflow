"""Обмен с учётной системой — точка расширения, в демо не входит.

Интерфейс зафиксирован, чтобы смета и спецификация уже сейчас отдавались в виде,
пригодном для выгрузки. Реальный адаптер — отдельная задача (см. 07-releases.md).
"""

from typing import Protocol

from app.domain.estimate import Estimate


class AccountingExporter(Protocol):
    def export_estimate(self, request_id: int, estimate: Estimate) -> str: ...


class NoopAccountingExporter:
    """Ничего не выгружает, возвращает пустую ссылку. Работает без сети и ключей."""

    def export_estimate(self, request_id: int, estimate: Estimate) -> str:
        return ""
