from flask import jsonify


def success_response(data=None, message='Success', status_code=200, pagination=None):
    response = {'success': True, 'data': data, 'message': message}
    if pagination:
        response['pagination'] = pagination
    return jsonify(response), status_code


def error_response(error='An error occurred', status_code=400, code=None):
    response = {'success': False, 'error': error}
    if code:
        response['code'] = code
    return jsonify(response), status_code


def paginate_query(query, page, per_page):
    """Helper to paginate a SQLAlchemy query and return (items, pagination_dict)."""
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    pagination = {
        'page': paginated.page,
        'per_page': paginated.per_page,
        'total': paginated.total,
        'pages': paginated.pages,
        'has_next': paginated.has_next,
        'has_prev': paginated.has_prev,
    }
    return paginated.items, pagination
