from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash, validate_password_strength,
    create_access_token, create_password_reset_token, verify_password_reset_token
)
from app.models.models import User, Customer, UserRole
from app.schemas.schemas import (
    UserLogin, UserRegister, UserCreateStaff,
    PasswordResetRequest, PasswordResetConfirm, Token, UserResponse
)
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    # 1. Validate password rules: >8 chars, 1 uppercase, 1 lowercase, 1 special char
    is_valid, err_msg = validate_password_strength(user_in.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    # 2. Unique email
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # 3. Create user
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=UserRole.CUSTOMER,
        is_active=True
    )
    db.add(user)
    db.flush()

    # 4. Create customer record linked to user
    customer = Customer(
        user_id=user.id,
        name=user_in.full_name,
        email=user_in.email,
        phone=user_in.phone,
        company=user_in.company,
        address=user_in.address
    )
    db.add(customer)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=user.id, role=user.role.value)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "customer_id": customer.id
    }

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is deactivated.")

    customer_id = user.customer_profile.id if user.customer_profile else None

    access_token = create_access_token(subject=user.id, role=user.role.value)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "customer_id": customer_id
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    customer_id = current_user.customer_profile.id if current_user.customer_profile else None
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "customer_id": customer_id
    }

@router.post("/create-staff", response_model=UserResponse)
def create_staff(
    staff_in: UserCreateStaff,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Only Admin can create Staff accounts"""
    is_valid, err_msg = validate_password_strength(staff_in.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    existing_user = db.query(User).filter(User.email == staff_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    user = User(
        email=staff_in.email,
        hashed_password=get_password_hash(staff_in.password),
        full_name=staff_in.full_name,
        role=staff_in.role if staff_in.role in [UserRole.STAFF, UserRole.ADMIN] else UserRole.STAFF,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "customer_id": None
    }

@router.post("/password-reset-request")
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Avoid user enumeration in public responses
        return {"message": "If the account exists, a secure reset token has been generated."}
    
    reset_token = create_password_reset_token(user.email)
    # In a full deployment, this token is emailed. For hackathon/demo inspection, return token in response & log
    return {
        "message": "Password reset token generated successfully.",
        "reset_token": reset_token
    }

@router.post("/password-reset-confirm")
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    email = verify_password_reset_token(payload.token)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")

    is_valid, err_msg = validate_password_strength(payload.new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()

    return {"message": "Password updated successfully. You can now login with your new credentials."}
