# 📦 Guide de Soumission — Projet Collecte Agadir

## Lancement Rapide

### Windows (un clic)
```
Double-cliquer sur run.bat
```

### Manuel
```bash
# 1. Créer l'environnement virtuel
python -m venv .venv

# 2. Activer l'environnement
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'application
python -m webapp.app
```

L'application démarre sur **http://localhost:5050**
- **Login** : `admin` / `admin123`

---

## Tests de Benchmark

### Via la webapp
1. Naviguer vers http://localhost:5050/tests
2. Cliquer sur les boutons pour lancer chaque scénario

### En ligne de commande
```bash
python -m tests.benchmark_tests
```

Les résultats sont sauvegardés dans `tests/results/benchmark_results.json`

---

## Structure du Projet

```
collecte_agadir1/
├── commun/              # Modèles de données partagés
├── niveau1/             # Graphe routier (Haversine)
├── niveau2/             # Affectation bipartie (glouton)
├── niveau3/             # Planification temporelle
├── niveau4/             # VRP SDVRP + Multi-objectif
├── niveau5/             # Simulation temps réel
├── webapp/              # Application web Flask
│   ├── templates/       # Pages HTML (dashboard, carte, simulation, tests)
│   ├── services/        # Pipeline d'optimisation
│   └── routes.py        # API REST
├── tests/               # Tests de benchmark
│   ├── benchmark_tests.py
│   └── results/         # Résultats JSON
├── docs/                # Documentation
│   └── document_algorithmes.md
├── run.bat              # Lancement en un clic (Windows)
├── requirements.txt     # Dépendances Python
└── README_SOUMISSION.md # Ce fichier
```

---

## Documentation

- **Algorithmes** : `docs/document_algorithmes.md` — Explication détaillée de chaque algorithme, complexité, et discussion d'optimalité
- **README** : `README.md` — Documentation technique complète du projet

---

## Création de l'Archive

```bash
# Depuis le répertoire parent du projet
# Exclure les fichiers temporaires et environnements virtuels

# Windows (PowerShell)
Compress-Archive -Path collecte_agadir1\* -DestinationPath collecte_agadir1.zip -Force

# Ou manuellement : clic droit → Compresser en fichier ZIP
# ⚠️ Exclure les dossiers : .venv/, venv/, __pycache__/, .idea/, node_modules/
```

---

## Transparence IA

Les conversations avec les outils d'IA utilisés pour le développement de ce projet sont documentées et incluses dans l'archive de soumission, conformément aux exigences de transparence.
