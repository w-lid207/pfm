"""
Configuration de l'application Flask
Gestion des environnements : développement, test, production
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuration de base partagée par tous les environnements"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Agadir coordinates (center)
    MAP_CENTER_LAT = 30.4278
    MAP_CENTER_LNG = -9.5981
    MAP_DEFAULT_ZOOM = 13

    # Paramètres métier
    TRUCK_CAPACITY_M3 = 10.0          # m³
    TRUCK_SPEED_KMH = 30.0            # km/h en ville
    CO2_PER_KM = 0.27                 # kg CO2 / km (camion diesel moyen)
    FUEL_COST_PER_KM = 0.85           # MAD / km
    WORKING_HOURS_PER_DAY = 8         # heures

    CORS_ORIGINS = ["http://localhost:5000", "http://127.0.0.1:5000"]


class DevelopmentConfig(Config):
    """Configuration développement avec SQLite"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(BASE_DIR, "database", "collecte.db")}'
    )


class ProductionConfig(Config):
    """Configuration production avec PostgreSQL"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://user:password@localhost/collecte_agadir'
    )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Mapping des configs
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}


def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)
