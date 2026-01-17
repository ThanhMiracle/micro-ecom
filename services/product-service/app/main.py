from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db import Base, engine, SessionLocal, init_schema
from .models import Product
from .schemas import ProductOut, ProductCreate, ProductUpdate
from shared.security import require_user, require_admin

app = FastAPI(title="product-service")

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

# Public homepage products
@app.get("/products", response_model=list[ProductOut])
def list_published(db: Session = Depends(get_db)):
    rows = db.query(Product).filter(Product.published == True).order_by(Product.id.desc()).all()
    return [ProductOut(id=r.id, name=r.name, description=r.description, price=float(r.price), published=r.published) for r in rows]

@app.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    r = db.query(Product).filter(Product.id == product_id, Product.published == True).first()
    if not r:
        raise HTTPException(404, "Not found")
    return ProductOut(id=r.id, name=r.name, description=r.description, price=float(r.price), published=r.published)

# Admin endpoints
@app.get("/admin/products", response_model=list[ProductOut])
def admin_list(claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    rows = db.query(Product).order_by(Product.id.desc()).all()
    return [ProductOut(id=r.id, name=r.name, description=r.description, price=float(r.price), published=r.published) for r in rows]

@app.post("/admin/products", response_model=ProductOut)
def admin_create(payload: ProductCreate, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    p = Product(name=payload.name, description=payload.description, price=payload.price, published=payload.published)
    db.add(p); db.commit(); db.refresh(p)
    return ProductOut(id=p.id, name=p.name, description=p.description, price=float(p.price), published=p.published)

@app.patch("/admin/products/{product_id}", response_model=ProductOut)
def admin_update(product_id: int, payload: ProductUpdate, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Not found")

    if payload.name is not None: p.name = payload.name
    if payload.description is not None: p.description = payload.description
    if payload.price is not None: p.price = payload.price
    if payload.published is not None: p.published = payload.published

    db.commit(); db.refresh(p)
    return ProductOut(id=p.id, name=p.name, description=p.description, price=float(p.price), published=p.published)

@app.delete("/admin/products/{product_id}")
def admin_delete(product_id: int, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    require_admin(claims)
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(404, "Not found")
    db.delete(p); db.commit()
    return {"ok": True}
