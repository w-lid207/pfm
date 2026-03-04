"""
Webapp — Routes API (Blueprint).

Endpoints REST pour le frontend :
  POST /api/solve     — Lancer l'optimisation complète
  POST /api/simulate  — Avancer d'un pas de simulation
  GET  /api/status    — Statut du pipeline
  GET  /api/results   — Derniers résultats
  POST /api/osrm-route — Obtenir une route OSRM
"""
from functools import wraps
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session

api_bp = Blueprint('api', __name__)

# ── Admin credentials ────────────────────────────────────────
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin123'


def login_required(f):
    """Décorateur : exige une session authentifiée."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('api.login'))
        return f(*args, **kwargs)
    return wrapper


# ── Auth ─────────────────────────────────────────────────────

@api_bp.route('/')
def root():
    """Redirige vers le dashboard si connecté, sinon login."""
    if session.get('logged_in'):
        return redirect(url_for('api.dashboard'))
    return redirect(url_for('api.login'))


@api_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion admin."""
    if session.get('logged_in'):
        return redirect(url_for('api.dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('api.dashboard'))
        else:
            error = 'Identifiants incorrects. Réessayez.'

    return render_template('login.html', error=error)


@api_bp.route('/logout')
def logout():
    """Déconnexion."""
    session.clear()
    return redirect(url_for('api.login'))


# ── Pages frontend (protégées) ───────────────────────────────

@api_bp.route('/dashboard')
@login_required
def dashboard():
    """Tableau de bord avec métriques."""
    return render_template('dashboard.html')


@api_bp.route('/carte')
@login_required
def carte():
    """Page carte interactive."""
    return render_template('index.html')


@api_bp.route('/simulation')
@login_required
def simulation_page():
    """Page de simulation temps réel."""
    return render_template('simulation.html')

@api_bp.route('/simulation-camion')
@login_required
def simulation_camion_page():
    """Page de simulation de chargement d'un camion (3000 kg)."""
    return render_template('simulation_camion.html')





# ── API REST ─────────────────────────────────────────────────

@api_bp.route('/api/solve', methods=['POST'])
def solve():
    """
    Lance l'optimisation complète 5 niveaux.

    Body JSON attendu :
    {
      "depot": {"lat": 33.5731, "lng": -7.5898},
      "points": [{"lat": ..., "lng": ..., "volume": ...}, ...],
      "zones": [{"points": [0, 1]}, ...],
      "camions": [{"capacite": 5000, "cout_fixe": 200}, ...],
      "parametres": {"multi_objectif": true, "simulation": true}
    }
    """
    from webapp.services.pipeline_service import solve_full_problem

    data = request.get_json()
    if not data:
        return jsonify({"error": "Corps JSON requis"}), 400

    if not data.get("points"):
        return jsonify({"error": "Au moins un point de collecte requis"}), 400

    result = solve_full_problem(data)

    status_code = 200 if result.get("success") else 500
    return jsonify(result), status_code


@api_bp.route('/api/simulate', methods=['POST'])
def simulate():
    """Avance la simulation d'un pas et retourne les positions."""
    from webapp.services.pipeline_service import simulate_step
    result = simulate_step()
    return jsonify(result), 200


@api_bp.route('/api/status', methods=['GET'])
def status():
    """Retourne le statut courant du pipeline."""
    from webapp.services.pipeline_service import get_status
    return jsonify(get_status()), 200


@api_bp.route('/api/results', methods=['GET'])
def results():
    """Retourne les derniers résultats d'optimisation."""
    from webapp.services.pipeline_service import get_results
    return jsonify(get_results()), 200


@api_bp.route('/api/run-benchmark', methods=['POST'])
def run_benchmark():
    """
    Exécute un test de benchmark avec un nombre donné de camions et points.
    Body: {"camions": 5, "points": 50}
    """
    import sys as _sys
    import os as _os
    ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
    if ROOT not in _sys.path:
        _sys.path.insert(0, ROOT)

    from benchmarks.benchmark_runner import executer_scenario

    data = request.get_json()
    if not data:
        return jsonify({"error": "Corps JSON requis"}), 400

    n_camions = data.get("camions", 5)
    n_points = data.get("points", 50)

    # Determine scenario name
    if n_points <= 50:
        nom = "Petit"
    elif n_points <= 100:
        nom = "Intermédiaire"
    else:
        nom = "Grand"

    try:
        result = executer_scenario(nom, n_camions, n_points)

        # Also include VRP routes for map display
        vrp_routes = result.get("_vrp_routes", [])

        return jsonify({
            "success": True,
            **result,
            "vrp_routes": vrp_routes,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


_osrm_cache = {}  # In-memory segment cache


@api_bp.route('/api/osrm-route', methods=['POST'])
def osrm_route():
    """
    Obtient des routes OSRM réelles pour une séquence de coordonnées.
    Body: {"coordinates": [[lat,lng], [lat,lng], ...]}
    Utilise un cache par segment pour éviter les appels redondants.
    """
    import requests as req
    import time
    import math

    data = request.get_json()
    coords = data.get('coordinates', [])
    if len(coords) < 2:
        return jsonify({"error": "Au moins 2 coordonnées requises"}), 400

    OSRM_BASE = "https://router.project-osrm.org"
    CHUNK_SIZE = 50
    full_route = []

    for i in range(0, len(coords) - 1, CHUNK_SIZE - 1):
        chunk = coords[i:i + CHUNK_SIZE]
        coords_str = ";".join([f"{c[1]:.6f},{c[0]:.6f}" for c in chunk])
        url = f"{OSRM_BASE}/route/v1/driving/{coords_str}"
        params = {"overview": "full", "geometries": "geojson"}
        
        success = False
        for attempt in range(3):
            try:
                resp = req.get(url, params=params,
                               headers={"User-Agent": "CollecteOpt/2.0"},
                               timeout=3)
                if resp.status_code == 429:
                    time.sleep(1)
                    continue
                resp.raise_for_status()
                result = resp.json()
                if result.get("code") == "Ok" and result.get("routes"):
                    segment = [[lat, lon] for lon, lat in result["routes"][0]["geometry"]["coordinates"]]
                    if full_route:
                        full_route.extend(segment[1:])
                    else:
                        full_route.extend(segment)
                    success = True
                    break
            except Exception:
                pass
                
        if not success:
            if full_route:
                full_route.extend(chunk[1:])
            else:
                full_route.extend(chunk)
                
        if i + CHUNK_SIZE - 1 < len(coords) - 1:
            time.sleep(0.2)

    return jsonify({
        "coordinates": full_route,
        "segments_fetched": math.ceil(len(coords) / (CHUNK_SIZE - 1)),
    }), 200
