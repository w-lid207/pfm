"""
Décorateurs utilitaires : contrôle d'accès par rôle, pagination
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def admin_required(fn):
    """Middleware : accès réservé aux administrateurs"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') != 'admin':
            return jsonify({'error': 'Accès réservé aux administrateurs'}), 403
        return fn(*args, **kwargs)
    return wrapper


def operateur_or_admin(fn):
    """Middleware : accès pour opérateurs et admins"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get('role') not in ('admin', 'operateur'):
            return jsonify({'error': 'Accès non autorisé'}), 403
        return fn(*args, **kwargs)
    return wrapper


def paginate_query(query, page: int, per_page: int = 20):
    """Paginaison d'une requête SQLAlchemy"""
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    }
