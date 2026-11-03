"""Находки ревью Codex на реальном PostgreSQL: R-03, R-05, R-06, R-08, R-10."""

import threading
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app import services
from app.domain import estimate as estimate_mod
from app.domain.status import RequestStatus
from app.integrations.notifier import LogNotifier
from app.schemas import DesignParamsIn
from tests.integration.test_flow import WARDROBE, confirm_all, create, to_parsed

THREE_SHELVES_TOTAL_KOP = 1_165_888


def designed_request(client: TestClient) -> int:
    req = confirm_all(client, create(client))
    to_parsed(client, req["id"])
    assert client.put(f"/api/requests/{req['id']}/design", json=WARDROBE).status_code == 200
    return int(req["id"])


def estimated_request(client: TestClient) -> int:
    req_id = designed_request(client)
    assert client.post(f"/api/requests/{req_id}/estimate").status_code == 200
    return req_id


def run(fn: Any) -> threading.Thread:
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    return t


def test_r03_estimate_is_not_built_from_replaced_design(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Расчёт прочитал конструкцию, в это время её заменили: смета не должна остаться
    от старой конструкции."""
    req_id = designed_request(client)
    entered, release = threading.Event(), threading.Event()
    original = estimate_mod.build_estimate

    def slow_build(*args: Any, **kwargs: Any) -> Any:
        entered.set()
        release.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(services, "build_estimate", slow_build)
    errors: list[BaseException] = []

    def calc() -> None:
        with session_factory() as s:
            try:
                services.calculate_estimate(s, req_id)
            except BaseException as e:
                errors.append(e)

    def redesign() -> None:
        with session_factory() as s:
            services.save_design(s, req_id, DesignParamsIn(**{**WARDROBE, "shelves": 3}))

    t1 = run(calc)
    assert entered.wait(5)
    t2 = run(redesign)
    t2.join(0.5)  # с блокировкой ждёт расчёт, без неё — успевает заменить конструкцию
    release.set()
    t1.join(5)
    t2.join(5)
    assert not errors

    est = client.get(f"/api/requests/{req_id}/estimate")
    shelves = next(
        p
        for p in client.get(f"/api/requests/{req_id}/design").json()["parts"]
        if p["code"] == "shelf"
    )
    assert shelves["qty"] == 3
    if est.status_code == 200:
        assert est.json()["total_kop"] == THREE_SHELVES_TOTAL_KOP
    else:
        assert client.get(f"/api/requests/{req_id}").json()["status"] == "designed"


class BlockingNotifier(LogNotifier):
    def __init__(self) -> None:
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()

    def send_estimate(self, request_id: int, contact: str, total_kop: int) -> str:
        if not self.sent:
            self.entered.set()
            self.release.wait(5)
        return super().send_estimate(request_id, contact, total_kop)


def test_r05_concurrent_send_notifies_once(
    client: TestClient, session_factory: sessionmaker[Session], engine: Engine
) -> None:
    req_id = estimated_request(client)
    notifier = BlockingNotifier()
    results: list[str] = []

    def send() -> None:
        with session_factory() as s:
            try:
                services.transition(s, notifier, req_id, RequestStatus.SENT)
                results.append("ok")
            except services.DomainError as e:
                results.append(str(e.status_code))

    t1 = run(send)
    notifier.entered.wait(2)
    t2 = run(send)
    t2.join(1)
    notifier.release.set()
    t1.join(5)
    t2.join(5)

    assert sorted(results) == ["409", "ok"]
    assert len(notifier.sent) == 1
    with engine.connect() as conn:
        n = conn.execute(
            text("select count(*) from status_changes where to_status = 'sent'")
        ).scalar_one()
    assert n == 1


def test_r06_too_long_value_from_text_is_dropped_not_500(client: TestClient) -> None:
    email = "a" * 260 + "@example.com"
    req = create(client, f"шкаф 1200х2100х600, почта {email}")
    assert "email" not in {f["key"] for f in req["fields"]}
    assert client.post("/api/requests", json={"fields": {"phone": "1" * 256}}).status_code == 422


def test_r08_optional_field_can_be_cleared(client: TestClient) -> None:
    req = create(client)
    r = client.put(f"/api/requests/{req['id']}/fields/email", json={"value": ""})
    assert r.status_code == 200
    assert "email" not in {f["key"] for f in r.json()["fields"]}


def test_r10_send_actually_notifies_client(client: TestClient) -> None:
    req_id = estimated_request(client)
    notifier = client.app.state.notifier  # type: ignore[attr-defined]
    r = client.post(f"/api/requests/{req_id}/transition", json={"to": "sent"})
    assert r.status_code == 200
    assert notifier.sent == [(req_id, "anna@example.com", 1_233_196)]
