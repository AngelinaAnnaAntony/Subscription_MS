from datetime import datetime, timezone
from app.extensions import db


class Invoice(db.Model):
    __tablename__ = 'invoices'
    __table_args__ = (
        db.UniqueConstraint('subscription_id', 'billing_period_start', 'billing_period_end',
                            name='uq_invoice_subscription_period'),
    )

    STATUSES = ['draft', 'confirmed', 'paid', 'cancelled']

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    billing_period_start = db.Column(db.Date, nullable=False)
    billing_period_end = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='draft')
    due_date = db.Column(db.Date, nullable=True)
    subtotal = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    amount_paid = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    amount_outstanding = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    lines = db.relationship('InvoiceLine', backref='invoice', lazy='dynamic',
                            cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy='dynamic')

    def to_dict(self, include_lines=False):
        data = {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'subscription_id': self.subscription_id,
            'subscription_number': self.subscription.subscription_number if self.subscription else None,
            'customer_id': self.customer_id,
            'customer_name': self.customer.full_name if self.customer else None,
            'customer_email': self.customer.email if self.customer else None,
            'billing_period_start': self.billing_period_start.isoformat() if self.billing_period_start else None,
            'billing_period_end': self.billing_period_end.isoformat() if self.billing_period_end else None,
            'status': self.status,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'subtotal': str(self.subtotal),
            'tax_amount': str(self.tax_amount),
            'discount_amount': str(self.discount_amount),
            'total_amount': str(self.total_amount),
            'amount_paid': str(self.amount_paid),
            'amount_outstanding': str(self.amount_outstanding),
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
        }
        if include_lines:
            data['lines'] = [l.to_dict() for l in self.lines.all()]
        return data


class InvoiceLine(db.Model):
    __tablename__ = 'invoice_lines'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id'), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    line_total = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    product = db.relationship('Product', backref='invoice_lines')
    variant = db.relationship('ProductVariant', backref='invoice_lines')

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'variant_id': self.variant_id,
            'variant_name': self.variant.name if self.variant else None,
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': str(self.unit_price),
            'tax_rate': str(self.tax_rate),
            'tax_amount': str(self.tax_amount),
            'discount_amount': str(self.discount_amount),
            'line_total': str(self.line_total),
        }
