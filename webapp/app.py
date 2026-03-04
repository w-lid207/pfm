"""
Webapp — Application Flask principale.

Point d'entrée du serveur web pour le Système d'Optimisation
des Tournées de Collecte.

Usage:
    python -m webapp.app
"""
import sys
import os

# Ajouter le répertoire racine pour les imports niveau*
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from flask import Flask
from flask_cors import CORS


def create_app() -> Flask:
    """Factory pattern Flask."""
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    app.config['SECRET_KEY'] = 'collecte-opt-secret-2024'
    CORS(app, resources={r'/api/*': {'origins': '*'}})

    # Enregistrement du blueprint
    from webapp.routes import api_bp
    app.register_blueprint(api_bp)

    return app


# ── Point d'entrée ──────────────────────────────────────────
app = create_app()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  🚛 Système d'Optimisation des Tournées de Collecte")
    print("  📍 Pipeline 5 niveaux — Web Application")
    print("=" * 60)
    print("  URL : http://localhost:5050")
    print("=" * 60 + "\n")
    app.run(host='0.0.0.0', port=5050, debug=True)
