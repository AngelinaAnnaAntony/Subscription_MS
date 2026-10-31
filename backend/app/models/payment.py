from datetime import datetime, timezone
from app.extensions import db


class Payment(db.Model):
    __tablename__ = 'payments'

    METHODS = ['cash', 'bank_transfer', 'card', 'cheque', 'upi', 'other']

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    payment_method = db.Column(db.String(30), nullable=False, default='bank_transfer')
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'invoice_number': self.invoice.invoice_number if self.invoice else None,
            'subscription_number': (
                self.invoice.subscription.subscription_number
                if self.invoice and self.invoice.subscription else None
            ),
            'customer_name': (
                self.invoice.customer.full_name
                if self.invoice and self.invoice.customer else None
            ),
            'recorded_by': self.recorded_by,
            'recorder_name': self.recorder.full_name if self.recorder else None,
            'payment_method': self.payment_method,
            'amount': str(self.amount),
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
