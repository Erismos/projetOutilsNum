#!/usr/bin/env python3
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import load_model
import pickle
import sys
import os

def main(input_csv, output_csv):
    """
    Prédit les trajectoires futures pour les navires dans le fichier d'entrée.
    
    Args:
        input_csv (str): Chemin vers le fichier CSV d'entrée
        output_csv (str): Chemin vers le fichier CSV de sortie
    """
    # Charger le modèle et les scalers
    model = load_model('trajectory_model\best_model.keras')
    with open('prepared_data_trajectory\geo_scalers.pkl', 'rb') as f:
        scalers = pickle.load(f)
    
    # Charger les données d'entrée
    df = pd.read_csv(input_csv)
    
    # Prétraitement des données (simplifié)
    # NOTE: Ici vous devriez reproduire le même prétraitement que pendant l'entraînement
    df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime'])
    df = df.sort_values(['MMSI', 'BaseDateTime'])
    
    # Feature engineering (simplifié)
    df['time_diff'] = df.groupby('MMSI')['BaseDateTime'].diff().dt.total_seconds().fillna(0)
    df['lat_diff'] = df.groupby('MMSI')['LAT'].diff().fillna(0)
    df['lon_diff'] = df.groupby('MMSI')['LON'].diff().fillna(0)
    df['speed'] = np.sqrt(df['lat_diff']**2 + df['lon_diff']**2) / (df['time_diff'] + 1e-6)
    
    # Sélectionner les 10 dernières observations pour chaque navire
    sequences = []
    mmsi_list = []
    for mmsi, group in df.groupby('MMSI'):
        group = group.tail(10)  # Prendre les 10 dernières observations
        if len(group) < 10:
            continue  # Ignorer les navires avec moins de 10 observations
            
        # Sélectionner les features dans le bon ordre
        features = group[['LAT', 'LON', 'SOG', 'COG', 'Heading', 'VesselType', 
                         'Length', 'Width', 'Draft', 'Cargo', 'time_diff',
                         'lat_diff', 'lon_diff', 'speed']].values
        sequences.append(features)
        mmsi_list.append(mmsi)
    
    if not sequences:
        print("Aucune séquence valide trouvée.")
        return
    
    # Convertir en tableau numpy et normaliser
    X = np.array(sequences)
    original_shape = X.shape
    X = scalers['feature_scaler'].transform(X.reshape(-1, original_shape[-1])).reshape(original_shape)
    
    # Faire des prédictions
    predictions = model.predict(X)
    
    # Dénormaliser les résultats
    time_horizons = [5, 10, 15]
    results = []
    for i, t in enumerate(time_horizons):
        key = f'target_{t}m'
        lat_scaler = scalers['target_scalers'][key]['lat']
        lon_scaler = scalers['target_scalers'][key]['lon']
        
        pred = predictions[i]
        pred_denorm = np.zeros_like(pred)
        pred_denorm[:, 0] = lat_scaler.inverse_transform(pred[:, 0].reshape(-1, 1)).flatten()
        pred_denorm[:, 1] = lon_scaler.inverse_transform(pred[:, 1].reshape(-1, 1)).flatten()
        
        for j in range(len(mmsi_list)):
            results.append({
                'MMSI': mmsi_list[j],
                'Horizon_min': t,
                'Predicted_LAT': pred_denorm[j, 0],
                'Predicted_LON': pred_denorm[j, 1]
            })
    
    # Sauvegarder les résultats
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_csv, index=False)
    print(f"Prédictions sauvegardées dans {output_csv}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python predict_trajectory.py <input_csv> <output_csv>")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_csv = sys.argv[2]
    
    if not os.path.exists(input_csv):
        print(f"Le fichier d'entrée {input_csv} n'existe pas.")
        sys.exit(1)
    
    main(input_csv, output_csv)
