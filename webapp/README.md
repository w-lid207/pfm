# 🚛 Système d'Optimisation des Tournées de Collecte — Web Application

Application web complète pour l'optimisation des tournées de collecte de déchets,
intégrant un pipeline d'optimisation à 5 niveaux avec support SDVRP (Split Delivery VRP).

## Architecture

```
projet_collecte_dechets/
│
├── commun/              # Modèles partagés (dataclasses)
├── niveau1/             # Graphe routier (matrice de distances)
├── niveau2/             # Affectation camion ↔ zone (biparti)
├── niveau3/             # Planification temporelle
├── niveau4/             # Optimisation VRP + Multi-objectif
├── niveau5/             # Simulation temps réel
│
├── webapp/              # Application Flask
│   ├── app.py           # Point d'entrée Flask
│   ├── routes.py        # API REST (Blueprint)
│   ├── services/
│   │   └── pipeline_service.py  # Orchestrateur central
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/app.js
│   └── templates/
│       ├── index.html       # Carte interactive
│       ├── dashboard.html   # Tableau de bord
│       └── simulation.html  # Simulation temps réel
│
└── README.md
```

## Installation

```bash
cd collecte_agadir

# Créer un environnement virtuel
python -m venv .venv

# Activer l'environnement
# Windows :
.venv\Scripts\activate
# Linux/Mac :
source .venv/bin/activate

# Installer les dépendances
pip install -r webapp/requirements.txt
```

## Démarrage

```bash
python -m webapp.app
```

Ouvrir dans le navigateur : **http://localhost:5000**

## Utilisation

1. **Rechercher une ville** — tapez le nom dans la barre de recherche
2. **Placer le dépôt** — cliquez sur la carte en mode « Dépôt »
3. **Ajouter des points** — passez en mode « Points » et cliquez
4. **Définir des zones** — entrez les numéros de points
5. **Configurer les camions** — ajoutez capacité et coût
6. **Lancer l'optimisation** — cliquez sur « 🚀 Lancer l'Optimisation »
7. **Voir les résultats** — routes colorées, métriques, animation

## API Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| POST | `/api/solve` | Lance l'optimisation complète |
| POST | `/api/simulate` | Avance la simulation d'un pas |
| GET | `/api/status` | Statut du pipeline |
| GET | `/api/results` | Derniers résultats |

## Fonctionnalités

- ✅ Pipeline 5 niveaux (Graphe → Affectation → Planning → VRP → Simulation)
- ✅ SDVRP — Split Delivery Vehicle Routing Problem
- ✅ Carte interactive Leaflet + OpenStreetMap
- ✅ Animation des camions en temps réel
- ✅ Tableau de bord multi-objectif (distance, CO₂, coût, utilisation)
- ✅ Support 100 points, 10 camions, < 5 secondes
