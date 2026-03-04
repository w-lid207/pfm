"""
Modèles de données - Initialisation
"""
from niveau1.src.database import db
from .user import User
from .zone import Zone
from .point_collecte import PointCollecte
from .camion import Camion
from .tournee import Tournee, TourneePoint
from .alert import Alert
from .security_log import SecurityLog

__all__ = [
    'db', 'User', 'Zone', 'PointCollecte',
    'Camion', 'Tournee', 'TourneePoint',
    'Alert', 'SecurityLog'
]
