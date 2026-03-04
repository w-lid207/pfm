"""
Modèle Alerte système
"""
from datetime import datetime
from niveau1.src.database import db


class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    type_alerte = db.Column(db.String(50), nullable=False)  # panne|remplissage|retard|securite
    titre = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)
    niveau = db.Column(db.String(20), default='info')  # info|warning|danger
    entite_type = db.Column(db.String(50), nullable=True)   # camion|point|tournee
    entite_id = db.Column(db.Integer, nullable=True)
    lue = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'type_alerte': self.type_alerte,
            'titre': self.titre,
            'message': self.message,
            'niveau': self.niveau,
            'entite_type': self.entite_type,
            'entite_id': self.entite_id,
            'lue': self.lue,
            'created_at': self.created_at.isoformat(),
        }
