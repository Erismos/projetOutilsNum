# Système de Prédiction de Positions AIS

## Description

Ce projet fournit un système de prédiction des positions futures des navires à partir de données AIS (Automatic Identification System). Le système utilise un modèle d'apprentissage automatique pour estimer les positions futures sur un horizon temporel configurable.

## Fonctionnalités

- Prédiction des positions (latitude/longitude) des navires
- Prise en compte de la vitesse (SOG), du cap (COG) et d'autres paramètres dynamiques
- Horizon de prédiction configurable (en secondes)
- Génération de trajectoires prédites par itérations successives

## Prérequis

- Python 3.7+
- Bibliothèques Python requises :
  - pandas
  - numpy
  - scikit-learn
  - joblib

## Installation

1. Clonez le dépôt du projet
2. Installez les dépendances :
```bash
pip install pandas numpy scikit-learn joblib
```

## Utilisation

### Format des données d'entrée

Le fichier CSV d'entrée doit contenir au moins les colonnes suivantes :
- MMSI (identifiant du navire)
- BaseDateTime (horodatage)
- LAT (latitude)
- LON (longitude)
- SOG (vitesse sur le fond)
- COG (cap sur le fond)
- VesselType (type de navire)
- Heading (direction)

### Exécution du script

```bash
python predict_ais.py <input_file.csv> <output_file.csv> [--horizon TEMPS_EN_SECONDES]
```

Arguments :
- `input_file.csv` : Chemin vers le fichier CSV contenant les données AIS
- `output_file.csv` : Chemin où sauvegarder les prédictions
- `--horizon` : Optionnel. Horizon de prédiction en secondes (défaut: 300)

### Exemples

Prédiction standard (300 secondes) :
```bash
python predict_ais.py data/ais_data.csv data/predictions.csv
```

Prédiction sur 10 minutes (600 secondes) :
```bash
python predict_ais.py data/ais_data.csv data/predictions.csv --horizon 600
```

Prédiction sur 15 minutes (900 secondes) :
```bash
python predict_ais.py data/ais_data.csv data/predictions.csv --horizon 900
```

## Fonctionnement interne

Le système fonctionne en trois étapes principales :

1. **Préparation des données** :
   - Conversion des unités (noeuds → m/s, degrés → radians)
   - Calcul des caractéristiques (accélération, composantes vectorielles)
   - Encodage des caractéristiques temporelles

2. **Prédiction** :
   - Utilisation d'un modèle Random Forest pré-entraîné
   - Prédiction des variations de position (latitude/longitude)

3. **Reconstruction des données AIS** :
   - Calcul des nouvelles positions
   - Mise à jour de la vitesse et de l'horodatage
   - Itération jusqu'à atteindre l'horizon souhaité

## Fichiers Modèles

Le script nécessite un modèle pré-entraîné situé dans :
```
models/random_forest_model.pkl
```

## Limitations

- La précision diminue avec l'augmentation de l'horizon de prédiction
- Les manoeuvres brusques peuvent affecter la qualité des prédictions
- Le modèle suppose une continuité dans le comportement du navire
