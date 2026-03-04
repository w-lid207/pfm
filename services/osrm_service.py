"""
Intégration simple avec OSRM pour obtenir des trajets routiers.

Pré-requis côté système :
- Lancer un serveur OSRM, par exemple via Docker :

  docker run -t -i -p 5001:5000 osrm/osrm-backend osrm-routed --algorithm mld /data/map.osrm

Et définir la variable d'environnement OSRM_BASE_URL si nécessaire.
"""

import os
import time
from typing import Dict, List, Optional, Tuple

import requests


# Serveur public officiel : https://router.project-osrm.org
# En local : OSRM_BASE_URL=http://localhost:5001 (Docker avec carte Maroc)
OSRM_BASE_URL = os.environ.get("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
OSRM_PROFILE = os.environ.get("OSRM_PROFILE", "driving")
OSRM_TIMEOUT_S = float(os.environ.get("OSRM_TIMEOUT_S", "25"))
MAX_RETRIES = 3


class OsrmRoutingError(RuntimeError):
    pass


def _build_multi_waypoint_route(latlngs: List[Tuple[float, float]]) -> List[List[float]]:
    """
    Route OSRM en découpant en morceaux de taille maximale pour éviter les limites de l'URL publique.
    latlngs: [(lat, lng), ...]
    Retour: [[lat, lng], ...] (polyline routière complète)
    """
    CHUNK_SIZE = 15
    full_route = []

    # S'il y a très peu de points ou un seul chunk, on fait une seule requête
    chunks = []
    for i in range(0, len(latlngs), CHUNK_SIZE - 1): # -1 pour avoir un recouvrement d'1 point entre les chunks
        chunk = latlngs[i:i + CHUNK_SIZE]
        if len(chunk) > 1:
            chunks.append(chunk)

    if not chunks:
        return []

    headers = {"User-Agent": "CollecteOpt-Agadir/1.0 (route optimisation)"}

    for idx, chunk in enumerate(chunks):
        coords_str = ";".join(f"{lng},{lat}" for lat, lng in chunk)
        url = f"{OSRM_BASE_URL}/route/v1/{OSRM_PROFILE}/{coords_str}"
        params = {"overview": "full", "geometries": "geojson"}

        last_error = None
        success = False
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=OSRM_TIMEOUT_S)
                resp.raise_for_status()
                data = resp.json()

                code = data.get("code", "")
                if code != "Ok" or not data.get("routes"):
                    msg = data.get("message") or code or "no route"
                    raise OsrmRoutingError(f"OSRM {code}: {msg}")

                coords_geojson = data["routes"][0]["geometry"]["coordinates"]
                # GeoJSON = [lon, lat] → Leaflet = [lat, lon]
                segment = [[lat, lon] for lon, lat in coords_geojson]
                
                if idx == 0:
                    full_route.extend(segment)
                else:
                    # Ne pas dupliquer la coordonnée de jonction
                    full_route.extend(segment[1:])
                
                success = True
                break

            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    time.sleep(0.5 * (attempt + 1))  # backoff
                    continue
                break
        
        if not success:
            raise OsrmRoutingError(f"OSRM chunk failed after {MAX_RETRIES + 1} attempts: {last_error}")

        # Limite serveur public ~1 req/s : pause entre les tronçons
        if idx < len(chunks) - 1:
            time.sleep(1.1)

    return full_route


def _route_leg(a: Tuple[float, float], b: Tuple[float, float]) -> List[List[float]]:
    """
    Route OSRM entre 2 points. Fallback temporaire pour les scripts annexes.
    a, b: (lat, lng)
    Retour: [[lat,lng], ...]
    """
    return _build_multi_waypoint_route([a, b])


def build_osrm_route(points: List[Dict], strict: bool = True) -> List[List[float]]:
    """
    Construit une route routière OSRM en une seule requête multi-waypoints.

    points: liste de dicts avec latitude/longitude dans l'ordre.
    Retour: [[lat,lng], ...] (polyline routière)
    """
    if len(points) < 2:
        p = points[0]
        return [[p["latitude"], p["longitude"]]]

    latlngs: List[Tuple[float, float]] = [(p["latitude"], p["longitude"]) for p in points]

    try:
        result = _build_multi_waypoint_route(latlngs)
    except Exception as e:
        if strict:
            raise OsrmRoutingError(str(e))
        return []

    if len(result) < 2 and strict:
        raise OsrmRoutingError("OSRM geometry too short")

    return result
