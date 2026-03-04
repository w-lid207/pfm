"""
Routes Niveau 5 : Dashboard, Simulation, Alertes
"""
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import db, Alert, Camion, PointCollecte, Tournee
from services.dashboard_service import get_dashboard_stats
from services.simulation_service import (
    simulate_truck_movement, get_all_trucks_positions,
    simulate_breakdown, replan_after_breakdown
)
from utils.decorators import admin_required

dashboard_bp = Blueprint('dashboard', __name__)


# ────────────── DASHBOARD ──────────────

@dashboard_bp.route('/api/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    """KPIs et statistiques pour le tableau de bord"""
    stats = get_dashboard_stats()
    return jsonify(stats), 200


def _scan_alertes_automatiques() -> int:
    """
    Exécute les règles d'alertes automatiques (remplissage, retard, maintenance).
    Retourne le nombre d'alertes créées.
    """
    now = datetime.now()
    today = now.date()
    created = 0

    # Points saturés
    points = PointCollecte.query.filter(
        PointCollecte.actif.is_(True),
        PointCollecte.taux_remplissage >= 0.9,
    ).all()

    for pt in points:
        last_alert = (
            Alert.query
            .filter_by(
                type_alerte='remplissage',
                entite_type='point',
                entite_id=pt.id,
            )
            .order_by(Alert.created_at.desc())
            .first()
        )
        if last_alert and last_alert.created_at.date() == today:
            continue

        pourcent = int((pt.taux_remplissage or 0) * 100)
        alert = Alert(
            type_alerte='remplissage',
            titre=f'Point saturé : {pt.nom}',
            message=f'Taux de remplissage: {pourcent}%. Collecte urgente recommandée.',
            niveau='danger',
            entite_type='point',
            entite_id=pt.id,
        )
        db.session.add(alert)
        created += 1

    # Tournées en retard
    tournees = Tournee.query.filter(
        Tournee.date_tournee == today,
        Tournee.statut.in_(('planifiee', 'en_cours')),
    ).all()

    for t in tournees:
        try:
            hh, mm = (t.heure_depart or '06:00').split(':')
            depart = datetime.combine(today, datetime.min.time()).replace(hour=int(hh), minute=int(mm))
        except Exception:
            continue

        if now <= depart + timedelta(minutes=30):
            continue

        last_alert = (
            Alert.query
            .filter_by(type_alerte='retard', entite_type='tournee', entite_id=t.id)
            .order_by(Alert.created_at.desc())
            .first()
        )
        if last_alert and last_alert.created_at.date() == today:
            continue

        camion_label = t.camion.immatriculation if t.camion else '—'
        minutes = int((now - depart).total_seconds() // 60)
        alert = Alert(
            type_alerte='retard',
            titre=f'Tournée en retard : {t.nom}',
            message=f'Tournée prévue à {t.heure_depart} (camion {camion_label}). Retard ~{minutes} min.',
            niveau='warning',
            entite_type='tournee',
            entite_id=t.id,
        )
        db.session.add(alert)
        created += 1

    # Maintenance préventive
    camions = Camion.query.filter(Camion.actif.is_(True)).all()
    for c in camions:
        if (c.km_total or 0) < 80000:
            continue
        last_alert = (
            Alert.query
            .filter_by(type_alerte='maintenance', entite_type='camion', entite_id=c.id)
            .order_by(Alert.created_at.desc())
            .first()
        )
        if last_alert and last_alert.created_at.date() == today:
            continue

        alert = Alert(
            type_alerte='maintenance',
            titre=f'Alerte préventive : {c.immatriculation}',
            message=f'Kilométrage élevé ({int(c.km_total)} km). Maintenance recommandée.',
            niveau='warning',
            entite_type='camion',
            entite_id=c.id,
        )
        db.session.add(alert)
        created += 1

    if created:
        db.session.commit()

    return created


# ────────────── SIMULATION ──────────────

@dashboard_bp.route('/api/simulation', methods=['POST'])
@jwt_required()
def simulation():
    """
    Démarre une simulation de tournée
    Met à jour les positions GPS des camions
    et déclenche les règles d'alertes automatiques.
    """
    data = request.get_json() or {}
    action = data.get('action', 'move')  # move | breakdown | replan | reset

    if action == 'move':
        camions = Camion.query.filter(
            Camion.actif == True,
            Camion.statut == 'en_tournee'
        ).all()
        positions = []
        for c in camions:
            result = simulate_truck_movement(c.id)
            positions.append(result)

        nb_alerts = _scan_alertes_automatiques()
        return jsonify({'positions': positions, 'nb_camions': len(positions), 'nb_alertes': nb_alerts}), 200

    elif action == 'breakdown':
        camion_id = data.get('camion_id')
        if not camion_id:
            return jsonify({'error': 'camion_id requis'}), 400
        return jsonify(simulate_breakdown(camion_id)), 200

    elif action == 'replan':
        camion_id = data.get('camion_id')
        if not camion_id:
            return jsonify({'error': 'camion_id requis'}), 400
        return jsonify(replan_after_breakdown(camion_id)), 200

    elif action == 'reset':
        Camion.query.filter_by(actif=True).update({'statut': 'disponible'})
        db.session.commit()
        return jsonify({'message': 'Simulation réinitialisée'}), 200

    return jsonify({'error': 'Action inconnue'}), 400


@dashboard_bp.route('/api/simulation/positions', methods=['GET'])
@jwt_required()
def get_positions():
    """Positions GPS en temps réel de tous les camions"""
    positions = get_all_trucks_positions()
    return jsonify({'positions': positions}), 200


# ────────────── ALERTES ──────────────

@dashboard_bp.route('/api/alertes', methods=['GET'])
@jwt_required()
def get_alertes():
    """Liste des alertes (non lues par défaut)"""
    non_lues_only = request.args.get('non_lues', 'false').lower() == 'true'
    query = Alert.query
    if non_lues_only:
        query = query.filter_by(lue=False)
    alertes = query.order_by(Alert.created_at.desc()).limit(50).all()
    return jsonify({
        'alertes': [a.to_dict() for a in alertes],
        'non_lues': Alert.query.filter_by(lue=False).count(),
    }), 200


@dashboard_bp.route('/api/alertes/generer', methods=['POST'])
@jwt_required()
@admin_required
def generate_alertes():
    """Lance manuellement le scan des alertes automatiques (mêmes règles que la simulation)."""
    created = _scan_alertes_automatiques()
    return jsonify({'message': 'Alertes générées', 'nb_creees': created}), 200


@dashboard_bp.route('/api/alertes/<int:alert_id>/lue', methods=['PUT'])
@jwt_required()
def mark_alerte_lue(alert_id):
    alerte = Alert.query.get_or_404(alert_id)
    alerte.lue = True
    db.session.commit()
    return jsonify({'message': 'Alerte marquée comme lue'}), 200


@dashboard_bp.route('/api/alertes/lire-tout', methods=['PUT'])
@jwt_required()
def mark_all_lues():
    Alert.query.filter_by(lue=False).update({'lue': True})
    db.session.commit()
    return jsonify({'message': 'Toutes les alertes marquées comme lues'}), 200
