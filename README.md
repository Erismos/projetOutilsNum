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

## Installation et Exécution

### Prérequis
1. **R** (version ≥ 4.4.3) - [Téléchargement](https://cran.r-project.org/)
2. **Librairies R** : Voir la liste complète dans [Technologies utilisées](#technologies-utilisées)

### Instructions
1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/Erismos/projetOutilsNum.git
   cd projetOutilsNum
   ```

2. **Installer les dépendances R** :
   ```r
   # Dans RStudio ou R CLI :
   install.packages(c("readr", "dplyr", "ggplot2", "cowplot", "lubridate", "viridis", "RColorBrewer", "maps", "mapdata", "ggmap", "sf", "leaflet", "plotly", "cluster", "dbscan", "htmlwidgets", "corrplot", "randomForest", "caret", "reshape2"))
   ```
   

3. **Exécuter l'analyse - Lancer le script principal** :
     ```r
     source("scripts/main.R")
     ```

4. **Résultats générés** :
   - Données nettoyées : `data/export_IA.csv`
   - Figures : dossier `plots/`
   - Carte interactive : `map/interactive_map.html`

---

## Fonctionnalités implémentées

### 1. Nettoyage et Traitement des Données

* **Prétraitement complet** :
  - Conversion des types de données (numériques, géospatiales)
  - Gestion des valeurs spéciales (`\N` → NA)
* **Traitement des valeurs manquantes** :
  - Stratégie adaptative (suppression si <5% de NA, imputation sinon)
  - Médianes par groupe pour les variables numériques
* **Détection d'anomalies** :
  - Méthode IQR (Interquartile Range) pour les outliers
  - Seuils dynamiques par variable
* **Optimisation** :
  - Suppression des doublons basée sur l'ID unique
  - Conservation de l'intégrité référentielle

### 2. Visualisations Graphiques

* **Analyse directionnelle** :
  - Diagrammes polaires pour les caps (Heading) et directions (COG)
  - Binning angulaire par pas de 15° pour détecter les orientations dominantes
* **Répartition des navires** :
  - Histogramme horizontal par type de navire (codes numériques)
  - Affichage des pourcentages et effectifs
* **Relations dimensions** :
  - Nuage de points Longueur vs Largeur avec régression linéaire par type
  - Filtrage des valeurs aberrantes (Longueur < 500m, Largeur < 100m)
* **Analyse des vitesses** :
  - Histogramme des SOG (Speed Over Ground) avec indicateur de moyenne
  - Détection automatique des bins optimaux
* **Statuts des navires** :
  - Diagramme circulaire annoté avec pourcentages précis
* **Densité géographique** :
  - Carte 2D avec contours de densité (kernel density estimation)

### 3. Cartographie Interactive

* **Visualisation des trajectoires** :
  - Affichage des routes par type de navire (couleurs distinctes)
  - Trajectoires individuelles avec popups détaillés (caractéristiques du navire, statistiques de voyage)
  - Surcouche des routes principales (clustering des trajets fréquents)

* **Détection intelligente** :
  - Identification automatique des zones portuaires par analyse des arrêts (vitesse < 1 nœud pendant > 4h)
  - Classification des activités portuaires (chargement/déchargement via le Δ de tirant d'eau)
  - Regroupement spatial des zones similaires (DBSCAN avec eps=0.4°)

* **Filtres dynamiques** :
  - Contrôle des couches par type de navire, statut de chargement, activité portuaire
  - Légendes interactives avec seuils personnalisés

### 4. Étude des corrélations

* **Analyse multivariée** :
  - Matrice de corrélation (Pearson) entre variables numériques
  - Calcul du R² pour mesurer les dépendances linéaires
  - Visualisation avec `corrplot`

* **Tests statistiques** :
  - Tests du Chi² et Fisher pour évaluer les dépendances entre variables catégorielles
  - Mosaic plots pour visualiser les relations Type × Status et Type × Cargo

* **Boxplots comparatifs** :
  - Distribution des variables numériques (SOG, Length, Width...) par type de navire
  - Détection des valeurs aberrantes

### 5. Prédictions & régressions

* **Modélisation prédictive** :
  - Régression linéaire entre Longueur et Largeur des navires (R² = 0.89)
  - Régression logistique multinomiale pour prédire le type de navire
    - Variables explicatives : SOG, Length, Draft, Width, Cargo, TransceiverClass, Status
    - Prétraitement : suppression des valeurs extrêmes (SOG > 94e percentile)
    - **Précision** : 93% sur le jeu de test

* **Optimisation** :
  - Validation croisée des modèles
  - Comparaison de différentes stratégies de traitement des NA
  - Sélection des variables les plus discriminantes
---

## Structure du dépôt

```
.
├── data/                      
│   ├── vessel-total-clean.csv # Données brutes
│   └── export_IA.csv          # Données nettoyées
├── plots/                     # Graphiques générés (PNG)
│   └── ...
├── map/
│   └── interactive_map.html
├── scripts/
│   ├── main.R                      # Script principal R
│   ├── data_cleaning.R             # Fonctionnalité 1
│   ├── data_visualization.R        # Fonctionnalité 2
│   ├── interactive_map.R           # Fonctionnalité 3
│   └── statistical_analysis.R      # Fonctionnalité 4 & 5
├── subjects/
│   └── ...   # PDFs des sujets
├── rapport.pdf
├── gantt.pdf
└── README.md
```
---

## Technologies utilisées

* **Langage** : R (v4.4.3)
* **Librairies** : `readr`, `dplyr`, `ggplot2`, `cowplot`, `lubridate`, `viridis`, `RColorBrewer`, `maps`, `mapdata`, `ggmap`, `sf`, `leaflet`, `plotly`, `cluster`, `dbscan`, `htmlwidgets`, `corrplot`, `randomForest`, `caret`, `reshape2`

---

## Livrables

* Scripts R commenté et fonctionnel (`scripts/`)
* Figures PNG (`plots/`)
* Cartes des itinéraires (`map/interactive_map.html`)
* Fichier CSV nettoyé pour export IA (`data/export_IA.csv`)
* [Rapport d'interpretations](https://yncrea-my.sharepoint.com/:w:/g/personal/laure_warlop_isen-ouest_yncrea_fr/EebxoPbonphEktEg7kkJzAYBx9FXocOLJYg8FxU2RHDpFg?rtime=Yoh1lHaq3Ug)
* Gantt (`gantt_bigdata.pdf`)

* [Diaporama pour présentation](https://www.canva.com/design/DAGqOPXfTrg/HhhohKB4mu1Z3uXXFCNG3g/edit?utm_content=DAGqOPXfTrg&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton) (pas à rendre)














