import time
import pytest
from jose import jwt
from fastapi import HTTPException


def _create_user(db, User, email, pw_hash, is_admin=False, is_verified=False):
    user = User(
        email=email,
        password_hash=pw_hash,
        is_admin=is_admin,
        is_verified=is_verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_hash_and_verify_password(app_and_db):
    main, _, _ = app_and_db

    pw = "P@ssw0rd!"
    h = main.hash_password(pw)
    assert isinstance(h, str)
    assert h != pw
    assert main.verify_password(pw, h) is True
    assert main.verify_password("wrong", h) is False


def test_password_required(app_and_db):
    main, _, _ = app_and_db
    with pytest.raises(HTTPException) as e:
        main.hash_password("")
    assert e.value.status_code == 400
    assert "Password is required" in e.value.detail


def test_password_too_long(app_and_db, monkeypatch):
    main, _, _ = app_and_db
    # create a string bigger than MAX_PASSWORD_BYTES when utf-8 encoded
    huge = "a" * (main.MAX_PASSWORD_BYTES + 1)
    with pytest.raises(HTTPException) as e:
        main.hash_password(huge)
    assert e.value.status_code == 400
    assert "Password too long" in e.value.detail


def test_register_success_no_rabbitmq(client, app_and_db, monkeypatch):
    main, _, TestingSessionLocal = app_and_db

    # stub token maker
    monkeypatch.setattr(main, "make_verify_token", lambda uid, email: "tok123")

    # stub publish (should NOT be called because RABBITMQ_URL empty)
    called = {"n": 0}

    def fake_publish(*args, **kwargs):
        called["n"] += 1

    monkeypatch.setattr(main, "publish", fake_publish)

    r = client.post("/auth/register", json={"email": "a@example.com", "password": "pw"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True

    # confirm user created
    from auth_service.models import User

    with TestingSessionLocal() as db:
        u = db.query(User).filter(User.email == "a@example.com").first()
        assert u is not None
        assert u.is_verified is False

    assert called["n"] == 0


def test_register_success_with_rabbitmq_publishes(client, app_and_db, monkeypatch):
    main, _, _ = app_and_db

    # Force rabbit enabled
    monkeypatch.setattr(main, "RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    monkeypatch.setattr(main, "make_verify_token", lambda uid, email: "tok456")

    published = {}

    def fake_publish(url, routing_key, payload):
        published["url"] = url
        published["routing_key"] = routing_key
        published["payload"] = payload

    monkeypatch.setattr(main, "publish", fake_publish)

    r = client.post("/auth/register", json={"email": "b@example.com", "password": "pw"})
    assert r.status_code == 200

    assert published["routing_key"] == "user.registered"
    assert published["payload"]["email"] == "b@example.com"
    assert "verify?token=tok456" in published["payload"]["verify_url"]


def test_register_duplicate_email_409(client, app_and_db, monkeypatch):
    main, _, TestingSessionLocal = app_and_db
    from auth_service.models import User

    with TestingSessionLocal() as db:
        u = User(
            email="dup@example.com",
            password_hash=main.hash_password("pw"),
            is_admin=False,
            is_verified=False,
        )
        db.add(u)
        db.commit()

    r = client.post("/auth/register", json={"email": "dup@example.com", "password": "pw"})
    assert r.status_code == 409
    assert r.json()["detail"] == "Email already registered"


def test_verify_get_missing_user_404(client, app_and_db, monkeypatch):
    main, _, _ = app_and_db

    monkeypatch.setattr(main, "decode_verify_token", lambda token: {"sub": "999", "email": "x@example.com"})

    r = client.get("/auth/verify", params={"token": "any"})
    assert r.status_code == 404
    assert r.json()["detail"] == "User not found"


def test_verify_get_invalid_token_400(client, app_and_db, monkeypatch):
    main, _, _ = app_and_db

    def boom(_):
        raise Exception("bad token")

    monkeypatch.setattr(main, "decode_verify_token", boom)

    r = client.get("/auth/verify", params={"token": "bad"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid or expired token"


def test_verify_post_missing_token_400(client):
    r = client.post("/auth/verify", json={})
    assert r.status_code == 400
    assert r.json()["detail"] == "Missing token"


def test_verify_success_sets_verified(client, app_and_db, monkeypatch):
    main, _, TestingSessionLocal = app_and_db
    from auth_service.models import User

    with TestingSessionLocal() as db:
        u = User(
            email="v@example.com",
            password_hash=main.hash_password("pw"),
            is_admin=False,
            is_verified=False,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        uid = u.id

    monkeypatch.setattr(main, "decode_verify_token", lambda token: {"sub": str(uid), "email": "v@example.com"})

    r = client.get("/auth/verify", params={"token": "good"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    with TestingSessionLocal() as db:
        u2 = db.query(User).filter(User.id == uid).first()
        assert u2.is_verified is True


def test_login_invalid_email_401(client):
    r = client.post("/auth/login", json={"email": "nope@example.com", "password": "pw"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials"


def test_login_wrong_password_401(client, app_and_db):
    main, _, TestingSessionLocal = app_and_db
    from auth_service.models import User

    with TestingSessionLocal() as db:
        _create_user(
            db,
            User,
            email="lpw@example.com",
            pw_hash=main.hash_password("right"),
            is_admin=False,
            is_verified=True,
        )

    r = client.post("/auth/login", json={"email": "lpw@example.com", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials"


def test_login_not_verified_403(client, app_and_db):
    main, _, TestingSessionLocal = app_and_db
    from auth_service.models import User

    with TestingSessionLocal() as db:
        _create_user(
            db,
            User,
            email="nv@example.com",
            pw_hash=main.hash_password("pw"),
            is_admin=False,
            is_verified=False,
        )

    r = client.post("/auth/login", json={"email": "nv@example.com", "password": "pw"})
    assert r.status_code == 403
    assert r.json()["detail"] == "Email not verified"


def test_login_success_returns_jwt_with_claims(client, app_and_db, jwt_secret):
    main, _, TestingSessionLocal = app_and_db
    from auth_service.models import User

    with TestingSessionLocal() as db:
        u = _create_user(
            db,
            User,
            email="ok@example.com",
            pw_hash=main.hash_password("pw"),
            is_admin=True,
            is_verified=True,
        )

    r = client.post("/auth/login", json={"email": "ok@example.com", "password": "pw"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert isinstance(token, str) and len(token) > 10

    decoded = jwt.decode(token, jwt_secret, algorithms=[main.ALGO])
    assert decoded["sub"] == str(u.id)
    assert decoded["email"] == "ok@example.com"
    assert decoded["is_admin"] is True
    assert decoded["typ"] == "access"
    assert decoded["exp"] > int(time.time())


def test_me_success(client, app_and_db):
    main, _, TestingSessionLocal = app_and_db
    from auth_service.models import User

    with TestingSessionLocal() as db:
        u = _create_user(
            db,
            User,
            email="me@example.com",
            pw_hash=main.hash_password("pw"),
            is_admin=False,
            is_verified=True,
        )

    # Override require_user dependency to “authenticate”
    main.app.dependency_overrides[main.require_user] = lambda: {"sub": str(u.id)}

    r = client.get("/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == u.id
    assert body["email"] == "me@example.com"
    assert body["is_admin"] is False
    assert body["is_verified"] is True


def test_me_user_not_found_404(client, app_and_db):
    main, _, _ = app_and_db

    main.app.dependency_overrides[main.require_user] = lambda: {"sub": "999999"}

    r = client.get("/auth/me")
    assert r.status_code == 404
    assert r.json()["detail"] == "User not found"


def test_seed_admin_creates_admin_user(app_and_db, monkeypatch):
    main, _, TestingSessionLocal = app_and_db
    from auth_service.models import User

    # Patch globals used by seed_admin()
    monkeypatch.setattr(main, "ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setattr(main, "ADMIN_PASSWORD", "adminpw")

    with TestingSessionLocal() as db:
        main.seed_admin(db)

    with TestingSessionLocal() as db:
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        assert admin is not None
        assert admin.is_admin is True
        assert admin.is_verified is True