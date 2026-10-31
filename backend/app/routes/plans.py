from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.plan import SubscriptionPlan
from app.utils.response import success_response, error_response, paginate_query
from app.utils.decorators import role_required

plans_bp = Blueprint('plans', __name__)


@plans_bp.route('/', methods=['GET'])
@jwt_required()
def list_plans():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    is_active = request.args.get('is_active', 'true')

    query = SubscriptionPlan.query
    if is_active.lower() == 'true':
        query = query.filter_by(is_active=True)
    query = query.order_by(SubscriptionPlan.name)
    items, pagination = paginate_query(query, page, per_page)
    return success_response([p.to_dict() for p in items], pagination=pagination)


@plans_bp.route('/', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_plan():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    frequency = data.get('billing_frequency', 'monthly')

    if not name:
        return error_response('Plan name is required', 400)
    if frequency not in SubscriptionPlan.FREQUENCIES:
        return error_response(
            f'billing_frequency must be one of: {", ".join(SubscriptionPlan.FREQUENCIES)}', 400
        )
    renewal = data.get('renewal_behaviour', 'auto_renew')
    if renewal not in SubscriptionPlan.RENEWAL_BEHAVIOURS:
        return error_response(
            f'renewal_behaviour must be one of: {", ".join(SubscriptionPlan.RENEWAL_BEHAVIOURS)}', 400
        )

    try:
        plan = SubscriptionPlan(
            name=name,
            description=data.get('description'),
            price=data.get('price', 0),
            billing_frequency=frequency,
            min_quantity=data.get('min_quantity', 1),
            available_from=data.get('available_from'),
            available_until=data.get('available_until'),
            renewal_behaviour=renewal,
            pause_allowed=data.get('pause_allowed', True),
            early_close_allowed=data.get('early_close_allowed', True),
            auto_close=data.get('auto_close', False),
        )
        db.session.add(plan)
        db.session.commit()
        return success_response(plan.to_dict(), 'Plan created', 201)
    except Exception:
        db.session.rollback()
        return error_response('Failed to create plan', 500)


@plans_bp.route('/<int:plan_id>', methods=['GET'])
@jwt_required()
def get_plan(plan_id):
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    return success_response(plan.to_dict())


@plans_bp.route('/<int:plan_id>', methods=['PUT'])
@jwt_required()
@role_required('admin')
def update_plan(plan_id):
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    data = request.get_json() or {}

    allowed = ['name', 'description', 'price', 'billing_frequency', 'min_quantity',
               'available_from', 'available_until', 'renewal_behaviour',
               'pause_allowed', 'early_close_allowed', 'auto_close', 'is_active']
    for field in allowed:
        if field in data:
            setattr(plan, field, data[field])

    try:
        db.session.commit()
        return success_response(plan.to_dict(), 'Plan updated')
    except Exception:
        db.session.rollback()
        return error_response('Update failed', 500)


@plans_bp.route('/<int:plan_id>', methods=['DELETE'])
@jwt_required()
@role_required('admin')
def deactivate_plan(plan_id):
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    plan.is_active = False
    db.session.commit()
    return success_response(message='Plan deactivated')
