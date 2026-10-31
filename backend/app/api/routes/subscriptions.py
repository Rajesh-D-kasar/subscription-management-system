from typing import List, Optional
from datetime import date, timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.models.models import (
    Subscription, SubscriptionLine, Customer, Plan, Product,
    ProductVariant, Discount, QuotationTemplate, User,
    SubscriptionStatus, DiscountType
)
from app.schemas.schemas import (
    SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse,
    SubscriptionLineResponse
)
from app.api.deps import (
    get_current_user, require_staff_or_admin,
    require_customer_owner_or_staff
)

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

def build_subscription_response(sub: Subscription) -> dict:
    lines_resp = []
    for line in sub.lines:
        lines_resp.append({
            "id": line.id,
            "product_id": line.product_id,
            "product_name": line.product.name if line.product else "N/A",
            "variant_id": line.variant_id,
            "variant_name": f"{line.variant.attribute_name}: {line.variant.attribute_value}" if line.variant else None,
            "description": line.description,
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "variant_price": line.variant_price,
            "tax_rate": line.tax_rate,
            "tax_amount": line.tax_amount,
            "discount_amount": line.discount_amount,
            "subtotal": line.subtotal,
            "total_amount": line.total_amount
        })

    return {
        "id": sub.id,
        "subscription_number": sub.subscription_number,
        "customer_id": sub.customer_id,
        "customer_name": sub.customer.name if sub.customer else "Unknown",
        "customer_email": sub.customer.email if sub.customer else "",
        "plan_id": sub.plan_id,
        "plan_name": sub.plan.name if sub.plan else "Unknown",
        "plan_recurrence": sub.plan.recurrence.value if sub.plan else "monthly",
        "status": sub.status,
        "start_date": sub.start_date,
        "expiry_date": sub.expiry_date,
        "next_billing_date": sub.next_billing_date,
        "payment_terms": sub.payment_terms,
        "notes": sub.notes,
        "cancellation_reason": sub.cancellation_reason,
        "subtotal": sub.subtotal,
        "tax_amount": sub.tax_amount,
        "discount_amount": sub.discount_amount,
        "total_amount": sub.total_amount,
        "created_at": sub.created_at,
        "lines": lines_resp
    }

@router.get("", response_model=List[SubscriptionResponse])
def get_subscriptions(
    customer_id: Optional[int] = None,
    status_filter: Optional[SubscriptionStatus] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Subscription)

    # If customer role, strictly restrict to their customer ID
    if current_user.role.value == "customer":
        if not current_user.customer_profile:
            return []
        query = query.filter(Subscription.customer_id == current_user.customer_profile.id)
    elif customer_id:
        query = query.filter(Subscription.customer_id == customer_id)

    if status_filter:
        query = query.filter(Subscription.status == status_filter)

    if search:
        search_fmt = f"%{search}%"
        query = query.join(Customer).filter(
            or_(
                Subscription.subscription_number.ilike(search_fmt),
                Customer.name.ilike(search_fmt),
                Customer.email.ilike(search_fmt)
            )
        )

    subs = query.order_by(Subscription.created_at.desc()).offset(skip).limit(limit).all()
    return [build_subscription_response(s) for s in subs]

