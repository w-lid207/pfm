"""
Modèle Point de Collecte (poubelle / conteneur)
"""
from datetime import datetime
from niveau1.src.database import db


class PointCollecte(db.Model):
    __tablename__ = 'points_collecte'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    adresse = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    zone_id = db.Column(db.Integer, db.ForeignKey('zones.id'), nullable=True)
    type_dechet = db.Column(db.String(50), default='menager')  # menager|recyclable|encombrant
    capacite_m3 = db.Column(db.Float, default=1.0)
    taux_remplissage = db.Column(db.Float, default=0.0)  # 0.0 à 1.0
    priorite = db.Column(db.Integer, default=2)          # 1=faible, 2=normale, 3=urgente
    actif = db.Column(db.Boolean, default=True)
    derniere_collecte = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation avec les tournées
    tournee_points = db.relationship('TourneePoint', backref='point', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'adresse': self.adresse,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'zone_id': self.zone_id,
            'zone_nom': self.zone.nom if self.zone else None,
            'type_dechet': self.type_dechet,
            'capacite_m3': self.capacite_m3,
            'taux_remplissage': self.taux_remplissage,
            'priorite': self.priorite,
            'actif': self.actif,
            'derniere_collecte': self.derniere_collecte.isoformat() if self.derniere_collecte else None,
        }

    def __repr__(self):
        return f'<PointCollecte {self.nom}>'
