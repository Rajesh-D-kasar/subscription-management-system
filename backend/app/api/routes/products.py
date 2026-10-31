from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.models.models import Product, ProductVariant, User
from app.schemas.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductVariantCreate, ProductVariantResponse
)
from app.api.deps import require_admin, get_current_user

router = APIRouter(prefix="/products", tags=["Products & Variants"])

@router.get("", response_model=List[ProductResponse])
def get_products(
    search: Optional[str] = None,
    product_type: Optional[str] = None,
    active_only: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if active_only:
        query = query.filter(Product.is_active == True)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if product_type:
        query = query.filter(Product.product_type == product_type)
    return query.order_by(Product.name.asc()).offset(skip).limit(limit).all()

@router.post("", response_model=ProductResponse)
def create_product(
    product_in: ProductCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    product = Product(
        name=product_in.name,
        product_type=product_in.product_type,
        sales_price=product_in.sales_price,
        cost_price=product_in.cost_price,
        notes=product_in.notes,
        is_active=product_in.is_active
    )
    db.add(product)
    db.flush()

    if product_in.variants:
        for v in product_in.variants:
            variant = ProductVariant(
                product_id=product.id,
                attribute_name=v.attribute_name,
                attribute_value=v.attribute_value,
                additional_price=v.additional_price,
                sku=v.sku,
                is_active=v.is_active
            )
            db.add(variant)

    db.commit()
    db.refresh(product)
    return product

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    for field, value in product_in.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    # Check if tied to existing subscription lines
    if product.subscription_lines:
        # Soft-delete to preserve billing and historical integrity
        product.is_active = False
        db.commit()
        return {"message": "Product is referenced in subscriptions and has been deactivated instead of deleted."}
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully."}

# Variant Endpoints
@router.post("/{product_id}/variants", response_model=ProductVariantResponse)
def add_product_variant(
    product_id: int,
    variant_in: ProductVariantCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    variant = ProductVariant(
        product_id=product_id,
        attribute_name=variant_in.attribute_name,
        attribute_value=variant_in.attribute_value,
        additional_price=variant_in.additional_price,
        sku=variant_in.sku,
        is_active=variant_in.is_active
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant

@router.delete("/{product_id}/variants/{variant_id}")
def delete_product_variant(
    product_id: int,
    variant_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id,
        ProductVariant.product_id == product_id
    ).first()
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found")

    db.delete(variant)
    db.commit()
    return {"message": "Product variant deleted successfully."}
