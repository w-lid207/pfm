"""
Système d'Optimisation des Tournées de Collecte — Agadir
Application Flask principale avec WebSocket
"""
import os
from flask import Flask, render_template, redirect, url_for
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from config import get_config
from niveau1.src.database import db
from services.auth_service import bcrypt

# Extensions globales
jwt = JWTManager()
socketio = SocketIO()


def create_app(config_class=None):
    """Factory pattern Flask"""
    app = Flask(__name__)

    # Configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # ── Initialisation des extensions ──
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r'/api/*': {'origins': '*'}}, supports_credentials=True)
    # Mode threading : compatible Python 3.12+, pas besoin de gevent/eventlet
    socketio.init_app(app, cors_allowed_origins='*', async_mode='threading', logger=False)

    # ── Enregistrement des blueprints ──
    from routes.auth import auth_bp
    from routes.points import points_bp
    from routes.tournees import tournees_bp
    from routes.dashboard import dashboard_bp

    for bp in [auth_bp, points_bp, tournees_bp, dashboard_bp]:
        app.register_blueprint(bp)

    # ── Gestion des erreurs JWT ──
    @jwt.expired_token_loader
    def expired_token(_jwt_header, _jwt_payload):
        from flask import jsonify
        return jsonify({'error': 'Token expiré, reconnectez-vous'}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        from flask import jsonify
        return jsonify({'error': f'Token invalide: {reason}'}), 422

    @jwt.unauthorized_loader
    def unauthorized(reason):
        from flask import jsonify
        return jsonify({'error': 'Authentification requise'}), 401

    # ── Routes frontend ──
    @app.route('/')
    def index():
        return render_template('login.html')

    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/carte')
    def carte():
        return render_template('carte.html')

    @app.route('/tournees')
    def tournees():
        return render_template('tournees.html')

    @app.route('/camions')
    def camions():
        return render_template('camions.html')

    @app.route('/points')
    def points():
        return render_template('points.html')

    @app.route('/alertes')
    def alertes():
        return render_template('alertes.html')

    @app.route('/logs')
    def logs():
        return render_template('logs.html')

    # ── WebSocket events ──
    @socketio.on('connect')
    def on_connect():
        emit('connected', {'message': 'Connecté au serveur temps réel'})

    @socketio.on('request_positions')
    def handle_positions():
        from services.simulation_service import get_all_trucks_positions
        positions = get_all_trucks_positions()
        emit('truck_positions', {'positions': positions}, broadcast=True)

    @socketio.on('simulate_move')
    def handle_simulate():
        from models import Camion
        from services.simulation_service import simulate_truck_movement
        with app.app_context():
            camions = Camion.query.filter_by(statut='en_tournee', actif=True).all()
            updated = [simulate_truck_movement(c.id) for c in camions]
        emit('truck_positions', {'positions': updated}, broadcast=True)

    @socketio.on('new_alert')
    def handle_new_alert(data):
        emit('alert_received', data, broadcast=True)

    # ── Création des tables et seed ──
    with app.app_context():
        os.makedirs('database', exist_ok=True)
        db.create_all()

        from models import User, Zone, PointCollecte
        if User.query.count() == 0:
            from database.seed import seed_database
            from models import Camion, Tournee, TourneePoint, Alert
            seed_database(db, User, Zone, PointCollecte, Camion, Tournee, TourneePoint, Alert)
        else:
            # Base existante : ajouter la zone Inezgane (remplace Talborjt) si absente
            if not Zone.query.filter_by(code='INZ').first():
                from database.seed import seed_database
                from models import Camion, Tournee, TourneePoint, Alert
                seed_database(db, User, Zone, PointCollecte, Camion, Tournee, TourneePoint, Alert)

    return app


# ── Point d'entrée ──
app = create_app()

if __name__ == '__main__':
    print("\n" + "="*55)
    print("  🚛 Système de Collecte Agadir — Démarrage")
    print("="*55)
    print("  URL: http://localhost:5000")
    print("  Admin: admin / admin123")
    print("="*55 + "\n")
    socketio.run(app, host='0.0.0.0', port=8000, debug=True, use_reloader=False)

