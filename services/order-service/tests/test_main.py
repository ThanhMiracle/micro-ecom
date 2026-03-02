import time
import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_create_order_empty_cart_400(client):
    r = client.post("/orders", json={"items": []})
    assert r.status_code == 400
    assert r.json()["detail"] == "Empty cart"


def test_create_order_invalid_qty_400(client):
    r = client.post("/orders", json={"items": [{"product_id": 1, "qty": 0}]})
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid qty"


def test_create_order_merges_items_and_calculates_total(client, app_and_db, monkeypatch):
    main, _, TestingSessionLocal = app_and_db

    async def fake_fetch(pid: int) -> float:
        return float(pid * 10)

    monkeypatch.setattr(main, "fetch_product_price", fake_fetch)

    payload = {
        "items": [
            {"product_id": 1, "qty": 2},
            {"product_id": 1, "qty": 3},  # merged => 5
            {"product_id": 2, "qty": 1},
        ]
    }

    r = client.post("/orders", json=payload)
    assert r.status_code == 200
    data = r.json()

    assert data["status"] == "CREATED"
    assert float(data["total"]) == 70.0  # 1*10*5 + 2*10*1

    items = sorted(data["items"], key=lambda x: x["product_id"])
    assert items == [
        {"product_id": 1, "qty": 5, "unit_price": 10.0},
        {"product_id": 2, "qty": 1, "unit_price": 20.0},
    ]

    from order_service.models import Order, OrderItem
    with TestingSessionLocal() as db:
        o = db.query(Order).first()
        assert o is not None
        assert float(o.total) == 70.0
        assert o.status == "CREATED"
        its = db.query(OrderItem).filter(OrderItem.order_id == o.id).all()
        assert len(its) == 2


def test_create_order_product_timeout_503(client, app_and_db, monkeypatch):
    main, _, _ = app_and_db

    async def fake_fetch(_pid: int) -> float:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(main, "fetch_product_price", fake_fetch)

    r = client.post("/orders", json={"items": [{"product_id": 1, "qty": 1}]})
    assert r.status_code == 503
    assert r.json()["detail"] == "Product service timeout"


def test_create_order_product_unavailable_bubbles_400(client, app_and_db, monkeypatch):
    main, _, _ = app_and_db

    async def fake_fetch(_pid: int) -> float:
        raise HTTPException(status_code=400, detail="Product 1 not available")

    monkeypatch.setattr(main, "fetch_product_price", fake_fetch)

    r = client.post("/orders", json={"items": [{"product_id": 1, "qty": 1}]})
    assert r.status_code == 400
    assert "not available" in r.json()["detail"]


def test_create_order_request_error_503(client, app_and_db, monkeypatch):
    main, _, _ = app_and_db

    async def fake_fetch(_pid: int) -> float:
        raise httpx.RequestError("conn error")

    monkeypatch.setattr(main, "fetch_product_price", fake_fetch)

    r = client.post("/orders", json={"items": [{"product_id": 1, "qty": 1}]})
    assert r.status_code == 503
    assert r.json()["detail"] == "Product service unavailable"


def test_create_order_db_failure_500(client, app_and_db, monkeypatch):
    main, _, TestingSessionLocal = app_and_db

    async def fake_fetch(_pid: int) -> float:
        return 10.0

    monkeypatch.setattr(main, "fetch_product_price", fake_fetch)

    real_begin = TestingSessionLocal.begin

    def boom_begin(self, *args, **kwargs):
        raise SQLAlchemyError("db boom")

    monkeypatch.setattr(TestingSessionLocal, "begin", boom_begin, raising=True)

    r = client.post("/orders", json={"items": [{"product_id": 1, "qty": 1}]})
    assert r.status_code == 500
    assert r.json()["detail"] == "Failed to create order"

    monkeypatch.setattr(TestingSessionLocal, "begin", real_begin, raising=True)


def test_get_order_owner_only(client, app_and_db):
    main, _, TestingSessionLocal = app_and_db
    from order_service.models import Order, OrderItem

    with TestingSessionLocal() as db:
        o = Order(user_id=1, user_email="u1@example.com", status="CREATED", total=10.0)
        db.add(o)
        db.flush()
        db.add(OrderItem(order_id=o.id, product_id=1, qty=1, unit_price=10.0))
        db.commit()
        db.refresh(o)
        oid = o.id

    r = client.get(f"/orders/{oid}")
    assert r.status_code == 200

    # different user => 404
    main.app.dependency_overrides[main.require_user] = lambda: {"sub": "2", "email": "u2@example.com"}
    r2 = client.get(f"/orders/{oid}")
    assert r2.status_code == 404


def test_pay_order_not_found_404(client):
    r = client.post("/orders/999/pay")
    assert r.status_code == 404


def test_pay_order_already_paid_idempotent(client, app_and_db):
    _, _, TestingSessionLocal = app_and_db
    from order_service.models import Order

    with TestingSessionLocal() as db:
        o = Order(user_id=1, user_email="u1@example.com", status="PAID", total=10.0)
        db.add(o)
        db.commit()
        db.refresh(o)
        oid = o.id

    r = client.post(f"/orders/{oid}/pay")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "status": "PAID"}


def test_pay_order_wrong_status_400(client, app_and_db):
    _, _, TestingSessionLocal = app_and_db
    from order_service.models import Order

    with TestingSessionLocal() as db:
        o = Order(user_id=1, user_email="u1@example.com", status="CANCELLED", total=10.0)
        db.add(o)
        db.commit()
        db.refresh(o)
        oid = o.id

    r = client.post(f"/orders/{oid}/pay")
    assert r.status_code == 400
    assert "Cannot pay" in r.json()["detail"]


def test_pay_order_success_publishes_when_rabbit_set(client, app_and_db, monkeypatch):
    main, _, TestingSessionLocal = app_and_db
    from order_service.models import Order

    monkeypatch.setattr(main, "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    published = {}

    def fake_publish(url, event_type, payload):
        published["url"] = url
        published["event_type"] = event_type
        published["payload"] = payload

    monkeypatch.setattr(main, "publish", fake_publish)

    with TestingSessionLocal() as db:
        o = Order(user_id=1, user_email="u1@example.com", status="CREATED", total=123.45)
        db.add(o)
        db.commit()
        db.refresh(o)
        oid = o.id

    r = client.post(f"/orders/{oid}/pay")
    assert r.status_code == 200
    assert r.json()["status"] == "PAID"

    assert published["event_type"] == "payment.succeeded"
    assert published["payload"]["email"] == "u1@example.com"
    assert published["payload"]["order_id"] == oid
    assert float(published["payload"]["total"]) == 123.45


def test_pay_order_success_no_publish_when_rabbit_empty(client, app_and_db, monkeypatch):
    main, _, TestingSessionLocal = app_and_db
    from order_service.models import Order

    monkeypatch.setattr(main, "RABBITMQ_URL", "")

    called = {"n": 0}

    def fake_publish(*args, **kwargs):
        called["n"] += 1

    monkeypatch.setattr(main, "publish", fake_publish)

    with TestingSessionLocal() as db:
        o = Order(user_id=1, user_email="u1@example.com", status="CREATED", total=10.0)
        db.add(o)
        db.commit()
        db.refresh(o)
        oid = o.id

    r = client.post(f"/orders/{oid}/pay")
    assert r.status_code == 200
    assert called["n"] == 0