"""
Routes Niveaux 2-4 : Affectation, Planification, Optimisation VRP
"""
from datetime import datetime, date, timedelta
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt
import io

from models import db, Camion, Tournee, TourneePoint, PointCollecte, Zone
from services.vrp_service import optimize_routes, compute_metrics
from utils.decorators import admin_required, operateur_or_admin
from utils.export import export_tournees_csv, export_tournees_pdf

tournees_bp = Blueprint('tournees', __name__)


# ────────────── NIVEAU 2 : AFFECTATION ──────────────

@tournees_bp.route('/api/affectation', methods=['POST'])
@jwt_required()
def affecter_camion():
    """Affecter un camion à une tournée"""
    data = request.get_json()
    tournee_id = data.get('tournee_id')
    camion_id = data.get('camion_id')

    if not all([tournee_id, camion_id]):
        return jsonify({'error': 'tournee_id et camion_id requis'}), 400

    tournee = Tournee.query.get_or_404(tournee_id)
    camion = Camion.query.get_or_404(camion_id)

    if camion.statut not in ('disponible',):
        return jsonify({'error': f'Camion {camion.immatriculation} non disponible (statut: {camion.statut})'}), 409

    tournee.camion_id = camion_id
    camion.statut = 'en_tournee'
    db.session.commit()

    return jsonify({
        'message': 'Affectation réussie',
        'tournee': tournee.to_dict(),
        'camion': camion.to_dict(),
    }), 200


@tournees_bp.route('/api/affectation/resultat', methods=['GET'])
@jwt_required()
def get_affectations():
    """Vue d'ensemble des affectations du jour"""
    today = date.today()
    tournees = Tournee.query.filter_by(date_tournee=today).all()
    camions = Camion.query.filter_by(actif=True).all()

    return jsonify({
        'date': today.isoformat(),
        'tournees': [t.to_dict() for t in tournees],
        'camions': [c.to_dict() for c in camions],
        'affectes': sum(1 for t in tournees if t.camion_id),
        'disponibles': sum(1 for c in camions if c.statut == 'disponible'),
    }), 200


# ────────────── NIVEAU 3 : PLANIFICATION ──────────────

@tournees_bp.route('/api/planification', methods=['POST'])
@jwt_required()
def planifier_tournee():
    """Créer une nouvelle tournée planifiée"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Données manquantes'}), 400

    # Date par défaut = demain
    date_str = data.get('date_tournee', (date.today() + timedelta(days=1)).isoformat())
    try:
        date_tournee = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({'error': 'Format de date invalide (YYYY-MM-DD)'}), 400

    tournee = Tournee(
        nom=data.get('nom', f'Tournée {date_tournee}'),
        camion_id=data.get('camion_id'),
        date_tournee=date_tournee,
        heure_depart=data.get('heure_depart', '06:00'),
        statut='planifiee',
        distance_km=data.get('distance_km', 0),
        co2_kg=data.get('co2_kg', 0),
        cout_mad=data.get('cout_mad', 0),
        nb_points=0,
    )
    db.session.add(tournee)
    db.session.flush()

    # Ajout des points si fournis
    point_ids = data.get('point_ids', [])
    for ordre, pid in enumerate(point_ids, start=1):
        tp = TourneePoint(tournee_id=tournee.id, point_id=pid, ordre=ordre)
        db.session.add(tp)
    tournee.nb_points = len(point_ids)

    db.session.commit()
    return jsonify({'message': 'Tournée planifiée', 'tournee': tournee.to_dict()}), 201


@tournees_bp.route('/api/planification/hebdomadaire', methods=['GET'])
@jwt_required()
def planification_hebdomadaire():
    """Tournées de la semaine courante ou d'une semaine spécifique"""
    semaine = request.args.get('semaine')  # format: YYYY-WXX
    today = date.today()

    # Début et fin de la semaine
    lundi = today - timedelta(days=today.weekday())
    dimanche = lundi + timedelta(days=6)

    tournees = Tournee.query.filter(
        Tournee.date_tournee >= lundi,
        Tournee.date_tournee <= dimanche,
    ).order_by(Tournee.date_tournee).all()

    # Grouper par jour
    planning = {}
    for i in range(7):
        day = lundi + timedelta(days=i)
        key = day.isoformat()
        planning[key] = {
            'date': key,
            'jour': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'][i],
            'tournees': [],
        }

    for t in tournees:
        key = t.date_tournee.isoformat()
        if key in planning:
            planning[key]['tournees'].append(t.to_dict())

    return jsonify({
        'semaine': f'{lundi} / {dimanche}',
        'planning': list(planning.values()),
        'total_tournees': len(tournees),
    }), 200


