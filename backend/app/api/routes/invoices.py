from typing import List, Optional
from datetime import date, timedelta
import uuid
import io
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.models.models import (
    Invoice, InvoiceLine, Subscription, Customer,
    Payment, User, InvoiceStatus, SubscriptionStatus
)
from app.schemas.schemas import InvoiceResponse, InvoiceGenerateRequest
from app.api.deps import (
    get_current_user, require_staff_or_admin,
    require_customer_owner_or_staff
)
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

router = APIRouter(prefix="/invoices", tags=["Invoices"])

def build_invoice_response(inv: Invoice) -> dict:
    lines = []
    for l in inv.lines:
        lines.append({
            "id": l.id,
            "product_id": l.product_id,
            "product_name": l.product.name if l.product else None,
            "variant_id": l.variant_id,
            "description": l.description,
            "quantity": l.quantity,
            "unit_price": l.unit_price,
            "tax_rate": l.tax_rate,
            "tax_amount": l.tax_amount,
            "discount_amount": l.discount_amount,
            "subtotal": l.subtotal,
            "total_amount": l.total_amount
        })

    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "subscription_id": inv.subscription_id,
        "subscription_number": inv.subscription.subscription_number if inv.subscription else None,
        "customer_id": inv.customer_id,
        "customer_name": inv.customer.name if inv.customer else "Unknown",
        "customer_email": inv.customer.email if inv.customer else "",
        "status": inv.status,
        "invoice_date": inv.invoice_date,
        "due_date": inv.due_date,
        "billing_period_start": inv.billing_period_start,
        "billing_period_end": inv.billing_period_end,
        "subtotal": inv.subtotal,
        "discount_amount": inv.discount_amount,
        "tax_amount": inv.tax_amount,
        "total_amount": inv.total_amount,
        "amount_paid": inv.amount_paid,
        "amount_due": inv.amount_due,
        "notes": inv.notes,
        "created_at": inv.created_at,
        "lines": lines
    }

@router.get("", response_model=List[InvoiceResponse])
def get_invoices(
    customer_id: Optional[int] = None,
    status_filter: Optional[InvoiceStatus] = None,
    overdue_only: bool = False,
    outstanding_only: bool = False,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Invoice)

    if current_user.role.value == "customer":
        if not current_user.customer_profile:
            return []
        query = query.filter(Invoice.customer_id == current_user.customer_profile.id)
    elif customer_id:
        query = query.filter(Invoice.customer_id == customer_id)

    if status_filter:
        query = query.filter(Invoice.status == status_filter)

    today = date.today()
    if overdue_only:
        query = query.filter(Invoice.due_date < today, Invoice.status != InvoiceStatus.PAID, Invoice.status != InvoiceStatus.CANCELLED)

    if outstanding_only:
        query = query.filter(Invoice.amount_due > 0, Invoice.status != InvoiceStatus.CANCELLED)

    if search:
        search_fmt = f"%{search}%"
        query = query.join(Customer).filter(
            or_(
                Invoice.invoice_number.ilike(search_fmt),
                Customer.name.ilike(search_fmt),
                Customer.email.ilike(search_fmt)
            )
        )

    invoices = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    return [build_invoice_response(inv) for inv in invoices]

