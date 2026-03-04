"""
Pipeline Service — Orchestrateur central du pipeline d'optimisation.

Coordonne les 5 niveaux :
  1. GrapheRoutier   (niveau1)
  2. AffectateurBiparti (niveau2)
  3. PlanificateurTriparti (niveau3)
  4. OptimiseurVRP + MultiObjectif (niveau4)
  5. SimulateurTempsReel (niveau5)
"""
import sys
import os
import time
from typing import Dict, List, Optional

# Ajouter le répertoire racine au path pour les imports niveau*
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from commun.models import PointCollecte, Camion, Zone, Depot
from niveau1.src.graphe_routier import GrapheRoutier
from niveau2.src.affectateur_biparti import AffectateurBiparti
from niveau3.src.planificateur_triparti import PlanificateurTriparti
from niveau4.src.optimiseur_vrp import OptimiseurVRP
from niveau5.src.optimiseur_multi_objectif import OptimiseurMultiObjectif
from niveau5.src.simulateur_temps_reel import SimulateurTempsReel

# Garder une référence globale au simulateur actif
_active_simulator: Optional[SimulateurTempsReel] = None
_last_result: Optional[Dict] = None
_status: str = "idle"


def solve_full_problem(user_input: dict) -> dict:
    """
    Point d'entrée principal du pipeline.

    Accepte le JSON du frontend, convertit en objets métier,
    exécute les 5 niveaux, et retourne un résultat structuré.

    Args:
        user_input: dict au format défini par le frontend:
            {
              "depot": {"lat": ..., "lng": ...},
              "points": [{"lat": ..., "lng": ..., "volume": ...}, ...],
              "zones": [{"points": [0, 1, ...]}, ...],
              "camions": [{"capacite": ..., "cout_fixe": ...}, ...],
              "parametres": {"multi_objectif": bool, "simulation": bool}
            }

    Returns:
        dict avec routes, métriques, planning, et positions de simulation.
    """
    global _active_simulator, _last_result, _status
    _status = "running"
    start_time = time.time()
    import sys as _sys

    try:
        print("[PIPELINE] Starting solve_full_problem...", flush=True)
        # ── PARSING ──────────────────────────────────────────
        depot_data = user_input.get("depot", {})
        depot = Depot(
            lat=depot_data.get("lat", 30.4278),
            lng=depot_data.get("lng", -9.5981),
        )

        points_data = user_input.get("points", [])
        points: List[PointCollecte] = []
        for i, pd in enumerate(points_data):
            vol = pd.get("volume", 1000)
            points.append(PointCollecte(
                id=i + 1,
                lat=pd["lat"],
                lng=pd["lng"],
                volume_total=vol,
                volume_restant=vol,
                priorite=pd.get("priorite", 2),
                nom=pd.get("nom", f"Point {i + 1}"),
            ))

        camions_data = user_input.get("camions", [{"capacite": 5000}])
        camions: List[Camion] = []
        for i, cd in enumerate(camions_data):
            cap = cd.get("capacite", 5000)
            camions.append(Camion(
                id=i + 1,
                capacite=cap,
                cout_fixe=cd.get("cout_fixe", 200),
                nom=f"Camion {i + 1}",
            ))

        zones_data = user_input.get("zones", [])
        zones: List[Zone] = []
        if zones_data:
            for i, zd in enumerate(zones_data):
                pids = zd.get("points", [])
                # Les indices dans "points" sont 0-based, nos IDs sont 1-based
                zones.append(Zone(
                    id=i + 1,
                    nom=zd.get("nom", f"Zone {i + 1}"),
                    point_ids=[pid + 1 for pid in pids],
                ))
        else:
            # Pas de zones définies → une seule zone contenant tous les points
            zones.append(Zone(
                id=1,
                nom="Zone unique",
                point_ids=[p.id for p in points],
            ))

        # Affecter les zone_id aux points
        for z in zones:
            for pid in z.point_ids:
                for p in points:
                    if p.id == pid:
                        p.zone_id = z.id

        params = user_input.get("parametres", {})
        do_multi_objectif = params.get("multi_objectif", True)
        do_simulation = params.get("simulation", False)

        # ── NIVEAU 1 : GRAPHE ROUTIER ────────────────────────
        print(f"[PIPELINE] Niveau 1: building graph ({len(points)} points)...", flush=True)
        graphe = GrapheRoutier(depot, points)
        print(f"[PIPELINE] Niveau 1 done ({time.time()-start_time:.3f}s)", flush=True)

        # ── NIVEAU 2 : AFFECTATION ───────────────────────────
        print("[PIPELINE] Niveau 2: affectation...", flush=True)
        affecteur = AffectateurBiparti(zones, camions, points)
        affectation = affecteur.affecter()
        print(f"[PIPELINE] Niveau 2 done ({time.time()-start_time:.3f}s)", flush=True)

        # ── NIVEAU 3 : PLANIFICATION ─────────────────────────
        print("[PIPELINE] Niveau 3: planification...", flush=True)
        planificateur = PlanificateurTriparti(graphe)
        print(f"[PIPELINE] Niveau 3 done ({time.time()-start_time:.3f}s)", flush=True)

        # ── NIVEAU 4 : OPTIMISATION VRP (SDVRP) ─────────────
        print("[PIPELINE] Niveau 4: VRP optimization...", flush=True)
        landfill = params.get("landfill", {"lat": 30.38, "lng": -9.55})
        optimiseur = OptimiseurVRP(graphe, camions, points, depot, landfill=landfill)
        vrp_result = optimiseur.optimiser()
        print(f"[PIPELINE] Niveau 4 done ({time.time()-start_time:.3f}s)", flush=True)

        # Les coordonnées sont déjà incluses par le VRP optimizer
        # (lat/lng pour le tracé simple — OSRM appelé côté client)

        # Planning temporel pour chaque route
        camions_map = {c.id: c for c in camions}
        plannings = []
        for route in vrp_result.get("routes", []):
            route_indices = route.get("route_indices", [])
            camion_id = route.get("camion_id")
            camion = camions_map.get(camion_id)
            if camion and route.get("visits"):
                p = planificateur.planifier_tournee(route["visits"], camion)
                plannings.append(p)
                route["planning"] = p

        # ── NIVEAU 4 (suite) : MULTI-OBJECTIF ────────────────
        evaluation = None
        if do_multi_objectif:
            evaluateur = OptimiseurMultiObjectif()
            evaluation = evaluateur.evaluer(vrp_result)

        # ── NIVEAU 5 : SIMULATION (optionnel) ────────────────
        sim_positions = None
        if do_simulation and vrp_result.get("routes"):
            _active_simulator = SimulateurTempsReel(
                vrp_result["routes"], depot)
            sim_positions = _active_simulator.get_positions()

        # ── RÉSULTAT ─────────────────────────────────────────
        elapsed = round(time.time() - start_time, 3)

        result = {
            "success": True,
            "elapsed_seconds": elapsed,
            "depot": depot.to_dict(),
            "nb_points": len(points),
            "nb_camions": len(camions),
            "nb_zones": len(zones),
            "vrp": vrp_result,
            "plannings": plannings,
            "evaluation": evaluation,
            "simulation": sim_positions,
            "affectation": {str(k): v for k, v in affectation.items()},
        }

        _last_result = result
        _status = "done"
        return result

    except Exception as e:
        _status = "error"
        return {
            "success": False,
            "error": str(e),
            "elapsed_seconds": round(time.time() - start_time, 3),
        }


def simulate_step() -> dict:
    """Avance la simulation d'un pas et retourne les positions."""
    global _active_simulator
    if _active_simulator is None:
        return {"error": "Aucune simulation active", "positions": []}
    positions = _active_simulator.simuler_pas(delta_seconds=1.0)
    return {
        "positions": positions,
        "termine": _active_simulator.is_termine(),
    }


def get_status() -> dict:
    """Retourne le statut courant du pipeline."""
    return {"status": _status}


def get_results() -> dict:
    """Retourne les derniers résultats d'optimisation."""
    if _last_result is None:
        return {"error": "Aucun résultat disponible"}
    return _last_result
