# 🚛 Système d'Optimisation des Tournées de Collecte — Agadir

Système web complet pour la gestion et l'optimisation des tournées de collecte des déchets à **Agadir, Maroc**.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?logo=flask)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple?logo=bootstrap)
![Leaflet](https://img.shields.io/badge/Leaflet-1.9-green?logo=leaflet)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📸 Fonctionnalités

| Module | Fonctionnalités |
|--------|----------------|
| 🔐 Auth | Login/Register, JWT, BCrypt, Rôles Admin/Opérateur |
| 🗺️ Carte | OpenStreetMap + Leaflet, marqueurs, polylines VRP, GPS simulé |
| 📊 Dashboard | KPIs, Charts.js, CO2, distances, coûts |
| 🚛 VRP | Clarke-Wright + 2-opt, économies calculées, sauvegarde |
| 📅 Planning | Hebdomadaire, affectation camions |
| 🔔 Alertes | Temps réel via WebSocket, niveaux danger/warning/info |
| 📤 Export | CSV (Excel) + PDF (ReportLab) |
| 🌙 Dark Mode | Thème clair/sombre persistant |
| 📡 WebSocket | Socket.IO pour positions GPS temps réel |
| 🔒 Sécurité | Logs des connexions, middleware JWT |

---

## 🏗️ Architecture du Projet

```
collecte_agadir/
├── app.py                  # Application Flask + SocketIO
├── config.py               # Configuration multi-environnement
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
│
├── models/                 # Modèles SQLAlchemy
│   ├── user.py             # Utilisateurs + rôles
│   ├── zone.py             # Zones géographiques
│   ├── point_collecte.py   # Points de collecte (conteneurs)
│   ├── camion.py           # Flotte de camions
│   ├── tournee.py          # Tournées + séquences
│   ├── alert.py            # Alertes système
│   └── security_log.py     # Logs de sécurité
│
├── routes/                 # Blueprints Flask (REST API)
│   ├── auth.py             # /api/login, /api/register, ...
│   ├── points.py           # /api/points, /api/zones, /api/distances
│   ├── tournees.py         # /api/tournees, /api/optimisation-vrp, ...
│   └── dashboard.py        # /api/dashboard, /api/simulation, /api/alertes
│
├── services/               # Logique métier
│   ├── auth_service.py     # Hash bcrypt, JWT, logs
│   ├── vrp_service.py      # Algorithme VRP (NN + 2-opt)
│   ├── dashboard_service.py # KPIs et statistiques
│   └── simulation_service.py # GPS simulé, pannes, replanif.
│
├── utils/
│   ├── decorators.py       # @admin_required, @operateur_or_admin
│   └── export.py           # Export CSV + PDF (ReportLab)
│
├── templates/              # Jinja2 HTML
│   ├── base.html           # Layout principal avec navbar
│   ├── login.html          # Page d'authentification
│   ├── dashboard.html      # Tableau de bord + Charts
│   ├── carte.html          # Carte Leaflet + VRP
│   ├── tournees.html       # Gestion des tournées
│   ├── camions.html        # Flotte de camions
│   ├── points.html         # Points de collecte
│   ├── alertes.html        # Centre d'alertes
│   └── logs.html           # Logs de sécurité
│
├── static/
│   ├── css/main.css        # Styles avec CSS variables + dark mode
│   └── js/
│       ├── api.js          # Couche API (fetch + JWT)
│       └── app.js          # Auth guard, dark mode, WebSocket
│
└── database/
    └── seed.py             # Données de démonstration Agadir
```

---

## 🚀 Installation Rapide

### Option 1 : Installation locale

```bash
# 1. Cloner le projet
git clone https://github.com/your-repo/collecte-agadir.git
cd collecte-agadir

# 2. Environnement virtuel Python
python -m venv venv
source venv/bin/activate      # Linux/macOS
# ou
venv\Scripts\activate         # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configuration (copier et modifier)
cp .env.example .env

# 5. Démarrer l'application
python app.py
```

Ouvrez **http://localhost:5000** dans votre navigateur.

### Option 2 : Docker (recommandé)

```bash
# Démarrer tous les services (Flask + PostgreSQL)
docker-compose up -d

# Voir les logs
docker-compose logs -f web
```

---

## 🔑 Connexion Démonstration

| Rôle | Identifiant | Mot de passe | Accès |
|------|-------------|--------------|-------|
| Admin | `admin` | `admin123` | Tout + Logs sécurité |
| Opérateur | `operateur` | `oper123` | Dashboard, Carte, Tournées |

---

## 📡 API Endpoints

### Authentification
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/register` | Créer un compte |
| POST | `/api/login` | Connexion → JWT tokens |
| POST | `/api/refresh` | Rafraîchir token |
| GET | `/api/me` | Profil utilisateur |

### Niveau 1 — Points & Distances
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/points` | Liste des points (filtres: zone, priorité, type) |
| POST | `/api/points` | Créer un point |
| PUT | `/api/points/<id>` | Modifier un point |
| GET | `/api/distances` | Matrice de distances |
| GET | `/api/zones` | Liste des zones |

### Niveau 2 — Affectation
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/affectation` | Affecter camion à tournée |
| GET | `/api/affectation/resultat` | Vue des affectations du jour |

### Niveau 3 — Planification
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/planification` | Créer une tournée |
| GET | `/api/planification/hebdomadaire` | Planning de la semaine |

### Niveau 4 — Optimisation VRP
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/optimisation-vrp` | Lancer l'optimisation (NN + 2-opt) |
| GET | `/api/tournees` | Liste des tournées |
| PUT | `/api/tournees/<id>` | Mettre à jour statut |

### Niveau 5 — Dashboard & Simulation
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/dashboard` | KPIs et statistiques |
| POST | `/api/simulation` | Simulation GPS (move/breakdown/replan) |
| GET | `/api/simulation/positions` | Positions GPS en temps réel |
| GET | `/api/alertes` | Liste des alertes |
| GET | `/api/export/tournees/csv` | Export CSV |
| GET | `/api/export/tournees/pdf` | Export PDF |
| GET | `/api/security-logs` | Logs de sécurité (admin) |

---

## 🧠 Algorithme VRP

L'optimisation des tournées utilise une heuristique en deux phases :

1. **Phase 1 — Nearest Neighbor** : Construction initiale des routes par plus proche voisin avec respect des contraintes de capacité des camions.

2. **Phase 2 — 2-opt** : Amélioration locale par inversion de segments pour réduire la distance totale. Typiquement **15-30% d'économie** sur la distance.

```python
# Exemple d'utilisation du service VRP
from services.vrp_service import optimize_routes

result = optimize_routes(
    points=points_data,    # Liste de dicts avec lat/lng
    depot=depot_data,      # Position du dépôt
    num_trucks=3,          # Nombre de camions
    truck_capacity=10.0    # Capacité en m³
)
# result.routes → tournées optimisées avec coordonnées
# result.savings_pct → pourcentage d'économie
```

---

## ⚙️ Configuration

Variables d'environnement (`.env`) :

```env
FLASK_ENV=development           # development | production | testing
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
DATABASE_URL=sqlite:///database/collecte.db  # ou PostgreSQL URI
```

---

## 🛠️ Technologies

- **Backend** : Flask 3.0, Flask-JWT-Extended, Flask-Bcrypt, Flask-SQLAlchemy
- **Base de données** : SQLite (dev) / PostgreSQL (prod)
- **Temps réel** : Flask-SocketIO + Eventlet
- **Frontend** : HTML5, CSS3, Bootstrap 5, JavaScript ES6+
- **Carte** : Leaflet.js + OpenStreetMap
- **Graphiques** : Chart.js 4
- **Export** : ReportLab (PDF), CSV natif
- **Conteneur** : Docker + Docker Compose
- **CI/CD** : GitHub Actions

---

## 📄 Licence

MIT © 2024 — Système de Collecte Agadir
#   p f m  
 