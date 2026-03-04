"""
Service de Gestion de Carburant (Fuel Management System)
"""
from typing import Dict, Any

class FuelService:
    @staticmethod
    def fuel_needed_for_route(distance_km: float, consommation_litre_par_km: float) -> float:
        """
        Calcule la quantité de carburant requise (en litres) pour parcourir une distance
        donnée avec une consommation spécifique.
        """
        return distance_km * consommation_litre_par_km

    @staticmethod
    def liters_per_ton_km(total_fuel_used: float, total_tonnage: float, distance_km: float) -> float:
        """
        Calcule l'efficacité du carburant : litres consommés par tonne-kilomètre.
        (Combien de litres il faut pour transporter 1 tonne sur 1 km)
        """
        if total_tonnage <= 0 or distance_km <= 0:
            return 0.0
        return total_fuel_used / (total_tonnage * distance_km)

    @staticmethod
    def fuel_efficiency_per_truck(truck_stats: Dict[str, Any]) -> float:
        """
        Calcule l'efficacité globale par camion, typiquement à partir de ses statistiques récupérées
        auprès de simulateurs ou après optimisation.
        """
        fuel_used = truck_stats.get('fuel_used_liters', 0.0)
        tonnage = truck_stats.get('total_tonnage', 0.0)
        distance = truck_stats.get('total_distance_km', 0.0)
        
        return FuelService.liters_per_ton_km(fuel_used, tonnage, distance)
