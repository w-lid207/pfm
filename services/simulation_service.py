"""
Service Simulation : déplacement GPS simulé des camions en temps réel
"""
import json
import math
import random
from datetime import datetime
from models import db, Camion, Tournee, Alert


def _move_along_route(camion: Camion, tournee: Tournee) -> tuple[float, float]:
    """
    Fait avancer le camion le long de la polyligne geojson_trajet de sa tournée.
    Si aucune polyligne valide n'est disponible, retourne (None, None).
    """
    if not tournee or not tournee.geojson_trajet:
        return None, None

    try:
        coords = json.loads(tournee.geojson_trajet)
    except Exception:
        return None, None

    if not isinstance(coords, list) or not coords:
        return None, None

    # Si le camion n'a pas encore de position, on le place au début
    if camion.latitude is None or camion.longitude is None:
        return coords[0][0], coords[0][1]

    # Trouver le point de la polyligne le plus proche de la position actuelle
    cur_lat, cur_lng = camion.latitude, camion.longitude
    nearest_idx = 0
    nearest_dist = float("inf")

    for i, (lat, lng) in enumerate(coords):
        d = (lat - cur_lat) ** 2 + (lng - cur_lng) ** 2
        if d < nearest_dist:
            nearest_dist = d
            nearest_idx = i

    # Aller au point suivant (ou rester au dernier)
    next_idx = min(nearest_idx + 1, len(coords) - 1)
    return coords[next_idx][0], coords[next_idx][1]


def simulate_truck_movement(camion_id: int, tournee_id: int = None) -> dict:
    """
    Simule le déplacement d'un camion.
    - Si une tournée active avec polyligne existe, le camion suit cette route.
    - Sinon, petit déplacement aléatoire autour de sa position actuelle.
    """
    camion = Camion.query.get(camion_id)
    if not camion:
        return {'error': 'Camion introuvable'}

    # Chercher une tournée active liée à ce camion
    tournee = None
    if tournee_id:
        tournee = Tournee.query.get(tournee_id)
    if not tournee:
        # Utiliser la tournée la plus récente de ce camion, quel que soit le statut.
        tournee = (
            Tournee.query
            .filter_by(camion_id=camion_id)
            .order_by(Tournee.date_tournee.desc(), Tournee.id.desc())
            .first()
        )

    new_lat, new_lng = _move_along_route(camion, tournee)

    # Si aucune route exploitable => fallback aléatoire léger
    if new_lat is None or new_lng is None:
        delta_lat = random.uniform(-0.0005, 0.0005)
        delta_lng = random.uniform(-0.0005, 0.0005)
        new_lat = (camion.latitude or 30.4278) + delta_lat
        new_lng = (camion.longitude or -9.5981) + delta_lng

    camion.latitude = new_lat
    camion.longitude = new_lng
    db.session.commit()

    return {
        'camion_id': camion_id,
        'latitude': new_lat,
        'longitude': new_lng,
        'timestamp': datetime.utcnow().isoformat(),
        'statut': camion.statut,
    }


def get_all_trucks_positions() -> list:
    """Retourne les positions de tous les camions actifs"""
    camions = Camion.query.filter_by(actif=True).all()
    positions = []
    for c in camions:
        if c.latitude and c.longitude:
            positions.append({
                'id': c.id,
                'immatriculation': c.immatriculation,
                'latitude': c.latitude,
                'longitude': c.longitude,
                'statut': c.statut,
            })
    return positions


def simulate_breakdown(camion_id: int) -> dict:
    """Simule une panne de camion et génère une alerte"""
    camion = Camion.query.get(camion_id)
    if not camion:
        return {'error': 'Camion introuvable'}

    camion.statut = 'panne'
    db.session.commit()

    # Créer une alerte
    alert = Alert(
        type_alerte='panne',
        titre=f'Panne signalée : {camion.immatriculation}',
        message=f'Le camion {camion.immatriculation} est en panne. Replanification nécessaire.',
        niveau='danger',
        entite_type='camion',
        entite_id=camion_id,
    )
    db.session.add(alert)
    db.session.commit()

    return {
        'camion': camion.to_dict(),
        'alert': alert.to_dict(),
    }


def replan_after_breakdown(camion_id: int) -> dict:
    """
    Replanification automatique après panne :
    Redistribue les tournées non terminées du camion en panne
    """
    from models import Tournee

    # Trouver tournées actives du camion en panne
    tournees = Tournee.query.filter_by(
        camion_id=camion_id,
        statut='planifiee'
    ).all()

    if not tournees:
        return {'message': 'Aucune tournée à replanifier', 'reaffectees': 0}

    # Trouver camion de remplacement
    remplacement = Camion.query.filter_by(statut='disponible', actif=True).first()
    if not remplacement:
        return {'error': 'Aucun camion disponible pour remplacement'}

    reaffectees = 0
    for t in tournees:
        t.camion_id = remplacement.id
        t.nom = t.nom + ' [REPLANIFIE]'
        reaffectees += 1

    remplacement.statut = 'en_tournee'
    db.session.commit()

    return {
        'message': f'{reaffectees} tournée(s) réaffectée(s) au camion {remplacement.immatriculation}',
        'reaffectees': reaffectees,
        'nouveau_camion': remplacement.to_dict(),
    }
