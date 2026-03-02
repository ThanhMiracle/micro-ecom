import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError


# -----------------------
# httpx AsyncClient stub
# -----------------------
class _Resp:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json


class FakeAsyncClient:
    """
    Queue responses for get/post/patch calls.
    Also captures last request details.
    """
    def __init__(self, timeout=5.0, responses=None, raise_on=None):
        self.timeout = timeout
        self._responses = responses or {}
        self._raise_on = raise_on or set()
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def _maybe_raise(self, method):
        if method in self._raise_on:
            raise httpx.RequestError(f"{method} error", request=None)

    async def get(self, url, headers=None):
        self._maybe_raise("get")
        self.requests.append(("get", url, headers, None))
        return self._responses.get(("get", url), _Resp(200, {}))

    async def post(self, url, headers=None):
        self._maybe_raise("post")
        self.requests.append(("post", url, headers, None))
        return self._responses.get(("post", url), _Resp(200, {}))

    async def patch(self, url, json=None, headers=None):
        self._maybe_raise("patch")
        self.requests.append(("patch", url, headers, json))
        return self._responses.get(("patch", url), _Resp(200, {}))


# -----------------------
# Basic endpoints/helpers
# -----------------------
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_extract_token_priority(app_and_db):
    main, _, _ = app_and_db
    assert main.extract_token({"raw_token": "a", "token": "b", "access_token": "c"}) == "a"
    assert main.extract_token({"token": "b", "access_token": "c"}) == "b"
    assert main.extract_token({"access_token": "c"}) == "c"
    assert main.extract_token({}) == ""


@pytest.mark.anyio
async def test_fetch_order_success_sets_auth_header(app_and_db, monkeypatch):
    main, _, _ = app_and_db

    order_id = 10
    url = f"{main.ORDER_URL_INTERNAL}/orders/{order_id}"

    client = FakeAsyncClient(
        responses={
            ("get", url): _Resp(200, {"id": order_id, "status": "CREATED", "total": 12.5})
        }
    )

    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: client)

    data = await main.fetch_order(order_id, token="t123")
    assert data["id"] == order_id
    assert client.requests[0][0] == "get"
    assert client.requests[0][1] == url
    assert client.requests[0][2]["Authorization"] == "Bearer t123"


@pytest.mark.anyio
async def test_fetch_order_unauthorized_401(app_and_db, monkeypatch):
    main, _, _ = app_and_db
    order_id = 11
    url = f"{main.ORDER_URL_INTERNAL}/orders/{order_id}"

    client = FakeAsyncClient(responses={("get", url): _Resp(403, {})})
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: client)

    with pytest.raises(HTTPException) as e:
        await main.fetch_order(order_id, token="t")
    assert e.value.status_code == 401


@pytest.mark.anyio
async def test_fetch_order_not_found_400(app_and_db, monkeypatch):
    main, _, _ = app_and_db
    order_id = 12
    url = f"{main.ORDER_URL_INTERNAL}/orders/{order_id}"

    client = FakeAsyncClient(responses={("get", url): _Resp(404, {})})
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: client)

    with pytest.raises(HTTPException) as e:
        await main.fetch_order(order_id, token="")
    assert e.value.status_code == 400


@pytest.mark.anyio
async def test_fetch_order_request_error_503(app_and_db, monkeypatch):
    main, _, _ = app_and_db
    client = FakeAsyncClient(raise_on={"get"})
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: client)

    with pytest.raises(HTTPException) as e:
        await main.fetch_order(1, token="")
    assert e.value.status_code == 503


@pytest.mark.anyio
async def test_mark_order_paid_noop_when_path_empty(app_and_db, monkeypatch):
    main, _, _ = app_and_db
    monkeypatch.setattr(main, "ORDER_MARK_PAID_PATH", "")

    # should not call AsyncClient at all
    called = {"n": 0}
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: called.update(n=1))

    await main.mark_order_paid_if_supported(1, token="t")
    assert called["n"] == 0


