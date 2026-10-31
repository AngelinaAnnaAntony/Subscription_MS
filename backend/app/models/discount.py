from datetime import datetime, date, timezone
from app.extensions import db


class DiscountRule(db.Model):
    __tablename__ = 'discount_rules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    discount_type = db.Column(db.String(20), nullable=False, default='percentage')  # fixed, percentage
    value = db.Column(db.Numeric(15, 2), nullable=False)
    min_purchase = db.Column(db.Numeric(15, 2), nullable=True)
    min_quantity = db.Column(db.Integer, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    usage_limit = db.Column(db.Integer, nullable=True)
    usage_count = db.Column(db.Integer, nullable=False, default=0)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    subscription_wide = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    product = db.relationship('Product', backref='discounts', foreign_keys=[product_id])

    @property
    def is_valid(self):
        today = date.today()
        if not self.is_active:
            return False
        if self.start_date and today < self.start_date:
            return False
        if self.end_date and today > self.end_date:
            return False
        if self.usage_limit is not None and self.usage_count >= self.usage_limit:
            return False
        return True

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'discount_type': self.discount_type,
            'value': str(self.value),
            'min_purchase': str(self.min_purchase) if self.min_purchase is not None else None,
            'min_quantity': self.min_quantity,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'usage_limit': self.usage_limit,
            'usage_count': self.usage_count,
            'product_id': self.product_id,
            'subscription_wide': self.subscription_wide,
            'is_active': self.is_active,
            'is_valid': self.is_valid,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
