"""
Routes d'authentification : /api/register, /api/login, /api/logout
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token
from services.auth_service import register_user, login_user
from models import User, SecurityLog, db
from utils.decorators import admin_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/register', methods=['POST'])
def register():
    """Créer un nouvel utilisateur"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Données manquantes'}), 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'operateur')

    if not all([username, email, password]):
        return jsonify({'error': 'Champs obligatoires : username, email, password'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Mot de passe trop court (min 6 caractères)'}), 400
    if role not in ('admin', 'operateur'):
        role = 'operateur'

    result = register_user(username, email, password, role)
    if 'error' in result:
        return jsonify(result), 409

    return jsonify({
        'message': 'Compte créé avec succès',
        'user': result['user'].to_dict()
    }), 201


@auth_bp.route('/api/login', methods=['POST'])
def login():
    """Connexion et obtention du token JWT"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Données manquantes'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not all([username, password]):
        return jsonify({'error': 'Identifiants manquants'}), 400

    ip = request.remote_addr
    ua = request.headers.get('User-Agent', '')

    result = login_user(username, password, ip=ip, ua=ua)
    if 'error' in result:
        return jsonify(result), 401

    return jsonify(result), 200


@auth_bp.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Rafraîchir le token d'accès"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404

    new_token = create_access_token(
        identity=str(user.id),
        additional_claims={'role': user.role, 'username': user.username}
    )
    return jsonify({'access_token': new_token}), 200


@auth_bp.route('/api/me', methods=['GET'])
@jwt_required()
def me():
    """Informations de l'utilisateur connecté"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/api/users', methods=['GET'])
@admin_required
def list_users():
    """Liste tous les utilisateurs (admin seulement)"""
    users = User.query.all()
    return jsonify({'users': [u.to_dict() for u in users]}), 200


@auth_bp.route('/api/security-logs', methods=['GET'])
@admin_required
def security_logs():
    """Historique des connexions (admin seulement)"""
    logs = SecurityLog.query.order_by(SecurityLog.created_at.desc()).limit(100).all()
    return jsonify({'logs': [l.to_dict() for l in logs]}), 200
