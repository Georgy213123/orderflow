"""Сквозной сценарий через API и реальную БД: US-01…US-05."""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

SAMPLE = (
    "Здравствуйте! Нужен шкаф в прихожую 1200х2100х600 мм, 4 полки, две двери. "
    "Меня зовут Анна Смирнова, телефон +7 (900) 123-45-67, почта anna@example.com"
)
WARDROBE = {"width_mm": 1200, "height_mm": 2100, "depth_mm": 600, "shelves": 4, "doors": 2}


def create(client: TestClient, text_: str = SAMPLE, **fields: str) -> dict[str, Any]:
    r = client.post("/api/requests", json={"raw_text": text_, "fields": fields})
    assert r.status_code == 201, r.text
    body: dict[str, Any] = r.json()
    return body


def confirm_all(client: TestClient, req: dict[str, Any]) -> dict[str, Any]:
    body = req
    for f in req["fields"]:
        r = client.put(f"/api/requests/{req['id']}/fields/{f['key']}", json={"value": f["value"]})
        assert r.status_code == 200, r.text
        body = r.json()
    return body


def to_parsed(client: TestClient, req_id: int) -> dict[str, Any]:
    r = client.post(f"/api/requests/{req_id}/transition", json={"to": "parsed"})
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


def test_us01_text_is_parsed_into_unconfirmed_fields(client: TestClient) -> None:
    req = create(client)
    assert req["status"] == "new"
    assert req["parser"] == "rules"
    by_key = {f["key"]: f for f in req["fields"]}
    assert by_key["width_mm"]["value"] == "1200"
    assert all(f["source"] == "text" and not f["confirmed"] for f in req["fields"])
    assert len(req["missing"]) == 9


def test_us01_manual_fields_are_human_and_confirmed(client: TestClient) -> None:
    req = create(client, "шкаф 1200х2100х600", phone="+79990000000", client_name="Пётр")
    by_key = {f["key"]: f for f in req["fields"]}
    assert by_key["phone"]["source"] == "human"
    assert by_key["phone"]["confirmed"]
    assert by_key["width_mm"]["source"] == "text"


def test_us02_parsed_status_requires_confirmation(client: TestClient) -> None:
    req = create(client)
    r = client.post(f"/api/requests/{req['id']}/transition", json={"to": "parsed"})
    assert r.status_code == 409
    assert "Ширина, мм: найдено в тексте, но не подтверждено" in r.json()["problems"]


def test_us02_confirm_twice_and_edit(client: TestClient) -> None:
    req = create(client)
    url = f"/api/requests/{req['id']}/fields/width_mm"
    for _ in range(2):  # BUG-04: повторное подтверждение
        body = client.put(url, json={"value": "1200"}).json()
    width = next(f for f in body["fields"] if f["key"] == "width_mm")
    assert (width["source"], width["confirmed"]) == ("text", True)

    body = client.put(url, json={"value": "1250"}).json()
    width = next(f for f in body["fields"] if f["key"] == "width_mm")
    assert (width["value"], width["source"], width["fragment"]) == ("1250", "human", None)

    bad = client.put(url, json={"value": "сто"})
    assert bad.status_code == 422


