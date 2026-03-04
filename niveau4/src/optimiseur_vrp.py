"""
Niveau 4 — Optimiseur VRP avec Split Delivery (SDVRP)

Cluster-First, Route-Second :
- Les points sont répartis en N groupes (1 par camion) par angle depuis le dépôt.
- Chaque camion dessert son propre groupe.
- Si un camion est surchargé, le surplus est repris par un autre (split delivery).
- 2-opt améliore chaque route individuellement.
"""
import math
import copy
from typing import Dict, List, Tuple

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from commun.models import Camion, PointCollecte, Depot
from niveau1.src.graphe_routier import GrapheRoutier
from webapp.services.fuel_service import FuelService


class OptimiseurVRP:
    """
    Optimiseur VRP — Cluster-First, Route-Second avec support SDVRP.
    """

    def __init__(self, graphe: GrapheRoutier, camions: List[Camion],
                 points: List[PointCollecte], depot: Depot,
                 landfill: Dict = None):
        self.graphe = graphe
        self.camions = camions
        self.points = points
        self.depot = depot
        self.landfill = landfill or {"lat": 30.38, "lng": -9.55}
        self.matrix = graphe.get_matrix()
        self.fuel_stations = [
            {"lat": 30.40, "lng": -9.58, "nom": "Station Essence A"},
            {"lat": 30.43, "lng": -9.60, "nom": "Station Essence B"}
        ]

    # ── API publique ─────────────────────────────────────────

    def optimiser(self) -> Dict:
        """
        Lance l'optimisation VRP.
        Répartit les points entre tous les camions disponibles,
        puis optimise chaque route individuellement.
        """
        points = copy.deepcopy(self.points)
        camions = copy.deepcopy(self.camions)

        n_trucks = len(camions)
        n_points = len(points)

        if n_points == 0 or n_trucks == 0:
            return self._format_result([], points)

        # ── ÉTAPE 1 : Répartir les points entre les camions ──
        clusters = self._cluster_points(points, n_trucks)

        # ── ÉTAPE 2 : Construire une route par camion ────────
        all_routes = []
        overflow_points = []  # Points non servis (surplus)

        for truck_idx, camion in enumerate(camions):
            cluster = clusters.get(truck_idx, [])
            if not cluster:
                continue

            route_result = self._build_route_for_cluster(
                points, cluster, camion
            )

            if route_result["visits"]:
                all_routes.append(route_result)

            # Collecter les points avec volume restant (overflow)
            for pid in cluster:
                pt = next((p for p in points if p.id == pid), None)
                if pt and pt.volume_restant > 0:
                    overflow_points.append(pid)

        # ── ÉTAPE 3 : Traiter les surplus (split delivery) ───
        if overflow_points:
            for camion in camions:
                camion_route = next(
                    (r for r in all_routes if r["camion_id"] == camion.id),
                    None
                )
                remaining_cap = camion.capacite - sum(
                    v["quantite_collectee"]
                    for v in (camion_route["visits"] if camion_route else [])
                )
                if remaining_cap <= 0:
                    continue
                for pid in overflow_points[:]:
                    pt = next((p for p in points if p.id == pid), None)
                    if pt and pt.volume_restant > 0:
                        qty = min(remaining_cap, pt.volume_restant)
                        pt.volume_restant -= qty
                        remaining_cap -= qty
                        if camion_route:
                            camion_route["visits"].append({
                                "point_id": pt.id,
                                "point_index": self._point_graph_idx(pt.id),
                                "lat": pt.lat,
                                "lng": pt.lng,
                                "nom": pt.nom,
                                "volume_total": pt.volume_total,
                                "quantite_collectee": round(qty, 1),
                                "volume_restant_apres": round(pt.volume_restant, 1),
                            })
                        if pt.volume_restant <= 0:
                            overflow_points.remove(pid)
                        if remaining_cap <= 0:
                            break

        # Recalculate coordinates for each route
        for route in all_routes:
            route["coordinates"] = self._build_coordinates(route)
            # Recalculate distance
            indices = [v["point_index"] for v in route["visits"]]
            if indices:
                route["route_indices"] = indices
                route["distance_km"] = round(self._route_distance(indices), 2)

        return self._format_result(all_routes, points)

    # ── Clustering par angle ─────────────────────────────────

    def _cluster_points(self, points: List[PointCollecte],
                        n_trucks: int) -> Dict[int, List[int]]:
        """
        Répartit les points en n_trucks groupes par angle depuis le dépôt.
        Cela garantit que chaque camion a ses propres points à desservir.
        """
        if n_trucks <= 0:
            return {}
        if n_trucks == 1:
            return {0: [p.id for p in points]}

        # Calculer l'angle de chaque point depuis le dépôt
        angles = []
        for p in points:
            dx = p.lng - self.depot.lng
            dy = p.lat - self.depot.lat
            angle = math.atan2(dy, dx)
            angles.append((angle, p.id, p.volume_total))

        # Trier par angle
        angles.sort(key=lambda x: x[0])

        # Répartir les points en n_trucks groupes
        clusters: Dict[int, List[int]] = {i: [] for i in range(n_trucks)}
        points_per_truck = max(1, len(angles) // n_trucks)

        for idx, (angle, pid, vol) in enumerate(angles):
            truck_idx = min(idx // points_per_truck, n_trucks - 1)
            clusters[truck_idx].append(pid)

        # S'assurer qu'aucun cluster n'est vide si possible
        non_empty = [k for k, v in clusters.items() if v]
        empty = [k for k, v in clusters.items() if not v]
        for empty_idx in empty:
            # Prendre un point du plus gros cluster
            biggest = max(non_empty, key=lambda k: len(clusters[k]))
            if len(clusters[biggest]) > 1:
                clusters[empty_idx].append(clusters[biggest].pop())
                non_empty.append(empty_idx)

        return clusters

    # ── Construction de route pour un cluster ────────────────

    def _build_route_for_cluster(self, points: List[PointCollecte],
                                  cluster_pids: List[int],
                                  camion: Camion) -> Dict:
        """
        Construit une route multi-voyage pour un sous-ensemble de points.
        Le camion fait des allers-retours à la décharge quand il est plein,
        puis revient continuer la collecte jusqu'à épuisement total.
        """
        n = len(self.points)
        visits = []
        visited_order = []
        current_idx = 0  # dépôt
        total_dist = 0.0
        capacity_left = camion.capacite
        fuel_left = getattr(camion, 'capacite_reservoir', 200.0)
        fuel_consumption = getattr(camion, 'consommation_litre_par_km', 0.5)
        fuel_capacity = getattr(camion, 'capacite_reservoir', 200.0)
        seuil_critique = getattr(camion, 'seuil_critique', 40.0)
        
        landfill_trips = 0
        refuel_trips = 0
        total_fuel_used = 0.0

        # Map point_id → graph index
        point_index_map = {}
        for i, p in enumerate(self.points):
            point_index_map[p.id] = i + 1

        available_ids = set(cluster_pids)

        while available_ids:
            best_id = None
            best_dist = float('inf')
            best_graph_idx = -1

            for pid in available_ids:
                gidx = point_index_map.get(pid)
                if gidx is None or gidx >= len(self.matrix[0]):
                    continue
                d = self.matrix[current_idx][gidx]
                if d < best_dist:
                    best_dist = d
                    best_id = pid
                    best_graph_idx = gidx

            if best_id is None:
                break

            point = next((p for p in points if p.id == best_id), None)
            if not point: break

            # ── FUEL CHECK ──────────────────────────────────────────
            dist_to_depot_from_next = self.matrix[best_graph_idx][0]
            fuel_needed_to_go_and_return = FuelService.fuel_needed_for_route(best_dist + dist_to_depot_from_next, fuel_consumption)
            
            if fuel_left - (best_dist * fuel_consumption) < fuel_needed_to_go_and_return or fuel_left <= seuil_critique:
                # Must refuel at nearest station
                current_lat, current_lng = self._get_lat_lng(current_idx)
                nearest_station = min(self.fuel_stations, key=lambda s: GrapheRoutier.haversine(current_lat, current_lng, s["lat"], s["lng"]))
                dist_to_station = GrapheRoutier.haversine(current_lat, current_lng, nearest_station["lat"], nearest_station["lng"])
                dist_from_station_to_next = GrapheRoutier.haversine(nearest_station["lat"], nearest_station["lng"], point.lat, point.lng)
                
                # Appliquer la consommation vers la station
                fuel_consumed_to_station = dist_to_station * fuel_consumption
                fuel_left -= fuel_consumed_to_station
                total_fuel_used += fuel_consumed_to_station
                total_dist += dist_to_station
                
                refuel_trips += 1
                visits.append({
                    "point_id": -2,
                    "point_index": -2,
                    "lat": nearest_station["lat"],
                    "lng": nearest_station["lng"],
                    "nom": nearest_station["nom"],
                    "volume_total": 0,
                    "quantite_collectee": 0,
                    "volume_restant_apres": 0,
                    "is_refuel_trip": True,
                    "trip_number": refuel_trips,
                })
                
                # Plein fait
                fuel_left = fuel_capacity
                
                # Update distance and current pseudo-index for the trip to the destination
                best_dist = dist_from_station_to_next

            # Consume fuel to go to the expected next destination
            fuel_consumed = best_dist * fuel_consumption
            fuel_left -= fuel_consumed
            total_fuel_used += fuel_consumed
            
            total_dist += best_dist
            current_idx = best_graph_idx

            # Collecter autant que possible (peut nécessiter plusieurs voyages)
            while point.volume_restant > 0:
                quantite_collectee = min(capacity_left, point.volume_restant)
                if quantite_collectee <= 0:
                    # Truck is full — must go to landfill before collecting more
                    # Calculate fuel to landfill
                    current_lat, current_lng = self._get_lat_lng(current_idx)
                    dist_to_landfill = GrapheRoutier.haversine(current_lat, current_lng, self.landfill["lat"], self.landfill["lng"])
                    fuel_to_landfill = dist_to_landfill * fuel_consumption
                    fuel_left -= fuel_to_landfill
                    total_fuel_used += fuel_to_landfill
                    total_dist += dist_to_landfill
                    
                    visits.append({
                        "point_id": -1,
                        "point_index": -1,
                        "lat": self.landfill["lat"],
                        "lng": self.landfill["lng"],
                        "nom": "Décharge",
                        "volume_total": 0,
                        "quantite_collectee": 0,
                        "volume_restant_apres": 0,
                        "is_landfill_trip": True,
                        "trip_number": landfill_trips,
                    })
                    capacity_left = camion.capacite
                    
                    # Update current_pos logically to landfill? Just approximation.
                    continue

                point.volume_restant -= quantite_collectee
                capacity_left -= quantite_collectee

                visits.append({
                    "point_id": point.id,
                    "point_index": best_graph_idx,
                    "lat": point.lat,
                    "lng": point.lng,
                    "nom": point.nom,
                    "volume_total": point.volume_total,
                    "quantite_collectee": round(quantite_collectee, 1),
                    "volume_restant_apres": round(point.volume_restant, 1),
                    "trip_number": landfill_trips + 1,
                })

                if best_graph_idx not in visited_order:
                    visited_order.append(best_graph_idx)

                # Si le camion est plein après collecte, aller à la décharge
                if capacity_left <= 0 and point.volume_restant > 0:
                    # distance current -> landfill
                    current_lat, current_lng = self._get_lat_lng(current_idx)
                    d_land = GrapheRoutier.haversine(current_lat, current_lng, self.landfill["lat"], self.landfill["lng"])
                    total_dist += d_land
                    total_fuel_used += d_land * fuel_consumption
                    fuel_left -= d_land * fuel_consumption
                    
                    landfill_trips += 1
                    visits.append({
                        "point_id": -1,
                        "point_index": -1,
                        "lat": self.landfill["lat"],
                        "lng": self.landfill["lng"],
                        "nom": "Décharge",
                        "volume_total": 0,
                        "quantite_collectee": 0,
                        "volume_restant_apres": 0,
                        "is_landfill_trip": True,
                        "trip_number": landfill_trips,
                    })
                    capacity_left = camion.capacite

            available_ids.discard(best_id)

        # Retour au dépôt
        if current_idx != 0 and current_idx < len(self.matrix[0]):
            d_return = self.matrix[current_idx][0]
            total_dist += d_return
            total_fuel_used += d_return * fuel_consumption
            fuel_left -= d_return * fuel_consumption

        # 2-opt (seulement sur les indices de points uniques)
        if len(visited_order) >= 3:
            improved = self._two_opt(visited_order)
            total_dist = self._route_distance(improved)
            visited_order = improved

        # Si le camion n'est pas vide à la fin de sa tournée, il DOIT aller à la décharge
        if capacity_left < camion.capacite:
            landfill_trips += 1
            visits.append({
                "point_id": -1,
                "point_index": -1,
                "lat": self.landfill["lat"],
                "lng": self.landfill["lng"],
                "nom": "Décharge (Fin de tournée)",
                "volume_total": 0,
                "quantite_collectee": 0,
                "volume_restant_apres": 0,
                "is_landfill_trip": True,
                "trip_number": landfill_trips,
            })
            capacity_left = camion.capacite

        return {
            "camion_id": camion.id,
            "camion_capacite": camion.capacite,
            "visits": visits,
            "route_indices": visited_order,
            "distance_km": round(total_dist, 2),
            "landfill_trips": landfill_trips,
            "refuel_trips": refuel_trips,
            "fuel_used_liters": round(total_fuel_used, 2),
            "fuel_left_liters": round(max(0.0, fuel_left), 2),
        }

    # ── Helpers ───────────────────────────────────────────────

    def _point_graph_idx(self, pid: int) -> int:
        for i, p in enumerate(self.points):
            if p.id == pid:
                return i + 1
        return -1

    def _get_lat_lng(self, gidx: int) -> Tuple[float, float]:
        """Retourne les coordonnées correspondant à un index du graphe."""
        if gidx <= 0 or gidx > len(self.points):
            return self.depot.lat, self.depot.lng
        p = self.points[gidx - 1]
        return p.lat, p.lng

    def _build_coordinates(self, route: Dict) -> List[List[float]]:
        """Construit la liste de coordonnées: Dépôt → Points/Décharges → Dépôt."""
        coords = [[self.depot.lat, self.depot.lng]]
        visits = route.get("visits", [])
        
        for visit in visits:
            coords.append([visit["lat"], visit["lng"]])
            
        # Fin de la tournée : On retourne au dépôt (le passage par la décharge a déjà été ajouté dans les `visits` si nécessaire)
        coords.append([self.depot.lat, self.depot.lng])
            
        return coords

    # ── 2-opt ────────────────────────────────────────────────

    def _two_opt(self, route: List[int], max_iter: int = 100) -> List[int]:
        """Amélioration 2-opt sur la route."""
        best = route[:]
        improved = True
        iterations = 0

        while improved and iterations < max_iter:
            improved = False
            iterations += 1
            for i in range(len(best) - 1):
                for j in range(i + 2, len(best)):
                    prev_i = 0 if i == 0 else best[i - 1]
                    next_j = 0 if j == len(best) - 1 else best[j + 1]

                    current_cost = (self.matrix[prev_i][best[i]]
                                    + self.matrix[best[j]][next_j])
                    new_cost = (self.matrix[prev_i][best[j]]
                                + self.matrix[best[i]][next_j])

                    if new_cost < current_cost - 1e-10:
                        best[i:j + 1] = best[i:j + 1][::-1]
                        improved = True
        return best

    def _route_distance(self, route: List[int]) -> float:
        """Distance totale dépôt → route → dépôt."""
        if not route:
            return 0.0
        dist = self.matrix[0][route[0]]
        for i in range(len(route) - 1):
            dist += self.matrix[route[i]][route[i + 1]]
        dist += self.matrix[route[-1]][0]
        return dist

    # ── Formatage résultat ───────────────────────────────────

    def _format_result(self, all_routes: List[Dict],
                       points: List[PointCollecte]) -> Dict:
        """Formate les résultats de l'optimisation."""
        total_distance = sum(r["distance_km"] for r in all_routes)
        points_non_complets = [
            p.to_dict() for p in points if p.volume_restant > 0
        ]

        return {
            "routes": all_routes,
            "total_distance_km": round(total_distance, 2),
            "num_trucks_used": len(all_routes),
            "points_pending": points_non_complets,
            "all_collected": len(points_non_complets) == 0,
        }
