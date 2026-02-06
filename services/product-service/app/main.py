from pathlib import Path
import uuid
import os
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .db import Base, engine, SessionLocal, init_schema
from .models import Product
from .schemas import ProductOut, ProductCreate, ProductUpdate
from shared.security import require_user, require_admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("product-service")

# =========================
# Storage config
# =========================
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()  # local | s3

# Local storage (explicit contract)
# - When STORAGE_BACKEND=local: UPLOAD_DIR must be set and must be a writable path (typically a mounted volume)
# - When STORAGE_BACKEND=s3: UPLOAD_DIR is not required (uploads go to S3)
if STORAGE_BACKEND == "local":
    if "UPLOAD_DIR" not in os.environ:
        raise RuntimeError("UPLOAD_DIR environment variable must be set when STORAGE_BACKEND=local")
    UPLOAD_DIR = Path(os.environ["UPLOAD_DIR"])
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
else:
    # still define it for type/clarity; not used in s3 mode
    UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))

# S3 storage (only required when STORAGE_BACKEND=s3)
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")  # e.g. https://dxxxxx.cloudfront.net

s3 = None
if STORAGE_BACKEND == "s3":
    if not S3_BUCKET:
        raise RuntimeError("Missing required env var: S3_BUCKET (when STORAGE_BACKEND=s3)")
    s3 = boto3.client("s3", region_name=AWS_REGION)

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}

app = FastAPI(title="product-service")

# Serve uploaded images only in LOCAL mode
# NOTE: This mounts /static/* -> files from UPLOAD_DIR (filesystem)
if STORAGE_BACKEND == "local":
    app.mount("/static", StaticFiles(directory=str(UPLOAD_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup():
    init_schema()
    Base.metadata.create_all(bind=engine)
    if STORAGE_BACKEND == "local":
        logger.info("Storage backend=local; UPLOAD_DIR=%s; serving at /static/*", str(UPLOAD_DIR))
    else:
        logger.info("Storage backend=s3; bucket=%s region=%s public_base=%s", S3_BUCKET, AWS_REGION, PUBLIC_BASE_URL or "(none)")


# -------------------------
# Helpers
# -------------------------
def normalize_image_url(url: str | None) -> str | None:
    """
    Backward compatible fixes for old DB values.
    - Local mode: serve files under /static (mounted to UPLOAD_DIR)
    - S3 mode: keep absolute URLs
    """
    if not url:
        return None

    u = url.strip()
    if not u:
        return None

    # Absolute URL (S3/CloudFront) - keep as-is
    if u.startswith("http://") or u.startswith("https://"):
        return u

    # Already correct for local
    if u.startswith("/static/"):
        return u

    # Old/bad records: "/prod_1_xxx.jpg" or "prod_1_xxx.jpg"
    if u.startswith("/prod_") or u.startswith("prod_"):
        filename = u.lstrip("/")
        return f"/static/{filename}"

    # Sometimes people used "/uploads/..." or "uploads/..."
    if u.startswith("/uploads/"):
        return u.replace("/uploads/", "/static/", 1)
    if u.startswith("uploads/"):
        return f"/static/{u[len('uploads/'):]}"  # drop uploads/

    return u


def to_out(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        name=p.name,
        description=p.description,
        price=float(p.price),
        published=p.published,
        image_url=normalize_image_url(p.image_url),
    )


# -------------------------
# Public endpoints
# -------------------------
@app.get("/products", response_model=list[ProductOut])
def list_published(db: Session = Depends(get_db)):
    rows = db.query(Product).filter(Product.published == True).order_by(Product.id.desc()).all()
    return [to_out(r) for r in rows]


@app.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    r = db.query(Product).filter(Product.id == product_id, Product.published == True).first()
    if not r:
        raise HTTPException(404, "Not found")
    return to_out(r)


# -------------------------
# Admin endpoints
# -------------------------
@app.get("/admin/products", response_model=list[ProductOut])
def admin_list(claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    rows = db.query(Product).order_by(Product.id.desc()).all()
    return [to_out(r) for r in rows]


@app.post("/admin/products", response_model=ProductOut)
def admin_create(payload: ProductCreate, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    p = Product(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        published=payload.published,
        image_url=payload.image_url,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return to_out(p)


@app.patch("/admin/products/{product_id}", response_model=ProductOut)
def admin_update(product_id: int, payload: ProductUpdate, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Not found")

    if payload.name is not None:
        p.name = payload.name
    if payload.description is not None:
        p.description = payload.description
    if payload.price is not None:
        p.price = payload.price
    if payload.published is not None:
        p.published = payload.published
    if payload.image_url is not None:
        p.image_url = payload.image_url

    db.commit()
    db.refresh(p)
    return to_out(p)


@app.delete("/admin/products/{product_id}")
def admin_delete(product_id: int, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Not found")
    db.delete(p)
    db.commit()
    return {"ok": True}


# -------------------------
# Upload image (admin-only)
# -------------------------
@app.post("/admin/products/{product_id}/image", response_model=ProductOut)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    claims: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    require_admin(claims)

    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Product not found")

    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Only .png, .jpg, .jpeg, .webp allowed")

    # Optional MIME check
    if file.content_type and file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, f"Unsupported content type: {file.content_type}")

    # -------------------------
    # LOCAL MODE
    # -------------------------
    if STORAGE_BACKEND == "local":
        out_name = f"prod_{product_id}_{uuid.uuid4().hex}{ext}"
        dest = UPLOAD_DIR / out_name

        data = await file.read()
        try:
            if not data:
                raise HTTPException(400, "Empty file")
            dest.write_bytes(data)
        finally:
            await file.close()

        # Always store correct local URL
        p.image_url = f"/static/{out_name}"
        db.commit()
        db.refresh(p)
        return to_out(p)

    # -------------------------
    # S3 MODE
    # -------------------------
    if STORAGE_BACKEND == "s3":
        out_name = f"{uuid.uuid4().hex}{ext}"
        key = f"products/{product_id}/{out_name}"

        try:
            file.file.seek(0)
            s3.upload_fileobj(
                Fileobj=file.file,
                Bucket=S3_BUCKET,
                Key=key,
                ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
            )
        except (BotoCoreError, ClientError) as e:
            raise HTTPException(500, f"Failed to upload to S3: {str(e)}")
        finally:
            try:
                await file.close()
            except Exception:
                pass

        # Build public URL
        if PUBLIC_BASE_URL:
            image_url = f"{PUBLIC_BASE_URL}/{key}"
        else:
            image_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"

        # Optional: delete old image if it looks like our products prefix
        old = (p.image_url or "").strip()
        if old:
            idx = old.find("/products/")
            if idx != -1:
                old_key = old[idx + 1 :]  # remove leading slash
                try:
                    s3.delete_object(Bucket=S3_BUCKET, Key=old_key)
                except Exception:
                    pass

        p.image_url = image_url
        db.commit()
        db.refresh(p)
        return to_out(p)

    raise HTTPException(500, f"Unknown STORAGE_BACKEND={STORAGE_BACKEND}")


@app.get("/health")
def health():
    return {"ok": True}
