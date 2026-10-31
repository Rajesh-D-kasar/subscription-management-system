from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Payment, Invoice, Customer, User, InvoiceStatus, Subscription, SubscriptionStatus
from app.schemas.schemas import PaymentCreate, PaymentResponse
from app.api.deps import get_current_user, require_customer_owner_or_staff

router = APIRouter(prefix="/payments", tags=["Payments"])

def build_payment_response(p: Payment) -> dict:
    return {
        "id": p.id,
        "payment_reference": p.payment_reference,
        "invoice_id": p.invoice_id,
        "invoice_number": p.invoice.invoice_number if p.invoice else None,
        "customer_name": p.invoice.customer.name if p.invoice and p.invoice.customer else "Unknown",
        "payment_method": p.payment_method,
        "amount": p.amount,
        "payment_date": p.payment_date,
        "notes": p.notes
    }

@router.get("", response_model=List[PaymentResponse])
def get_payments(
    invoice_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Payment).join(Invoice)

    if current_user.role.value == "customer":
        if not current_user.customer_profile:
            return []
        query = query.filter(Invoice.customer_id == current_user.customer_profile.id)
    elif customer_id:
        query = query.filter(Invoice.customer_id == customer_id)

    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)

    payments = query.order_by(Payment.payment_date.desc()).offset(skip).limit(limit).all()
    return [build_payment_response(p) for p in payments]

@router.post("", response_model=PaymentResponse)
def record_payment(
    payment_in: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == payment_in.invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    require_customer_owner_or_staff(inv.customer_id, current_user, db)

    if inv.status == InvoiceStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot record payment on a cancelled invoice.")

    if payment_in.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount must be greater than zero.")

    # Prevent Overpayment (tolerance for float imprecision)
    if round(payment_in.amount, 2) > round(inv.amount_due, 2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount ({payment_in.amount:.2f}) exceeds outstanding balance ({inv.amount_due:.2f}). Overpayment is prevented."
        )

    pay_ref = f"PAY-{uuid.uuid4().hex[:8].upper()}"

    payment = Payment(
        payment_reference=pay_ref,
        invoice_id=inv.id,
        payment_method=payment_in.payment_method,
        amount=payment_in.amount,
        notes=payment_in.notes
    )
    db.add(payment)

    # Update invoice balances
    inv.amount_paid = round(inv.amount_paid + payment_in.amount, 2)
    inv.amount_due = max(0.0, round(inv.total_amount - inv.amount_paid, 2))

    if inv.amount_due == 0.0:
        inv.status = InvoiceStatus.PAID
        
        # Also ensure related subscription is active
        if inv.subscription and inv.subscription.status != SubscriptionStatus.ACTIVE:
            inv.subscription.status = SubscriptionStatus.ACTIVE

    db.commit()
    db.refresh(payment)
    return build_payment_response(payment)
