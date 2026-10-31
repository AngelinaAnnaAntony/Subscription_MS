from datetime import date
from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.subscription import Subscription, SubscriptionLine
from app.models.plan import SubscriptionPlan
from app.utils.response import success_response, error_response, paginate_query
from app.utils.decorators import role_required, get_current_user

subscriptions_bp = Blueprint('subscriptions', __name__)


def _generate_subscription_number():
    year = date.today().year
    count = Subscription.query.filter(
        db.extract('year', Subscription.created_at) == year
    ).count() + 1
    return f'SUB-{year}-{count:04d}'


@subscriptions_bp.route('/', methods=['GET'])
@jwt_required()
@role_required('admin', 'staff')
def list_subscriptions():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    customer_id = request.args.get('customer_id', type=int)
    plan_id = request.args.get('plan_id', type=int)

    query = Subscription.query
    if status:
        query = query.filter_by(status=status)
    if customer_id:
        query = query.filter_by(customer_id=customer_id)
    if plan_id:
        query = query.filter_by(plan_id=plan_id)
    query = query.order_by(Subscription.created_at.desc())
    items, pagination = paginate_query(query, page, per_page)
    return success_response([s.to_dict() for s in items], pagination=pagination)


@subscriptions_bp.route('/my', methods=['GET'])
@jwt_required()
@role_required('customer')
def my_subscriptions():
    current_user = get_current_user()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    query = Subscription.query.filter_by(customer_id=current_user.id).order_by(
        Subscription.created_at.desc()
    )
    items, pagination = paginate_query(query, page, per_page)
    return success_response([s.to_dict() for s in items], pagination=pagination)


@subscriptions_bp.route('/', methods=['POST'])
@jwt_required()
@role_required('admin', 'staff')
def create_subscription():
    data = request.get_json() or {}
    customer_id = data.get('customer_id')
    plan_id = data.get('plan_id')

    if not customer_id or not plan_id:
        return error_response('customer_id and plan_id are required', 400)

    plan = SubscriptionPlan.query.get(plan_id)
    if not plan:
        return error_response('Plan not found', 404)

    start_str = data.get('start_date', str(date.today()))
    try:
        start_date = date.fromisoformat(start_str)
    except ValueError:
        return error_response('Invalid start_date format. Use YYYY-MM-DD', 400)

    try:
        sub = Subscription(
            subscription_number=_generate_subscription_number(),
            customer_id=customer_id,
            plan_id=plan_id,
            quotation_id=data.get('quotation_id'),
            status='draft',
            start_date=start_date,
            next_billing_date=start_date,
            expiry_date=data.get('expiry_date'),
            payment_terms=data.get('payment_terms', 'immediate'),
            status_history=[],
        )
        sub.add_status_change('draft', 'Subscription created')
        db.session.add(sub)
        db.session.flush()

        total = 0
        for line_data in data.get('lines', []):
            from decimal import Decimal
            qty = line_data.get('quantity', 1)
            unit_price = Decimal(str(line_data.get('unit_price', plan.price)))
            tax_rate = Decimal(str(line_data.get('tax_rate', 0)))
            discount = Decimal(str(line_data.get('discount_amount', 0)))
            line_sub = Decimal(str(qty)) * unit_price
            line_tax = (line_sub * tax_rate / Decimal('100')).quantize(Decimal('0.01'))
            line_total = line_sub + line_tax - discount

            sl = SubscriptionLine(
                subscription_id=sub.id,
                product_id=line_data.get('product_id'),
                variant_id=line_data.get('variant_id'),
                tax_id=line_data.get('tax_id'),
                description=line_data.get('description', ''),
                quantity=qty,
                unit_price=unit_price,
                tax_rate=tax_rate,
                discount_amount=discount,
                line_total=line_total,
            )
            db.session.add(sl)
            total += float(line_total)

        if not data.get('lines'):
            # Auto-create a line from the plan price
            sl = SubscriptionLine(
                subscription_id=sub.id,
                description=plan.name,
                quantity=1,
                unit_price=plan.price,
                tax_rate=0,
                discount_amount=0,
                line_total=plan.price,
            )
            db.session.add(sl)
            total = float(plan.price)

        sub.total_amount = total
        db.session.commit()
        return success_response(sub.to_dict(include_lines=True), 'Subscription created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Failed to create subscription: {str(e)}', 500)


