import json
from datetime import datetime, date, timezone
from app.extensions import db


class QuotationTemplate(db.Model):
    __tablename__ = 'quotation_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    plan = db.relationship('SubscriptionPlan', backref='templates')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'plan_id': self.plan_id,
            'plan_name': self.plan.name if self.plan else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Quotation(db.Model):
    __tablename__ = 'quotations'

    STATUSES = ['draft', 'sent', 'accepted', 'rejected', 'expired', 'converted']

    id = db.Column(db.Integer, primary_key=True)
    quotation_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('quotation_templates.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')
    validity_days = db.Column(db.Integer, nullable=False, default=30)
    valid_until = db.Column(db.Date, nullable=True)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    creator = db.relationship('User', foreign_keys=[created_by], backref='created_quotations')
    template = db.relationship('QuotationTemplate', backref='quotations')
    lines = db.relationship('QuotationLine', backref='quotation', lazy='dynamic',
                            cascade='all, delete-orphan')

    @property
    def is_expired(self):
        if self.valid_until:
            return date.today() > self.valid_until
        return False

    def to_dict(self, include_lines=False):
        data = {
            'id': self.id,
            'quotation_number': self.quotation_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer.full_name if self.customer else None,
            'customer_email': self.customer.email if self.customer else None,
            'created_by': self.created_by,
            'creator_name': self.creator.full_name if self.creator else None,
            'template_id': self.template_id,
            'status': self.status,
            'validity_days': self.validity_days,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'is_expired': self.is_expired,
            'total_amount': str(self.total_amount),
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_lines:
            data['lines'] = [l.to_dict() for l in self.lines.all()]
        return data


class QuotationLine(db.Model):
    __tablename__ = 'quotation_lines'

    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotations.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variants.id'), nullable=True)
    description = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    line_total = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    plan = db.relationship('SubscriptionPlan', backref='quotation_lines')
    product = db.relationship('Product', backref='quotation_lines')
    variant = db.relationship('ProductVariant', backref='quotation_lines')

    def to_dict(self):
        return {
            'id': self.id,
            'quotation_id': self.quotation_id,
            'plan_id': self.plan_id,
            'plan_name': self.plan.name if self.plan else None,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'variant_id': self.variant_id,
            'variant_name': self.variant.name if self.variant else None,
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': str(self.unit_price),
            'discount_amount': str(self.discount_amount),
            'tax_amount': str(self.tax_amount),
            'line_total': str(self.line_total),
        }
