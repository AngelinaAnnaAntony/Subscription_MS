import json
from datetime import datetime, timezone
from app.extensions import db


class Subscription(db.Model):
    __tablename__ = 'subscriptions'

    STATUSES = ['draft', 'quotation', 'confirmed', 'active', 'paused', 'closed']
    PAYMENT_TERMS = ['immediate', 'net_15', 'net_30', 'net_45']

    id = db.Column(db.Integer, primary_key=True)
    subscription_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotations.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')
    start_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    next_billing_date = db.Column(db.Date, nullable=True)
    payment_terms = db.Column(db.String(20), nullable=False, default='immediate')
    total_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    status_history = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    lines = db.relationship('SubscriptionLine', backref='subscription', lazy='dynamic',
                            cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='subscription', lazy='dynamic')

    def add_status_change(self, status, note=''):
        history = self.status_history or []
        history.append({
            'status': status,
            'changed_at': datetime.now(timezone.utc).isoformat(),
            'note': note,
        })
        self.status_history = history

    def to_dict(self, include_lines=False):
        data = {
            'id': self.id,
            'subscription_number': self.subscription_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer.full_name if self.customer else None,
            'customer_email': self.customer.email if self.customer else None,
            'plan_id': self.plan_id,
            'plan_name': self.plan.name if self.plan else None,
            'billing_frequency': self.plan.billing_frequency if self.plan else None,
            'quotation_id': self.quotation_id,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'next_billing_date': self.next_billing_date.isoformat() if self.next_billing_date else None,
            'payment_terms': self.payment_terms,
            'total_amount': str(self.total_amount),
            'status_history': self.status_history or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_lines:
            data['lines'] = [l.to_dict() for l in self.lines.all()]
        return data


class SubscriptionLine(db.Model):
    __tablename__ = 'subscription_lines'

    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id'), nullable=True)
    tax_id = db.Column(db.Integer, db.ForeignKey('tax_rules.id'), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    line_total = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    product = db.relationship('Product', backref='subscription_lines')
    variant = db.relationship('ProductVariant', backref='subscription_lines')
    tax = db.relationship('TaxRule', backref='subscription_lines')

    def to_dict(self):
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'variant_id': self.variant_id,
            'variant_name': self.variant.name if self.variant else None,
            'tax_id': self.tax_id,
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': str(self.unit_price),
            'tax_rate': str(self.tax_rate),
            'discount_amount': str(self.discount_amount),
            'line_total': str(self.line_total),
        }