@subscriptions_bp.route('/<int:sub_id>', methods=['GET'])
@jwt_required()
def get_subscription(sub_id):
    current_user = get_current_user()
    sub = Subscription.query.get_or_404(sub_id)
    # Customer isolation
    if current_user.role == 'customer' and sub.customer_id != current_user.id:
        return error_response('Access denied', 403)
    return success_response(sub.to_dict(include_lines=True))


@subscriptions_bp.route('/<int:sub_id>', methods=['PUT'])
@jwt_required()
@role_required('admin', 'staff')
def update_subscription(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    data = request.get_json() or {}
    for field in ['payment_terms', 'expiry_date', 'notes']:
        if field in data:
            setattr(sub, field, data[field])
    try:
        db.session.commit()
        return success_response(sub.to_dict(), 'Subscription updated')
    except Exception:
        db.session.rollback()
        return error_response('Update failed', 500)


@subscriptions_bp.route('/<int:sub_id>/activate', methods=['POST'])
@jwt_required()
@role_required('admin', 'staff')
def activate_subscription(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    if sub.status not in ('draft', 'confirmed'):
        return error_response(f'Cannot activate from status: {sub.status}', 400)
    sub.status = 'active'
    if not sub.next_billing_date:
        sub.next_billing_date = sub.start_date or date.today()
    sub.add_status_change('active', 'Subscription activated')
    db.session.commit()
    return success_response(sub.to_dict(), 'Subscription activated')


@subscriptions_bp.route('/<int:sub_id>/pause', methods=['POST'])
@jwt_required()
@role_required('admin', 'staff')
def pause_subscription(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    if sub.status != 'active':
        return error_response('Only active subscriptions can be paused', 400)
    if not sub.plan.pause_allowed:
        return error_response('This plan does not allow pausing', 400)
    data = request.get_json() or {}
    sub.status = 'paused'
    sub.add_status_change('paused', data.get('reason', 'Paused by staff'))
    db.session.commit()
    return success_response(sub.to_dict(), 'Subscription paused')


@subscriptions_bp.route('/<int:sub_id>/resume', methods=['POST'])
@jwt_required()
@role_required('admin', 'staff')
def resume_subscription(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    if sub.status != 'paused':
        return error_response('Only paused subscriptions can be resumed', 400)
    sub.status = 'active'
    sub.add_status_change('active', 'Resumed')
    db.session.commit()
    return success_response(sub.to_dict(), 'Subscription resumed')


@subscriptions_bp.route('/<int:sub_id>/close', methods=['POST'])
@jwt_required()
@role_required('admin', 'staff')
def close_subscription(sub_id):
    sub = Subscription.query.get_or_404(sub_id)
    if sub.status == 'closed':
        return error_response('Subscription is already closed', 400)
    if sub.status == 'active' and not sub.plan.early_close_allowed:
        return error_response('This plan does not allow early closure', 400)
    data = request.get_json() or {}
    sub.status = 'closed'
    sub.add_status_change('closed', data.get('reason', 'Closed by staff'))
    db.session.commit()
    return success_response(sub.to_dict(), 'Subscription closed')


@subscriptions_bp.route('/<int:sub_id>/invoices', methods=['GET'])
@jwt_required()
def subscription_invoices(sub_id):
    current_user = get_current_user()
    sub = Subscription.query.get_or_404(sub_id)
    if current_user.role == 'customer' and sub.customer_id != current_user.id:
        return error_response('Access denied', 403)
    from app.models.invoice import Invoice
    invoices = Invoice.query.filter_by(subscription_id=sub_id).order_by(
        Invoice.created_at.desc()
    ).all()
    return success_response([i.to_dict() for i in invoices])