def test_us03_us04_us05_full_flow(client: TestClient, engine: Engine) -> None:
    req = confirm_all(client, create(client))
    assert req["missing"] == []
    assert to_parsed(client, req["id"])["status"] == "parsed"

    r = client.put(f"/api/requests/{req['id']}/design", json=WARDROBE)
    assert r.status_code == 200, r.text
    design = r.json()
    assert design["inner_width_mm"] == 1168
    shelf = next(p for p in design["parts"] if p["code"] == "shelf")
    assert (shelf["length_mm"], shelf["qty"]) == (1166, 4)
    assert client.get(f"/api/requests/{req['id']}").json()["status"] == "designed"

    r = client.post(f"/api/requests/{req['id']}/estimate")
    assert r.status_code == 200, r.text
    est = r.json()
    assert est["total_kop"] == 1_233_196
    assert est["total_formatted"] == "12 331,96"
    assert est["complete"] is True
    board = next(ln for ln in est["lines"] if ln["material_code"] == "LDSP16-WHITE")
    assert board["quantity"] == "10.49"  # Decimal в JSON — строкой, без float
    assert client.get(f"/api/requests/{req['id']}/estimate").json()["total_kop"] == 1_233_196

    r = client.post(f"/api/requests/{req['id']}/transition", json={"to": "sent"})
    assert r.status_code == 200
    final = r.json()
    assert final["status"] == "sent"
    assert [h["to_status"] for h in final["history"]] == ["parsed", "designed", "estimated", "sent"]

    with engine.connect() as conn:
        stored = conn.execute(text("select total_kop from estimates")).scalar_one()
    assert stored == 1_233_196


def test_us05_server_rejects_skipping(client: TestClient) -> None:
    req = create(client)
    r = client.post(f"/api/requests/{req['id']}/transition", json={"to": "sent"})
    assert r.status_code == 409
    r = client.post(f"/api/requests/{req['id']}/transition", json={"to": "estimated"})
    assert r.status_code == 409
    r = client.put(f"/api/requests/{req['id']}/design", json=WARDROBE)
    assert r.status_code == 409
    r = client.post(f"/api/requests/{req['id']}/estimate")
    assert r.status_code == 409


def test_us03_invalid_design_returns_problems(client: TestClient) -> None:
    req = confirm_all(client, create(client))
    to_parsed(client, req["id"])
    r = client.put(
        f"/api/requests/{req['id']}/design", json={**WARDROBE, "width_mm": 800, "doors": 4}
    )
    assert r.status_code == 422
    assert r.json()["problems"] == [
        "ширина двери 196 мм вне пределов 250–700: измените число дверей"
    ]

    r = client.put(f"/api/requests/{req['id']}/design", json={**WARDROBE, "thickness_mm": 18})
    assert r.status_code == 422
    assert "толщиной 16 мм" in r.json()["problems"][0]


def test_us04_incomplete_estimate_cannot_be_sent(client: TestClient) -> None:
    req = confirm_all(client, create(client))
    to_parsed(client, req["id"])
    client.put(
        f"/api/requests/{req['id']}/design", json={**WARDROBE, "handle_code": "HW-HANDLE-BLACK"}
    )
    est = client.post(f"/api/requests/{req['id']}/estimate").json()
    assert est["complete"] is False
    assert est["warnings"][0].startswith("итог неполный")
    r = client.post(f"/api/requests/{req['id']}/transition", json={"to": "sent"})
    assert r.status_code == 409


def test_redesign_drops_estimate(client: TestClient) -> None:
    req = confirm_all(client, create(client))
    to_parsed(client, req["id"])
    client.put(f"/api/requests/{req['id']}/design", json=WARDROBE)
    client.post(f"/api/requests/{req['id']}/estimate")
    r = client.put(f"/api/requests/{req['id']}/design", json={**WARDROBE, "shelves": 3})
    assert r.status_code == 200
    assert client.get(f"/api/requests/{req['id']}").json()["status"] == "designed"
    assert client.get(f"/api/requests/{req['id']}/estimate").status_code == 404


def test_list_materials_and_requests(client: TestClient) -> None:
    create(client)
    materials = client.get("/api/materials").json()
    assert {m["code"] for m in materials} >= {"LDSP16-WHITE", "HW-HANDLE-BLACK"}
    listed = client.get("/api/requests").json()
    assert listed[0]["client_name"] == "Анна Смирнова"
    assert listed[0]["status_label"] == "новая"
    assert client.get("/api/requests/999").status_code == 404
    assert client.get("/api/health").json() == {"status": "ok", "parser": "rules"}