# ────────────── NIVEAU 4 : OPTIMISATION VRP ──────────────

@tournees_bp.route('/api/optimisation-vrp', methods=['POST'])
@jwt_required()
def optimiser_vrp():
    """
    Lance l'optimisation VRP sur les points sélectionnés
    Retourne les tournées optimisées avec comparaison avant/après
    """
    data = request.get_json() or {}

    # Paramètres
    zone_id = data.get('zone_id')
    num_trucks = int(data.get('num_trucks', 3))
    truck_capacity = float(data.get('truck_capacity', 10.0))
    date_str = data.get('date_tournee', date.today().isoformat())
    sauvegarder = data.get('sauvegarder', False)

    # Dépôt (centre de tri d'Agadir)
    depot = data.get('depot', {
        'id': 0,
        'nom': 'Dépôt Central Agadir',
        'latitude': 30.4132,
        'longitude': -9.5889,
    })

    # Points à optimiser : points actifs ; seules les zones actives (ex. Talborjt désactivée = exclue)
    query = (
        PointCollecte.query
        .outerjoin(Zone, PointCollecte.zone_id == Zone.id)
        .filter(
            PointCollecte.actif == True,
            (Zone.id == None) | (Zone.actif == True),  # pas de zone ou zone active
        )
    )
    if zone_id:
        query = query.filter(PointCollecte.zone_id == zone_id)
    query = query.filter(PointCollecte.taux_remplissage >= 0.3)

    points = query.all()
    if not points:
        return jsonify({'error': 'Aucun point à optimiser'}), 400

    points_data = [p.to_dict() for p in points]

    # Optimisation
    result = optimize_routes(points_data, depot, num_trucks, truck_capacity)

    # Sauvegarder les tournées si demandé
    saved_tournees = []
    if sauvegarder and result['routes']:
        try:
            date_tournee = date.fromisoformat(date_str)
        except ValueError:
            date_tournee = date.today()

        camions = Camion.query.filter_by(statut='disponible', actif=True).limit(num_trucks).all()

        for idx, route in enumerate(result['routes']):
            if not route.get('coordinates'):
                # Pas de route routière valide -> ne pas sauvegarder
                continue
            metrics = compute_metrics(route['distance_km'])
            import json
            tournee = Tournee(
                nom=f'Tournée VRP {date_tournee} #{idx+1}',
                camion_id=camions[idx].id if idx < len(camions) else None,
                date_tournee=date_tournee,
                statut='planifiee',
                distance_km=route['distance_km'],
                duree_min=metrics['duree_min'],
                co2_kg=metrics['co2_kg'],
                cout_mad=metrics['cout_mad'],
                nb_points=route['nb_points'],
                geojson_trajet=json.dumps(route['coordinates']),
                optimisee=True,
            )
            db.session.add(tournee)
            db.session.flush()

            for ordre, pt in enumerate(route['points'], start=1):
                tp = TourneePoint(
                    tournee_id=tournee.id,
                    point_id=pt['id'],
                    ordre=ordre,
                )
                db.session.add(tp)

            if idx < len(camions):
                camions[idx].statut = 'en_tournee'

            saved_tournees.append(tournee.to_dict())

        db.session.commit()

    return jsonify({
        'optimisation': result,
        'saved': sauvegarder,
        'tournees_crees': saved_tournees,
        'nb_points_traites': len(points),
    }), 200


