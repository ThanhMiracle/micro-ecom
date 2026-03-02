import os
from pathlib import Path


def _seed_product(db, Product, name="P1", published=True, price=10.0, image_url=None):
    p = Product(
        name=name,
        description="desc",
        price=price,
        published=published,
        image_url=image_url,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_health(local_client):
    r = local_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_normalize_image_url(local_app_and_db):
    main, _, _ = local_app_and_db

    assert main.normalize_image_url(None) is None
    assert main.normalize_image_url("") is None
    assert main.normalize_image_url("   ") is None

    # absolute stays
    assert main.normalize_image_url("https://x/y.jpg") == "https://x/y.jpg"

    # already local correct
    assert main.normalize_image_url("/static/a.jpg") == "/static/a.jpg"

    # old/bad
    assert main.normalize_image_url("prod_1_x.jpg") == "/static/prod_1_x.jpg"
    assert main.normalize_image_url("/prod_1_x.jpg") == "/static/prod_1_x.jpg"

    # uploads mapping
    assert main.normalize_image_url("/uploads/a.jpg") == "/static/a.jpg"
    assert main.normalize_image_url("uploads/a.jpg") == "/static/a.jpg"


def test_public_list_only_published(local_client, local_app_and_db):
    _, _, TestingSessionLocal = local_app_and_db
    from product_service.models import Product

    with TestingSessionLocal() as db:
        _seed_product(db, Product, name="pub", published=True, price=1.0)
        _seed_product(db, Product, name="unpub", published=False, price=2.0)

    r = local_client.get("/products")
    assert r.status_code == 200
    data = r.json()

    assert all(p["published"] is True for p in data)
    names = [p["name"] for p in data]
    assert "pub" in names
    assert "unpub" not in names


def test_get_product_404_if_unpublished(local_client, local_app_and_db):
    _, _, TestingSessionLocal = local_app_and_db
    from product_service.models import Product

    with TestingSessionLocal() as db:
        p = _seed_product(db, Product, name="x", published=False)

    r = local_client.get(f"/products/{p.id}")
    assert r.status_code == 404


def test_admin_list_requires_admin(local_client, local_app_and_db):
    main, _, _ = local_app_and_db

    # set non-admin
    main.app.dependency_overrides[main.require_user] = lambda: {"sub": "1", "is_admin": False}

    r = local_client.get("/admin/products")
    assert r.status_code == 403


def test_admin_crud(local_client, local_app_and_db):
    main, _, _ = local_app_and_db

    # create
    r = local_client.post(
        "/admin/products",
        json={"name": "N1", "description": "D", "price": 12.5, "published": False, "image_url": "prod_1_old.jpg"},
    )
    assert r.status_code == 200
    created = r.json()
    pid = created["id"]
    assert created["name"] == "N1"
    # image_url normalized in output
    assert created["image_url"] == "/static/prod_1_old.jpg"

    # update
    r2 = local_client.patch(
        f"/admin/products/{pid}",
        json={"published": True, "price": 99.0, "image_url": "/uploads/new.jpg"},
    )
    assert r2.status_code == 200
    updated = r2.json()
    assert updated["published"] is True
    assert float(updated["price"]) == 99.0
    assert updated["image_url"] == "/static/new.jpg"

    # admin list includes unpublished/published
    r3 = local_client.get("/admin/products")
    assert r3.status_code == 200
    ids = [p["id"] for p in r3.json()]
    assert pid in ids

    # delete
    r4 = local_client.delete(f"/admin/products/{pid}")
    assert r4.status_code == 200
    assert r4.json() == {"ok": True}

    # gone
    r5 = local_client.get(f"/products/{pid}")
    assert r5.status_code == 404


def test_upload_image_rejects_extension(local_client, local_app_and_db):
    _, _, TestingSessionLocal = local_app_and_db
    from product_service.models import Product

    with TestingSessionLocal() as db:
        p = _seed_product(db, Product, name="img", published=True)

    files = {"file": ("bad.gif", b"GIF89a", "image/gif")}
    r = local_client.post(f"/admin/products/{p.id}/image", files=files)
    assert r.status_code == 400
    assert "Only .png" in r.json()["detail"]


def test_upload_image_rejects_mime(local_client, local_app_and_db):
    _, _, TestingSessionLocal = local_app_and_db
    from product_service.models import Product

    with TestingSessionLocal() as db:
        p = _seed_product(db, Product, name="img2", published=True)

    files = {"file": ("ok.jpg", b"\xff\xd8\xff", "application/pdf")}
    r = local_client.post(f"/admin/products/{p.id}/image", files=files)
    assert r.status_code == 400
    assert "Unsupported content type" in r.json()["detail"]


def test_upload_image_empty_file_400(local_client, local_app_and_db):
    _, _, TestingSessionLocal = local_app_and_db
    from product_service.models import Product

    with TestingSessionLocal() as db:
        p = _seed_product(db, Product, name="img3", published=True)

    files = {"file": ("ok.jpg", b"", "image/jpeg")}
    r = local_client.post(f"/admin/products/{p.id}/image", files=files)
    assert r.status_code == 400
    assert "Empty file" in r.json()["detail"]


def test_upload_image_success_writes_file_and_serves_static(local_client, local_app_and_db, tmp_path):
    main, _, TestingSessionLocal = local_app_and_db
    from product_service.models import Product

    with TestingSessionLocal() as db:
        p = _seed_product(db, Product, name="img4", published=True)

    # minimal jpeg header bytes
    jpg_bytes = b"\xff\xd8\xff\xe0" + b"x" * 10

    files = {"file": ("pic.jpg", jpg_bytes, "image/jpeg")}
    r = local_client.post(f"/admin/products/{p.id}/image", files=files)
    assert r.status_code == 200
    out = r.json()

    assert out["image_url"].startswith("/static/prod_")
    assert out["image_url"].endswith(".jpg")

    # ensure file exists on disk
    filename = out["image_url"].split("/static/")[1]
    dest = main.UPLOAD_DIR / filename
    assert dest.exists()
    assert dest.read_bytes() == jpg_bytes

    # static serving works
    r2 = local_client.get(out["image_url"])
    assert r2.status_code == 200
    assert r2.content == jpg_bytes