# Projet Outils Numériques - Analyse de Trafic Maritime


**Contexte** : Projet de 3e année - ISEN Ouest (Big Data / Intelligence Artificielle / Développement Web)

>**Auteurs** : [Laure Warlop](https://github.com/wrlp), [Gabriel Boucneau](https://github.com/Nectolyt), [Auvray Clément](https://github.com/Erismos)  
**Date** : Juin 2025

## Sommaire
- [Objectif](#objectif)
- [Installation et Exécution](#installation-et-exécution)
- [Structure du dossier besoin_client_1](#structure-du-dossier-besoin_client_1)
- [Objectif du besoin_client_1](#objectif-du-besoin_client_1)
- [Méthodes utilisées](#méthodes-utilisées)
- [Entraînement des modèles](#pour-entraîner-chaque-modèle)
- [Étapes du besoin client 1](#besoin-client-1---visualisation-sur-carte)
- [Livrables](#livrable-de-besoin_client_1)

---
## Objectif

Ce projet vise à **explorer, nettoyer, analyser et visualiser** les données AIS (Automatic Identification System) des navires dans le golfe du Mexique. Il s'inscrit dans un projet global en trois volets :

* Big Data
* Intelligence Artificielle
* Développement Web

Cette deuxième partie se concentre sur l'analyser les données AIS des navires afin de modéliser leurs comportements de navigation. Cela inclut la segmentation non supervisée (clustering), la prédiction du type de navire (classification supervisée) et la prédiction de trajectoire future (régression sur séries temporelles).

---

## Installation et Exécution

### Instructions
1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/Erismos/projetOutilsNum.git
   cd projetOutilsNum
   ```

2. **Installer les packages** :
   ```python
    pip install pandas numpy scikit-learn plotly matplotlib joblib
   ```
   
3. **Lancer le script principal du besoin_client_1** :
     ```python
     cd projetIA_groupe1/besoin_client_1
     python3 script_cluster.py
     ```
## Script principal script_cluster.py
* **Chargement du modèle et du scaler**
    Le script charge un modèle KMeans sauvegardé (kmeans_model.pkl) ainsi que le scaler associé (scaler_kmeans.pkl), qui a servi à normaliser les données pendant l’entraînement.
* **Entrée utilisateur**
    Le script demande à l’utilisateur de saisir :
        SOG (Speed Over Ground) → vitesse en nœuds
        COG (Course Over Ground) → cap en degrés (0–360°)
        Heading → direction de la proue du navire (en degrés)
* **Prétraitement**
    Les données entrées sont regroupées en un tableau unique.
    Elles sont normalisées avec le scaler chargé pour correspondre à l’espace de travail du modèle.
* **Prédiction du cluster**
    Le modèle KMeans prédit le cluster du navire selon son comportement.
* **Affichage du résultat**
    Le numéro du cluster est affiché.
---

## Structure du dossier besoin_client_1
├── data/ 
│   └── export_IA.csv          # Données nettoyées
Besoin_Client_1/
├── csv/
│   ├── kmeans_metrics.csv
│   ├── dbscan_metrics.csv
│   ├── birch_metrics.csv
│   ├── export_IA_with_clusters_kmeans.csv
│   ├── export_IA_with_clusters_dbscan.csv
│   └── export_IA_with_clusters_birch.csv
├── graphique/
│   ├── kmeans_elbow_method.png
│   ├── graph_scores_subplots_kmeans.png
│   ├── kmeans_combined.png
│   ├── dbscan_scores_subplots.png
│   ├── dbscan_combined_score.png
│   ├── graph_scores_subplots_birch.png
│   └── birch_combined.png
├── carte/
│   ├── trajectoires_clusters_kmeans.html
│   ├── trajectoires_clusters_dbscan.html
│   └── trajectoires_clusters_birch.html
├── pkl/
│   ├── kmeans_model.pkl
│   ├── dbscan_model.pkl
│   ├── birch_model.pkl
│   ├── scaler_kmeans.pkl
│   ├── scaler_dbscan.pkl
│   └── scaler_birch.pkl
├── script_cluster.py              # Script de prédiction KMeans
├── dbscan.py                # Script complet pour DBSCAN
├── birch.py                 # Script complet pour Birch
├── client1.py                # Script complet pour KMeans
└── README.md


## Objectif du besoin_client_1
Ce module a pour but de regrouper automatiquement les navires en clusters selon leurs comportements de navigation (vitesse SOG, cap COG, orientation Heading) grâce à différentes techniques de clustering non supervisé.
Chaque cluster est visualisé sur une carte interactive afin d’identifier des trajectoires typiques, des anomalies, ou des zones à optimiser.

## Méthodes utilisées 
KMeans	Clustering basé sur des centres de gravité
DBSCAN	Clustering basé sur la densité (gère le bruit/anomalies)
Birch	Clustering hiérarchique incrémental, efficace pour les grands jeux de données

## Pour entraîner chaque modèle 
```bash
  python3 client1.py    #kmeans
  python3 dbscan.py     #dbscan
  python3 birch.py      #birch
```
  * **chaque script fait** :
    nettoie et normalise les données
    évalue plusieurs paramètres
    sélectionne le meilleur modèle automatiquement
    sauvegarde les résultats :
        métriques CSV
        carte interactive .html
        graphiques de scores
        modèles .pkl

## Besoin client 1 - Visualisation sur carte 

* **Préparation des données** :
  - Extraction des données d'intérêt
  - Encodage des données catégorielles si nécessaire
* **Apprentissage non-supervisé** :
  - Choix de l'algorithme de clustering
  - Détermination du nombre de clusters
* **Métriques pour l'apprentissage non-supervisé** :
  - Évaluation des cluster
* **Visualisation sur un carte** :
  - Création de la carte
* **Préparation d'un script** :
  - Script prenant en entré les spécificités d’un navire et qui renvoie le cluster associé

## Livrable de besoin_client_1
  - Les fichiers csv
  - Les graphiques
  - Les cartes
  - Les modèles pkl
  - Les scripts python
  - Le readme

## Livrable général 
  - Besoin_client1
  - Besoin_client2
  - Besoin_client3
  - data
