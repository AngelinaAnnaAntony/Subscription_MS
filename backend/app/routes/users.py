from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models.user import User
from app.utils.response import success_response, error_response, paginate_query
from app.utils.decorators import role_required, get_current_user

users_bp = Blueprint('users', __name__)


@users_bp.route('/', methods=['GET'])
@jwt_required()
@role_required('admin')
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    role = request.args.get('role')
    search = request.args.get('search', '')

    query = User.query
    if role:
        query = query.filter_by(role=role)
    if search:
        query = query.filter(
            db.or_(
                User.email.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%'),
            )
        )
    query = query.order_by(User.created_at.desc())
    items, pagination = paginate_query(query, page, per_page)
    return success_response([u.to_dict() for u in items], pagination=pagination)


@users_bp.route('/', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_user():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    role = data.get('role', 'staff')

    if not all([email, password, first_name, last_name]):
        return error_response('email, password, first_name, last_name are required', 400)

    if role not in ('admin', 'staff', 'customer'):
        return error_response('Role must be admin, staff, or customer', 400)

    if User.query.filter_by(email=email).first():
        return error_response('Email already registered', 409)

    valid, msg = User.validate_password(password)
    if not valid:
        return error_response(msg, 400)

    try:
        user = User(email=email, first_name=first_name, last_name=last_name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return success_response(user.to_dict(), 'User created', 201)
    except Exception:
        db.session.rollback()
        return error_response('Failed to create user', 500)


@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
@role_required('admin')
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return success_response(user.to_dict())


@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@role_required('admin')
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    if 'first_name' in data:
        user.first_name = data['first_name'].strip()
    if 'last_name' in data:
        user.last_name = data['last_name'].strip()
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
    if 'role' in data and data['role'] in ('admin', 'staff', 'customer'):
        user.role = data['role']

    try:
        db.session.commit()
        return success_response(user.to_dict(), 'User updated')
    except Exception:
        db.session.rollback()
        return error_response('Update failed', 500)


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@role_required('admin')
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    current = get_current_user()
    if current and current.id == user_id:
        return error_response('Cannot deactivate your own account', 400)
    user.is_active = False
    db.session.commit()
    return success_response(message='User deactivated')
