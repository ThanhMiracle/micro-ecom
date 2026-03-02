import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import httpx
from sqlalchemy.exc import SQLAlchemyError
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
async def create_order(
    payload: OrderCreateIn,
    claims: dict = Depends(require_user),
    db: Session = Depends(get_db),
):
    user_id = int(claims["sub"])
    user_email = claims["email"]

    if not payload.items:
        raise HTTPException(status_code=400, detail="Empty cart")

    # Normalize/merge duplicate items by product_id
    merged: dict[int, int] = {}
    for it in payload.items:
        pid = int(it.product_id)
        qty = int(it.qty)
        if qty <= 0:
            raise HTTPException(status_code=400, detail="Invalid qty")
        merged[pid] = merged.get(pid, 0) + qty

    # Fetch prices first (so we don't create DB records if product lookup fails)
    prices: dict[int, float] = {}
    try:
        for pid in merged.keys():
            prices[pid] = float(await fetch_product_price(pid))
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Product service timeout")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Product service unavailable")
    # fetch_product_price may raise HTTPException(400/...) already — let it bubble up

    total = 0.0
    for pid, qty in merged.items():
        total += prices[pid] * qty

    try:
        # Atomic transaction: either everything commits or nothing does
        with db.begin():
            order = Order(user_id=user_id, user_email=user_email, status="CREATED", total=total)
            db.add(order)
            db.flush()  # ensures order.id exists without committing

            items_out: list[OrderItemOut] = []
            for pid, qty in merged.items():
                unit_price = prices[pid]
                db.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=pid,
                        qty=qty,
                        unit_price=unit_price,
                    )
                )
                items_out.append(
                    OrderItemOut(product_id=pid, qty=qty, unit_price=float(unit_price))
                )

        # refresh after commit
        db.refresh(order)

        return OrderOut(
            id=order.id,
            status=order.status,
            total=float(order.total),
            items=items_out,
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create order")

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