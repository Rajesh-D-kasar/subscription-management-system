# FluxSub: Subscription Management System
### Odoo x FLUX Lucknow Hackathon 2026

A modern, high-performance, modular Subscription Management System built with **FastAPI**, **SQLAlchemy**, **SQLite**, and **Vanilla HTML5/CSS3/JavaScript**. Designed specifically to run on lightweight hardware (8GB RAM laptops) while providing enterprise-grade ERP workflows.

---

## ⚡ Highlights & Key Features

### 1. Robust Role-Based Access Control (RBAC)
- **Roles**: `Admin`, `Staff`, and `Customer`.
- **Admin**: Full control across catalog, plans, discounts, tax rules, staff accounts, and financial analytics.
- **Staff**: Day-to-day operations: managing customers, drafting/modifying subscriptions, issuing invoices, and recording payments.
- **Customer Portal**: Strictly isolated customer workspace. Customers can only view and manage their own subscriptions, review invoices, download PDF statements, and initiate renewal or early termination.
- **Password Policy Enforced**: Minimum 9 characters, at least 1 uppercase letter, 1 lowercase letter, and 1 special symbol.
- **Security**: Argon2/Bcrypt password hashing, JWT bearer tokens, and secure password-reset tokens.

### 2. Product Catalog & Variant Pricing Model
- Supports Products and dynamic Variants (e.g. `Brand`, `RAM`, `Tier`).
- **Odoo Hackathon Specification**:
  - Base Product: **Software** (₹2,000.00)
  - Variant: **Brand = Odoo** (+₹560.00)
  - Selecting Odoo automatically adds ₹560 to the base price before taxes and invoice calculations.

### 3. Subscription Lifecycle Engine
- Supports **Daily**, **Weekly**, **Monthly**, and **Yearly** recurrence plans.
- Lifecycle state transitions: `Draft` ➔ `Quotation` ➔ `Confirmed` ➔ `Active` ➔ `Paused` ➔ `Closed`.
- Configurable plan rules: Allow pause/resume, early closure restrictions, minimum quantities, and renewal settings.
- Quotation templates with customizable validity windows and payment terms.

### 4. Invoicing, Taxes & Duplicate Billing Prevention
- Automatic generation of invoices from active or confirmed subscriptions.
- Unique sequential invoice numbers (`INV-XXXXXXXX`).
- Strict validation that prevents duplicate billing for the same subscription period (`billing_period_start` to `billing_period_end`).
- Integrated Tax Engine (e.g., GST 18%, VAT 10%) and dynamic discount calculations (percentage & fixed).
- On-the-fly **PDF Invoice Generation** using ReportLab.

### 5. Payment Recording & Overpayment Guard
- Multi-method payment recording: `Cash`, `Bank Transfer`, `UPI`, `Card`.
- Supports partial payments with real-time balance tracking (`amount_due`).
- Automatic invoice status update to `Paid` upon complete settlement.
- **Anti-Overpayment Guard**: Backend refuses any payment greater than the outstanding balance.

### 6. Live Business Intelligence & Dashboard
- Live dashboard metrics derived strictly from the database:
  - Total Customers
  - Active Subscriptions
  - Invoices Issued
  - Revenue Collected
  - Outstanding Payments
  - Real-time Overdue Invoices alert list

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ (Tested on Python 3.12)
- Pip

### 1. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Start the Backend & Web Application
Navigate to the `backend` folder and run the server:
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```
*(The FastAPI server serves both the REST API at `/api/v1` and the complete single-page ERP frontend directly at `/`)*

---

## 🔑 Pre-Seeded Evaluator Accounts

The system automatically initializes and seeds demo data on first boot:

| Role | Email | Password | Scope & Permissions |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@example.com` | `Admin@12345` | Complete system control, products, plans, discounts, staff creation |
| **Staff** | `staff@example.com` | `Staff@12345` | Day-to-day operations, subscriptions, invoicing, payments |
| **Customer** | `customer@example.com` | `Customer@12345` | Customer Portal: personal subscriptions, invoices, and payments |

---

## 🧪 Automated Testing

Execute the automated test suite verifying password rules, role guards, variant pricing, and invoice generation:
```bash
cd backend
python -m pytest tests/test_core.py
```
All tests should pass with `100%` success rate.
