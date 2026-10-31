from datetime import datetime, timezone
from app.extensions import db


class TaxRule(db.Model):
    __tablename__ = 'tax_rules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rate = db.Column(db.Numeric(5, 2), nullable=False)  # e.g. 18.00 = 18%
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rate': str(self.rate),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
