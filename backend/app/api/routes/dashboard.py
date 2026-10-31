from datetime import date
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.models import (
    Customer, Subscription, Product, Plan, Invoice,
    Payment, SubscriptionStatus, InvoiceStatus, User
)
from app.schemas.schemas import (
    DashboardAnalyticsResponse, DashboardStats,
    MonthlyRevenueItem, StatusBreakdownItem
)
from app.api.deps import require_staff_or_admin
from app.api.routes.invoices import build_invoice_response
from app.api.routes.payments import build_payment_response

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])

@router.get("/analytics", response_model=DashboardAnalyticsResponse)
def get_dashboard_analytics(
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    today = date.today()

    total_customers = db.query(Customer).count()
    active_subscriptions = db.query(Subscription).filter(Subscription.status == SubscriptionStatus.ACTIVE).count()
    total_products = db.query(Product).filter(Product.is_active == True).count()
    total_plans = db.query(Plan).filter(Plan.is_active == True).count()
    total_invoices = db.query(Invoice).count()

    total_rev = db.query(func.coalesce(func.sum(Payment.amount), 0.0)).scalar()
    
    # Outstanding is sum of amount_due on un-cancelled invoices
    outstanding = db.query(
        func.coalesce(func.sum(Invoice.amount_due), 0.0)
    ).filter(Invoice.status != InvoiceStatus.CANCELLED).scalar()

    overdue_count = db.query(Invoice).filter(
        Invoice.due_date < today,
        Invoice.status != InvoiceStatus.PAID,
        Invoice.status != InvoiceStatus.CANCELLED
    ).count()

    stats = DashboardStats(
        total_customers=total_customers,
        active_subscriptions=active_subscriptions,
        total_products=total_products,
        total_plans=total_plans,
        total_invoices=total_invoices,
        total_revenue_collected=round(total_rev, 2),
        outstanding_payments=round(outstanding, 2),
        overdue_invoices_count=overdue_count
    )

    # Subscription Status Breakdown
    status_counts = db.query(
        Subscription.status, func.count(Subscription.id)
    ).group_by(Subscription.status).all()

    sub_breakdown = [
        StatusBreakdownItem(status=str(s.value if hasattr(s, 'value') else s), count=c)
        for s, c in status_counts
    ]

    # Recent Transactions (Last 5 payments)
    recent_pays = db.query(Payment).order_by(Payment.payment_date.desc()).limit(5).all()
    recent_transactions_resp = [build_payment_response(p) for p in recent_pays]

    # Overdue Invoices (Top 5)
    overdue_invs = db.query(Invoice).filter(
        Invoice.due_date < today,
        Invoice.status != InvoiceStatus.PAID,
        Invoice.status != InvoiceStatus.CANCELLED
    ).order_by(Invoice.due_date.asc()).limit(5).all()
    overdue_invs_resp = [build_invoice_response(i) for i in overdue_invs]

    # Monthly revenue: real aggregation of payments grouped by calendar month (last 6 months)
    monthly_map = {}
    for pdate, amt in db.query(Payment.payment_date, Payment.amount).all():
        if pdate is None:
            continue
        key = (pdate.year, pdate.month)
        monthly_map[key] = monthly_map.get(key, 0.0) + float(amt)

    buckets = []
    y, m = today.year, today.month
    for i in range(5, -1, -1):
        mm, yy = m - i, y
        while mm <= 0:
            mm += 12
            yy -= 1
        buckets.append((yy, mm))

    monthly_data = [
        MonthlyRevenueItem(
            month=date(yy, mm, 1).strftime("%b %Y"),
            revenue=round(monthly_map.get((yy, mm), 0.0), 2)
        )
        for yy, mm in buckets
    ]

    return {
        "stats": stats,
        "monthly_revenue": monthly_data,
        "subscription_status_breakdown": sub_breakdown,
        "recent_transactions": recent_transactions_resp,
        "overdue_invoices": overdue_invs_resp
    }
