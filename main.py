import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import db, create_document, get_documents
from schemas import Product, Category, Order, OrderItem, Customer

app = FastAPI(title="Honey Shop API", version="1.1.0")

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
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
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
    inserted_id = create_document("order", payload)
    return {"id": inserted_id, "status": "received"}

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
    created = {"categories": 0, "products": 0}

    # Categories
    categories = [
        {"name": "Raw Honey", "slug": "raw-honey", "description": "Unfiltered, unheated honey"},
        {"name": "Flavored Honey", "slug": "flavored-honey", "description": "Infused with natural botanicals"},
        {"name": "Propolis", "slug": "propolis", "description": "Natural resin with benefits"},
        {"name": "Beeswax", "slug": "beeswax", "description": "Pure wax for candles & crafts"},
    ]

    if db["category"].count_documents({}) == 0:
        db["category"].insert_many(categories)
        created["categories"] = len(categories)

    # Products
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

    if db["product"].count_documents({}) == 0:
        db["product"].insert_many(products)
        created["products"] = len(products)

    return {"seeded": created}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
