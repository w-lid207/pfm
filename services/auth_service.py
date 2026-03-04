"""
Service d'authentification : register, login, hachage des mots de passe
"""
from datetime import datetime
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, create_refresh_token
from models import db, User, SecurityLog

bcrypt = Bcrypt()


def hash_password(password: str) -> str:
    """Hache un mot de passe avec bcrypt"""
    return bcrypt.generate_password_hash(password).decode('utf-8')


def check_password(password: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    return bcrypt.check_password_hash(hashed, password)


def register_user(username: str, email: str, password: str, role: str = 'operateur') -> dict:
    """
    Crée un nouvel utilisateur
    Retourne dict avec user ou erreur
    """
    if User.query.filter_by(username=username).first():
        return {'error': 'Ce nom d\'utilisateur existe déjà'}
    if User.query.filter_by(email=email).first():
        return {'error': 'Cette adresse email est déjà utilisée'}

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()

    _log_action(user.id, 'register', succes=True)
    return {'user': user}


def login_user(username: str, password: str, ip: str = None, ua: str = None) -> dict:
    """
    Authentifie un utilisateur
    Retourne tokens JWT ou erreur
    """
    user = User.query.filter(
        (User.username == username) | (User.email == username)
    ).first()

    if not user or not check_password(password, user.password_hash):
        _log_action(None, 'failed_login', ip=ip, ua=ua, succes=False,
                    details=f'Tentative pour: {username}')
        return {'error': 'Identifiants incorrects'}

    if not user.is_active:
        return {'error': 'Compte désactivé'}

    # Mise à jour last_login
    user.last_login = datetime.utcnow()
    db.session.commit()

    # Génération des tokens
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={'role': user.role, 'username': user.username}
    )
    refresh_token = create_refresh_token(identity=str(user.id))

    _log_action(user.id, 'login', ip=ip, ua=ua, succes=True)

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }


def _log_action(user_id, action, ip=None, ua=None, succes=True, details=None):
    """Enregistre une action dans les logs de sécurité"""
    log = SecurityLog(
        user_id=user_id,
        action=action,
        ip_address=ip,
        user_agent=ua,
        succes=succes,
        details=details
    )
    db.session.add(log)
    db.session.commit()
