"""
Niveau 2 — Affectation Bipartie Camion ↔ Zone

Affecte les camions aux zones de collecte en utilisant un algorithme
glouton basé sur la demande totale de chaque zone et la capacité
des camions disponibles.
"""
from typing import Dict, List

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from commun.models import Camion, Zone, PointCollecte


class AffectateurBiparti:
    """
    Affectation gloutonne : trie les zones par demande décroissante
    et les camions par capacité décroissante, puis affecte.
    """

    def __init__(self, zones: List[Zone], camions: List[Camion],
                 points: List[PointCollecte]):
        self.zones = zones
        self.camions = camions
        self.points = points
        self._points_by_id = {p.id: p for p in points}

    def _demande_zone(self, zone: Zone) -> float:
        """Calcule la demande totale (volume_restant) d'une zone."""
        total = 0.0
        for pid in zone.point_ids:
            pt = self._points_by_id.get(pid)
            if pt:
                total += pt.volume_restant
        return total

    def affecter(self) -> Dict[int, List[int]]:
        """
        Retourne un mapping {camion_id: [zone_id, ...]}
        Un même camion peut être affecté à plusieurs zones si sa capacité
        le permet.  Les zones sans demande sont ignorées.
        """
        # Calcul demande par zone
        zone_demands = []
        for z in self.zones:
            d = self._demande_zone(z)
            if d > 0:
                zone_demands.append((z, d))
        zone_demands.sort(key=lambda x: x[1], reverse=True)

        # Tri camions par capacité décroissante
        sorted_camions = sorted(self.camions, key=lambda c: c.capacite, reverse=True)

        affectation: Dict[int, List[int]] = {c.id: [] for c in sorted_camions}
        capacites_restantes = {c.id: c.capacite for c in sorted_camions}

        for zone, demande in zone_demands:
            # Trouver le camion avec le plus de capacité restante
            best_camion = max(sorted_camions,
                              key=lambda c: capacites_restantes[c.id])
            affectation[best_camion.id].append(zone.id)
            # On ne réduit pas la capacité ici (la réduction se fait au VRP)

        # Retirer les camions sans affectation
        return {k: v for k, v in affectation.items() if v}

    def to_dict(self) -> dict:
        result = self.affecter()
        return {
            "affectation": {str(k): v for k, v in result.items()},
            "nb_camions_utilises": len(result),
            "nb_zones": len(self.zones),
        }
