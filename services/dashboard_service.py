"""
Service Dashboard : calcul des KPIs et statistiques
"""
from datetime import datetime, date, timedelta
from sqlalchemy import func
from models import db, Camion, PointCollecte, Tournee, Zone, Alert


def get_dashboard_stats() -> dict:
    """Retourne tous les KPIs pour le tableau de bord"""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # --- Camions ---
    total_camions = Camion.query.filter_by(actif=True).count()
    camions_en_tournee = Camion.query.filter_by(statut='en_tournee').count()
    camions_panne = Camion.query.filter_by(statut='panne').count()

    # --- Points ---
    total_points = PointCollecte.query.filter_by(actif=True).count()
    points_urgents = PointCollecte.query.filter(
        PointCollecte.taux_remplissage >= 0.8,
        PointCollecte.actif == True
    ).count()

    # --- Zones ---
    total_zones = Zone.query.filter_by(actif=True).count()

    # --- Tournées ce mois ---
    tournees_mois = Tournee.query.filter(
        Tournee.date_tournee >= month_ago
    ).all()

    dist_totale = sum(t.distance_km for t in tournees_mois)
    co2_total = sum(t.co2_kg for t in tournees_mois)
    cout_total = sum(t.cout_mad for t in tournees_mois)
    tournees_terminees = sum(1 for t in tournees_mois if t.statut == 'terminee')

    # --- Graphique : distances des 7 derniers jours ---
    chart_distances = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        tournees_jour = Tournee.query.filter(
            Tournee.date_tournee == day
        ).all()
        chart_distances.append({
            'date': day.strftime('%d/%m'),
            'distance': round(sum(t.distance_km for t in tournees_jour), 1),
            'nb_tournees': len(tournees_jour),
        })

    # --- Alertes non lues ---
    alertes_non_lues = Alert.query.filter_by(lue=False).count()

    # --- Répartition par zone ---
    zones_data = []
    for zone in Zone.query.filter_by(actif=True).all():
        nb_points = PointCollecte.query.filter_by(zone_id=zone.id, actif=True).count()
        zones_data.append({
            'nom': zone.nom,
            'code': zone.code,
            'nb_points': nb_points,
            'priorite': zone.priorite,
            'couleur': zone.couleur,
        })

    return {
        'camions': {
            'total': total_camions,
            'en_tournee': camions_en_tournee,
            'disponibles': total_camions - camions_en_tournee - camions_panne,
            'en_panne': camions_panne,
        },
        'points': {
            'total': total_points,
            'urgents': points_urgents,
            'taux_urgence': round(points_urgents / total_points * 100, 1) if total_points else 0,
        },
        'zones': {
            'total': total_zones,
            'detail': zones_data,
        },
        'performances': {
            'distance_totale_km': round(dist_totale, 1),
            'co2_total_kg': round(co2_total, 1),
            'cout_total_mad': round(cout_total, 2),
            'tournees_terminees': tournees_terminees,
            'tournees_total': len(tournees_mois),
        },
        'chart_distances': chart_distances,
        'alertes_non_lues': alertes_non_lues,
        'last_updated': datetime.utcnow().isoformat(),
    }
