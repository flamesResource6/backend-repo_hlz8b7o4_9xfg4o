"""
Database Schemas for Honey E‑commerce

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercase class name. Example: class Product -> "product" collection.

Use these models in your API for validation before writing to MongoDB.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

# -----------------
# Core Collections
# -----------------

class Category(BaseModel):
    name: str = Field(..., description="Category display name, e.g., 'Raw Honey'")
    slug: str = Field(..., description="URL-friendly identifier, e.g., 'raw-honey'")
    description: Optional[str] = Field(None, description="Short description of the category")

class Product(BaseModel):
    title: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Marketing description")
    price: float = Field(..., ge=0, description="Unit price in USD")
    category: str = Field(..., description="Category slug")
    image_url: Optional[str] = Field(None, description="Primary product image URL")
    in_stock: bool = Field(True, description="Stock availability")
    weight_grams: Optional[int] = Field(None, ge=0, description="Net weight in grams")
    variant: Optional[str] = Field(None, description="Variant label (e.g., 'Lavender', 'Acacia')")

# ------------
# Order Models
# ------------

class OrderItem(BaseModel):
    product_id: str = Field(..., description="Referenced product _id (string)")
    title: str = Field(..., description="Product title snapshot")
    price: float = Field(..., ge=0, description="Unit price at time of order")
    quantity: int = Field(..., ge=1, description="Quantity ordered")

class Customer(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str = "US"

class Order(BaseModel):
    items: List[OrderItem]
    customer: Customer
    subtotal: float = Field(..., ge=0)
    shipping: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    status: str = Field("pending", description="Order status: pending, paid, shipped, completed, cancelled")
