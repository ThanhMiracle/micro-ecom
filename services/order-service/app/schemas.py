from pydantic import BaseModel

class CartItemIn(BaseModel):
    product_id: int
    qty: int = 1

class OrderCreateIn(BaseModel):
    items: list[CartItemIn]

class OrderItemOut(BaseModel):
    product_id: int
    qty: int
    unit_price: float

class OrderOut(BaseModel):
    id: int
    status: str
    total: float
    items: list[OrderItemOut]
