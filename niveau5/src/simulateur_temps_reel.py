"""
Niveau 5 — Simulateur Temps Réel

Simule le déplacement des camions le long de leurs routes optimisées,
gère les événements dynamiques (pannes, nouveaux points) et permet
la re-planification.
"""
import copy
import math
from typing import Dict, List, Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from commun.models import Camion, PointCollecte, Depot


class SimulateurTempsReel:
    """
    Simulateur pas-à-pas : avance chaque camion le long de sa route
    et gère les événements dynamiques.
    """

    def __init__(self, routes: List[Dict], depot: Depot,
                 vitesse_kmh: float = 30.0):
        """
        routes: résultat de OptimiseurVRP (liste de routes)
        depot: point de départ
        vitesse_kmh: vitesse moyenne
        """
        self.depot = depot
        self.vitesse = vitesse_kmh
        self.routes = routes

        # État de simulation par route
        self.etats = []
        for route in routes:
            visits = route.get("visits", [])
            # Construire la liste des coordonnées
            coords = [(depot.lat, depot.lng)]
            for v in visits:
                coords.append((v["lat"], v["lng"]))
            coords.append((depot.lat, depot.lng))  # retour dépôt

            self.etats.append({
                "camion_id": route.get("camion_id"),
                "coords": coords,
                "current_segment": 0,
                "progress": 0.0,        # 0-1 dans le segment courant
                "lat": depot.lat,
                "lng": depot.lng,
                "distance_parcourue": 0.0,
                "distance_totale": route.get("distance_km", 0),
                "termine": False,
                "visits": visits,
                "visit_index": 0,
            })

    def simuler_pas(self, delta_seconds: float = 1.0) -> List[Dict]:
        """
        Avance la simulation d'un pas (delta_seconds).
        Retourne les positions mises à jour de tous les camions.
        """
        positions = []
        step_km = (self.vitesse / 3600) * delta_seconds

        for etat in self.etats:
            if etat["termine"]:
                positions.append(self._format_position(etat))
                continue

            coords = etat["coords"]
            seg = etat["current_segment"]

            if seg >= len(coords) - 1:
                etat["termine"] = True
                positions.append(self._format_position(etat))
                continue

            # Distance du segment courant
            lat1, lng1 = coords[seg]
            lat2, lng2 = coords[seg + 1]
            seg_dist = self._haversine(lat1, lng1, lat2, lng2)

            if seg_dist < 0.0001:
                etat["current_segment"] += 1
                etat["progress"] = 0.0
                positions.append(self._format_position(etat))
                continue

            # Avancer
            etat["progress"] += step_km / seg_dist
            etat["distance_parcourue"] += step_km

            if etat["progress"] >= 1.0:
                etat["current_segment"] += 1
                etat["progress"] = 0.0
                etat["lat"] = lat2
                etat["lng"] = lng2
            else:
                t = etat["progress"]
                etat["lat"] = lat1 + (lat2 - lat1) * t
                etat["lng"] = lng1 + (lng2 - lng1) * t

            positions.append(self._format_position(etat))

        return positions

    def get_positions(self) -> List[Dict]:
        """Retourne les positions actuelles sans avancer."""
        return [self._format_position(e) for e in self.etats]

    def is_termine(self) -> bool:
        """Vérifie si toutes les routes sont terminées."""
        return all(e["termine"] for e in self.etats)

    def replanifier(self, camion_id_panne: int,
                    new_routes: List[Dict]) -> Dict:
        """
        Replanifie après une panne : retire le camion en panne
        et ajoute les nouvelles routes.
        """
        # Marquer le camion en panne
        for etat in self.etats:
            if etat["camion_id"] == camion_id_panne:
                etat["termine"] = True

        # Ajouter les nouvelles routes
        for route in new_routes:
            visits = route.get("visits", [])
            coords = [(self.depot.lat, self.depot.lng)]
            for v in visits:
                coords.append((v["lat"], v["lng"]))
            coords.append((self.depot.lat, self.depot.lng))

            self.etats.append({
                "camion_id": route.get("camion_id"),
                "coords": coords,
                "current_segment": 0,
                "progress": 0.0,
                "lat": self.depot.lat,
                "lng": self.depot.lng,
                "distance_parcourue": 0.0,
                "distance_totale": route.get("distance_km", 0),
                "termine": False,
                "visits": visits,
                "visit_index": 0,
            })

        return {"message": f"Camion {camion_id_panne} retiré, {len(new_routes)} nouvelle(s) route(s) ajoutée(s)"}

    # ── Internals ────────────────────────────────────────────

    def _format_position(self, etat: Dict) -> Dict:
        remaining = max(0, etat["distance_totale"] - etat["distance_parcourue"])
        progress_pct = 0
        if etat["distance_totale"] > 0:
            progress_pct = min(100, (etat["distance_parcourue"]
                                     / etat["distance_totale"]) * 100)
        return {
            "camion_id": etat["camion_id"],
            "lat": round(etat["lat"], 6),
            "lng": round(etat["lng"], 6),
            "distance_parcourue_km": round(etat["distance_parcourue"], 2),
            "distance_restante_km": round(remaining, 2),
            "progress_pct": round(progress_pct, 1),
            "termine": etat["termine"],
        }

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1))
             * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
