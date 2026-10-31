import secrets
from datetime import datetime, timezone

from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required

from app.extensions import db
from app.models.user import User
from app.utils.response import success_response, error_response
from app.utils.decorators import get_current_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return error_response('Request body required', 400)

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()

    if not all([email, password, first_name, last_name]):
        return error_response('email, password, first_name and last_name are required', 400)

    if User.query.filter_by(email=email).first():
        return error_response('Email address already registered', 409, 'EMAIL_EXISTS')

    valid, msg = User.validate_password(password)
    if not valid:
        return error_response(msg, 400, 'INVALID_PASSWORD')

    try:
        user = User(email=email, first_name=first_name, last_name=last_name, role='customer')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        return success_response({'user': user.to_dict(), 'access_token': token},
                                'Registration successful', 201)
    except Exception as e:
        db.session.rollback()
        return error_response('Registration failed', 500)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return error_response('Request body required', 400)

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return error_response('Email and password are required', 400)

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return error_response('Invalid email or password', 401, 'INVALID_CREDENTIALS')

    if not user.is_active:
        return error_response('Account is deactivated. Contact administrator.', 403, 'ACCOUNT_INACTIVE')

    token = create_access_token(identity=str(user.id))
    return success_response({'user': user.to_dict(), 'access_token': token}, 'Login successful')


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return success_response(message='Logged out successfully')


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user = get_current_user()
    if not user:
        return error_response('User not found', 404)
    return success_response(user.to_dict())


@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_me():
    user = get_current_user()
    if not user:
        return error_response('User not found', 404)

    data = request.get_json() or {}
    if 'first_name' in data:
        user.first_name = data['first_name'].strip()
    if 'last_name' in data:
        user.last_name = data['last_name'].strip()
    if 'password' in data and data['password']:
        valid, msg = User.validate_password(data['password'])
        if not valid:
            return error_response(msg, 400)
        user.set_password(data['password'])

    try:
        db.session.commit()
        return success_response(user.to_dict(), 'Profile updated')
    except Exception:
        db.session.rollback()
        return error_response('Update failed', 500)


@auth_bp.route('/password-reset-request', methods=['POST'])
def password_reset_request():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    if not email:
        return error_response('Email is required', 400)

    user = User.query.filter_by(email=email).first()
    if not user:
        # Return generic response to avoid user enumeration
        return success_response(
            {'message': 'If that email exists, a reset link has been sent'},
            'Reset request processed'
        )

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    db.session.commit()

    # In production: send email. For demo: return token in response.
    return success_response(
        {
            'reset_token': token,
            'note': 'DEMO MODE: In production this would be emailed. Use this token with /password-reset.'
        },
        'Password reset token generated'
    )


@auth_bp.route('/password-reset', methods=['POST'])
def password_reset():
    data = request.get_json() or {}
    token = data.get('token', '')
    new_password = data.get('new_password', '')

    if not token or not new_password:
        return error_response('Token and new_password are required', 400)

    user = User.query.filter_by(reset_token=token).first()
    if not user:
        return error_response('Invalid or expired reset token', 400, 'INVALID_TOKEN')

    valid, msg = User.validate_password(new_password)
    if not valid:
        return error_response(msg, 400)

    user.set_password(new_password)
    user.reset_token = None
    db.session.commit()
    return success_response(message='Password reset successfully')
