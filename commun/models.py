"""
Modèles de données partagés (dataclasses pures, sans dépendance BDD).

Utilisés par le pipeline d'optimisation (niveaux 1-5) et le webapp.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Depot:
    """Dépôt central (point de départ / retour des camions)."""
    lat: float
    lng: float
    nom: str = "Dépôt"

    def to_dict(self) -> dict:
        return {"lat": self.lat, "lng": self.lng, "nom": self.nom}


@dataclass
class PointCollecte:
    """Point de collecte de déchets avec gestion du tonnage (SDVRP)."""
    id: int
    lat: float
    lng: float
    volume_total: float = 1000.0      # kg
    volume_restant: float = -1.0      # kg (-1 → initialisé à volume_total)
    priorite: int = 2                 # 1=faible, 2=normale, 3=urgente
    zone_id: Optional[int] = None
    nom: str = ""
    nombre_bennes: int = 2

    def __post_init__(self):
        if self.volume_restant < 0:
            self.volume_restant = self.volume_total

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lat": self.lat,
            "lng": self.lng,
            "nom": self.nom,
            "volume_total": self.volume_total,
            "volume_restant": self.volume_restant,
            "priorite": self.priorite,
            "zone_id": self.zone_id,
            "nombre_bennes": self.nombre_bennes,
        }


@dataclass
class Camion:
    """Camion de collecte avec suivi de la capacité restante, du carburant, et des horaires."""
    id: int
    capacite: float = 5000.0          # kg
    cout_fixe: float = 200.0          # MAD
    capacite_restante: float = -1.0   # kg (-1 → initialisé à capacite)
    nom: str = ""
    
    # Fuel Management
    capacite_reservoir: float = 200.0           # liters
    consommation_litre_par_km: float = 0.5      # liters / km
    niveau_carburant: float = -1.0              # initialized to capacite_reservoir
    seuil_critique: float = 40.0                # liters
    
    # Working Hours
    heure_debut_service: str = "06:00"
    heure_fin_service: str = "14:00"
    pause_obligatoire: int = 60                 # minutes
    temps_de_dechargement: int = 30             # minutes
    temps_conduite_continue: float = 0.0        # minutes

    def __post_init__(self):
        if self.capacite_restante < 0:
            self.capacite_restante = self.capacite
        if self.niveau_carburant < 0:
            self.niveau_carburant = self.capacite_reservoir

    def reset(self):
        """Réinitialise la capacité restante pour un nouveau trajet."""
        self.capacite_restante = self.capacite

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nom": self.nom,
            "capacite": self.capacite,
            "cout_fixe": self.cout_fixe,
            "capacite_restante": self.capacite_restante,
            "capacite_reservoir": self.capacite_reservoir,
            "consommation_litre_par_km": self.consommation_litre_par_km,
            "niveau_carburant": self.niveau_carburant,
            "seuil_critique": self.seuil_critique,
            "heure_debut_service": self.heure_debut_service,
            "heure_fin_service": self.heure_fin_service,
            "pause_obligatoire": self.pause_obligatoire,
            "temps_de_dechargement": self.temps_de_dechargement,
            "temps_conduite_continue": self.temps_conduite_continue,
        }


@dataclass
class Zone:
    """Zone géographique regroupant des points de collecte."""
    id: int
    nom: str = ""
    point_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nom": self.nom,
            "point_ids": self.point_ids,
        }
