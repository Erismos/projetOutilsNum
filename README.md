# Projet Outils Numériques - Analyse de Trafic Maritime


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
├── data/                      
│   ├── vessel-total-clean.csv # Données brutes
│   └── export_IA.csv          # Données nettoyées
├── plots/                     # Graphiques générés (PNG)
│   └── ...
├── outputs/
│   └── interactive_map.html
├── scripts/
│   ├── main.R             # Script principal R
│   ├── data_cleaning.R
│   ├── data_visualization.R
│   ├── Gabirel.R
│   └── interactive_map.R
├── subjects/
│   └── ...   # PDFs des sujets
└── README.md
```

---

## Fonctionnalités implémentées

### 1. Nettoyage et traitement des données

* Remplacement des valeurs manquantes et aberrantes
* Suppression des doublons
* Calculs statistiques descriptifs
* Sauvegarde du fichier nettoyé (`vessel-cleaned.csv`)

### 2. Visualisations graphiques

* Histogrammes directionnels (COG, Heading) en polaire
* Itinéraire principaux et ports
* Histogramme de vitesses
* Répartition des navires par type
* Camembert des status
* Corrélation Longueur / Largeur par type de navire

### 3. Cartographie

* Carte statique de toutes les trajectoires
* Carte d’un bateau spécifique
* Détection des routes principales (clustering avec DBSCAN)
* Carte interactive (Leaflet + Plotly) avec filtres dynamiques

### 4. Etudes des corrélation

### 5. Prédictions & régressions

---

## Technologies utilisées

* **Langage** : R (v4.4.3)
* **Librairies** : `readr`, `dplyr`, `ggplot2`, `cowplot`, `lubridate`, `viridis`, `RColorBrewer`, `maps`, `mapdata`, `ggmap`, `sf`, `leaflet`, `plotly`, `cluster`, `dbscan`, `htmlwidgets`, `corrplot`, `randomForest`, `caret`, `reshape2`

---

## Livrables

* Scripts R commenté et fonctionnel (`scripts/`)
* Figures PNG (`plots/`)
* Cartes des itinéraires (`outputs/interactive_map.html`)
* Fichier CSV nettoyé pour export IA (`data/export_IA.csv`)
* [Rapport d'interpretations](https://yncrea-my.sharepoint.com/:w:/g/personal/laure_warlop_isen-ouest_yncrea_fr/EebxoPbonphEktEg7kkJzAYBx9FXocOLJYg8FxU2RHDpFg?rtime=Yoh1lHaq3Ug)
* Gantt (`gantt_bigdata.pdf`)

