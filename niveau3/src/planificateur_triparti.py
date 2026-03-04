"""
Niveau 3 — Planification Temporelle

Calcule les heures de départ et d'arrivée estimées pour chaque camion
et chaque point de sa tournée, en tenant compte de la vitesse moyenne,
du temps de service à chaque point, et éventuellement de fenêtres
temporelles.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from commun.models import PointCollecte, Camion
from niveau1.src.graphe_routier import GrapheRoutier


class PlanificateurTriparti:
    """
    Planificateur temporel.

    Pour chaque tournée (liste ordonnée de points), calcule :
    - heure de départ du dépôt
    - heure d'arrivée à chaque point
    - heure de retour au dépôt
    """

    # Paramètres par défaut
    VITESSE_KMH = 30.0         # km/h en milieu urbain
    TEMPS_SERVICE_MIN = 5.0    # minutes par point de collecte
    HEURE_DEPART = "06:00"     # heure de départ par défaut

    def __init__(self, graphe: GrapheRoutier,
                 vitesse_kmh: float = None,
                 temps_service_min: float = None,
                 heure_depart: str = None):
        self.graphe = graphe
        self.vitesse = vitesse_kmh or self.VITESSE_KMH
        self.temps_service = temps_service_min or self.TEMPS_SERVICE_MIN
        self.heure_depart_str = heure_depart or self.HEURE_DEPART

    def planifier_tournee(self, visits: List[Dict],
                          camion: Camion) -> Dict:
        """
        Planifie une tournée individuelle.

        route_indices: indices des points (1-based, 0=dépôt dans le graphe)
        camion: camion affecté

        Retourne un dict avec le planning détaillé.
        """
        # Heure réelle (now)
        current_time = datetime.now()
        start_time = current_time
        heure_debut_str = current_time.strftime("%H:%M")
        
        pause_obl_min = getattr(camion, 'pause_obligatoire', 45)
        temps_dechargement_min = getattr(camion, 'temps_de_dechargement', 30)

        # Shift implicite de 8 heures
        max_end_time = current_time + timedelta(hours=8)

        schedule = []
        current_lat = self.graphe.depot.lat
        current_lng = self.graphe.depot.lng
        
        has_taken_break = False
        conduite_continue = getattr(camion, 'temps_conduite_continue', 0.0)

        for i, visit in enumerate(visits):
            # Calcul distance réelle
            dist = GrapheRoutier.haversine(current_lat, current_lng, visit["lat"], visit["lng"])
            travel_min = (dist / self.vitesse) * 60 if self.vitesse > 0 else 0
            
            # Application strict de la pause au bout de 4h (240 min) de conduite
            conduite_continue += travel_min
            if pause_obl_min > 0 and conduite_continue > 240:
                current_time += timedelta(minutes=pause_obl_min)
                conduite_continue = 0  # Reset
                has_taken_break = True
                
            current_time += timedelta(minutes=travel_min)

            # Vérification du dépassement horaire global
            if current_time > max_end_time:
                # Dépassement d'horaire détecté: fin de service, retour automatique au dépôt
                dist_retour = GrapheRoutier.haversine(current_lat, current_lng, self.graphe.depot.lat, self.graphe.depot.lng)
                travel_retour = (dist_retour / self.vitesse) * 60 if self.vitesse > 0 else 0
                current_time += timedelta(minutes=travel_retour)
                break # On tronque la tournée

            schedule.append({
                "point_index": visit["point_index"],
                "nom": visit.get("nom", "Inconnu"),
                "arrivee": current_time.strftime("%H:%M"),
                "distance_depuis_precedent_km": round(dist, 2),
                "temps_trajet_min": round(travel_min, 1),
                "is_landfill": visit.get("is_landfill_trip", False),
                "is_refuel": visit.get("is_refuel_trip", False)
            })

            # Temps de service en fonction du type de visite
            if visit.get("is_landfill_trip"):
                current_time += timedelta(minutes=temps_dechargement_min)
                conduite_continue += temps_dechargement_min # Le temps de travail compte
            elif visit.get("is_refuel_trip"):
                current_time += timedelta(minutes=15) # 15 minutes pour un plein
                conduite_continue += 15
            else:
                current_time += timedelta(minutes=self.temps_service)
                conduite_continue += self.temps_service
                
            current_lat = visit["lat"]
            current_lng = visit["lng"]

        else:
            # Retour normal au dépôt si pas de break (pas de dépassement horaire strict)
            dist_retour = GrapheRoutier.haversine(current_lat, current_lng, self.graphe.depot.lat, self.graphe.depot.lng)
            travel_retour = (dist_retour / self.vitesse) * 60 if self.vitesse > 0 else 0
            conduite_continue += travel_retour
            if pause_obl_min > 0 and conduite_continue > 240:
                current_time += timedelta(minutes=pause_obl_min)
            current_time += timedelta(minutes=travel_retour)

        return {
            "camion_id": camion.id,
            "heure_depart": heure_debut_str,
            "heure_retour": current_time.strftime("%H:%M"),
            "duree_totale_min": round(
                (current_time - start_time).total_seconds() / 60, 1),
            "depasse_horaire": current_time > max_end_time,
            "schedule": schedule,
        }

    def planifier_toutes(self, routes: List[Dict],
                         camions_map: Dict[int, Camion]) -> List[Dict]:
        """
        Planifie toutes les tournées.

        routes: liste de dicts (retour de _format_result optimizeur VRP)
        camions_map: {camion_id: Camion}
        """
        plannings = []
        for route in routes:
            camion_id = route.get("camion_id")
            camion = camions_map.get(camion_id)
            if camion and route.get("visits"):
                p = self.planifier_tournee(route["visits"], camion)
                plannings.append(p)
        return plannings
