from datetime import date, timedelta
from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.quotation import Quotation, QuotationLine, QuotationTemplate
from app.models.subscription import Subscription, SubscriptionLine
from app.utils.response import success_response, error_response, paginate_query
from app.utils.decorators import role_required, get_current_user

quotations_bp = Blueprint('quotations', __name__)


def _generate_quotation_number():
    year = date.today().year
    count = Quotation.query.filter(
        db.extract('year', Quotation.created_at) == year
    ).count() + 1
    return f'QUO-{year}-{count:04d}'


def _generate_subscription_number():
    year = date.today().year
    count = Subscription.query.filter(
        db.extract('year', Subscription.created_at) == year
    ).count() + 1
    return f'SUB-{year}-{count:04d}'


@quotations_bp.route('/', methods=['GET'])
@jwt_required()
@role_required('admin', 'staff')
def list_quotations():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')

    query = Quotation.query
    if status:
        query = query.filter_by(status=status)
    query = query.order_by(Quotation.created_at.desc())
    items, pagination = paginate_query(query, page, per_page)
    return success_response([q.to_dict() for q in items], pagination=pagination)


@quotations_bp.route('/', methods=['POST'])
@jwt_required()
@role_required('admin', 'staff')
def create_quotation():
    data = request.get_json() or {}
    current_user = get_current_user()
    customer_id = data.get('customer_id')
    if not customer_id:
        return error_response('customer_id is required', 400)

    validity_days = data.get('validity_days', 30)
    valid_until = date.today() + timedelta(days=validity_days)

    try:
        quotation = Quotation(
            quotation_number=_generate_quotation_number(),
            customer_id=customer_id,
            created_by=current_user.id,
            template_id=data.get('template_id'),
            status='draft',
            validity_days=validity_days,
            valid_until=valid_until,
            notes=data.get('notes'),
        )
        db.session.add(quotation)
        db.session.flush()

        total = 0
        for line_data in data.get('lines', []):
            qty = line_data.get('quantity', 1)
            unit_price = float(line_data.get('unit_price', 0))
            tax_rate = float(line_data.get('tax_rate', 0))
            discount = float(line_data.get('discount_amount', 0))
            line_sub = qty * unit_price
            line_tax = line_sub * tax_rate / 100
            line_total = line_sub + line_tax - discount

            line = QuotationLine(
                quotation_id=quotation.id,
                plan_id=line_data.get('plan_id'),
                product_id=line_data.get('product_id'),
                variant_id=line_data.get('variant_id'),
                description=line_data.get('description'),
                quantity=qty,
                unit_price=unit_price,
                discount_amount=discount,
                tax_amount=line_tax,
                line_total=line_total,
            )
            db.session.add(line)
            total += line_total

        quotation.total_amount = total
        db.session.commit()
        return success_response(quotation.to_dict(include_lines=True), 'Quotation created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Failed to create quotation: {str(e)}', 500)


@quotations_bp.route('/<int:quotation_id>', methods=['GET'])
@jwt_required()
@role_required('admin', 'staff')
def get_quotation(quotation_id):
    q = Quotation.query.get_or_404(quotation_id)
    return success_response(q.to_dict(include_lines=True))


@quotations_bp.route('/<int:quotation_id>', methods=['PUT'])
@jwt_required()
@role_required('admin', 'staff')
def update_quotation(quotation_id):
    q = Quotation.query.get_or_404(quotation_id)
    if q.status not in ('draft', 'sent'):
        return error_response('Cannot edit a quotation that is not in draft or sent status', 400)

    data = request.get_json() or {}
    for field in ['notes', 'validity_days']:
        if field in data:
            setattr(q, field, data[field])
    if 'validity_days' in data:
        q.valid_until = date.today() + timedelta(days=data['validity_days'])

    db.session.commit()
    return success_response(q.to_dict(), 'Quotation updated')


@quotations_bp.route('/<int:quotation_id>/confirm', methods=['POST'])
@jwt_required()
@role_required('admin', 'staff')
def confirm_quotation(quotation_id):
    q = Quotation.query.get_or_404(quotation_id)
    if q.is_expired and q.status not in ('accepted',):
        return error_response('Quotation has expired. Use /override-expiry first.', 400)
    q.status = 'accepted'
    db.session.commit()
    return success_response(q.to_dict(), 'Quotation accepted')


@quotations_bp.route('/<int:quotation_id>/convert', methods=['POST'])
@jwt_required()
@role_required('admin', 'staff')
def convert_quotation(quotation_id):
    q = Quotation.query.get_or_404(quotation_id)
    if q.status != 'accepted':
        return error_response('Quotation must be accepted before converting', 400)

    data = request.get_json() or {}
    plan_id = data.get('plan_id')
    if not plan_id:
        # Try to get plan from first quotation line
        first_line = q.lines.filter(QuotationLine.plan_id.isnot(None)).first()
        if first_line:
            plan_id = first_line.plan_id
    if not plan_id:
        return error_response('plan_id is required to convert quotation', 400)

    try:
        start_date_str = data.get('start_date', str(date.today()))
        start_date = date.fromisoformat(start_date_str)

        sub = Subscription(
            subscription_number=_generate_subscription_number(),
            customer_id=q.customer_id,
            plan_id=plan_id,
            quotation_id=q.id,
            status='confirmed',
            start_date=start_date,
            next_billing_date=start_date,
            payment_terms=data.get('payment_terms', 'immediate'),
            total_amount=q.total_amount,
            status_history=[],
        )
        sub.add_status_change('confirmed', 'Converted from quotation')
        db.session.add(sub)
        db.session.flush()

        for ql in q.lines.all():
            sl = SubscriptionLine(
                subscription_id=sub.id,
                product_id=ql.product_id,
                variant_id=ql.variant_id,
                description=ql.description,
                quantity=ql.quantity,
                unit_price=ql.unit_price,
                tax_rate=0,
                discount_amount=ql.discount_amount,
                line_total=ql.line_total,
            )
            db.session.add(sl)

        q.status = 'converted'
        db.session.commit()
        return success_response(sub.to_dict(include_lines=True), 'Subscription created from quotation', 201)
    except Exception as e:
        db.session.rollback()
        return error_response(f'Conversion failed: {str(e)}', 500)


@quotations_bp.route('/<int:quotation_id>/override-expiry', methods=['POST'])
@jwt_required()
@role_required('admin')
def override_expiry(quotation_id):
    q = Quotation.query.get_or_404(quotation_id)
    data = request.get_json() or {}
    extra_days = data.get('extra_days', 30)
    q.valid_until = date.today() + timedelta(days=extra_days)
    if q.status == 'expired':
        q.status = 'draft'
    db.session.commit()
    return success_response(q.to_dict(), 'Expiry extended')


@quotations_bp.route('/templates', methods=['GET'])
@jwt_required()
@role_required('admin', 'staff')
def list_templates():
    templates = QuotationTemplate.query.order_by(QuotationTemplate.name).all()
    return success_response([t.to_dict() for t in templates])


@quotations_bp.route('/templates', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_template():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return error_response('Template name is required', 400)
    try:
        tmpl = QuotationTemplate(
            name=name,
            description=data.get('description'),
            plan_id=data.get('plan_id'),
        )
        db.session.add(tmpl)
        db.session.commit()
        return success_response(tmpl.to_dict(), 'Template created', 201)
    except Exception:
        db.session.rollback()
        return error_response('Failed to create template', 500)
