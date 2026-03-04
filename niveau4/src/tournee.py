"""
Modèles Tournée et TournéePoint (séquence de collecte)
"""
from datetime import datetime
from niveau1.src.database import db


class Tournee(db.Model):
    __tablename__ = 'tournees'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    camion_id = db.Column(db.Integer, db.ForeignKey('camions.id'), nullable=True)
    date_tournee = db.Column(db.Date, nullable=False)
    heure_depart = db.Column(db.String(5), default='06:00')
    statut = db.Column(db.String(20), default='planifiee')  # planifiee|en_cours|terminee|annulee
    distance_km = db.Column(db.Float, default=0.0)
    duree_min = db.Column(db.Float, default=0.0)
    co2_kg = db.Column(db.Float, default=0.0)
    cout_mad = db.Column(db.Float, default=0.0)
    nb_points = db.Column(db.Integer, default=0)
    geojson_trajet = db.Column(db.Text, nullable=True)  # polyline encodée
    optimisee = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    points_tournee = db.relationship('TourneePoint', backref='tournee',
                                      lazy=True, order_by='TourneePoint.ordre')

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'camion_id': self.camion_id,
            'camion': self.camion.immatriculation if self.camion else None,
            'date_tournee': self.date_tournee.isoformat() if self.date_tournee else None,
            'heure_depart': self.heure_depart,
            'statut': self.statut,
            'distance_km': round(self.distance_km, 2),
            'duree_min': round(self.duree_min, 1),
            'co2_kg': round(self.co2_kg, 3),
            'cout_mad': round(self.cout_mad, 2),
            'nb_points': self.nb_points,
            'optimisee': self.optimisee,
            'points': [tp.to_dict() for tp in self.points_tournee],
        }

    def __repr__(self):
        return f'<Tournee {self.nom} - {self.date_tournee}>'


class TourneePoint(db.Model):
    """Point visité dans une tournée avec son ordre de passage"""
    __tablename__ = 'tournee_points'

    id = db.Column(db.Integer, primary_key=True)
    tournee_id = db.Column(db.Integer, db.ForeignKey('tournees.id'), nullable=False)
    point_id = db.Column(db.Integer, db.ForeignKey('points_collecte.id'), nullable=False)
    ordre = db.Column(db.Integer, nullable=False)
    heure_arrivee = db.Column(db.String(5), nullable=True)
    collecte_effectuee = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'point_id': self.point_id,
            'ordre': self.ordre,
            'heure_arrivee': self.heure_arrivee,
            'collecte_effectuee': self.collecte_effectuee,
            'point': self.point.to_dict() if self.point else None,
        }
