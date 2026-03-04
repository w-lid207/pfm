"""
Niveau 4 — Optimiseur Multi-Objectif

Score pondéré combinant distance, coût, CO2, et utilisation des camions.
"""
from typing import Dict, List


class OptimiseurMultiObjectif:
    """
    Calcule un score multi-objectif pour évaluer la qualité
    d'une solution VRP.
    """

    # Poids par défaut
    POIDS = {
        "distance": 0.30,
        "cout": 0.25,
        "co2": 0.25,
        "utilisation": 0.20,
    }

    # Constantes de calcul
    CO2_PAR_KM = 0.27       # kg CO2 / km
    COUT_PAR_KM = 0.85      # MAD / km
    COUT_FIXE_CAMION = 200   # MAD par camion

    def __init__(self, poids: Dict[str, float] = None):
        if poids:
            self.poids = poids
        else:
            self.poids = self.POIDS.copy()

    def evaluer(self, solution: Dict) -> Dict:
        """
        Évalue une solution VRP et retourne les métriques + score global.

        solution: résultat de OptimiseurVRP.optimiser()
        """
        routes = solution.get("routes", [])
        total_distance = solution.get("total_distance_km", 0)
        num_trucks = solution.get("num_trucks_used", 0)

        # Métriques brutes
        co2_total = total_distance * self.CO2_PAR_KM
        cout_carburant = total_distance * self.COUT_PAR_KM
        cout_fixe = num_trucks * self.COUT_FIXE_CAMION
        cout_total = cout_carburant + cout_fixe

        # Utilisation moyenne des camions
        utilisation = 0.0
        if routes:
            for r in routes:
                cap = r.get("camion_capacite", 5000)
                collecte = sum(v.get("quantite_collectee", 0)
                               for v in r.get("visits", []))
                utilisation += (collecte / cap) if cap > 0 else 0
            utilisation = (utilisation / len(routes)) * 100

        # Score normalisé (0-100, plus élevé = meilleur)
        # Normalisation heuristique
        score_distance = max(0, 100 - total_distance * 0.5)
        score_cout = max(0, 100 - cout_total * 0.02)
        score_co2 = max(0, 100 - co2_total * 2)
        score_utilisation = utilisation

        score_global = (
            self.poids["distance"] * score_distance
            + self.poids["cout"] * score_cout
            + self.poids["co2"] * score_co2
            + self.poids["utilisation"] * score_utilisation
        )

        return {
            "metrics": {
                "total_distance_km": round(total_distance, 2),
                "co2_total_kg": round(co2_total, 3),
                "cout_total_mad": round(cout_total, 2),
                "cout_carburant_mad": round(cout_carburant, 2),
                "cout_fixe_mad": round(cout_fixe, 2),
                "num_trucks_used": num_trucks,
                "utilisation_moyenne_pct": round(utilisation, 1),
                "duree_estimee_min": round(total_distance / 30 * 60, 1),
            },
            "scores": {
                "distance": round(score_distance, 1),
                "cout": round(score_cout, 1),
                "co2": round(score_co2, 1),
                "utilisation": round(score_utilisation, 1),
                "global": round(score_global, 1),
            },
        }
