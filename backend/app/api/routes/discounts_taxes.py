from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Discount, TaxRule, QuotationTemplate, User, DiscountType
from app.schemas.schemas import (
    DiscountCreate, DiscountUpdate, DiscountResponse,
    TaxRuleCreate, TaxRuleResponse,
    QuotationTemplateCreate, QuotationTemplateResponse
)
from app.api.deps import require_admin, get_current_user

router = APIRouter(tags=["Discounts, Taxes & Templates"])

# --- Discounts ---

@router.get("/discounts", response_model=List[DiscountResponse])
def get_discounts(
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Discount)
    if active_only:
        query = query.filter(Discount.is_active == True)
    return query.order_by(Discount.created_at.desc()).all()

@router.post("/discounts", response_model=DiscountResponse)
def create_discount(
    discount_in: DiscountCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(Discount).filter(Discount.code == discount_in.code.upper()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discount code already exists.")

    data = discount_in.model_dump()
    data["code"] = data["code"].upper()
    discount = Discount(**data)
    db.add(discount)
    db.commit()
    db.refresh(discount)
    return discount

@router.put("/discounts/{discount_id}", response_model=DiscountResponse)
def update_discount(
    discount_id: int,
    discount_in: DiscountUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    discount = db.query(Discount).filter(Discount.id == discount_id).first()
    if not discount:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found")

    for field, value in discount_in.model_dump(exclude_unset=True).items():
        setattr(discount, field, value)

    db.commit()
    db.refresh(discount)
    return discount

@router.delete("/discounts/{discount_id}")
def delete_discount(
    discount_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    discount = db.query(Discount).filter(Discount.id == discount_id).first()
    if not discount:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found")
    
    discount.is_active = False
    db.commit()
    return {"message": "Discount deactivated successfully."}

# --- Tax Rules ---

@router.get("/taxes", response_model=List[TaxRuleResponse])
def get_taxes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(TaxRule).filter(TaxRule.is_active == True).all()

@router.post("/taxes", response_model=TaxRuleResponse)
def create_tax_rule(
    tax_in: TaxRuleCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    tax = TaxRule(**tax_in.model_dump())
    db.add(tax)
    db.commit()
    db.refresh(tax)
    return tax

# --- Quotation Templates ---

@router.get("/quotation-templates", response_model=List[QuotationTemplateResponse])
def get_quotation_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(QuotationTemplate).filter(QuotationTemplate.is_active == True).all()

@router.post("/quotation-templates", response_model=QuotationTemplateResponse)
def create_quotation_template(
    template_in: QuotationTemplateCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    template = QuotationTemplate(**template_in.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template
