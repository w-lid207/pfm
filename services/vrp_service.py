"""
Service VRP (Vehicle Routing Problem)
Algorithme d'optimisation des tournées de collecte
Utilise une heuristique de type Clarke-Wright + 2-opt

Intégration OSRM :
- L'ordre des points est optimisé en interne (distances haversine).
- Une fois l'ordre trouvé, on appelle OSRM pour obtenir une polyline
  qui suit réellement le réseau routier d'Agadir.
"""
import math
from typing import List, Dict, Tuple

from services.osrm_service import build_osrm_route, OsrmRoutingError


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcule la distance en km entre deux coordonnées GPS"""
    R = 6371  # Rayon de la Terre en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def build_distance_matrix(points: List[Dict]) -> List[List[float]]:
    """
    Construit la matrice de distances entre tous les points
    points: liste de dicts avec 'latitude' et 'longitude'
    """
    n = len(points)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = haversine(
                    points[i]['latitude'], points[i]['longitude'],
                    points[j]['latitude'], points[j]['longitude']
                )
    return matrix


def nearest_neighbor(points: List[Dict], depot: Dict,
                     capacity: float = 10.0) -> List[List[int]]:
    """
    Heuristique du Plus Proche Voisin pour construire des routes initiales
    Retourne une liste de routes (chaque route = liste d'indices de points)
    """
    n = len(points)
    all_points = [depot] + points  # index 0 = dépôt
    matrix = build_distance_matrix(all_points)

    unvisited = set(range(1, n + 1))
    routes = []

    while unvisited:
        route = []
        current = 0  # départ du dépôt
        load = 0.0

        while unvisited:
            # Cherche le plus proche non visité avec capacité suffisante
            best_next = None
            best_dist = float('inf')
            for j in unvisited:
                demand = all_points[j].get('capacite_m3', 1.0) * all_points[j].get('taux_remplissage', 0.5)
                if load + demand <= capacity:
                    if matrix[current][j] < best_dist:
                        best_dist = matrix[current][j]
                        best_next = j
            if best_next is None:
                break
            route.append(best_next)
            load += all_points[best_next].get('capacite_m3', 1.0) * all_points[best_next].get('taux_remplissage', 0.5)
            unvisited.remove(best_next)
            current = best_next

        if route:
            routes.append(route)

    return routes, all_points, matrix


def two_opt_improve(route: List[int], matrix: List[List[float]],
                    max_iter: int = 100) -> List[int]:
    """
    Amélioration 2-opt : inverse des segments pour réduire la distance totale
    """
    best = route[:]
    improved = True
    iterations = 0

    while improved and iterations < max_iter:
        improved = False
        iterations += 1
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best)):
                # Coût actuel
                current = matrix[best[i - 1]][best[i]] + matrix[best[j - 1]][best[j % len(best)]]
                # Coût si on inverse le segment [i..j-1]
                new_dist = matrix[best[i - 1]][best[j - 1]] + matrix[best[i]][best[j % len(best)]]
                if new_dist < current - 1e-10:
                    best[i:j] = best[i:j][::-1]
                    improved = True
    return best


def optimize_routes(points: List[Dict], depot: Dict,
                    num_trucks: int = 3,
                    truck_capacity: float = 10.0) -> Dict:
    """
    Fonction principale d'optimisation VRP
    Retourne les tournées optimisées avec métriques
    """
    if not points:
        return {'routes': [], 'total_distance': 0, 'savings_pct': 0}

    # Construction initiale par plus proche voisin
    routes, all_points, matrix = nearest_neighbor(points, depot, truck_capacity)

    # Limite au nombre de camions disponibles
    routes = routes[:num_trucks]

    # Amélioration 2-opt sur chaque route
    optimized_routes = []
    total_dist_before = 0
    total_dist_after = 0

    for route_indices in routes:
        if len(route_indices) < 3:
            optimized_routes.append(route_indices)
            continue

        # Distance avant 2-opt
        d_before = _route_distance(route_indices, 0, matrix)
        total_dist_before += d_before

        # Amélioration
        improved = two_opt_improve(route_indices, matrix)
        d_after = _route_distance(improved, 0, matrix)
        total_dist_after += d_after

        optimized_routes.append(improved)

    if not optimized_routes:
        return {'routes': [], 'total_distance': 0, 'savings_pct': 0}

    savings_pct = 0
    if total_dist_before > 0:
        savings_pct = round((1 - total_dist_after / total_dist_before) * 100, 1)

    # Construction du résultat détaillé
    result_routes = []
    for idx, route in enumerate(optimized_routes):
        route_points = [all_points[i] for i in route]
        dist = _route_distance(route, 0, matrix)

        # Points pour OSRM : dépôt + points de la tournée + retour dépôt
        osrm_points = [depot] + route_points + [depot]
        routing_error = None
        coords = []
        try:
            coords = build_osrm_route(osrm_points, strict=True)
        except OsrmRoutingError as e:
            routing_error = str(e)
            # Pas de fallback ligne droite : on ne trace rien (évite les traits qui traversent les bâtiments)

        result_routes.append({
            'truck_index': idx,
            'points': route_points,
            'point_ids': [p['id'] for p in route_points],
            'distance_km': round(dist, 2),
            'nb_points': len(route),
            'coordinates': coords,
            'routing_error': routing_error,
        })

    return {
        'routes': result_routes,
        'total_distance': round(sum(r['distance_km'] for r in result_routes), 2),
        'total_distance_before': round(total_dist_before, 2),
        'savings_pct': savings_pct,
        'num_trucks_used': len(result_routes),
    }


def _route_distance(route: List[int], depot_idx: int,
                    matrix: List[List[float]]) -> float:
    """Calcule la distance totale d'une route (dépôt → ... → dépôt)"""
    if not route:
        return 0.0
    dist = matrix[depot_idx][route[0]]
    for i in range(len(route) - 1):
        dist += matrix[route[i]][route[i + 1]]
    dist += matrix[route[-1]][depot_idx]
    return dist


def compute_metrics(distance_km: float, co2_per_km: float = 0.27,
                    fuel_cost_per_km: float = 0.85) -> Dict:
    """Calcule CO2 et coût à partir de la distance"""
    return {
        'co2_kg': round(distance_km * co2_per_km, 3),
        'cout_mad': round(distance_km * fuel_cost_per_km, 2),
        'duree_min': round(distance_km / 30 * 60, 1),  # vitesse 30 km/h
    }
