import math

class Point:
    def __init__(self, nom, x, y):
        self.nom = nom
        self.x = x
        self.y = y

    def distance_vers(self, autre_point):
        return math.sqrt((self.x - autre_point.x)**2 + (self.y - autre_point.y)**2)

class Station(Point):
    def __init__(self, nom, x, y):
        super().__init__(nom, x, y)

class Camion:
    def __init__(self, nom, depot, cap_carburant, conso_au_km):
        self.nom = nom
        self.position = depot
        self.cap_carburant = cap_carburant
        self.carburant_actuel = cap_carburant
        self.conso_au_km = conso_au_km
        self.parcours = [depot.nom]

    def calcul_carburant_necessaire(self, destination):
        distance = self.position.distance_vers(destination)
        return distance * self.conso_au_km

    def aller_a(self, destination, type_action="Trajet"):
        carburant_necessaire = self.calcul_carburant_necessaire(destination)
        self.carburant_actuel -= carburant_necessaire
        self.position = destination
        self.parcours.append(destination.nom)
        print(f"[{self.nom}] {type_action} vers {destination.nom}.")
        print(f" -> Position : {self.position.nom} | Carburant restant : {self.carburant_actuel:.1f} L")

    def faire_le_plein(self):
        quantite_remplie = self.cap_carburant - self.carburant_actuel
        self.carburant_actuel = self.cap_carburant
        print(f"[{self.nom}] Plein effectué – Reprise de la tournée ! (+{quantite_remplie:.1f} L ajoutés)")

def trouver_station_proche(position, stations):
    plus_proche = stations[0]
    dist_min = position.distance_vers(plus_proche)
    for station in stations[1:]:
        dist = position.distance_vers(station)
        if dist < dist_min:
            dist_min = dist
            plus_proche = station
    return plus_proche

def simuler_collecte():
    depot = Point("Dépôt", 0, 0)

    # 1. Gestion de plusieurs stations
    stations = [
        Station("Station Nord", 10, 20),
        Station("Station Sud", -15, -10),
        Station("Station Est", 30, 5)
    ]

    # 2. Scénario avec plusieurs points de collecte
    points_c1 = [Point("Point A", 5, 10), Point("Point B", 12, 25), Point("Point C", 30, 20)]
    points_c2 = [Point("Point D", -10, -5), Point("Point E", -20, -15), Point("Point F", -5, -25)]

    # 3. Gestion de plusieurs camions
    camion1 = Camion("Camion 1", depot, cap_carburant=100.0, conso_au_km=2.5) # Consomme bcp
    camion2 = Camion("Camion 2", depot, cap_carburant=80.0, conso_au_km=1.8)

    tournees = {
        camion1: points_c1 + [depot],
        camion2: points_c2 + [depot]
    }

    print("=" * 60)
    print("DÉBUT DE LA SIMULATION : COLLECTE ET GESTION DE CARBURANT")
    print("=" * 60 + "\n")

    for camion, tournee in tournees.items():
        print(f"--- {camion.nom} démarre sa tournée ---")
        
        for destination in tournee:
            carburant_requis = camion.calcul_carburant_necessaire(destination)
            
            # Marge de sécurité de 5L
            if camion.carburant_actuel < (carburant_requis + 5):
                print(f"\n⚠️ [{camion.nom}] Alerte : Carburant insuffisant – Direction station !")
                
                station_proche = trouver_station_proche(camion.position, stations)
                
                # Aller à la station
                camion.aller_a(station_proche, type_action="Détour")
                
                # Faire le plein
                camion.faire_le_plein()
                print("-" * 50)
            
            # Aller au point de collecte
            action = "Aller au point de collecte" if destination != depot else "Retour au dépôt"
            camion.aller_a(destination, type_action=action)
        
        print(f"\n✅ Terminé. Parcours complet du {camion.nom} :")
        print(" ➔ ".join(camion.parcours))
        print("\n" + "=" * 60 + "\n")

if __name__ == '__main__':
    simuler_collecte()
