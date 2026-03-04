"""
Tests de Benchmark — Système de Collecte Agadir

Exécute le pipeline d'optimisation VRP avec 3 scénarios prédéfinis :
  1. Petit   : 5 camions,  50 points de collecte
  2. Moyen   : 10 camions, 100 points de collecte
  3. Grand   : 20 camions, 500 points de collecte

Chaque point possède 2-3 bennes avec un poids total entre 150 et 600 kg.

Usage :
    python -m benchmarks.benchmark_runner
"""
import json
import math
import os
import random
import sys
import time

# ── Path setup ──────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from commun.models import Camion, PointCollecte, Depot, Zone
from niveau1.src.graphe_routier import GrapheRoutier
from niveau2.src.affectateur_biparti import AffectateurBiparti
from niveau3.src.planificateur_triparti import PlanificateurTriparti
from niveau4.src.optimiseur_vrp import OptimiseurVRP
from niveau5.src.optimiseur_multi_objectif import OptimiseurMultiObjectif

# ── Constantes ──────────────────────────────────────────────
DEPOT = Depot(lat=30.4278, lng=-9.5981, nom="Dépôt Central Agadir")
LANDFILL = {"lat": 30.38, "lng": -9.55}

# Zone Agadir : lat 30.35 → 30.45, lng -9.63 → -9.53
LAT_MIN, LAT_MAX = 30.35, 30.45
LNG_MIN, LNG_MAX = -9.63, -9.53

# Seed pour reproductibilité
RANDOM_SEED = 42

# ── Scénarios ───────────────────────────────────────────────
SCENARIOS = [
    {"nom": "Petit",         "camions": 5,  "points": 50},
    {"nom": "Intermédiaire", "camions": 10, "points": 100},
    {"nom": "Grand",         "camions": 20, "points": 500},
]

# ── Générateur de données ───────────────────────────────────

def generer_points(n: int, seed: int = RANDOM_SEED) -> list[PointCollecte]:
    """
    Génère n points de collecte réalistes dans la zone d'Agadir.
    Chaque point a 2-3 bennes, poids total entre 150 et 600 kg.
    """
    rng = random.Random(seed)
    points = []
    noms_quartiers = [
        "Hay Mohammadi", "Agadir Ville", "Cité Dakhla", "Anza",
        "Tikouine", "Souss Massa", "Inezgane", "Talborjt",
        "Founty", "Charaf", "Hay Salam", "Nouveau Quartier",
        "Ben Sergao", "Dcheira", "Aourir", "Tamaris",
    ]
    for i in range(n):
        lat = rng.uniform(LAT_MIN, LAT_MAX)
        lng = rng.uniform(LNG_MIN, LNG_MAX)
        nb_bennes = rng.choice([2, 3])
        # Poids par benne : 50-200 kg → total 150-600 kg
        poids_total = sum(rng.uniform(50, 200) for _ in range(nb_bennes))
        poids_total = round(min(max(poids_total, 150), 600), 1)
        quartier = noms_quartiers[i % len(noms_quartiers)]
        points.append(PointCollecte(
            id=i + 1,
            lat=lat,
            lng=lng,
            volume_total=poids_total,
            volume_restant=poids_total,
            priorite=rng.choice([1, 2, 3]),
            nom=f"Benne {quartier} #{i + 1} ({nb_bennes} bennes)",
        ))
    return points


def generer_camions(n: int, seed: int = RANDOM_SEED) -> list[Camion]:
    """Génère n camions avec capacités variées (3000-8000 kg)."""
    rng = random.Random(seed + 1000)
    camions = []
    for i in range(n):
        cap = rng.choice([3000, 4000, 5000, 6000, 8000])
        camions.append(Camion(
            id=i + 1,
            capacite=cap,
            cout_fixe=200,
            nom=f"Camion-{i + 1:02d} ({cap} kg)",
        ))
    return camions


def generer_zones(points: list[PointCollecte], n_zones: int = 4,
                  seed: int = RANDOM_SEED) -> list[Zone]:
    """Répartit les points en n_zones zones géographiques."""
    rng = random.Random(seed + 2000)
    zones = [Zone(id=i + 1, nom=f"Zone {i + 1}", point_ids=[])
             for i in range(n_zones)]

    for p in points:
        zone_idx = rng.randint(0, n_zones - 1)
        zones[zone_idx].point_ids.append(p.id)
        p.zone_id = zone_idx + 1

    return zones