@router.post("", response_model=SubscriptionResponse)
def create_subscription(
    sub_in: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Customer can only create for self, Staff/Admin can create for any customer
    require_customer_owner_or_staff(sub_in.customer_id, current_user, db)

    customer = db.query(Customer).filter(Customer.id == sub_in.customer_id).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    plan = db.query(Plan).filter(Plan.id == sub_in.plan_id).first()
    if not plan or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected plan is inactive or not found")

    # Dates
    start_d = sub_in.start_date or date.today()
    interval_days = plan.billing_interval_days or 30
    expiry_d = start_d + timedelta(days=interval_days)

    # Optional quotation template terms
    payment_terms = sub_in.payment_terms
    if sub_in.template_id:
        tpl = db.query(QuotationTemplate).filter(QuotationTemplate.id == sub_in.template_id).first()
        if tpl:
            payment_terms = tpl.payment_terms or payment_terms

    # Check discount code
    discount_obj = None
    if sub_in.discount_code:
        d_code = sub_in.discount_code.strip().upper()
        discount_candidate = db.query(Discount).filter(Discount.code == d_code, Discount.is_active == True).first()
        if discount_candidate:
            # Check date and usage limits
            today = date.today()
            if (discount_candidate.start_date and today < discount_candidate.start_date) or \
               (discount_candidate.end_date and today > discount_candidate.end_date):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount code is expired or not yet active.")
            if discount_candidate.max_usage_limit and discount_candidate.times_used >= discount_candidate.max_usage_limit:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount code usage limit reached.")
            discount_obj = discount_candidate
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid discount code.")

    # Unique subscription number
    sub_num = f"SUB-{uuid.uuid4().hex[:8].upper()}"

    initial_status = SubscriptionStatus.QUOTATION if current_user.role.value == "customer" else SubscriptionStatus.CONFIRMED

    subscription = Subscription(
        subscription_number=sub_num,
        customer_id=customer.id,
        plan_id=plan.id,
        status=initial_status,
        start_date=start_d,
        expiry_date=expiry_d,
        next_billing_date=expiry_d,
        payment_terms=payment_terms,
        notes=sub_in.notes,
        discount_id=discount_obj.id if discount_obj else None
    )
    db.add(subscription)
    db.flush()

    total_subtotal = 0.0
    total_tax = 0.0
    total_items_qty = 0

    # Process lines
    for item in sub_in.lines:
        prod = db.query(Product).filter(Product.id == item.product_id).first()
        if not prod or not prod.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product ID {item.product_id} invalid or inactive")

        # Base price
        base_unit_price = item.unit_price if item.unit_price is not None else prod.sales_price
        variant_price = 0.0

        if item.variant_id:
            variant = db.query(ProductVariant).filter(
                ProductVariant.id == item.variant_id,
                ProductVariant.product_id == prod.id
            ).first()
            if variant:
                variant_price = variant.additional_price

        # Unit price with variant added automatically
        effective_unit_price = base_unit_price + variant_price
        line_subtotal = round(effective_unit_price * item.quantity, 2)
        
        tax_r = item.tax_rate if item.tax_rate is not None else 18.0
        line_tax = round(line_subtotal * (tax_r / 100.0), 2)
        line_total = line_subtotal + line_tax

        total_subtotal += line_subtotal
        total_tax += line_tax
        total_items_qty += item.quantity

        line_rec = SubscriptionLine(
            subscription_id=subscription.id,
            product_id=prod.id,
            variant_id=item.variant_id,
            description=f"{prod.name}{' - ' + variant.attribute_value if item.variant_id and variant else ''}",
            quantity=item.quantity,
            unit_price=base_unit_price,
            variant_price=variant_price,
            tax_rate=tax_r,
            tax_amount=line_tax,
            discount_amount=0.0,
            subtotal=line_subtotal,
            total_amount=line_total
        )
        db.add(line_rec)

    # Validate Plan minimum quantity
    if total_items_qty < plan.min_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum required quantity for {plan.name} is {plan.min_quantity}."
        )

    # Apply Discount Calculation
    calculated_discount = 0.0
    if discount_obj:
        if total_subtotal >= discount_obj.min_purchase_amount and total_items_qty >= discount_obj.min_quantity:
            if discount_obj.discount_type == DiscountType.PERCENTAGE:
                calculated_discount = round(total_subtotal * (discount_obj.value / 100.0), 2)
            else:
                calculated_discount = min(discount_obj.value, total_subtotal)
            
            discount_obj.times_used += 1

    grand_total = max(0.0, total_subtotal - calculated_discount + total_tax)

    subscription.subtotal = total_subtotal
    subscription.discount_amount = calculated_discount
    subscription.tax_amount = total_tax
    subscription.total_amount = round(grand_total, 2)

    db.commit()
    db.refresh(subscription)
    return build_subscription_response(subscription)

@router.get("/{sub_id}", response_model=SubscriptionResponse)
def get_subscription(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    require_customer_owner_or_staff(sub.customer_id, current_user, db)
    return build_subscription_response(sub)

@router.put("/{sub_id}/status")
def update_subscription_status(
    sub_id: int,
    new_status: SubscriptionStatus,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    require_customer_owner_or_staff(sub.customer_id, current_user, db)

    # Role specific status constraints
    if current_user.role.value == "customer":
        # Customers can request cancellation or close if plan allows early closure
        if new_status == SubscriptionStatus.CLOSED:
            if not sub.plan.allow_early_closure:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Early closure is not allowed for this plan.")
            sub.status = SubscriptionStatus.CLOSED
            sub.cancellation_reason = reason or "Closed by customer"
        elif new_status == SubscriptionStatus.PAUSED:
            if not sub.plan.allow_pause:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pausing is not allowed for this plan.")
            sub.status = SubscriptionStatus.PAUSED
        elif new_status == SubscriptionStatus.ACTIVE and sub.status == SubscriptionStatus.PAUSED:
            if not sub.plan.allow_resume:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resuming is not allowed for this plan.")
            sub.status = SubscriptionStatus.ACTIVE
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customers can only pause, resume or close their subscriptions.")
    else:
        # Staff and Admin have full lifecycle control
        sub.status = new_status
        if reason:
            sub.cancellation_reason = reason

    db.commit()
    db.refresh(sub)
    return {"message": f"Subscription status updated to {new_status.value}", "status": sub.status.value}

@router.post("/{sub_id}/renew")
def renew_subscription(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    require_customer_owner_or_staff(sub.customer_id, current_user, db)

    if not sub.plan.allow_renewal:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Renewal is disabled for this plan.")

    # Extend expiry date from current expiry or today (whichever is later)
    base_date = max(sub.expiry_date, date.today())
    interval_days = sub.plan.billing_interval_days or 30
    sub.expiry_date = base_date + timedelta(days=interval_days)
    sub.next_billing_date = sub.expiry_date
    sub.status = SubscriptionStatus.ACTIVE
    sub.cancellation_reason = None

    db.commit()
    return {
        "message": "Subscription renewed successfully",
        "new_expiry_date": sub.expiry_date,
        "status": sub.status.value
    }
