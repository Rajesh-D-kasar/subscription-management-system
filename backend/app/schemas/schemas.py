from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models.models import (
    UserRole, PlanRecurrence, SubscriptionStatus,
    InvoiceStatus, DiscountType, PaymentMethod
)

# --- Authentication & User Schemas ---

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    email: str
    full_name: str
    role: UserRole
    customer_id: Optional[int] = None

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None

class UserCreateStaff(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.STAFF

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    customer_id: Optional[int] = None

    class Config:
        from_attributes = True

# --- Customer Schemas ---

class CustomerBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = "India"
    tax_number: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    tax_number: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Product & Variant Schemas ---

class ProductVariantBase(BaseModel):
    attribute_name: str
    attribute_value: str
    additional_price: float = 0.0
    sku: Optional[str] = None
    is_active: bool = True

class ProductVariantCreate(ProductVariantBase):
    pass

class ProductVariantResponse(ProductVariantBase):
    id: int
    product_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    product_type: str = "Service"
    sales_price: float
    cost_price: float = 0.0
    notes: Optional[str] = None
    is_active: bool = True

class ProductCreate(ProductBase):
    variants: Optional[List[ProductVariantCreate]] = []

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    product_type: Optional[str] = None
    sales_price: Optional[float] = None
    cost_price: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    variants: List[ProductVariantResponse] = []

    class Config:
        from_attributes = True

# --- Plan Schemas ---

class PlanBase(BaseModel):
    name: str
    code: str
    recurrence: PlanRecurrence = PlanRecurrence.MONTHLY
    price: float = 0.0
    billing_interval_days: int = 30
    min_quantity: int = 1
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    auto_close: bool = False
    auto_close_days: int = 15
    allow_pause: bool = True
    allow_resume: bool = True
    allow_early_closure: bool = True
    allow_renewal: bool = True
    description: Optional[str] = None
    is_active: bool = True

class PlanCreate(PlanBase):
    pass

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    recurrence: Optional[PlanRecurrence] = None
    price: Optional[float] = None
    billing_interval_days: Optional[int] = None
    min_quantity: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    auto_close: Optional[bool] = None
    auto_close_days: Optional[int] = None
    allow_pause: Optional[bool] = None
    allow_resume: Optional[bool] = None
    allow_early_closure: Optional[bool] = None
    allow_renewal: Optional[bool] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class PlanResponse(PlanBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Tax Rule Schemas ---

class TaxRuleBase(BaseModel):
    name: str
    rate: float
    is_active: bool = True

class TaxRuleCreate(TaxRuleBase):
    pass

class TaxRuleResponse(TaxRuleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Discount Schemas ---

class DiscountBase(BaseModel):
    code: str
    description: Optional[str] = None
    discount_type: DiscountType = DiscountType.PERCENTAGE
    value: float
    min_purchase_amount: float = 0.0
    min_quantity: int = 1
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    max_usage_limit: Optional[int] = None
    product_id: Optional[int] = None
    is_subscription_wide: bool = True
    is_active: bool = True

class DiscountCreate(DiscountBase):
    pass

class DiscountUpdate(BaseModel):
    description: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    value: Optional[float] = None
    min_purchase_amount: Optional[float] = None
    min_quantity: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    max_usage_limit: Optional[int] = None
    product_id: Optional[int] = None
    is_subscription_wide: Optional[bool] = None
    is_active: Optional[bool] = None

class DiscountResponse(DiscountBase):
    id: int
    times_used: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Quotation Template Schemas ---

class QuotationTemplateBase(BaseModel):
    name: str
    validity_days: int = 30
    terms_and_conditions: Optional[str] = None
    payment_terms: str = "Immediate Payment"
    is_active: bool = True

class QuotationTemplateCreate(QuotationTemplateBase):
    pass

class QuotationTemplateResponse(QuotationTemplateBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Subscription Schemas ---

class SubscriptionLineCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = 1
    unit_price: Optional[float] = None  # If none, derived from product
    tax_rate: Optional[float] = 18.0    # Default tax rate

class SubscriptionLineResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    variant_id: Optional[int] = None
    variant_name: Optional[str] = None
    description: Optional[str] = None
    quantity: int
    unit_price: float
    variant_price: float
    tax_rate: float
    tax_amount: float
    discount_amount: float
    subtotal: float
    total_amount: float

    class Config:
        from_attributes = True

class SubscriptionCreate(BaseModel):
    customer_id: int
    plan_id: int
    start_date: Optional[date] = None  # defaults to today
    payment_terms: str = "Immediate Payment"
    notes: Optional[str] = None
    discount_code: Optional[str] = None
    lines: List[SubscriptionLineCreate]
    template_id: Optional[int] = None

class SubscriptionUpdate(BaseModel):
    plan_id: Optional[int] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[SubscriptionStatus] = None
    cancellation_reason: Optional[str] = None

class SubscriptionResponse(BaseModel):
    id: int
    subscription_number: str
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    plan_id: int
    plan_name: Optional[str] = None
    plan_recurrence: Optional[str] = None
    status: SubscriptionStatus
    start_date: date
    expiry_date: date
    next_billing_date: Optional[date] = None
    payment_terms: str
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    subtotal: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    created_at: datetime
    lines: List[SubscriptionLineResponse] = []

    class Config:
        from_attributes = True

# --- Invoice Schemas ---

class InvoiceLineResponse(BaseModel):
    id: int
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    variant_id: Optional[int] = None
    description: str
    quantity: int
    unit_price: float
    tax_rate: float
    tax_amount: float
    discount_amount: float
    subtotal: float
    total_amount: float

    class Config:
        from_attributes = True

class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    subscription_id: Optional[int] = None
    subscription_number: Optional[str] = None
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    status: InvoiceStatus
    invoice_date: date
    due_date: date
    billing_period_start: Optional[date] = None
    billing_period_end: Optional[date] = None
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    amount_paid: float
    amount_due: float
    notes: Optional[str] = None
    created_at: datetime
    lines: List[InvoiceLineResponse] = []

    class Config:
        from_attributes = True

class InvoiceGenerateRequest(BaseModel):
    subscription_id: int

# --- Payment Schemas ---

class PaymentCreate(BaseModel):
    invoice_id: int
    payment_method: PaymentMethod = PaymentMethod.UPI
    amount: float
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    id: int
    payment_reference: str
    invoice_id: int
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    payment_method: PaymentMethod
    amount: float
    payment_date: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True

# --- Dashboard & Analytics Schemas ---

class DashboardStats(BaseModel):
    total_customers: int
    active_subscriptions: int
    total_products: int
    total_plans: int
    total_invoices: int
    total_revenue_collected: float
    outstanding_payments: float
    overdue_invoices_count: int

class MonthlyRevenueItem(BaseModel):
    month: str
    revenue: float

class StatusBreakdownItem(BaseModel):
    status: str
    count: int

class DashboardAnalyticsResponse(BaseModel):
    stats: DashboardStats
    monthly_revenue: List[MonthlyRevenueItem]
    subscription_status_breakdown: List[StatusBreakdownItem]
    recent_transactions: List[PaymentResponse]
    overdue_invoices: List[InvoiceResponse]
