import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import httpx

from .db import Base, engine, SessionLocal, init_schema
from .models import Order, OrderItem
from .schemas import OrderCreateIn, OrderOut, OrderItemOut
from shared.security import require_user
from shared.events import publish

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
PRODUCT_URL_INTERNAL = os.getenv("PRODUCT_URL_INTERNAL", "http://product-service:8000")  # for docker network

app = FastAPI(title="order-service")

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

async def fetch_product_price(product_id: int) -> float:
    # Calls product-service (internal docker host). If running locally without docker, set PRODUCT_URL_INTERNAL to http://localhost:8002
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{PRODUCT_URL_INTERNAL}/products/{product_id}")
        if r.status_code != 200:
            raise HTTPException(400, f"Product {product_id} not available")
        data = r.json()
        return float(data["price"])

@app.post("/orders", response_model=OrderOut)
async def create_order(payload: OrderCreateIn, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    user_id = int(claims["sub"])
    user_email = claims["email"]

    if not payload.items:
        raise HTTPException(400, "Empty cart")

    order = Order(user_id=user_id, user_email=user_email, status="CREATED", total=0)
    db.add(order)
    db.commit()
    db.refresh(order)

    total = 0.0
    items_out: list[OrderItemOut] = []

    for it in payload.items:
        if it.qty <= 0:
            raise HTTPException(400, "Invalid qty")
        unit_price = await fetch_product_price(it.product_id)
        total += unit_price * it.qty
        oi = OrderItem(order_id=order.id, product_id=it.product_id, qty=it.qty, unit_price=unit_price)
        db.add(oi)
        items_out.append(OrderItemOut(product_id=it.product_id, qty=it.qty, unit_price=float(unit_price)))

    order.total = total
    db.commit()
    db.refresh(order)

    return OrderOut(id=order.id, status=order.status, total=float(order.total), items=items_out)

@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    user_id = int(claims["sub"])
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        raise HTTPException(404, "Not found")

    items = [
        OrderItemOut(product_id=i.product_id, qty=i.qty, unit_price=float(i.unit_price))
        for i in order.items
    ]
    return OrderOut(id=order.id, status=order.status, total=float(order.total), items=items)

@app.post("/orders/{order_id}/pay")
def pay_order(order_id: int, claims: dict = Depends(require_user), db: Session = Depends(get_db)):
    user_id = int(claims["sub"])
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        raise HTTPException(404, "Not found")
    if order.status == "PAID":
        return {"ok": True, "status": "PAID"}
    if order.status != "CREATED":
        raise HTTPException(400, f"Cannot pay in status {order.status}")

    # Simulated payment success
    order.status = "PAID"
    db.commit()
    db.refresh(order)

    if RABBITMQ_URL:
        publish(
            RABBITMQ_URL,
            "payment.succeeded",
            {"email": order.user_email, "order_id": order.id, "total": float(order.total)},
        )

    return {"ok": True, "status": "PAID"}

@app.get("/health")
def health():
    return {"ok": True}