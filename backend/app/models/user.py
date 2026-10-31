import re
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='customer')  # admin, staff, customer
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    reset_token = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    subscriptions = db.relationship(
        'Subscription', foreign_keys='Subscription.customer_id',
        backref='customer', lazy='dynamic'
    )
    invoices = db.relationship(
        'Invoice', foreign_keys='Invoice.customer_id',
        backref='customer', lazy='dynamic'
    )
    quotations = db.relationship(
        'Quotation', foreign_keys='Quotation.customer_id',
        backref='customer', lazy='dynamic'
    )
    payments_recorded = db.relationship(
        'Payment', foreign_keys='Payment.recorded_by',
        backref='recorder', lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def validate_password(password):
        if len(password) <= 8:
            return False, 'Password must be more than 8 characters'
        if not re.search(r'[A-Z]', password):
            return False, 'Password must contain at least one uppercase letter'
        if not re.search(r'[a-z]', password):
            return False, 'Password must contain at least one lowercase letter'
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-]', password):
            return False, 'Password must contain at least one special character'
        return True, None

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': f'{self.first_name} {self.last_name}',
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
