"""Заглушки внешних сервисов работают без сети (NFR-03, US-06)."""

from app.domain.design import CabinetParams, build_specification
from app.domain.estimate import build_estimate
from app.integrations.accounting import NoopAccountingExporter
from app.integrations.notifier import LogNotifier
from tests.unit.test_estimate import price_list


def test_us06_log_notifier_records_sent_estimate() -> None:
    notifier = LogNotifier()
    ref = notifier.send_estimate(7, "anna@example.com", 1_233_196)
    assert ref == "log-7"
    assert notifier.sent == [(7, "anna@example.com", 1_233_196)]


def test_accounting_exporter_stub_is_noop() -> None:
    spec = build_specification(CabinetParams(width_mm=800, height_mm=900, depth_mm=400))
    assert NoopAccountingExporter().export_estimate(1, build_estimate(spec, price_list())) == ""
