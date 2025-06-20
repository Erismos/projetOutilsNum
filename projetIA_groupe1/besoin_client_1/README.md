## Classification de Navires par Clustering

## Description
Ce projet permet de classer un navire dans un groupe (ou cluster) à partir de ses paramètres dynamiques. Le modèle utilisé repose sur l'algorithme de KMeans entraîné en amont sur des données AIS normalisées. L'utilisateur entre manuellement les valeurs de SOG (vitesse sur le fond), COG (cap sur le fond) et Heading (direction du navire), et le script renvoie le numéro du cluster auquel le navire appartient.

## Fonctionnalité
- Classification de navires en temps réel selon leur comportement dynamique
- Utilisation d’un modèle KMeans pré-entraîné
- Normalisation automatique des données saisies
- Interface interactive via la console

## Prérequis
  - Python 3.7+
  - Bibliothèques Python requises :
    - numpy
    - scikit-learn
    - joblib

## Installation
1. Clonez le dépôt du projet
2. Installez les dépendances :
```bash
pip install numpy scikit-learn joblib
```

## Utilisation
  ## Exécution du script
   ```bash
   python script_cluster.py
   ```
  Lors de l'exécution, le script demandera : 
    - La vitesse (SOG)
    - Le cap (COG)
    - La direction du navire (Heading)

## Exemple d'exécution
Entrez la vitesse (SOG) : 13.4
Entrez le cap (COG) : 227.6
Entrez le heading : 227

Le navire appartient au cluster : 2

## Fichiers modèles
Le script a besoin de deux fichiers situés dans le dossier pkl/ :
pkl/kmeans_model.pkl          # Modèle KMeans entraîné
pkl/scaler_kmeans.pkl         # Objet de normalisation 

## Limitations
- Le modèle ne prend en compte que trois variables (SOG, COG, Heading)
- L'exactitude de la classification dépend de la qualité de l'entraînement initial
- Le script fonctionne en mode console interactif, sans traitement en lot