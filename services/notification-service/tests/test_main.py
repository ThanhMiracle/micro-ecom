import types


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_handler_user_registered_sends_email(svc, monkeypatch, caplog):
    sent = {}

    def fake_send_email(to_email, subject, html_body):
        sent["to_email"] = to_email
        sent["subject"] = subject
        sent["html_body"] = html_body

    monkeypatch.setattr(svc, "send_email", fake_send_email)

    svc.handler(
        "user.registered",
        {"email": "a@example.com", "verify_url": "http://x/verify?token=123"},
    )

    assert sent["to_email"] == "a@example.com"
    assert "Verify your MicroShop account" in sent["subject"]
    assert "http://x/verify?token=123" in sent["html_body"]


def test_handler_payment_succeeded_sends_email(svc, monkeypatch):
    sent = {}

    def fake_send_email(to_email, subject, html_body):
        sent["to_email"] = to_email
        sent["subject"] = subject
        sent["html_body"] = html_body

    monkeypatch.setattr(svc, "send_email", fake_send_email)

    svc.handler(
        "payment.succeeded",
        {"email": "b@example.com", "order_id": 42, "total": 99.5},
    )

    assert sent["to_email"] == "b@example.com"
    assert "Payment confirmed" in sent["subject"]
    assert "#42" in sent["html_body"]
    assert "$99.5" in sent["html_body"]


def test_handler_unknown_event_no_email(svc, monkeypatch, caplog):
    called = {"n": 0}

    def fake_send_email(*args, **kwargs):
        called["n"] += 1

    monkeypatch.setattr(svc, "send_email", fake_send_email)

    with caplog.at_level("INFO"):
        svc.handler("something.else", {"x": 1})

    assert called["n"] == 0
    # log check (string may vary slightly)
    assert any("Ignoring event_type=something.else" in r.message for r in caplog.records)


def test_handler_missing_payload_fields_logged(svc, monkeypatch, caplog):
    def fake_send_email(*args, **kwargs):
        raise AssertionError("send_email should not be called when payload missing fields")

    monkeypatch.setattr(svc, "send_email", fake_send_email)

    with caplog.at_level("ERROR"):
        # missing verify_url
        svc.handler("user.registered", {"email": "a@example.com"})

    assert any("Missing required field" in r.message for r in caplog.records)


def test_handler_send_email_raises_is_caught(svc, monkeypatch, caplog):
    def fake_send_email(*args, **kwargs):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(svc, "send_email", fake_send_email)

    with caplog.at_level("ERROR"):
        svc.handler(
            "payment.succeeded",
            {"email": "b@example.com", "order_id": 1, "total": 10},
        )

    assert any("Handler failed" in r.message for r in caplog.records)


def test_startup_starts_consumer_thread_and_calls_consume(svc, monkeypatch):
    """
    We don't want real threads to run in unit tests, so we replace threading.Thread
    and verify it was configured and started, and that consume() is called.
    """
    consume_called = {}

    def fake_consume(rabbitmq_url, queue_name, bindings, handler):
        consume_called["rabbitmq_url"] = rabbitmq_url
        consume_called["queue_name"] = queue_name
        consume_called["bindings"] = bindings
        consume_called["handler"] = handler

    monkeypatch.setattr(svc, "consume", fake_consume)

    started = {"ok": False}

    class FakeThread:
        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            started["ok"] = True
            # run immediately (synchronously) so we can assert consume_called
            self.target()

    monkeypatch.setattr(svc.threading, "Thread", FakeThread)

    svc.startup()

    assert started["ok"] is True
    assert consume_called["rabbitmq_url"] == svc.RABBITMQ_URL
    assert consume_called["queue_name"] == "notification-service"
    assert consume_called["bindings"] == ["user.registered", "payment.succeeded"]
    assert consume_called["handler"] == svc.handler


def test_startup_consumer_crash_is_caught_and_logged(svc, monkeypatch, caplog):
    def boom_consume(*args, **kwargs):
        raise RuntimeError("rabbit down")

    monkeypatch.setattr(svc, "consume", boom_consume)

    class FakeThread:
        def __init__(self, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            # run immediately to capture log
            self.target()

    monkeypatch.setattr(svc.threading, "Thread", FakeThread)

    with caplog.at_level("ERROR"):
        svc.startup()

    assert any("RabbitMQ consumer crashed" in r.message for r in caplog.records)