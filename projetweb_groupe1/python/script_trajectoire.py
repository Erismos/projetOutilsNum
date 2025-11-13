#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de prédiction de positions AIS (Automatic Identification System)

Description:
    Ce script permet de prédire les positions futures des navires à partir de données AIS historiques.
    Il utilise un modèle d'apprentissage automatique pour estimer les déplacements futurs.

Fonctionnalités:
    - Prétraitement des données AIS
    - Prédiction des positions (latitude/longitude)
    - Reconstruction des trajectoires
    - Prédiction itérative pour différents horizons temporels

Auteur: Auvray Clément
Date: juin 2025
Version: 1.0
"""


import joblib
import pandas as pd
import numpy as np
import pandas as pd
import argparse
from datetime import timedelta

import os

def prepare_data(df: pd.DataFrame, horizon : int = 300) -> pd.DataFrame:
    """
    Prépare les données AIS pour la prédiction en effectuant diverses transformations.

    Args:
        df (pd.DataFrame): DataFrame contenant les données AIS brutes
        horizon (int): Horizon de prédiction en secondes (défaut: 300)

    Returns:
        pd.DataFrame: DataFrame contenant les données préparées avec les features calculées
    """

    # Suppression colonnes 'Unnamed' si présentes
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    # Vérification des colonnes obligatoires
    required_columns = [
        'MMSI', 'BaseDateTime', 'LAT', 'LON', 'SOG', 'COG', 'VesselType', 'Heading'
    ]

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")

    # On travaille sur les dernières 2 lignes (ou plus si besoin)
    df = df[required_columns].copy().iloc[-2:]

    # Conversion date
    df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime'], dayfirst=True)
    df['timestamp'] = (df['BaseDateTime'] - df['BaseDateTime'].min()).dt.total_seconds()

    # Conversion numérique
    numeric_cols = ['LAT', 'LON', 'SOG', 'COG', 'Heading']
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

    # Conversion angles et vitesse
    df['COG'] = np.deg2rad(df['COG'])
    df['COG_x'] = np.cos(df['COG'])
    df['COG_y'] = np.sin(df['COG'])
    df['Heading'] = np.deg2rad(df['Heading'])
    df['heading_x'] = np.cos(df['Heading'])
    df['heading_y'] = np.sin(df['Heading'])
    df['SOG'] = df['SOG'] * 0.514444  # noeuds -> m/s

    # Features temporelles
    df['hour'] = df['BaseDateTime'].dt.hour
    df['weekday'] = df['BaseDateTime'].dt.weekday
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

    # Deltas
    df['delta_t'] = df.groupby('MMSI')['BaseDateTime'].shift(-1) - df['BaseDateTime']
    df['delta_t'] = df['delta_t'].dt.total_seconds()
    df['delta_v'] = df.groupby('MMSI')['SOG'].shift(-1) - df['SOG']

    # Accélération
    df['acceleration'] = df['delta_v'] / df['delta_t']

    # Correction du dernier NaN accélération
    if df['acceleration'].isnull().any() and len(df) >= 2:
        last_idx = df.index[-1]
        second_last_idx = df.index[-2]
        delta_t = df.loc[last_idx, 'timestamp'] - df.loc[second_last_idx, 'timestamp']
        delta_v = df.loc[last_idx, 'SOG'] - df.loc[second_last_idx, 'SOG']
        df.loc[last_idx, 'acceleration'] = delta_v / delta_t if delta_t != 0 else 0

    df['acceleration'] = df['acceleration'].fillna(0)
    df.fillna({'delta_t': horizon}, inplace=True)
    df['acceleration'] = df['acceleration'].ffill()

    # Navires arrêtés
    seuil_arret = 0.5
    df['is_stopped'] = (df['SOG'] <= seuil_arret).astype(int)

    # Suppression colonnes inutiles
    df.drop(columns=['BaseDateTime', 'COG', 'Heading', 'delta_v'], inplace=True)

    features = ["LAT", "LON", "SOG", "acceleration", "hour", "heading_x", "heading_y",
                "COG_x", "COG_y", "hour_sin", "hour_cos", "delta_t", "weekday",
                "VesselType", "timestamp"]

    df = df[features]

    return df

def predict(input_data: pd.DataFrame)-> np.ndarray:
    """
    Effectue la prédiction des positions futures à partir des données préparées.

    Args:
        input_data (pd.DataFrame): DataFrame contenant les données préparées

    Returns:
        np.ndarray: Tableau numpy contenant les prédictions de latitude et longitude

    Raises:
        FileNotFoundError: Si le modèle pré-entraîné n'est pas trouvé
        Exception: Pour les autres erreurs lors de la prédiction
    """
    # Charge le modèle pré-entraîné
    #print(input_data.isnull().sum())
    #print(input_data)
    model = joblib.load('../../python/pkl/gradient_boosting_model.pkl')
    
    # Prédiction
    predictions = model.predict(input_data)
    return predictions

def reconstruct_AIS_data(df: pd.DataFrame, predictions: np.ndarray, acceleration: pd.Series, horizon: int = 300) -> pd.DataFrame:
    """
    Reconstruit les données AIS avec les positions prédites.

    Args:
        df (pd.DataFrame): Données AIS originales
        predictions (np.ndarray): Prédictions de position [delta_lat, delta_lon]
        acceleration (pd.Series): Valeurs d'accélération calculées
        horizon (int): Horizon de prédiction en secondes (défaut: 300)

    Returns:
        pd.DataFrame: Nouvelle ligne de données AIS avec les valeurs prédites

    Note:
        - Met à jour la position en ajoutant les deltas prédits
        - Met à jour l'horodatage en ajoutant l'horizon
        - Recalcule la vitesse en fonction de l'accélération
    """
    newdata = df.iloc[-1:].copy()  # Get the last row for new data
    newdata = newdata.reset_index(drop=True)  # Reset index to avoid issues with assignment
    newdata["LAT"] = newdata["LAT"] + predictions[0][0]
    newdata["LON"] = newdata["LON"] + predictions[0][1]
    newdata["BaseDateTime"] = pd.to_datetime(newdata["BaseDateTime"]) + timedelta(seconds=horizon)
    newdata["SOG"] = round(newdata["SOG"].values[0] + acceleration.values[0] * horizon,1)
    return newdata
    

if __name__ == "__main__":   
    import argparse
    from datetime import timedelta
    parser = argparse.ArgumentParser(
        description="Prédiction de position AIS à partir de données CSV."
    )
    parser.add_argument("input_file", help="Fichier CSV d'entrée")
    parser.add_argument("output_file", help="Fichier CSV de sortie")
    parser.add_argument("--horizon", type=int, default=300, help="Horizon en secondes")
    args = parser.parse_args()

    # Charge le CSV complet, avec toutes les colonnes d'origine
    current_data = pd.read_csv(args.input_file, sep=';')
    current_data = current_data.loc[:, ~current_data.columns.str.contains('^Unnamed')]

    remaining_horizon = args.horizon
    prediction_step = 300  # pas max par itération


    while remaining_horizon > 0:
        current_horizon = min(prediction_step, remaining_horizon)

        # Passe directement le DataFrame ici, sans relire le CSV
        df_prepared = prepare_data(current_data, horizon=current_horizon)
        predictions = predict(df_prepared)
        new_data = reconstruct_AIS_data(current_data, predictions,
                                       df_prepared["acceleration"].iloc[-1:],
                                       horizon=current_horizon)

        current_data = pd.concat([current_data, new_data], ignore_index=True)

        remaining_horizon -= current_horizon

    final_prediction = current_data.iloc[-1:]

    # print(f"Prédiction finale - horizon {args.horizon}s :")
    # print("Latitude :", final_prediction["LAT"].values[0])
    # print("Longitude :", final_prediction["LON"].values[0])

    final_prediction.to_csv(args.output_file, index=False)
    # print(f"Prédiction sauvegardée dans '{args.output_file}'")
    print([format(final_prediction["LAT"].values[0], ".5f"),format(final_prediction["LON"].values[0], ".5f")])