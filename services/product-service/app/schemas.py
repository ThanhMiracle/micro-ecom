from pydantic import BaseModel

class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    price: float
    published: bool

class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: float
    published: bool = False

class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    published: bool | None = None
