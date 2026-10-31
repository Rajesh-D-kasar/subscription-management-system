from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.models import (
    User, Customer, Product, ProductVariant, Plan,
    TaxRule, Discount, QuotationTemplate, Subscription,
    SubscriptionLine, Invoice, InvoiceLine, Payment,
    UserRole, PlanRecurrence, SubscriptionStatus,
    InvoiceStatus, DiscountType, PaymentMethod
)

def init_db(db: Session):
    Base.metadata.create_all(bind=engine)

    # 1. Check if already seeded
    if db.query(User).filter(User.email == "admin@example.com").first():
        print("Database already seeded. Skipping initial seed.")
        return

    print("Seeding initial demo data for Odoo x FLUX Hackathon...")

    # 2. Tax Rules
    gst18 = TaxRule(name="GST 18%", rate=18.0, is_active=True)
    gst5 = TaxRule(name="GST 5%", rate=5.0, is_active=True)
    vat10 = TaxRule(name="VAT 10%", rate=10.0, is_active=True)
    db.add_all([gst18, gst5, vat10])
    db.flush()

    # 3. Create Users & Customer Profiles
    admin_user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("Admin@12345"),
        full_name="Alex Administrator",
        role=UserRole.ADMIN,
        is_active=True
    )
    staff_user = User(
        email="staff@example.com",
        hashed_password=get_password_hash("Staff@12345"),
        full_name="Sarah Staff Operations",
        role=UserRole.STAFF,
        is_active=True
    )
    cust_user1 = User(
        email="customer@example.com",
        hashed_password=get_password_hash("Customer@12345"),
        full_name="Rahul Verma",
        role=UserRole.CUSTOMER,
        is_active=True
    )
    cust_user2 = User(
        email="priya@acmecorp.com",
        hashed_password=get_password_hash("Customer@12345"),
        full_name="Priya Sharma",
        role=UserRole.CUSTOMER,
        is_active=True
    )
    db.add_all([admin_user, staff_user, cust_user1, cust_user2])
    db.flush()

    # Customer Profiles
    cust1 = Customer(
        user_id=cust_user1.id,
        name="Rahul Verma",
        email="customer@example.com",
        phone="+91 98765 43210",
        company="Verma Solutions Pvt Ltd",
        address="104 Gomti Nagar",
        city="Lucknow",
        state="Uttar Pradesh",
        zip_code="226010",
        tax_number="09AAAAA0000A1Z5"
    )
    cust2 = Customer(
        user_id=cust_user2.id,
        name="Priya Sharma",
        email="priya@acmecorp.com",
        phone="+91 98111 22233",
        company="Acme Corp India",
        address="Sector 62",
        city="Noida",
        state="Uttar Pradesh",
        zip_code="201309",
        tax_number="07BBBBB1111B1Z9"
    )
    db.add_all([cust1, cust2])
    db.flush()

    # 4. Products & Variants (With Hackathon Example: Product Software, Brand Odoo +560)
    p_software = Product(
        name="Enterprise Software Suite",
        product_type="Software",
        sales_price=2000.0,
        cost_price=800.0,
        notes="All-in-one business ERP suite license",
        is_active=True
    )
    p_cloud = Product(
        name="Managed Cloud Server",
        product_type="Infrastructure",
        sales_price=1500.0,
        cost_price=600.0,
        notes="High availability container compute instance",
        is_active=True
    )
    p_support = Product(
        name="24/7 Priority Support",
        product_type="Service",
        sales_price=500.0,
        cost_price=150.0,
        notes="Dedicated Slack channel and SLA under 15 mins",
        is_active=True
    )
    db.add_all([p_software, p_cloud, p_support])
    db.flush()

    # Variants: specifically Odoo (+560) and Standard (+0)
    v_odoo = ProductVariant(
        product_id=p_software.id,
        attribute_name="Brand",
        attribute_value="Odoo",
        additional_price=560.0,
        sku="SOFT-ODOO-560",
        is_active=True
    )
    v_custom = ProductVariant(
        product_id=p_software.id,
        attribute_name="Brand",
        attribute_value="Custom ERP",
        additional_price=0.0,
        sku="SOFT-CUSTOM-00",
        is_active=True
    )
    v_cloud_8gb = ProductVariant(
        product_id=p_cloud.id,
        attribute_name="RAM",
        attribute_value="8 GB RAM",
        additional_price=400.0,
        sku="CLOUD-8G",
        is_active=True
    )
    v_cloud_16gb = ProductVariant(
        product_id=p_cloud.id,
        attribute_name="RAM",
        attribute_value="16 GB RAM",
        additional_price=900.0,
        sku="CLOUD-16G",
        is_active=True
    )
    db.add_all([v_odoo, v_custom, v_cloud_8gb, v_cloud_16gb])
    db.flush()

    # 5. Plans (Daily, Weekly, Monthly, Yearly)
    plan_daily = Plan(
        name="Daily Starter Sprint",
        code="PLAN-DAILY",
        recurrence=PlanRecurrence.DAILY,
        price=100.0,
        billing_interval_days=1,
        min_quantity=1,
        allow_pause=True,
        allow_resume=True,
        allow_early_closure=True,
        allow_renewal=True,
        description="Daily billing cycle for rapid evaluation.",
        is_active=True
    )
    plan_weekly = Plan(
        name="Weekly Team Pass",
        code="PLAN-WEEKLY",
        recurrence=PlanRecurrence.WEEKLY,
        price=600.0,
        billing_interval_days=7,
        min_quantity=1,
        allow_pause=True,
        allow_resume=True,
        allow_early_closure=True,
        allow_renewal=True,
        description="Flexible 7-day recurring cycle.",
        is_active=True
    )
    plan_monthly = Plan(
        name="Professional Monthly",
        code="PLAN-MONTHLY",
        recurrence=PlanRecurrence.MONTHLY,
        price=2200.0,
        billing_interval_days=30,
        min_quantity=1,
        allow_pause=True,
        allow_resume=True,
        allow_early_closure=True,
        allow_renewal=True,
        description="Most popular tier with monthly recurring cycle.",
        is_active=True
    )
    plan_yearly = Plan(
        name="Enterprise Annual",
        code="PLAN-YEARLY",
        recurrence=PlanRecurrence.YEARLY,
        price=22000.0,
        billing_interval_days=365,
        min_quantity=2,
        allow_pause=True,
        allow_resume=True,
        allow_early_closure=False,
        allow_renewal=True,
        description="Annual contract with bundled discount and priority dispatch.",
        is_active=True
    )
    db.add_all([plan_daily, plan_weekly, plan_monthly, plan_yearly])
    db.flush()

    # 6. Quotation Templates
    template_std = QuotationTemplate(
        name="Standard 30-Day Evaluation Quotation",
        validity_days=30,
        terms_and_conditions="Payment due upon invoice delivery. Subject to standard SLAs.",
        payment_terms="Net 15 Days",
        is_active=True
    )
    template_ent = QuotationTemplate(
        name="Enterprise High-Volume Agreement",
        validity_days=45,
        terms_and_conditions="Annual advance billing with 99.9% availability commitment.",
        payment_terms="Immediate Payment",
        is_active=True
    )
    db.add_all([template_std, template_ent])
    db.flush()

    # 7. Discounts
    disc_welcome = Discount(
        code="FLUX10",
        description="10% Hackathon Welcome Discount",
        discount_type=DiscountType.PERCENTAGE,
        value=10.0,
        min_purchase_amount=1000.0,
        min_quantity=1,
        max_usage_limit=100,
        is_subscription_wide=True,
        is_active=True
    )
    disc_flat = Discount(
        code="SAVE500",
        description="Flat ₹500 off on large deployments",
        discount_type=DiscountType.FIXED,
        value=500.0,
        min_purchase_amount=3000.0,
        min_quantity=1,
        max_usage_limit=50,
        is_subscription_wide=True,
        is_active=True
    )
    db.add_all([disc_welcome, disc_flat])
    db.flush()

    # 8. Demo Subscriptions & Invoices
    today = date.today()
    
    # Sub 1: Active Monthly Sub for Rahul with Odoo Software (+560)
    sub1 = Subscription(
        subscription_number="SUB-2026-001",
        customer_id=cust1.id,
        plan_id=plan_monthly.id,
        status=SubscriptionStatus.ACTIVE,
        start_date=today - timedelta(days=20),
        expiry_date=today + timedelta(days=10),
        next_billing_date=today + timedelta(days=10),
        payment_terms="Immediate Payment",
        notes="Demonstrates Software + Odoo Brand (+560) + 18% GST",
        subtotal=2560.0,
        tax_amount=460.8,
        discount_amount=0.0,
        total_amount=3020.8
    )
    db.add(sub1)
    db.flush()

    sub1_line = SubscriptionLine(
        subscription_id=sub1.id,
        product_id=p_software.id,
        variant_id=v_odoo.id,
        description="Enterprise Software Suite - Odoo Brand",
        quantity=1,
        unit_price=2000.0,
        variant_price=560.0,
        tax_rate=18.0,
        tax_amount=460.8,
        discount_amount=0.0,
        subtotal=2560.0,
        total_amount=3020.8
    )
    db.add(sub1_line)

    # Sub 2: Quotation status for Priya Sharma
    sub2 = Subscription(
        subscription_number="SUB-2026-002",
        customer_id=cust2.id,
        plan_id=plan_yearly.id,
        status=SubscriptionStatus.QUOTATION,
        start_date=today,
        expiry_date=today + timedelta(days=365),
        next_billing_date=today + timedelta(days=365),
        payment_terms="Net 15 Days",
        notes="Annual proposal with cloud hosting",
        subtotal=4800.0,
        tax_amount=864.0,
        discount_amount=480.0,
        total_amount=5184.0,
        discount_id=disc_welcome.id
    )
    db.add(sub2)
    db.flush()

    sub2_line1 = SubscriptionLine(
        subscription_id=sub2.id,
        product_id=p_cloud.id,
        variant_id=v_cloud_16gb.id,
        description="Managed Cloud Server - 16 GB RAM",
        quantity=2,
        unit_price=1500.0,
        variant_price=900.0,
        tax_rate=18.0,
        tax_amount=864.0,
        discount_amount=0.0,
        subtotal=4800.0,
        total_amount=5664.0
    )
    db.add(sub2_line1)

    # 9. Invoice 1: Paid for Rahul
    inv1 = Invoice(
        invoice_number="INV-2026-0001",
        subscription_id=sub1.id,
        customer_id=cust1.id,
        status=InvoiceStatus.PAID,
        invoice_date=today - timedelta(days=20),
        due_date=today - timedelta(days=5),
        billing_period_start=today - timedelta(days=20),
        billing_period_end=today + timedelta(days=10),
        subtotal=2560.0,
        discount_amount=0.0,
        tax_amount=460.8,
        total_amount=3020.8,
        amount_paid=3020.8,
        amount_due=0.0,
        notes="Auto-generated invoice, settled via UPI"
    )
    db.add(inv1)
    db.flush()

    inv1_line = InvoiceLine(
        invoice_id=inv1.id,
        product_id=p_software.id,
        variant_id=v_odoo.id,
        description="Enterprise Software Suite - Odoo Brand",
        quantity=1,
        unit_price=2560.0,
        tax_rate=18.0,
        tax_amount=460.8,
        discount_amount=0.0,
        subtotal=2560.0,
        total_amount=3020.8
    )
    db.add(inv1_line)

    pay1 = Payment(
        payment_reference="PAY-2026-TXN01",
        invoice_id=inv1.id,
        payment_method=PaymentMethod.UPI,
        amount=3020.8,
        payment_date=datetime.now(timezone.utc) - timedelta(days=19),
        notes="UPI Ref: 98721389012"
    )
    db.add(pay1)

    # Invoice 2: Overdue partial payment for Priya to demonstrate overdue and outstanding dashboard metrics!
    inv2 = Invoice(
        invoice_number="INV-2026-0002",
        subscription_id=None,
        customer_id=cust2.id,
        status=InvoiceStatus.CONFIRMED,
        invoice_date=today - timedelta(days=35),
        due_date=today - timedelta(days=5), # Overdue!
        billing_period_start=today - timedelta(days=35),
        billing_period_end=today - timedelta(days=5),
        subtotal=2000.0,
        discount_amount=0.0,
        tax_amount=360.0,
        total_amount=2360.0,
        amount_paid=1000.0,
        amount_due=1360.0,
        notes="Consulting services - partially paid, overdue"
    )
    db.add(inv2)
    db.flush()

    inv2_line = InvoiceLine(
        invoice_id=inv2.id,
        product_id=p_support.id,
        variant_id=None,
        description="24/7 Priority Support",
        quantity=4,
        unit_price=500.0,
        tax_rate=18.0,
        tax_amount=360.0,
        discount_amount=0.0,
        subtotal=2000.0,
        total_amount=2360.0
    )
    db.add(inv2_line)

    pay2 = Payment(
        payment_reference="PAY-2026-TXN02",
        invoice_id=inv2.id,
        payment_method=PaymentMethod.BANK_TRANSFER,
        amount=1000.0,
        payment_date=datetime.now(timezone.utc) - timedelta(days=25),
        notes="Initial advance transfer"
    )
    db.add(pay2)

    db.commit()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
