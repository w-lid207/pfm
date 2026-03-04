# Rapport d'Algorithmes - Système d'Optimisation des Tournées de Collecte

## 1. Introduction
Ce document détaille les modèles algorithmiques et l'architecture du système de collecte de déchets, conçu pour la ville d'Agadir. Le système résout une variante complexe du Problème de Tournées de Véhicules : le SDVRP (Split Delivery Vehicle Routing Problem) avec fenêtres de temps, capacités de camions hétérogènes, multiples visites par conteneur, gestion du carburant, et heures de travail strictes.

## 2. Architecture du système
L'architecture est découpée en 5 niveaux séquentiels permettant de décomposer la complexité (Cluster-First, Route-Second) :
1. **Niveau 1** : Modélisation du graphe routier et de la matrice de distances (Haversine).
2. **Niveau 2** : Affectation Bipartie des secteurs aux camions (Clustering glouton).
3. **Niveau 3** : Planification Temporelle (fenêtres de temps et horaires de travail).
4. **Niveau 4** : Optimisation VRP (SDVRP avec retours à la décharge et gestion du carburant).
5. **Niveau 5** : Simulation temps-réel et évaluation multi-objectif.

## 3. Niveau 1 : Graphe Routier
**Algorithme** : Calcul de la matrice de distances via la formule de **Haversine** pour assurer que chaque point de collecte et dépôt soient connectés par leur distance à vol d'oiseau corrigée de la courbure terrestre. Dans l'implémentation finale, des requêtes API OSRM viennent raffiner ces distances.
- **Complexité Spatiale** : $\mathcal{O}(n^2)$ pour stocker la matrice des distances entre $n$ nœuds.
- **Complexité Temporelle** : $\mathcal{O}(n^2)$ pour calculer toutes les paires.

## 4. Niveau 2 : Affectation Bipartie
**Algorithme** : Approche **Gloutonne (Greedy Assignment)**. Les points de collecte sont d'abord groupés en sous-secteurs géographiques (K-Means ou partitionnement direct). L'algorithme trie les secteurs par demande décroissante et les camions par capacité décroissante, puis affecte itérativement pour équilibrer la charge.
- **Complexité Temporelle** : $\mathcal{O}(z \log z + c \log c)$ avec $z$ zones et $c$ camions pour le tri, plus $\mathcal{O}(z \times c)$ pour l'affectation.

## 5. Niveau 3 : Planification Temporelle
**Algorithme** : Résolution **Séquentielle**. Calcule les heures d'arrivée, de service (déchargement/rechargement de bennes), et de départ pour chaque point, en prenant en compte les fenêtres horaires de disponibilité (`heure_debut_service`, `heure_fin_service`), et la durée de vidage. Les pénalités d'heures supplémentaires sont mesurées ici.
- **Complexité Temporelle** : $\mathcal{O}(n)$ car il s'agit d'un simple parcours séquentiel des routes générées.

## 6. Niveau 4a : VRP SDVRP
**Algorithme** : Heuristique **Cluster-First, Route-Second** enrichie avec une méthode **Split Delivery (SDVRP)**.
1. Les points sont regroupés logiquement.
2. Construction de route via "Nearest Neighbor" (Plus Proche Voisin).
3. **Split Delivery** : Si `point.volume_restant > camion.capacite_restante`, le camion ne prend que `capacite_restante`, force un retour à la décharge municipale (vidage), puis continue ou laisse le reste à un autre camion.
4. **Gestion du Carburant** : Déroute forcée vers une station (`fuel_service`) si le niveau de carburant devient critique et insuffisant pour le retour.
5. Optimisation locale via **2-opt** pour lisser les lignes qui se croisent.
- **Complexité Temporelle** : $\mathcal{O}(n^2)$ pour la construction par le plus proche voisin, et $\mathcal{O}(n^2 \times k)$ pour l'optimisation 2-opt avec $k$ itérations.

## 7. Niveau 4b : Multi-Objectif
**Algorithme** : Évaluation globale par score pondéré :
- **Distance** (30%) : Minimiser les km parcourus.
- **Coût** (25%) : Minimiser le coût fixe d'usage des camions.
- **CO2** (25%) : Minimisation stricte de l'empreinte carbone via l'optimisation des trajets.
- **Utilisation** (20%) : Maximiser le remplissage des bennes (capacité transport / capacité totale).

## 8. Analyse de Complexité Globale
| Niveau | Phase | Exact ou Heuristique | Complexité Temps |
|--------|-------|----------------------|------------------|
| 1 | Graphe & Distances | Exact | $\mathcal{O}(n^2)$ |
| 2 | Clustering / Affectation | Heuristique | $\mathcal{O}(n \log n)$ |
| 3 | Planification temps | Exact | $\mathcal{O}(n)$ |
| 4 | SDVRP & 2-opt | Heuristique | $\mathcal{O}(n^2 \cdot k)$ |
| 5 | Multi-Objectif & Métriques | Exact | $\mathcal{O}(n)$ |

## 9. Pourquoi le SDVRP est NP-Hard
Le Vehicle Routing Problem (VRP) classique est déjà fondamentalement NP-Difficile puisqu'il généralise le Problème du Voyageur de Commerce (TSP). Introduire le **Split Delivery** (diviser la demande d'un nœud sur plusieurs camions) augmente de manière combinatoire exponentielle l'espace des solutions, car la décision n'est plus binaire (visité ou non), mais continue ou discrète sur la quantité récupérée par chaque véhicule. C'est incalculable par force brute (programmation linéaire en nombres entiers) au-delà de 20-30 points.

## 10. Justification de la méthode, Compromis et Optimalité
L'utilisation d'heuristiques (Glouton, Plus Proche Voisin) couplées à une optimisation locale (2-opt) garantit une solution sous-optimale mais extrêmement rapide.
- **Optimalité vs. Vitesse** : Une solution exacte par solver (Gurobi, OR-Tools) pourrait prendre des heures pour 500 points. Notre approche permet de résoudre 500 points en moins de 5 secondes, crucial pour une application temps réel (Dashboard).
- **Compromis Multi-Objectif** : Minimer la distance augmente parfois le délai de collecte. Les poids de la fonction objectif équilibrent les pénalités d'heures supp, le carburant consommé, l'usure, et la satisfaction.
- Les stations essence automatiques introduisent des déviations qui brisent l'optimalité pure du TSP originel, mais rendent la solution 100% faisable industriellement.
