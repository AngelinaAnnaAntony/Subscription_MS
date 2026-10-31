from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    product_type = db.Column(db.String(50), nullable=False, default='service')  # service, physical, digital
    sales_price = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    cost_price = db.Column(db.Numeric(15, 2), nullable=True, default=0)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    variants = db.relationship('ProductVariant', backref='product', lazy='dynamic',
                               cascade='all, delete-orphan')

    def to_dict(self, include_variants=False):
        data = {
            'id': self.id,
            'name': self.name,
            'product_type': self.product_type,
            'sales_price': str(self.sales_price),
            'cost_price': str(self.cost_price) if self.cost_price is not None else '0.00',
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'variants_count': self.variants.filter_by(is_active=True).count(),
        }
        if include_variants:
            data['variants'] = [v.to_dict() for v in self.variants.filter_by(is_active=True).all()]
        return data


class ProductVariant(db.Model):
    __tablename__ = 'product_variants'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    price_adjustment = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @property
    def final_price(self):
        base = self.product.sales_price if self.product else Decimal('0')
        return base + self.price_adjustment

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'name': self.name,
            'price_adjustment': str(self.price_adjustment),
            'final_price': str(self.final_price),
            'is_active': self.is_active,
        }
