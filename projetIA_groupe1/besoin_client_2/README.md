# README - Prédiction du Type de Navire

## Description

Ce projet fournit un système de **prédiction du type de navire** à partir de ses caractéristiques physiques, en utilisant un modèle d'apprentissage automatique pré-entraîné. Le modèle prédit la catégorie du navire à partir de la **longueur**, la **largeur**, le **tirant d’eau** et le **type de cargaison**.

## Fonctionnalités

- Prédiction automatique du type de navire
- Pipeline scikit-learn incluant prétraitement + modèle
- Décodage automatique des catégories via un label encoder
- Utilisation simple via la ligne de commande

## Prérequis

- Python 3.7+
- Bibliothèques Python requises :
  - `pandas`
  - `joblib`
  - `scikit-learn`

## Installation

```bash
pip install pandas joblib scikit-learn
```

## Utilisation

### Format des données d'entrée

Le script accepte les caractéristiques du navire via des arguments en ligne de commande :

- `--Length` : Longueur du navire (en mètres)
- `--Width` : Largeur du navire (en mètres)
- `--Draft` : Tirant d’eau (en mètres)
- `--Cargo` : Type de cargaison (code numérique)

### Exécution du script

```bash
python script.py --Length 200 --Width 32 --Draft 10 --Cargo 70
```

### Exemple

```bash
python script.py --Length 150 --Width 25 --Draft 8 --Cargo 52
```

### Sortie attendue

```
Modèle chargé avec succès.

Résultat de prédiction :
- Code type de navire prédit : Cargo

Données d'entrée :
  - Length: 150.0
  - Draft: 8.0
  - Width: 25.0
  - Cargo: 52
```

## Fonctionnement interne

### 1. Chargement du modèle

- Le pipeline complet est chargé depuis `best_model.joblib`
- Le fichier `label_encoder.joblib` permet de décoder la prédiction en libellé lisible

### 2. Préparation des données

- Les arguments sont convertis en `DataFrame` pandas
- Le pipeline applique le prétraitement automatiquement

### 3. Prédiction

- Le modèle prédit une classe encodée (entier)
- Le `LabelEncoder` la traduit en nom de type de navire (ex. : Cargo, Tanker...)

## Fichiers nécessaires

Le script dépend des fichiers suivants (à placer dans le répertoire courant) qui sont créer par le fichier ``client2.py`` :

```
label_encoder.joblib
best_model.joblib
```

## Limitations

- La performance dépend fortement de la qualité des données d'entraînement
- Le champ `Cargo` doit correspondre à un code connu du modèle
- Le modèle ne prend pas en compte les données dynamiques (ex. : vitesse, position, cap)

## Auteurs & Contributeurs

Ce projet a été développé dans le cadre du projet IA de Caen par Gabriel Boucneau
