"""
Routes Niveau 1 : Points de collecte et distances
GET/POST /api/points
GET /api/distances
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import db, PointCollecte, Zone
from services.vrp_service import haversine, build_distance_matrix
from utils.decorators import admin_required

points_bp = Blueprint('points', __name__)


@points_bp.route('/api/points', methods=['GET'])
@jwt_required()
def get_points():
    """Liste les points de collecte avec filtres optionnels"""
    zone_id = request.args.get('zone_id', type=int)
    priorite = request.args.get('priorite', type=int)
    type_dechet = request.args.get('type_dechet')
    urgent = request.args.get('urgent', type=bool)

    query = PointCollecte.query.filter_by(actif=True)
    if zone_id:
        query = query.filter_by(zone_id=zone_id)
    if priorite:
        query = query.filter_by(priorite=priorite)
    if type_dechet:
        query = query.filter_by(type_dechet=type_dechet)
    if urgent:
        query = query.filter(PointCollecte.taux_remplissage >= 0.8)

    points = query.all()
    return jsonify({
        'points': [p.to_dict() for p in points],
        'total': len(points)
    }), 200


@points_bp.route('/api/points/<int:point_id>', methods=['GET'])
@jwt_required()
def get_point(point_id):
    p = PointCollecte.query.get_or_404(point_id)
    return jsonify({'point': p.to_dict()}), 200


@points_bp.route('/api/points', methods=['POST'])
@jwt_required()
def create_point():
    """Ajouter un point de collecte"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Données manquantes'}), 400

    required = ['nom', 'latitude', 'longitude']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Champ obligatoire manquant: {field}'}), 400

    point = PointCollecte(
        nom=data['nom'],
        adresse=data.get('adresse'),
        latitude=float(data['latitude']),
        longitude=float(data['longitude']),
        zone_id=data.get('zone_id'),
        type_dechet=data.get('type_dechet', 'menager'),
        capacite_m3=float(data.get('capacite_m3', 1.0)),
        taux_remplissage=float(data.get('taux_remplissage', 0.0)),
        priorite=int(data.get('priorite', 2)),
    )
    db.session.add(point)
    db.session.commit()
    return jsonify({'message': 'Point créé', 'point': point.to_dict()}), 201


@points_bp.route('/api/points/<int:point_id>', methods=['PUT'])
@jwt_required()
def update_point(point_id):
    """Mettre à jour un point de collecte"""
    point = PointCollecte.query.get_or_404(point_id)
    data = request.get_json()

    updatable = ['nom', 'adresse', 'latitude', 'longitude', 'zone_id',
                 'type_dechet', 'capacite_m3', 'taux_remplissage', 'priorite', 'actif']
    for field in updatable:
        if field in data:
            setattr(point, field, data[field])

    db.session.commit()
    return jsonify({'message': 'Point mis à jour', 'point': point.to_dict()}), 200


@points_bp.route('/api/points/<int:point_id>', methods=['DELETE'])
@admin_required
def delete_point(point_id):
    """Désactiver un point (soft delete)"""
    point = PointCollecte.query.get_or_404(point_id)
    point.actif = False
    db.session.commit()
    return jsonify({'message': 'Point désactivé'}), 200


@points_bp.route('/api/distances', methods=['GET'])
@jwt_required()
def get_distances():
    """
    Matrice de distances entre tous les points actifs
    Optionnel: filtrer par zone_id
    """
    zone_id = request.args.get('zone_id', type=int)
    query = PointCollecte.query.filter_by(actif=True)
    if zone_id:
        query = query.filter_by(zone_id=zone_id)

    points = query.limit(50).all()  # Limite pour performance
    if len(points) < 2:
        return jsonify({'error': 'Moins de 2 points pour calculer les distances'}), 400

    points_data = [p.to_dict() for p in points]
    matrix = build_distance_matrix(points_data)

    return jsonify({
        'points': [{'id': p['id'], 'nom': p['nom']} for p in points_data],
        'matrix': matrix,
        'nb_points': len(points),
    }), 200


@points_bp.route('/api/zones', methods=['GET'])
@jwt_required()
def get_zones():
    zones = Zone.query.filter_by(actif=True).all()
    return jsonify({'zones': [z.to_dict() for z in zones]}), 200


@points_bp.route('/api/zones', methods=['POST'])
@admin_required
def create_zone():
    data = request.get_json()
    zone = Zone(
        nom=data['nom'],
        code=data['code'],
        priorite=data.get('priorite', 2),
        population=data.get('population', 0),
        superficie_km2=data.get('superficie_km2', 0),
        frequence_semaine=data.get('frequence_semaine', 3),
        couleur=data.get('couleur', '#3388ff'),
    )
    db.session.add(zone)
    db.session.commit()
    return jsonify({'message': 'Zone créée', 'zone': zone.to_dict()}), 201


@points_bp.route('/api/zones/<int:zone_id>', methods=['DELETE'])
@admin_required
def delete_zone(zone_id):
    """Désactive une zone (actif=False) pour qu'elle n'apparaisse plus dans les listes."""
    zone = Zone.query.get_or_404(zone_id)
    zone.actif = False
    db.session.commit()
    return jsonify({'message': f'Zone {zone.nom} supprimée (désactivée)', 'zone': zone.to_dict()}), 200