@router.post("/generate", response_model=InvoiceResponse)
def generate_invoice_from_subscription(
    req: InvoiceGenerateRequest,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter(Subscription.id == req.subscription_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    period_start = sub.start_date
    period_end = sub.expiry_date

    # Prevent duplicate billing for same subscription billing period
    duplicate = db.query(Invoice).filter(
        Invoice.subscription_id == sub.id,
        Invoice.billing_period_start == period_start,
        Invoice.billing_period_end == period_end,
        Invoice.status != InvoiceStatus.CANCELLED
    ).first()

    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An active invoice ({duplicate.invoice_number}) already exists for this billing period ({period_start} to {period_end})."
        )

    inv_num = f"INV-{uuid.uuid4().hex[:8].upper()}"
    inv_date = date.today()
    due_d = inv_date + timedelta(days=15)

    invoice = Invoice(
        invoice_number=inv_num,
        subscription_id=sub.id,
        customer_id=sub.customer_id,
        status=InvoiceStatus.CONFIRMED,
        invoice_date=inv_date,
        due_date=due_d,
        billing_period_start=period_start,
        billing_period_end=period_end,
        subtotal=sub.subtotal,
        discount_amount=sub.discount_amount,
        tax_amount=sub.tax_amount,
        total_amount=sub.total_amount,
        amount_paid=0.0,
        amount_due=sub.total_amount,
        notes=f"Auto-generated for subscription {sub.subscription_number} ({sub.plan.name})"
    )
    db.add(invoice)
    db.flush()

    for line in sub.lines:
        inv_line = InvoiceLine(
            invoice_id=invoice.id,
            product_id=line.product_id,
            variant_id=line.variant_id,
            description=line.description or "Subscription Item",
            quantity=line.quantity,
            unit_price=line.unit_price + line.variant_price,
            tax_rate=line.tax_rate,
            tax_amount=line.tax_amount,
            discount_amount=line.discount_amount,
            subtotal=line.subtotal,
            total_amount=line.total_amount
        )
        db.add(inv_line)

    # Activate subscription if in confirmed or quotation state
    if sub.status in [SubscriptionStatus.QUOTATION, SubscriptionStatus.CONFIRMED]:
        sub.status = SubscriptionStatus.ACTIVE

    db.commit()
    db.refresh(invoice)
    return build_invoice_response(invoice)

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    require_customer_owner_or_staff(inv.customer_id, current_user, db)
    return build_invoice_response(inv)

@router.put("/{invoice_id}/confirm")
def confirm_invoice(
    invoice_id: int,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    inv.status = InvoiceStatus.CONFIRMED
    db.commit()
    return {"message": "Invoice confirmed successfully", "status": inv.status.value}

@router.put("/{invoice_id}/cancel")
def cancel_invoice(
    invoice_id: int,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    if inv.amount_paid > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel invoice with recorded payments.")

    inv.status = InvoiceStatus.CANCELLED
    inv.amount_due = 0.0
    db.commit()
    return {"message": "Invoice cancelled successfully", "status": inv.status.value}

@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    require_customer_owner_or_staff(inv.customer_id, current_user, db)

    # Generate Professional PDF in-memory using ReportLab
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    # Header title
    title_style = ParagraphStyle(
        name="InvoiceTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=12
    )
    elements.append(Paragraph(f"INVOICE: {inv.invoice_number}", title_style))
    elements.append(Spacer(1, 10))

    # Meta Info
    subheading_style = ParagraphStyle(
        name="MetaText",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        leading=14
    )
    meta_info = f"""
    <b>Status:</b> {inv.status.value.upper()} &nbsp;&nbsp;|&nbsp;&nbsp;
    <b>Date:</b> {inv.invoice_date} &nbsp;&nbsp;|&nbsp;&nbsp;
    <b>Due Date:</b> {inv.due_date}<br/>
    <b>Billed To:</b> {inv.customer.name} ({inv.customer.email})<br/>
    <b>Company / Org:</b> {inv.customer.company or 'N/A'}<br/>
    <b>Tax / GSTIN ID:</b> {inv.customer.tax_number or 'N/A'}<br/>
    <b>Billing Period:</b> {inv.billing_period_start or 'N/A'} to {inv.billing_period_end or 'N/A'}
    """
    elements.append(Paragraph(meta_info, subheading_style))
    elements.append(Spacer(1, 20))

    # Items Table
    data = [["Item Description", "Qty", "Unit Price", "Tax", "Subtotal"]]
    for line in inv.lines:
        data.append([
            line.description,
            str(line.quantity),
            f"INR {line.unit_price:.2f}",
            f"INR {line.tax_amount:.2f}",
            f"INR {line.total_amount:.2f}"
        ])

    table = Table(data, colWidths=[240, 50, 90, 70, 90])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 15))

    # Totals Summary
    totals_data = [
        ["Subtotal:", f"INR {inv.subtotal:.2f}"],
        ["Discounts Applied:", f"- INR {inv.discount_amount:.2f}"],
        ["Taxes (GST/VAT):", f"INR {inv.tax_amount:.2f}"],
        ["Grand Total:", f"INR {inv.total_amount:.2f}"],
        ["Amount Paid:", f"INR {inv.amount_paid:.2f}"],
        ["Balance Due:", f"INR {inv.amount_due:.2f}"]
    ]
    totals_table = Table(totals_data, colWidths=[150, 100], hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 5), (-1, 5), colors.HexColor("#b91c1c") if inv.amount_due > 0 else colors.HexColor("#15803d")),
        ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)

    doc.build(elements)
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Invoice_{inv.invoice_number}.pdf"
        }
    )
