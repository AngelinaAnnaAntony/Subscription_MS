from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db

def decimal_to_float(val):
    if val is None:
        return 0.0
    return float(val)

def generate_quotation_number():
    from app.models.quotation import Quotation
    year = datetime.now(timezone.utc).year
    prefix = f"QUO-{year}-"
    last_item = Quotation.query.filter(Quotation.quotation_number.like(f"{prefix}%")).order_by(Quotation.id.desc()).first()
    if last_item and last_item.quotation_number:
        try:
            seq = int(last_item.quotation_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = Quotation.query.filter(Quotation.quotation_number.like(f"{prefix}%")).count() + 1
    else:
        seq = 1
    candidate = f"{prefix}{seq:04d}"
    while Quotation.query.filter_by(quotation_number=candidate).first():
        seq += 1
        candidate = f"{prefix}{seq:04d}"
    return candidate

def generate_subscription_number():
    from app.models.subscription import Subscription
    year = datetime.now(timezone.utc).year
    prefix = f"SUB-{year}-"
    last_item = Subscription.query.filter(Subscription.subscription_number.like(f"{prefix}%")).order_by(Subscription.id.desc()).first()
    if last_item and last_item.subscription_number:
        try:
            seq = int(last_item.subscription_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = Subscription.query.filter(Subscription.subscription_number.like(f"{prefix}%")).count() + 1
    else:
        seq = 1
    candidate = f"{prefix}{seq:04d}"
    while Subscription.query.filter_by(subscription_number=candidate).first():
        seq += 1
        candidate = f"{prefix}{seq:04d}"
    return candidate

def generate_invoice_number():
    from app.models.invoice import Invoice
    year = datetime.now(timezone.utc).year
    prefix = f"INV-{year}-"
    last_item = Invoice.query.filter(Invoice.invoice_number.like(f"{prefix}%")).order_by(Invoice.id.desc()).first()
    if last_item and last_item.invoice_number:
        try:
            seq = int(last_item.invoice_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            seq = Invoice.query.filter(Invoice.invoice_number.like(f"{prefix}%")).count() + 1
    else:
        seq = 1
    candidate = f"{prefix}{seq:04d}"
    while Invoice.query.filter_by(invoice_number=candidate).first():
        seq += 1
        candidate = f"{prefix}{seq:04d}"
    return candidate

def paginate_query(query, page=1, per_page=20):
    try:
        page = max(1, int(page))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = max(1, min(100, int(per_page)))
    except (ValueError, TypeError):
        per_page = 20

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination_info = {
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }
    return pagination.items, pagination_info