def charger_ou_creer_dataset(n_points: int) -> list[PointCollecte]:
    """Charge le dataset JSON correspondant ou le crée s'il n'existe pas."""
    nom_fichier = f"test_{n_points}_points.json"
    chemin_dossier = os.path.join(ROOT, "benchmarks")
    os.makedirs(chemin_dossier, exist_ok=True)
    chemin = os.path.join(chemin_dossier, nom_fichier)

    if os.path.exists(chemin):
        with open(chemin, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [PointCollecte(**p) for p in data]
    else:
        points = generer_points(n_points)
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump([p.to_dict() for p in points], f, indent=2, ensure_ascii=False)
        return points


# ── Exécution d'un scénario ─────────────────────────────────

def executer_scenario(nom: str, n_camions: int, n_points: int) -> dict:
    """
    Exécute le pipeline complet pour un scénario donné.
    Retourne les résultats avec métriques de performance.
    """
    print(f"\n{'='*70}")
    print(f"  📋 Scénario : {nom}")
    print(f"     {n_camions} camions — {n_points} points de collecte")
    print(f"{'='*70}")

    # Générer ou charger les données
    t0 = time.perf_counter()
    points = charger_ou_creer_dataset(n_points)
    camions = generer_camions(n_camions)
    n_zones = max(2, n_camions // 2)
    zones = generer_zones(points, n_zones)
    t_data = time.perf_counter() - t0

    poids_total_collecte = sum(p.volume_total for p in points)
    print(f"  ✓ Données générées en {t_data*1000:.1f} ms")
    print(f"    Poids total à collecter : {poids_total_collecte:.0f} kg")
    print(f"    Nb bennes moyen/point   : {sum(2 if p.volume_total < 400 else 3 for p in points)/len(points):.1f}")
    print(f"    Poids moyen/point       : {poids_total_collecte/len(points):.0f} kg")

    # ── Niveau 1 : Graphe routier ──
    t1 = time.perf_counter()
    graphe = GrapheRoutier(DEPOT, points)
    t_graphe = time.perf_counter() - t1
    print(f"  ✓ Niveau 1 (Graphe)       : {t_graphe*1000:.1f} ms — matrice {graphe.n}×{graphe.n}")

    # ── Niveau 2 : Affectation ──
    t2 = time.perf_counter()
    affecteur = AffectateurBiparti(zones, camions, points)
    affectation = affecteur.affecter()
    t_affectation = time.perf_counter() - t2
    print(f"  ✓ Niveau 2 (Affectation)  : {t_affectation*1000:.1f} ms — {len(affectation)} camions affectés")

    # ── Niveau 4 : Optimisation VRP ──
    t4 = time.perf_counter()
    optimiseur = OptimiseurVRP(graphe, camions, points, DEPOT, landfill=LANDFILL)
    vrp_result = optimiseur.optimiser()
    t_vrp = time.perf_counter() - t4
    print(f"  ✓ Niveau 4 (VRP SDVRP)    : {t_vrp*1000:.1f} ms — {vrp_result['num_trucks_used']} camions utilisés")

    # ── Niveau 3 : Planification ──
    t3 = time.perf_counter()
    planificateur = PlanificateurTriparti(graphe)
    camions_map = {c.id: c for c in camions}
    plannings = []
    for route in vrp_result.get("routes", []):
        visits = route.get("visits", [])
        cid = route.get("camion_id")
        c = camions_map.get(cid)
        if c and visits:
            p = planificateur.planifier_tournee(visits, c)
            plannings.append(p)
    t_planification = time.perf_counter() - t3
    print(f"  ✓ Niveau 3 (Planification): {t_planification*1000:.1f} ms")

    # ── Niveau 4b : Multi-objectif ──
    t_mo = time.perf_counter()
    evaluateur = OptimiseurMultiObjectif()
    evaluation = evaluateur.evaluer(vrp_result)
    t_multi = time.perf_counter() - t_mo

    t_total = time.perf_counter() - t0

    # ── Métriques par camion ──
    camion_metrics = []
    for route in vrp_result.get("routes", []):
        cid = route["camion_id"]
        dist = route.get("distance_km", 0)
        tonnage = sum(
            v.get("quantite_collectee", 0)
            for v in route.get("visits", [])
            if not v.get("is_landfill_trip", False)
        )
        tonnage_km = (tonnage / dist) if dist > 0 else 0
        landfill_trips = route.get("landfill_trips", 0)

        camion_obj = camions_map.get(cid)
        camion_metrics.append({
            "camion_id": cid,
            "camion_nom": camion_obj.nom if camion_obj else f"Camion {cid}",
            "capacite_kg": camion_obj.capacite if camion_obj else 0,
            "distance_km": round(dist, 2),
            "tonnage_collecte_kg": round(tonnage, 1),
            "tonnage_par_km": round(tonnage_km, 2),
            "nb_points_visites": len([
                v for v in route.get("visits", [])
                if not v.get("is_landfill_trip", False)
            ]),
            "nb_voyages_decharge": landfill_trips,
        })

    # Moyennes
    total_tonnage = sum(m["tonnage_collecte_kg"] for m in camion_metrics)
    total_distance = vrp_result.get("total_distance_km", 0)
    avg_tonnage_km = (
        sum(m["tonnage_par_km"] for m in camion_metrics) / len(camion_metrics)
        if camion_metrics else 0
    )

    # ── Affichage des résultats ──
    print(f"\n  {'─'*66}")
    print(f"  📊 RÉSULTATS — {nom}")
    print(f"  {'─'*66}")
    print(f"  {'Camion':<25} {'Distance':>10} {'Tonnage':>10} {'Ton/km':>10} {'Voyages':>8}")
    print(f"  {'─'*66}")
    for m in camion_metrics:
        print(f"  {m['camion_nom']:<25} {m['distance_km']:>8.2f} km"
              f" {m['tonnage_collecte_kg']:>8.1f} kg"
              f" {m['tonnage_par_km']:>8.2f}"
              f" {m['nb_voyages_decharge']:>6}")
    print(f"  {'─'*66}")
    print(f"  {'TOTAL / MOYENNE':<25} {total_distance:>8.2f} km"
          f" {total_tonnage:>8.1f} kg"
          f" {avg_tonnage_km:>8.2f}"
          f" {sum(m['nb_voyages_decharge'] for m in camion_metrics):>6}")

    print(f"\n  ⏱️  Performance :")
    print(f"     Temps total            : {t_total*1000:.1f} ms")
    print(f"     — Génération données   : {t_data*1000:.1f} ms")
    print(f"     — Graphe routier       : {t_graphe*1000:.1f} ms")
    print(f"     — Affectation          : {t_affectation*1000:.1f} ms")
    print(f"     — VRP SDVRP            : {t_vrp*1000:.1f} ms")
    print(f"     — Planification        : {t_planification*1000:.1f} ms")
    print(f"     — Multi-objectif       : {t_multi*1000:.1f} ms")

    if evaluation:
        metrics = evaluation.get("metrics", {})
        scores = evaluation.get("scores", {})
        print(f"\n  🎯 Multi-objectif :")
        print(f"     CO₂ total           : {metrics.get('co2_total_kg', 0):.2f} kg")
        print(f"     Coût total          : {metrics.get('cout_total_mad', 0):.2f} MAD")
        print(f"     Utilisation moyenne  : {metrics.get('utilisation_moyenne_pct', 0):.1f}%")
        print(f"     Score global        : {scores.get('global', 0):.1f} / 100")

    all_collected = vrp_result.get("all_collected", False)
    pending = len(vrp_result.get("points_pending", []))
    print(f"\n  {'✅' if all_collected else '⚠️'}  Collecte : "
          f"{'Tous les points collectés' if all_collected else f'{pending} points non collectés'}")

    return {
        "scenario": nom,
        "n_camions": n_camions,
        "n_points": n_points,
        "poids_total_kg": round(poids_total_collecte, 1),
        "depot": DEPOT.to_dict(),
        "performance": {
            "temps_total_ms": round(t_total * 1000, 1),
            "temps_graphe_ms": round(t_graphe * 1000, 1),
            "temps_affectation_ms": round(t_affectation * 1000, 1),
            "temps_vrp_ms": round(t_vrp * 1000, 1),
            "temps_planification_ms": round(t_planification * 1000, 1),
            "temps_multi_objectif_ms": round(t_multi * 1000, 1),
        },
        "resultats": {
            "distance_totale_km": round(total_distance, 2),
            "tonnage_total_kg": round(total_tonnage, 1),
            "tonnage_par_km_moyen": round(avg_tonnage_km, 2),
            "camions_utilises": vrp_result.get("num_trucks_used", 0),
            "tous_collectes": all_collected,
            "points_non_collectes": pending,
        },
        "evaluation_multi_objectif": evaluation,
        "camions_detail": camion_metrics,
        "vrp_routes": vrp_result.get("routes", []),
    }


# ── Point d'entrée ──────────────────────────────────────────

def run_all_benchmarks() -> list[dict]:
    """Exécute tous les scénarios de benchmark."""
    print("\n" + "█" * 70)
    print("  🚛  BENCHMARK — Système de Collecte de Déchets Agadir")
    print("  📅  Exécution des tests de performance")
    print("█" * 70)

    results = []
    for scenario in SCENARIOS:
        result = executer_scenario(
            scenario["nom"], scenario["camions"], scenario["points"]
        )
        results.append(result)

    # ── Résumé comparatif ──
    print("\n\n" + "█" * 70)
    print("  📈  RÉSUMÉ COMPARATIF")
    print("█" * 70)
    print(f"\n  {'Scénario':<18} {'Pts':>5} {'Cam':>5} {'Temps':>10} {'Dist':>10}"
          f" {'Tonnage':>10} {'T/km':>8} {'Score':>7}")
    print(f"  {'─'*75}")
    for r in results:
        perf = r["performance"]
        res = r["resultats"]
        score = (r.get("evaluation_multi_objectif") or {}).get("scores", {}).get("global", 0)
        print(f"  {r['scenario']:<18} {r['n_points']:>5} {r['n_camions']:>5}"
              f" {perf['temps_total_ms']:>8.1f}ms"
              f" {res['distance_totale_km']:>8.2f}km"
              f" {res['tonnage_total_kg']:>8.1f}kg"
              f" {res['tonnage_par_km_moyen']:>7.2f}"
              f" {score:>6.1f}")
    print(f"  {'─'*75}")

    # Sauvegarder les résultats
    results_dir = os.path.join(ROOT, "tests", "results")
    os.makedirs(results_dir, exist_ok=True)
    results_file = os.path.join(results_dir, "benchmark_results.json")
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  💾 Résultats sauvegardés : {results_file}")
    print("█" * 70 + "\n")

    return results


if __name__ == "__main__":
    run_all_benchmarks()
