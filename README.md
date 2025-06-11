# Projet AIS - Analyse de Trafic Maritime


**Contexte** : Projet de 3e année - ISEN Ouest (Big Data / Intelligence Artificielle / Développement Web)

>**Auteurs** : [Laure Warlop](https://github.com/wrlp), [Gabriel Boucneau](https://github.com/Nectolyt), [Auvray Clément](https://github.com/Erismos)  
**Date** : Juin 2025

---

## Objectif

Ce projet vise à **explorer, nettoyer, analyser et visualiser** les données AIS (Automatic Identification System) des navires dans le golfe du Mexique. Il s'inscrit dans un projet global en trois volets :

* Big Data
* Intelligence Artificielle
* Développement Web

Cette première partie se concentre sur le **traitement de données massives**, leur **visualisation avancée** (graphiques, cartes statiques et interactives), et la **préparation à l'apprentissage automatique**.

---

## Structure du dépôt

```
.
├── data/                      # Données brutes et nettoyées
│   ├── vessel-total-clean.csv
│   └── vessel-cleaned.csv
├── plots/                    # Graphiques statiques générés (PNG)
│   ├── combined_direction_plots.png
│   ├── vessel_type_distribution_enhanced.png
│   ├── length_vs_width_by_type_enhanced.png
│   ├── all_trajectories.png
│   ├── single_trajectory.png
│   └── main_routes.png
├── outputs/
│   ├── stats_trajectoires.csv
│   └── interactive_map.html
├── scripts/
│   └── clement.R             # Script principal R
├── generalPresentation.pdf   # Présentation générale du projet
├── BigDataSubject.pdf        # Spécification de la partie Big Data
└── README.md
```

---

## Fonctionnalités implémentées

### 1. Nettoyage et traitement des données

* Remplacement des valeurs manquantes et aberrantes
* Suppression des doublons
* Calculs statistiques descriptifs
* Sauvegarde du fichier nettoyé (`vessel-cleaned.csv`)

### 2. Visualisations statiques

* Histogrammes directionnels (COG, Heading) en polaire
* Répartition des navires par type
* Corrélation Longueur / Largeur par type de navire
* Statistiques globales en texte

### 3. Cartographie

* Carte statique de toutes les trajectoires
* Carte d’un bateau spécifique
* Détection des routes principales (clustering avec DBSCAN)
* Carte interactive (Leaflet + Plotly) avec filtres dynamiques

---

## Technologies utilisées

* **Langage** : R (v4.4.3 recommandé)
* **Librairies principales** : `dplyr`, `ggplot2`, `leaflet`, `plotly`, `dbscan`, `sf`, `lubridate`, `viridis`, `htmlwidgets`
* **Clustering** : DBSCAN pour l’identification des routes maritimes
* **Visualisation interactive** : `leaflet`, `htmlwidgets`, `plotly`

---

## Livrables

* Script R commenté et fonctionnel (`clement.R`)
* Figures PNG (`plots/`)
* Cartes des itinéraires (`outputs/interactive_map.html`)
* Fichier CSV nettoyé pour export IA (`vessel-cleaned.csv`)
* Rapport d'interpretations
* [Gantt](https://yncrea-my.sharepoint.com/:x:/g/personal/gabriel_boucneau_isen-ouest_yncrea_fr/EeFyss4CFzFLqRMh9ZACRXUBCnqPZFdicaM9cvkcB_6CRw?e=efSeLb)

---

## TODO

* [ ] Compléter l’analyse de corrélation (mosaicplot, chi²)
* [ ] Implémenter la régression logistique (IA)
* [ ] Ajouter les ports principaux dans la carte interactive
* [ ] Intégrer tout dans l’application web finale
