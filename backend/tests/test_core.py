import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_admin_login():
    res = client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "Admin@12345"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "admin"

def test_password_policy_validation():
    # Weak password failure
    res = client.post("/api/v1/auth/register", json={
        "email": "weak@test.com",
        "password": "weak",
        "full_name": "Weak User"
    })
    assert res.status_code == 400
    assert "more than 8 characters" in res.json()["detail"]

    # Valid registration with unique email per test run
    import uuid
    uniq_email = f"user_{uuid.uuid4().hex[:6]}@test.com"
    res_ok = client.post("/api/v1/auth/register", json={
        "email": uniq_email,
        "password": "StrongPassword@2026",
        "full_name": "Strong User"
    })
    assert res_ok.status_code == 200
    assert "access_token" in res_ok.json()

def test_products_and_variants():
    # Login as admin
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "Admin@12345"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch products
    prods = client.get("/api/v1/products", headers=headers).json()
    assert len(prods) > 0
    # Check Odoo variant exists (+560)
    has_odoo = False
    for p in prods:
        for v in p["variants"]:
            if v["attribute_value"] == "Odoo" and v["additional_price"] == 560.0:
                has_odoo = True
    assert has_odoo is True

def test_dashboard_analytics():
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "Admin@12345"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    dash = client.get("/api/v1/dashboard/analytics", headers=headers)
    assert dash.status_code == 200
    d = dash.json()
    assert "stats" in d
    assert d["stats"]["total_customers"] >= 2
    assert d["stats"]["total_revenue_collected"] > 0
    assert d["stats"]["outstanding_payments"] > 0
