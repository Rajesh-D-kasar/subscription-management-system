from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Plan, User
from app.schemas.schemas import PlanCreate, PlanUpdate, PlanResponse
from app.api.deps import require_admin, get_current_user

router = APIRouter(prefix="/plans", tags=["Plans"])

@router.get("", response_model=List[PlanResponse])
def get_plans(
    active_only: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Plan)
    if active_only:
        query = query.filter(Plan.is_active == True)
    return query.order_by(Plan.price.asc()).offset(skip).limit(limit).all()

@router.post("", response_model=PlanResponse)
def create_plan(
    plan_in: PlanCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(Plan).filter(Plan.code == plan_in.code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan code already exists.")

    # Calculate default interval days if not provided
    interval = plan_in.billing_interval_days
    if not interval:
        if plan_in.recurrence == "daily":
            interval = 1
        elif plan_in.recurrence == "weekly":
            interval = 7
        elif plan_in.recurrence == "monthly":
            interval = 30
        elif plan_in.recurrence == "yearly":
            interval = 365

    plan = Plan(**plan_in.model_dump())
    plan.billing_interval_days = interval
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan

@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan

@router.put("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: int,
    plan_in: PlanUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    for field, value in plan_in.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)

    db.commit()
    db.refresh(plan)
    return plan

@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    if plan.subscriptions:
        plan.is_active = False
        db.commit()
        return {"message": "Plan has active or historical subscriptions; it was marked inactive."}

    db.delete(plan)
    db.commit()
    return {"message": "Plan deleted successfully."}
