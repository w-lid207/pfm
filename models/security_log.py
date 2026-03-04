"""
Modèle Log de Sécurité (historique des connexions)
"""
from datetime import datetime
from niveau1.src.database import db


class SecurityLog(db.Model):
    __tablename__ = 'security_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)  # login|logout|failed_login|register
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    details = db.Column(db.Text, nullable=True)
    succes = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else 'inconnu',
            'action': self.action,
            'ip_address': self.ip_address,
            'succes': self.succes,
            'created_at': self.created_at.isoformat(),
        }
