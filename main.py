import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import db, create_document, get_documents
from schemas import Product, Category, Order, OrderItem, Customer

# Extra imports for lookups
try:
    from bson.objectid import ObjectId
except Exception:
    ObjectId = None

app = FastAPI(title="Honey Shop API", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers

def to_str_id(doc: dict):
    if not doc:
        return doc
    d = doc.copy()
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d

# -----------------------
# Pricing/Tax/Shipping
# -----------------------

def calc_subtotal(items: List[OrderItem]) -> float:
    return round(sum(max(0.0, i.price) * max(1, i.quantity) for i in items), 2)


def calc_shipping(subtotal: float, destination: Optional[Customer]) -> float:
    # Simple policy: $0 for orders >= $50 in US, else $5 flat; $12 international
    country = (destination.country if destination else "US").upper()
    if country != "US":
        return 12.0 if subtotal > 0 else 0.0
    if subtotal >= 50:
        return 0.0
    return 5.0 if subtotal > 0 else 0.0


STATE_TAX = {
    # Simple illustrative rates
    "CA": 0.0825,
    "NY": 0.088,
    "TX": 0.0625,
    "FL": 0.06,
}


def calc_tax(subtotal: float, shipping: float, destination: Optional[Customer]) -> float:
    # Apply tax on goods only (not shipping) for simplicity
    country = (destination.country if destination else "US").upper()
    if country != "US":
        return 0.0
    state = (destination.state or "").upper() if destination else ""
    rate = STATE_TAX.get(state, 0.07)  # default 7%
    return round(subtotal * rate, 2)


# Seed helpers (idempotent)

def _seed_payload():
    categories = [
        {"name": "Raw Honey", "slug": "raw-honey", "description": "Unfiltered, unheated honey"},
        {"name": "Flavored Honey", "slug": "flavored-honey", "description": "Infused with natural botanicals"},
        {"name": "Propolis", "slug": "propolis", "description": "Natural resin with benefits"},
        {"name": "Beeswax", "slug": "beeswax", "description": "Pure wax for candles & crafts"},
    ]

    products = [
        {
            "title": "Raw Wildflower Honey 500g",
            "description": "Golden, floral notes from diverse wild blooms.",
            "price": 12.99,
            "category": "raw-honey",
            "image_url": "https://images.unsplash.com/photo-1505575972945-530f3fdde9f0?q=80&w=1200&auto=format&fit=crop",
            "in_stock": True,
            "weight_grams": 500,
            "variant": "Wildflower"
        },
        {
            "title": "Raw Acacia Honey 250g",
            "description": "Light, delicate taste with slow crystallization.",
            "price": 9.5,
            "category": "raw-honey",
            "image_url": "https://images.unsplash.com/photo-1519681393784-d120267933ba?q=80&w=1200&auto=format&fit=crop",
            "in_stock": True,
            "weight_grams": 250,
            "variant": "Acacia"
        },
        {
            "title": "Lavender Infused Honey 250g",
            "description": "Soothing lavender infusion, perfect for tea.",
            "price": 8.75,
            "category": "flavored-honey",
            "image_url": "https://images.unsplash.com/photo-1495501468073-4f1d9cfe4c0b?q=80&w=1200&auto=format&fit=crop",
            "in_stock": True,
            "weight_grams": 250,
            "variant": "Lavender"
        },
        {
            "title": "Cinnamon Infused Honey 250g",
            "description": "Warm cinnamon notes blended with raw honey.",
            "price": 8.95,
            "category": "flavored-honey",
            "image_url": "https://images.unsplash.com/photo-1498579150354-977475b7ea0b?q=80&w=1200&auto=format&fit=crop",
            "in_stock": True,
            "weight_grams": 250,
            "variant": "Cinnamon"
        },
        {
            "title": "Propolis Tincture 30ml",
            "description": "High-strength propolis extract.",
            "price": 14.0,
            "category": "propolis",
            "image_url": "https://images.unsplash.com/photo-1615485737651-6d7d5eb430dc?q=80&w=1200&auto=format&fit=crop",
            "in_stock": True,
            "variant": "Tincture"
        },
        {
            "title": "Beeswax Candles (Set of 2)",
            "description": "Naturally scented hand-rolled candles.",
            "price": 11.25,
            "category": "beeswax",
            "image_url": "https://images.unsplash.com/photo-1601582585289-4b59f95f3a1b?q=80&w=1200&auto=format&fit=crop",
            "in_stock": True,
            "variant": "Candles"
        }
    ]
    return categories, products


def ensure_seeded() -> dict:
    created = {"categories": 0, "products": 0}
    if db is None:
        return created
    categories, products = _seed_payload()
    try:
        if db["category"].count_documents({}) == 0:
            db["category"].insert_many(categories)
            created["categories"] = len(categories)
        if db["product"].count_documents({}) == 0:
            db["product"].insert_many(products)
            created["products"] = len(products)
    except Exception:
        # Best-effort; don't crash on seed failure
        pass
    return created

# ---------
# Root/Test
# ---------

@app.get("/")
def read_root():
    return {"message": "Honey Shop API is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = os.getenv("DATABASE_NAME") or "Unknown"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# ---------------
# Catalog Endpoints
# ---------------

@app.get("/api/products")
def list_products(category: Optional[str] = None, q: Optional[str] = None, limit: int = 50):
    filter_dict = {}
    if category:
        filter_dict["category"] = category
    if q:
        filter_dict["title"] = {"$regex": q, "$options": "i"}
    docs = get_documents("product", filter_dict, limit)
    return [to_str_id(d) for d in docs]

@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    doc = None
    # Try by ObjectId if possible, else try as string id, else slug query
    if ObjectId is not None:
        try:
            oid = ObjectId(product_id)
            doc = db["product"].find_one({"_id": oid})
        except Exception:
            doc = None
    if doc is None:
        # Try by id stored as string (rare) or by slug-like title match
        doc = db["product"].find_one({"id": product_id})
    if doc is None:
        # Try by slug (client may pass slug)
        doc = db["product"].find_one({"slug": product_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return to_str_id(doc)

class CreateProduct(Product):
    pass

@app.post("/api/products", status_code=201)
def create_product(payload: CreateProduct):
    inserted_id = create_document("product", payload)
    return {"id": inserted_id}

@app.get("/api/categories")
def list_categories(limit: int = 50):
    docs = get_documents("category", {}, limit)
    return [to_str_id(d) for d in docs]

class CreateCategory(Category):
    pass

@app.post("/api/categories", status_code=201)
def create_category(payload: CreateCategory):
    inserted_id = create_document("category", payload)
    return {"id": inserted_id}

# -------------------------
# Pricing endpoints (quote)
# -------------------------
from pydantic import BaseModel

class QuoteItem(BaseModel):
    product_id: Optional[str] = None
    title: str
    price: float
    quantity: int

class QuoteRequest(BaseModel):
    items: List[QuoteItem]
    customer: Optional[Customer] = None

@app.post("/api/pricing/quote")
def pricing_quote(payload: QuoteRequest):
    items = [OrderItem(product_id=i.product_id or "", title=i.title, price=i.price, quantity=i.quantity) for i in payload.items]
    subtotal = calc_subtotal(items)
    shipping = calc_shipping(subtotal, payload.customer)
    tax = calc_tax(subtotal, shipping, payload.customer)
    total = round(subtotal + shipping + tax, 2)
    return {
        "subtotal": round(subtotal, 2),
        "shipping": round(shipping, 2),
        "tax": round(tax, 2),
        "total": total,
    }

# ---------------
# Orders Endpoints
# ---------------

class CreateOrder(Order):
    pass

@app.post("/api/orders", status_code=201)
def create_order(payload: CreateOrder):
    # Basic sanity check
    if not payload.items or len(payload.items) == 0:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    # Recalculate server-side pricing for trust
    subtotal = calc_subtotal(payload.items)
    shipping_val = calc_shipping(subtotal, payload.customer)
    tax_val = calc_tax(subtotal, shipping_val, payload.customer)
    total_val = round(subtotal + shipping_val + tax_val, 2)

    # Build a safe order snapshot
    safe_order = payload.model_dump()
    safe_order["subtotal"] = round(subtotal, 2)
    safe_order["shipping"] = round(shipping_val, 2)
    safe_order["total"] = total_val

    inserted_id = create_document("order", safe_order)
    return {"id": inserted_id, "status": "received", "subtotal": safe_order["subtotal"], "shipping": safe_order["shipping"], "tax": tax_val, "total": total_val}

@app.get("/api/orders")
def list_orders(limit: int = 50):
    docs = get_documents("order", {}, limit)
    return [to_str_id(d) for d in docs]

# ---------------
# Seed demo data
# ---------------

@app.post("/api/seed")
def seed_demo():
    """Seed categories and sample products if collections are empty."""
    created = ensure_seeded()
    return {"seeded": created}

# Auto-seed on startup if empty (idempotent)

@app.on_event("startup")
async def startup_event():
    ensure_seeded()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