@tournees_bp.route('/api/tournees', methods=['GET'])
@jwt_required()
def get_tournees():
    """Liste des tournées avec filtres"""
    statut = request.args.get('statut')
    date_str = request.args.get('date')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    query = Tournee.query
    if statut:
        query = query.filter_by(statut=statut)
    if date_str:
        try:
            d = date.fromisoformat(date_str)
            query = query.filter_by(date_tournee=d)
        except ValueError:
            pass

    query = query.order_by(Tournee.date_tournee.desc(), Tournee.created_at.desc())
    total = query.count()
    tournees = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'tournees': [t.to_dict() for t in tournees],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page,
    }), 200


@tournees_bp.route('/api/tournees/<int:tid>', methods=['PUT'])
@jwt_required()
def update_tournee(tid):
    """Mettre à jour le statut d'une tournée"""
    tournee = Tournee.query.get_or_404(tid)
    data = request.get_json()
    if 'statut' in data:
        tournee.statut = data['statut']
        if data['statut'] == 'terminee' and tournee.camion:
            tournee.camion.statut = 'disponible'
    db.session.commit()
    return jsonify({'tournee': tournee.to_dict()}), 200


# ────────────── CAMIONS ──────────────

@tournees_bp.route('/api/camions', methods=['GET'])
@jwt_required()
def get_camions():
    camions = Camion.query.filter_by(actif=True).all()
    return jsonify({'camions': [c.to_dict() for c in camions]}), 200


@tournees_bp.route('/api/camions', methods=['POST'])
@admin_required
def create_camion():
    data = request.get_json()
    camion = Camion(
        immatriculation=data['immatriculation'],
        modele=data.get('modele', ''),
        capacite_m3=float(data.get('capacite_m3', 10.0)),
        latitude=data.get('latitude', 30.4278),
        longitude=data.get('longitude', -9.5981),
    )
    db.session.add(camion)
    db.session.commit()
    return jsonify({'camion': camion.to_dict()}), 201


@tournees_bp.route('/api/camions/<int:camion_id>', methods=['PUT'])
@jwt_required()
def update_camion(camion_id):
    """Met à jour un camion (statut, etc.)."""
    camion = Camion.query.get_or_404(camion_id)
    data = request.get_json() or {}
    if 'statut' in data:
        statut = data['statut']
        if statut in ('disponible', 'en_tournee', 'panne', 'maintenance'):
            camion.statut = statut
    if 'latitude' in data:
        camion.latitude = float(data['latitude'])
    if 'longitude' in data:
        camion.longitude = float(data['longitude'])
    db.session.commit()
    return jsonify({'camion': camion.to_dict()}), 200


# ────────────── EXPORTS ──────────────

@tournees_bp.route('/api/export/tournees/csv', methods=['GET'])
@jwt_required()
def export_csv():
    """Export CSV de toutes les tournées"""
    tournees = Tournee.query.order_by(Tournee.date_tournee.desc()).limit(500).all()
    csv_bytes = export_tournees_csv([t.to_dict() for t in tournees])
    return send_file(
        io.BytesIO(csv_bytes),
        mimetype='text/csv; charset=utf-8-sig',
        as_attachment=True,
        download_name=f'tournees_agadir_{date.today()}.csv'
    )


@tournees_bp.route('/api/export/tournees/pdf', methods=['GET'])
@jwt_required()
def export_pdf():
    """Export PDF rapport des tournées"""
    from services.dashboard_service import get_dashboard_stats
    tournees = Tournee.query.order_by(Tournee.date_tournee.desc()).limit(100).all()
    stats = get_dashboard_stats()
    pdf_bytes = export_tournees_pdf([t.to_dict() for t in tournees], stats['performances'])
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'rapport_tournees_{date.today()}.pdf'
    )
