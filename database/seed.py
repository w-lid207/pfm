"""
Données initiales pour le système de collecte d'Agadir
Points de collecte réels dans les quartiers d'Agadir
"""
from datetime import date, timedelta
import random


def seed_database(db, User, Zone, PointCollecte, Camion, Tournee, TourneePoint, Alert):
    """Insère les données de démonstration"""
    from services.auth_service import hash_password

    # ── Utilisateurs ──
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@agadir-collecte.ma',
            password_hash=hash_password('admin123'),
            role='admin',
        )
        op = User(
            username='operateur',
            email='operateur@agadir-collecte.ma',
            password_hash=hash_password('oper123'),
            role='operateur',
        )
        db.session.add_all([admin, op])
        db.session.commit()
        print("✓ Utilisateurs créés")

    # ── Zones (Talborjt remplacé par Inezgane pour OSRM) ──
    zones_data = [
        ('Hay Mohammadi', 'HMD', 2, 62000, '#e67e22'),
        ('Cité Dakhla', 'CDK', 2, 38000, '#f1c40f'),
        ('Souss Massa', 'SOM', 1, 29000, '#2ecc71'),
        ('Agadir Ville', 'AGA', 3, 78000, '#3498db'),
        ('Tikouine', 'TIK', 1, 22000, '#9b59b6'),
        ('Anza', 'ANZ', 2, 41000, '#1abc9c'),
        ('Inezgane', 'INZ', 2, 45000, '#e74c3c'),  # Remplace Talborjt, zone bien couverte OSRM
    ]

    zones = {}
    for nom, code, priorite, population, couleur in zones_data:
        if not Zone.query.filter_by(code=code).first():
            z = Zone(nom=nom, code=code, priorite=priorite,
                     population=population, couleur=couleur,
                     superficie_km2=random.uniform(2, 8))
            db.session.add(z)
            db.session.flush()
            zones[code] = z
        else:
            zones[code] = Zone.query.filter_by(code=code).first()

    db.session.commit()
    print("✓ Zones créées")

    # ── Points de collecte (Inezgane à la place de Talborjt, coords adaptées OSRM) ──
    points_data = [
        # Hay Mohammadi
        ('Bac Hay Mohammadi N1', 'Av. Hassan II', 30.4155, -9.5912, 'HMD', 'menager', 2.0, 0.90),
        ('Bac Hay Mohammadi N2', 'Rue du 18 Nov.', 30.4163, -9.5928, 'HMD', 'menager', 2.0, 0.60),
        ('Encombrants HM', 'Derrière école', 30.4170, -9.5900, 'HMD', 'encombrant', 3.0, 0.30),
        # Agadir Ville / Centre
        ('Bac Centre-Ville', 'Rue du Prince Héritier', 30.4272, -9.5968, 'AGA', 'menager', 1.5, 0.75),
        ('Conteneur Avenue Hassan', 'Av. Hassan II Centre', 30.4280, -9.5955, 'AGA', 'menager', 2.0, 0.55),
        ('Bac Quartier Commerce', 'Av. Mohammed V', 30.4260, -9.5940, 'AGA', 'menager', 1.5, 0.80),
        ('Recyclage Centre', 'Rue de la Poste', 30.4290, -9.5975, 'AGA', 'recyclable', 1.0, 0.40),
        # Cité Dakhla
        ('Bac Cité Dakhla', 'Rue Dakhla', 30.4312, -9.5835, 'CDK', 'menager', 2.0, 0.65),
        ('Conteneur Résidence', 'Cité Dakhla Bloc B', 30.4325, -9.5850, 'CDK', 'menager', 1.5, 0.50),
        # Anza
        ('Bac Anza Plage', 'Corniche Anza', 30.4410, -9.5750, 'ANZ', 'menager', 2.0, 0.45),
        ('Recyclage Anza', 'Zone Industrielle', 30.4380, -9.5780, 'ANZ', 'recyclable', 1.5, 0.30),
        # Tikouine
        ('Bac Tikouine', 'Route de Tikouine', 30.4050, -9.5820, 'TIK', 'menager', 1.5, 0.55),
        ('Conteneur Périphérie', 'Tikouine Nord', 30.4030, -9.5800, 'TIK', 'menager', 2.0, 0.35),
        # Souss
        ('Bac Souss Massa', 'Route de Taroudant', 30.4190, -9.5700, 'SOM', 'menager', 2.0, 0.70),
        ('Recyclage Souss', 'Rue Souss', 30.4200, -9.5720, 'SOM', 'recyclable', 1.0, 0.25),
        # Inezgane (remplace Talborjt — points sur routes OSM pour OSRM)
        ('Bac Inezgane Centre', 'Av. Al Massira, Inezgane', 30.3558, -9.5364, 'INZ', 'menager', 2.0, 0.65),
        ('Conteneur Inezgane Nord', 'Route d\'Agadir, Inezgane', 30.3610, -9.5380, 'INZ', 'menager', 1.5, 0.55),
        ('Recyclage Inezgane', 'Zone artisanale Inezgane', 30.3520, -9.5320, 'INZ', 'recyclable', 1.0, 0.40),
    ]

    zone_map = {z.code: z.id for z in Zone.query.all()}

    if PointCollecte.query.count() == 0:
        for nom, adresse, lat, lng, zone_code, type_d, cap, taux in points_data:
            p = PointCollecte(
                nom=nom, adresse=adresse,
                latitude=lat, longitude=lng,
                zone_id=zone_map.get(zone_code),
                type_dechet=type_d,
                capacite_m3=cap,
                taux_remplissage=taux,
                priorite=3 if taux >= 0.8 else (2 if taux >= 0.5 else 1),
            )
            db.session.add(p)
        db.session.commit()
        print("✓ Points de collecte créés")
    else:
        # Ajouter les points Inezgane si la zone existe et n'a pas encore ces points
        inz_id = zone_map.get('INZ')
        if inz_id and not PointCollecte.query.filter_by(zone_id=inz_id).first():
            inezgane_points = [
                ('Bac Inezgane Centre', 'Av. Al Massira, Inezgane', 30.3558, -9.5364, 'menager', 2.0, 0.65),
                ('Conteneur Inezgane Nord', "Route d'Agadir, Inezgane", 30.3610, -9.5380, 'menager', 1.5, 0.55),
                ('Recyclage Inezgane', 'Zone artisanale Inezgane', 30.3520, -9.5320, 'recyclable', 1.0, 0.40),
            ]
            for nom, adresse, lat, lng, type_d, cap, taux in inezgane_points:
                p = PointCollecte(
                    nom=nom, adresse=adresse, latitude=lat, longitude=lng,
                    zone_id=inz_id, type_dechet=type_d, capacite_m3=cap, taux_remplissage=taux,
                    priorite=3 if taux >= 0.8 else (2 if taux >= 0.5 else 1),
                )
                db.session.add(p)
            db.session.commit()
            print("✓ Points Inezgane ajoutés")

    # ── Camions ──
    camions_data = [
        ('AG-001-A', 'Mercedes Econic 1830', 12.0),
        ('AG-002-B', 'MAN TGS 26.320', 10.0),
        ('AG-003-C', 'Renault Trucks D Wide', 8.0),
        ('AG-004-D', 'Volvo FE 280', 10.0),
    ]

    if Camion.query.count() == 0:
        for immat, modele, cap in camions_data:
            c = Camion(
                immatriculation=immat,
                modele=modele,
                capacite_m3=cap,
                statut='disponible',
                latitude=30.4132 + random.uniform(-0.01, 0.01),
                longitude=-9.5889 + random.uniform(-0.01, 0.01),
                km_total=random.uniform(5000, 80000),
            )
            db.session.add(c)
        db.session.commit()
        print("✓ Camions créés")

    # ── Tournées d'exemple (7 derniers jours) ──
    if Tournee.query.count() == 0:
        camions = Camion.query.all()
        points = PointCollecte.query.all()

        for i in range(7):
            day = date.today() - timedelta(days=i)
            for j, camion in enumerate(camions[:3]):
                tournee = Tournee(
                    nom=f'Tournée {["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"][day.weekday()]} #{j+1}',
                    camion_id=camion.id,
                    date_tournee=day,
                    heure_depart=f'0{6+j}:00',
                    statut='terminee' if i > 0 else 'planifiee',
                    distance_km=round(random.uniform(18, 45), 1),
                    duree_min=round(random.uniform(120, 300), 0),
                    co2_kg=round(random.uniform(5, 12), 2),
                    cout_mad=round(random.uniform(15, 40), 2),
                    nb_points=random.randint(4, 8),
                    optimisee=(i % 2 == 0),
                )
                db.session.add(tournee)
                db.session.flush()

                # Assigner quelques points
                selected = random.sample(points, min(tournee.nb_points, len(points)))
                for ordre, pt in enumerate(selected, 1):
                    tp = TourneePoint(
                        tournee_id=tournee.id,
                        point_id=pt.id,
                        ordre=ordre,
                        collecte_effectuee=(i > 0),
                    )
                    db.session.add(tp)

        db.session.commit()
        print("✓ Tournées d'exemple créées")

    # ── Alertes ──
    if Alert.query.count() == 0:
        alertes = [
            Alert(type_alerte='remplissage', titre='Point saturé: Bac Hay Mohammadi N1',
                  message='Taux de remplissage: 90%. Collecte urgente recommandée.',
                  niveau='danger', entite_type='point', entite_id=4),
            Alert(type_alerte='panne', titre='Alerte préventive: AG-002-B',
                  message='Kilométrage élevé. Maintenance recommandée dans 500 km.',
                  niveau='warning', entite_type='camion', entite_id=2),
            Alert(type_alerte='retard', titre='Tournée en retard',
                  message='La tournée du matin accuse 45 min de retard.',
                  niveau='warning', entite_type='tournee'),
        ]
        db.session.add_all(alertes)
        db.session.commit()
        print("✓ Alertes créées")

    print("\n🚀 Base de données initialisée avec succès !")
    print("   Admin: admin / admin123")
    print("   Opérateur: operateur / oper123")
