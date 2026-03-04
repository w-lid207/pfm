"""
Modèle Zone géographique de collecte
"""
from datetime import datetime
from niveau1.src.database import db


class Zone(db.Model):
    __tablename__ = 'zones'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    priorite = db.Column(db.Integer, default=1)       # 1=faible, 2=normale, 3=haute
    population = db.Column(db.Integer, default=0)
    superficie_km2 = db.Column(db.Float, default=0.0)
    frequence_semaine = db.Column(db.Integer, default=3)  # collectes/semaine
    couleur = db.Column(db.String(7), default='#3388ff')  # couleur sur la carte
    actif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    points = db.relationship('PointCollecte', backref='zone', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'code': self.code,
            'priorite': self.priorite,
            'population': self.population,
            'superficie_km2': self.superficie_km2,
            'frequence_semaine': self.frequence_semaine,
            'couleur': self.couleur,
            'actif': self.actif,
            'nb_points': len(self.points),
        }

    def __repr__(self):
        return f'<Zone {self.nom}>'
