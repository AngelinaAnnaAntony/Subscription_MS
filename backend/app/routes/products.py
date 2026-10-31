from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.product import Product, ProductVariant
from app.utils.response import success_response, error_response, paginate_query
from app.utils.decorators import role_required

products_bp = Blueprint('products', __name__)


@products_bp.route('/', methods=['GET'])
@jwt_required()
def list_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    is_active = request.args.get('is_active')

    query = Product.query
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if is_active is not None:
        query = query.filter_by(is_active=(is_active.lower() == 'true'))
    else:
        query = query.filter_by(is_active=True)

    query = query.order_by(Product.name)
    items, pagination = paginate_query(query, page, per_page)
    return success_response([p.to_dict() for p in items], pagination=pagination)


@products_bp.route('/', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_product():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    product_type = data.get('product_type', 'service')
    sales_price = data.get('sales_price')

    if not name:
        return error_response('Product name is required', 400)
    if sales_price is None:
        return error_response('sales_price is required', 400)
    if product_type not in ('service', 'physical', 'digital'):
        return error_response('product_type must be service, physical, or digital', 400)

    try:
        product = Product(
            name=name,
            product_type=product_type,
            sales_price=sales_price,
            cost_price=data.get('cost_price', 0),
            notes=data.get('notes'),
        )
        db.session.add(product)
        db.session.commit()
        return success_response(product.to_dict(include_variants=True), 'Product created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response('Failed to create product', 500)


@products_bp.route('/<int:product_id>', methods=['GET'])
@jwt_required()
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return success_response(product.to_dict(include_variants=True))


@products_bp.route('/<int:product_id>', methods=['PUT'])
@jwt_required()
@role_required('admin')
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json() or {}

    if 'name' in data:
        product.name = data['name'].strip()
    if 'product_type' in data:
        if data['product_type'] not in ('service', 'physical', 'digital'):
            return error_response('Invalid product_type', 400)
        product.product_type = data['product_type']
    if 'sales_price' in data:
        product.sales_price = data['sales_price']
    if 'cost_price' in data:
        product.cost_price = data['cost_price']
    if 'notes' in data:
        product.notes = data['notes']

    try:
        db.session.commit()
        return success_response(product.to_dict(include_variants=True), 'Product updated')
    except Exception:
        db.session.rollback()
        return error_response('Update failed', 500)


@products_bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
@role_required('admin')
def deactivate_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_active = False
    db.session.commit()
    return success_response(message='Product deactivated')


@products_bp.route('/<int:product_id>/variants', methods=['GET'])
@jwt_required()
def list_variants(product_id):
    product = Product.query.get_or_404(product_id)
    variants = product.variants.filter_by(is_active=True).all()
    return success_response([v.to_dict() for v in variants])


@products_bp.route('/<int:product_id>/variants', methods=['POST'])
@jwt_required()
@role_required('admin')
def add_variant(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return error_response('Variant name is required', 400)

    try:
        variant = ProductVariant(
            product_id=product_id,
            name=name,
            price_adjustment=data.get('price_adjustment', 0),
        )
        db.session.add(variant)
        db.session.commit()
        return success_response(variant.to_dict(), 'Variant added', 201)
    except Exception:
        db.session.rollback()
        return error_response('Failed to add variant', 500)


@products_bp.route('/<int:product_id>/variants/<int:variant_id>', methods=['PUT'])
@jwt_required()
@role_required('admin')
def update_variant(product_id, variant_id):
    variant = ProductVariant.query.filter_by(id=variant_id, product_id=product_id).first_or_404()
    data = request.get_json() or {}
    if 'name' in data:
        variant.name = data['name'].strip()
    if 'price_adjustment' in data:
        variant.price_adjustment = data['price_adjustment']
    db.session.commit()
    return success_response(variant.to_dict(), 'Variant updated')


@products_bp.route('/<int:product_id>/variants/<int:variant_id>', methods=['DELETE'])
@jwt_required()
@role_required('admin')
def remove_variant(product_id, variant_id):
    variant = ProductVariant.query.filter_by(id=variant_id, product_id=product_id).first_or_404()
    variant.is_active = False
    db.session.commit()
    return success_response(message='Variant removed')