@pytest.mark.anyio
async def test_mark_order_paid_posts_to_configured_path(app_and_db, monkeypatch):
    main, _, _ = app_and_db
    monkeypatch.setattr(main, "ORDER_MARK_PAID_PATH", "/orders/{order_id}/pay")

    order_id = 9
    url = f"{main.ORDER_URL_INTERNAL}/orders/{order_id}/pay"

    client = FakeAsyncClient(responses={("post", url): _Resp(200, {})})
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: client)

    await main.mark_order_paid_if_supported(order_id, token="t123")
    assert client.requests[0][0] == "post"
    assert client.requests[0][1] == url
    assert client.requests[0][2]["Authorization"] == "Bearer t123"


@pytest.mark.anyio
async def test_mark_order_paid_fallback_patch_on_404(app_and_db, monkeypatch):
    main, _, _ = app_and_db
    monkeypatch.setattr(main, "ORDER_MARK_PAID_PATH", "/orders/{order_id}/pay")

    order_id = 7
    post_url = f"{main.ORDER_URL_INTERNAL}/orders/{order_id}/pay"
    patch_url = f"{main.ORDER_URL_INTERNAL}/orders/{order_id}"

    client = FakeAsyncClient(
        responses={
            ("post", post_url): _Resp(404, {}),
            ("patch", patch_url): _Resp(200, {}),
        }
    )
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: client)

    await main.mark_order_paid_if_supported(order_id, token="t")

    methods = [m for (m, *_rest) in client.requests]
    assert methods == ["post", "patch"]


@pytest.mark.anyio
async def test_mark_order_paid_request_error_swallowed(app_and_db, monkeypatch):
    main, _, _ = app_and_db
    monkeypatch.setattr(main, "ORDER_MARK_PAID_PATH", "/orders/{order_id}/pay")

    client = FakeAsyncClient(raise_on={"post"})
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda timeout=5.0: client)

    # should not raise
    await main.mark_order_paid_if_supported(1, token="t")


