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

def prepare_data(df: pd.DataFrame, horizon : int = 300) -> pd.DataFrame:
    """
    Prépare les données AIS pour la prédiction en effectuant diverses transformations.

    Args:
        df (pd.DataFrame): DataFrame contenant les données AIS brutes
        horizon (int): Horizon de prédiction en secondes (défaut: 300)

    Returns:
        pd.DataFrame: DataFrame contenant les données préparées avec les features calculées

    Raises:
        ValueError: Si des colonnes obligatoires sont manquantes dans les données d'entrée

    Note:
        Effectue les opérations suivantes:
        - Vérification des colonnes obligatoires
        - Conversion des types de données
        - Calcul des composantes vectorielles
        - Conversion des unités (noeuds -> m/s, degrés -> radians)
        - Calcul des caractéristiques temporelles
        - Estimation de l'accélération
        - Nettoyage des données
    """ 

    # Vérification et sélection des colonnes utiles
    colonnes_utiles = ['MMSI', 'BaseDateTime', 'LAT', 'LON', 'SOG', 'COG', "VesselType", "Heading"]
    missing_cols = [col for col in colonnes_utiles if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes dans le DataFrame : {missing_cols}")
    df = df[colonnes_utiles].copy().iloc[-2:]

    # Conversion en datetime et calcul du timestamp relatif
    df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime'])
    df['timestamp'] = df.groupby('MMSI')['BaseDateTime'].transform(
        lambda x: (x - x.min()).dt.total_seconds()
    )
    # Tri par navire et date
    df.sort_values(['MMSI', 'BaseDateTime'], inplace=True)

    # Suppression des doublons
    df.drop_duplicates(subset=['MMSI', 'BaseDateTime'], inplace=True)

    # Conversion des angles et vitesses
    df['COG'] = np.deg2rad(df['COG'])
    df['COG_x'] = np.cos(df['COG'])  # Composante x de la direction
    df['COG_y'] = np.sin(df['COG'])  # Composante y de la direction
    df['Heading'] = np.deg2rad(df['Heading'])
    df['heading_x'] = np.cos(df['Heading'])  # Composante x de la direction
    df['heading_y'] = np.sin(df['Heading'])  # Composante y de la direction
    df['SOG'] = df['SOG'] * 0.514444  # Conversion noeuds -> m/s


    # Extraction des features temporelles
    df['hour'] = df['BaseDateTime'].dt.hour
    df['weekday'] = df['BaseDateTime'].dt.weekday
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)  # Cyclic encoding
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)  # Cyclic encoding

    # Calcul du delta temps entre les points
    df['delta_t'] = df.groupby('MMSI')['BaseDateTime'].shift(-1) - df['BaseDateTime']
    df['delta_t'] = df['delta_t'].dt.total_seconds()
    
    # Calcul de la variation de vitesse vers l'avant
    df['delta_v'] = df.groupby('MMSI')['SOG'].shift(-1) - df['SOG']

    # Accélération = delta_v / delta_t
    df['acceleration'] = df['delta_v'] / df['delta_t']
    
    # Défini le dernier NA de delta_t comme horizon
    df.fillna({'delta_t':horizon}, inplace=True)
    # Défini le dernier NA de l'accéleration comme l'accélération précédente
    df['acceleration'] = df['acceleration'].ffill()
        
    # Détection des navires à l'arrêt
    seuil_arret = 0.5  # m/s
    df['is_stopped'] = (df['SOG'] <= seuil_arret).astype(int)

    # Suppression des colonnes non utilisées
    df.drop(columns=["BaseDateTime", "COG", "Heading", "delta_v"], inplace=True)
    
    features = ["LAT", "LON", "SOG", "acceleration", "hour", "heading_x", "heading_y", "COG_x", "COG_y",
                "hour_sin", "hour_cos", "delta_t", "weekday", 
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
    model = joblib.load('models/random_forest_model.pkl')
    
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
    # Configuration du parser d'arguments en ligne de commande
    parser = argparse.ArgumentParser(
        description="Prédiction de position AIS à partir de données CSV.",
        epilog="Exemple d'utilisation: python predict_ais.py input.csv output.csv --horizon 600"
    ) 
    parser.add_argument("input_file", help="Chemin vers le fichier CSV d'entrée")
    parser.add_argument("output_file", help="Chemin vers le fichier CSV de sortie")
    parser.add_argument("--horizon", type=int, default=300, 
                       help="Horizon de prédiction en secondes (défaut : 300)")

    args = parser.parse_args()

    df = pd.read_csv(args.input_file)
    current_data = df.copy()
    remaining_horizon = args.horizon
    
    # On utilise un pas de prédiction de 300s maximum par itération
    prediction_step = 300
    
    while remaining_horizon > 0:
        # On prend le minimum entre le pas standard et le reste à prédire
        current_horizon = min(prediction_step, remaining_horizon)
        
        df_prepared = prepare_data(current_data, horizon=current_horizon)
        predictions = predict(df_prepared)
        new_data = reconstruct_AIS_data(current_data, predictions, 
                                      df_prepared["acceleration"].iloc[-1:], 
                                      horizon=current_horizon)
        
        # Concaténation pour la prochaine itération
        current_data = pd.concat([current_data, new_data], ignore_index=True)
        remaining_horizon -= current_horizon
    
    # Résultat final
    final_prediction = current_data.iloc[-1:]
    
    print(f"Prédiction finale - horizon {args.horizon}s :")
    print("Latitude :", final_prediction["LAT"].values[0])
    print("Longitude :", final_prediction["LON"].values[0])

    final_prediction.to_csv(args.output_file, index=False)
    print(f"Prédiction sauvegardée dans '{args.output_file}'")