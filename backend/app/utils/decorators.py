from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from app.models.user import User


def role_required(*roles):
    """Decorator: require user to have one of the given roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(int(user_id))
            if not user or not user.is_active:
                return jsonify({'success': False, 'error': 'User not found or inactive'}), 401
            if user.role not in roles:
                return jsonify({
                    'success': False,
                    'error': f'Access denied. Required roles: {", ".join(roles)}'
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user():
    """Retrieve the current authenticated user from JWT identity."""
    user_id = get_jwt_identity()
    if user_id is None:
        return None
    return User.query.get(int(user_id))
