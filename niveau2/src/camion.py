"""
Modèle Camion de collecte
"""
from datetime import datetime
from niveau1.src.database import db


class Camion(db.Model):
    __tablename__ = 'camions'

    id = db.Column(db.Integer, primary_key=True)
    immatriculation = db.Column(db.String(20), unique=True, nullable=False)
    modele = db.Column(db.String(100), nullable=True)
    capacite_m3 = db.Column(db.Float, default=10.0)
    statut = db.Column(db.String(20), default='disponible')  # disponible|en_tournee|panne|maintenance
    latitude = db.Column(db.Float, nullable=True)    # position GPS simulée
    longitude = db.Column(db.Float, nullable=True)
    km_total = db.Column(db.Float, default=0.0)
    actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    tournees = db.relationship('Tournee', backref='camion', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'immatriculation': self.immatriculation,
            'modele': self.modele,
            'capacite_m3': self.capacite_m3,
            'statut': self.statut,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'km_total': self.km_total,
            'actif': self.actif,
        }

    def __repr__(self):
        return f'<Camion {self.immatriculation}>'
