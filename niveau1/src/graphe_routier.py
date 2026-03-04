"""
Niveau 1 — Graphe Routier

Construction de la matrice de distances entre tous les points de collecte
et le dépôt. Utilise la formule haversine (distance à vol d'oiseau).
"""
import math
from typing import List, Tuple

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from commun.models import PointCollecte, Depot


class GrapheRoutier:
    """
    Construit et maintient le graphe (matrice de distances)
    entre le dépôt et tous les points de collecte.

    Index 0 = dépôt, index 1..N = points de collecte.
    """

    def __init__(self, depot: Depot, points: List[PointCollecte]):
        self.depot = depot
        self.points = points
        self.n = len(points) + 1  # +1 pour le dépôt
        self.matrix: List[List[float]] = []
        self._build()

    # ── Construction ─────────────────────────────────────────

    def _build(self):
        """Construit la matrice de distances N+1 × N+1."""
        coords = self._all_coords()
        n = self.n
        self.matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                d = self.haversine(coords[i][0], coords[i][1],
                                   coords[j][0], coords[j][1])
                self.matrix[i][j] = d
                self.matrix[j][i] = d

    def _all_coords(self) -> List[Tuple[float, float]]:
        """Retourne [(lat, lng), ...] avec le dépôt en index 0."""
        coords = [(self.depot.lat, self.depot.lng)]
        for p in self.points:
            coords.append((p.lat, p.lng))
        return coords

    # ── API publique ─────────────────────────────────────────

    def get_distance(self, i: int, j: int) -> float:
        """Distance entre le nœud i et le nœud j (0=dépôt)."""
        return self.matrix[i][j]

    def get_matrix(self) -> List[List[float]]:
        """Retourne la matrice complète."""
        return self.matrix

    def to_dict(self) -> dict:
        """Sérialisation pour JSON."""
        return {
            "n": self.n,
            "depot": self.depot.to_dict(),
            "nb_points": len(self.points),
        }

    # ── Utilitaire statique ──────────────────────────────────

    @staticmethod
    def haversine(lat1: float, lon1: float,
                  lat2: float, lon2: float) -> float:
        """Distance en km entre deux coordonnées GPS (haversine)."""
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1))
             * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
