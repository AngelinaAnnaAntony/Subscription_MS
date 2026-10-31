from datetime import datetime, timezone
from app.extensions import db


class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'

    FREQUENCIES = ['daily', 'weekly', 'monthly', 'yearly']
    RENEWAL_BEHAVIOURS = ['auto_renew', 'manual_renew', 'expire']

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    billing_frequency = db.Column(db.String(20), nullable=False, default='monthly')
    min_quantity = db.Column(db.Integer, nullable=False, default=1)
    available_from = db.Column(db.Date, nullable=True)
    available_until = db.Column(db.Date, nullable=True)
    renewal_behaviour = db.Column(db.String(30), nullable=False, default='auto_renew')
    pause_allowed = db.Column(db.Boolean, default=True, nullable=False)
    early_close_allowed = db.Column(db.Boolean, default=True, nullable=False)
    auto_close = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    subscriptions = db.relationship('Subscription', backref='plan', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': str(self.price),
            'billing_frequency': self.billing_frequency,
            'min_quantity': self.min_quantity,
            'available_from': self.available_from.isoformat() if self.available_from else None,
            'available_until': self.available_until.isoformat() if self.available_until else None,
            'renewal_behaviour': self.renewal_behaviour,
            'pause_allowed': self.pause_allowed,
            'early_close_allowed': self.early_close_allowed,
            'auto_close': self.auto_close,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
