from sqlalchemy import String, Boolean, Numeric, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    user_email: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="CREATED")  # CREATED, PAID, CANCELLED
    total: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    order: Mapped[Order] = relationship(back_populates="items")