# -----------------------
# API: POST /payments/{order_id}
# -----------------------
def _seed_payment(db, Payment, order_id, user_id, amount, status):
    p = Payment(order_id=order_id, user_id=user_id, amount=amount, status=status)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_pay_idempotent_success_returns_existing(client, app_and_db):
    main, _, TestingSessionLocal = app_and_db
    from payment_service.models import Payment

    with TestingSessionLocal() as db:
        p = _seed_payment(db, Payment, order_id=100, user_id=1, amount=10.0, status="SUCCESS")

    r = client.post("/payments/100", json={"shipping_address": "A", "phone_number": "1"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["payment_id"] == p.id


def test_pay_existing_non_success_400(client, app_and_db):
    main, _, TestingSessionLocal = app_and_db
    from payment_service.models import Payment

    with TestingSessionLocal() as db:
        _seed_payment(db, Payment, order_id=101, user_id=1, amount=10.0, status="FAILED")

    r = client.post("/payments/101", json={"shipping_address": "A", "phone_number": "1"})
    assert r.status_code == 400
    assert "Payment already attempted" in r.json()["detail"]


def test_pay_order_not_created_400(client, app_and_db, monkeypatch):
    main, _, _ = app_and_db

    async def fake_fetch(order_id, token):
        return {"id": order_id, "status": "PAID", "total": 10.0}

    monkeypatch.setattr(main, "fetch_order", fake_fetch)

    r = client.post("/payments/200", json={"shipping_address": "A", "phone_number": "1"})
    assert r.status_code == 400
    assert "Cannot pay order in status" in r.json()["detail"]


def test_pay_db_failure_500(client, app_and_db, monkeypatch):
    main, _, TestingSessionLocal = app_and_db

    async def fake_fetch(order_id, token):
        return {"id": order_id, "status": "CREATED", "total": 10.0}

    monkeypatch.setattr(main, "fetch_order", fake_fetch)

    # Force commit to raise
    def boom_commit(self):
        raise SQLAlchemyError("db boom")

    monkeypatch.setattr(TestingSessionLocal, "commit", boom_commit, raising=True)

    r = client.post("/payments/201", json={"shipping_address": "A", "phone_number": "1"})
    assert r.status_code == 500
    assert "Failed to create payment" in r.json()["detail"]


def test_pay_success_publishes_and_marks_paid_best_effort(client, app_and_db, monkeypatch):
    main, _, TestingSessionLocal = app_and_db
    from payment_service.models import Payment

    async def fake_fetch(order_id, token):
        return {"id": order_id, "status": "CREATED", "total": 99.9}

    monkeypatch.setattr(main, "fetch_order", fake_fetch)

    marked = {"n": 0}

    async def fake_mark(order_id, token):
        marked["n"] += 1

    monkeypatch.setattr(main, "mark_order_paid_if_supported", fake_mark)

    monkeypatch.setattr(main, "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    published = {}

    def fake_publish(url, event_type, payload):
        published["url"] = url
        published["event_type"] = event_type
        published["payload"] = payload

    monkeypatch.setattr(main, "publish", fake_publish)

    r = client.post("/payments/300", json={"shipping_address": "addr", "phone_number": "099"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert isinstance(body["payment_id"], int)

    # verify payment exists
    with TestingSessionLocal() as db:
        p = db.query(Payment).filter(Payment.id == body["payment_id"]).first()
        assert p is not None
        assert p.order_id == 300
        assert p.user_id == 1
        assert float(p.amount) == 99.9
        assert p.status == "SUCCESS"

    assert published["event_type"] == "payment.succeeded"
    assert published["payload"]["order_id"] == 300
    assert published["payload"]["user_id"] == 1
    assert float(published["payload"]["amount"]) == 99.9
    assert published["payload"]["shipping_address"] == "addr"
    assert published["payload"]["phone_number"] == "099"

    assert marked["n"] == 1


def test_pay_success_no_publish_when_rabbit_empty(client, app_and_db, monkeypatch):
    main, _, _ = app_and_db

    async def fake_fetch(order_id, token):
        return {"id": order_id, "status": "CREATED", "total": 10.0}

    monkeypatch.setattr(main, "fetch_order", fake_fetch)
    monkeypatch.setattr(main, "RABBITMQ_URL", "")

    called = {"n": 0}

    def fake_publish(*args, **kwargs):
        called["n"] += 1

    monkeypatch.setattr(main, "publish", fake_publish)

    async def fake_mark(*args, **kwargs):
        return None

    monkeypatch.setattr(main, "mark_order_paid_if_supported", fake_mark)

    r = client.post("/payments/301", json={"shipping_address": "a", "phone_number": "b"})
    assert r.status_code == 200
    assert called["n"] == 0


# -----------------------
# API: GET /payments/{id} + list
# -----------------------
def test_get_payment_owner_only(client, app_and_db):
    main, _, TestingSessionLocal = app_and_db
    from payment_service.models import Payment

    with TestingSessionLocal() as db:
        p = Payment(order_id=1, user_id=1, amount=10.0, status="SUCCESS")
        db.add(p)
        db.commit()
        db.refresh(p)
        pid = p.id

    r = client.get(f"/payments/{pid}")
    assert r.status_code == 200
    assert r.json()["id"] == pid

    # different user => 404
    main.app.dependency_overrides[main.require_user] = lambda: {"sub": "2"}
    r2 = client.get(f"/payments/{pid}")
    assert r2.status_code == 404


def test_get_payment_not_found_404(client):
    r = client.get("/payments/99999")
    assert r.status_code == 404


def test_list_payments_returns_only_my_payments_sorted_desc(client, app_and_db):
    main, _, TestingSessionLocal = app_and_db
    from payment_service.models import Payment

    with TestingSessionLocal() as db:
        db.add(Payment(order_id=1, user_id=1, amount=10.0, status="SUCCESS"))
        db.add(Payment(order_id=2, user_id=1, amount=20.0, status="SUCCESS"))
        db.add(Payment(order_id=3, user_id=2, amount=30.0, status="SUCCESS"))  # other user
        db.commit()

    r = client.get("/payments")
    assert r.status_code == 200
    data = r.json()
    assert all(p["user_id"] == 1 for p in data)
    ids = [p["id"] for p in data]
    assert ids == sorted(ids, reverse=True)