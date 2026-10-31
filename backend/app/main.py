from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.init_db import init_db
from app.api.routes import (
    auth, customers, products, plans,
    discounts_taxes, subscriptions, invoices,
    payments, dashboard
)

# Initialize tables
Base.metadata.create_all(bind=engine)

# Auto seed if empty
db = SessionLocal()
try:
    init_db(db)
finally:
    db.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Professional Enterprise Subscription Management System for Odoo x FLUX Lucknow Hackathon 2026."
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}

# Mount API Routers
api_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=api_prefix)
app.include_router(customers.router, prefix=api_prefix)
app.include_router(products.router, prefix=api_prefix)
app.include_router(plans.router, prefix=api_prefix)
app.include_router(discounts_taxes.router, prefix=api_prefix)
app.include_router(subscriptions.router, prefix=api_prefix)
app.include_router(invoices.router, prefix=api_prefix)
app.include_router(payments.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)

# Serve Frontend static assets
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

