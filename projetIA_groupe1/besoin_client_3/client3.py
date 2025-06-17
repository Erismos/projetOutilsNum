import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
import pickle
import os
from datetime import datetime
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, LSTM, Dense, Dropout, concatenate
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
import matplotlib.pyplot as plt
from math import radians, sin, cos, sqrt, atan2


def prepare_trajectory_data(csv_path, output_dir, time_horizons=[5, 10, 15]):
    # Chargement et filtrage initial
    df = pd.read_csv(csv_path)
    
    # Filtrage géographique du Golfe du Mexique
    df = df[
        (df['LAT'].between(18, 31)) & 
        (df['LON'].between(-98, -80)) &
        (df['SOG'] >= 0) & (df['COG'].between(0, 360))
    ].copy()
    
    # Feature engineering avancé
    df['dt'] = pd.to_datetime(df['BaseDateTime'])
    df = df.sort_values(['MMSI', 'dt'])
    
    # Calculs différentiels
    df['time_diff'] = df.groupby('MMSI')['dt'].diff().dt.total_seconds().fillna(0)
    df['lat_diff'] = df.groupby('MMSI')['LAT'].diff().fillna(0)
    df['lon_diff'] = df.groupby('MMSI')['LON'].diff().fillna(0)
    
    # Variables dérivées
    df['speed'] = df['SOG'] * 0.514444  # Conversion knots -> m/s
    df['accel'] = df.groupby('MMSI')['speed'].diff().fillna(0) / (df['time_diff'] + 1e-6)
    df['turn_rate'] = df.groupby('MMSI')['COG'].diff().fillna(0) / (df['time_diff'] + 1e-6)
    
    # Sélection des features
    feature_cols = [
        'LAT', 'LON', 'speed', 'COG', 'Heading', 
        'VesselType', 'Length', 'Width', 'Draft',
        'time_diff', 'lat_diff', 'lon_diff', 'accel', 'turn_rate'
    ]
    
    # Création des séquences
    sequences, targets = [], {f'target_{t}m': [] for t in time_horizons}
    
    for mmsi, group in df.groupby('MMSI'):
        group = group.sort_values('dt')
        for i in range(10, len(group)-max(time_horizons)):
            seq = group.iloc[i-10:i][feature_cols].values
            sequences.append(seq)
            
            for t in time_horizons:
                target_idx = min(i + int(t*60/group['time_diff'].mean()), len(group)-1)
                targets[f'target_{t}m'].append([
                    group.iloc[target_idx]['LAT'],
                    group.iloc[target_idx]['LON']
                ])
    
    # Normalisation géographique spécifique
    X = np.array(sequences)
    lat_scaler = MinMaxScaler(feature_range=(-1, 1))
    lon_scaler = MinMaxScaler(feature_range=(-1, 1))
    
    # Reshape pour n'avoir qu'une seule feature
    lat_scaler.fit(X[:, :, 0].reshape(-1, 1))
    lon_scaler.fit(X[:, :, 1].reshape(-1, 1))
    
    # Appliquer la transformation
    X[:, :, 0] = lat_scaler.transform(X[:, :, 0].reshape(-1, 1)).reshape(X.shape[0], X.shape[1])
    X[:, :, 1] = lon_scaler.transform(X[:, :, 1].reshape(-1, 1)).reshape(X.shape[0], X.shape[1])
    
    # Sauvegarde des scalers
    with open(os.path.join(output_dir, 'geo_scalers.pkl'), 'wb') as f:
        pickle.dump({'lat': lat_scaler, 'lon': lon_scaler}, f)
    
    # Conversion des cibles en arrays numpy
    for t in time_horizons:
        targets[f'target_{t}m'] = np.array(targets[f'target_{t}m'])
    
    return {
        'X': np.array(sequences),
        'y': targets,
        'feature_names': feature_cols
    }

from tensorflow.keras.layers import Conv1D, Bidirectional, BatchNormalization
from tensorflow.keras.optimizers import Adam

def build_trajectory_model(input_shape):
    inputs = Input(shape=input_shape)
    
    # Couches partagées
    x = Conv1D(64, 3, activation='relu', padding='same')(inputs)
    x = BatchNormalization()(x)
    x = Dropout(0.2)(x)
    
    x = Bidirectional(LSTM(128, return_sequences=True))(x)
    x = Dropout(0.3)(x)
    x = Bidirectional(LSTM(64))(x)
    x = Dropout(0.3)(x)
    
    # Têtes de sortie séparées
    output_5m = Dense(2, name='output_5m')(x)
    output_10m = Dense(2, name='output_10m')(x)
    output_15m = Dense(2, name='output_15m')(x)
    
    model = Model(inputs=inputs, outputs=[output_5m, output_10m, output_15m])
    
    # Configuration des métriques pour chaque sortie
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='mse',
        metrics={
            'output_5m': ['mae'],
            'output_10m': ['mae'],
            'output_15m': ['mae']
        }
    )
    
    return model

def train_trajectory_model(X, y, output_dir, epochs=25, batch_size=64):
    os.makedirs(output_dir, exist_ok=True)
    
    # Préparation des cibles avec des noms correspondants
    y_train = {
        'output_5m': np.array(y['target_5m']),
        'output_10m': np.array(y['target_10m']),
        'output_15m': np.array(y['target_15m'])
    }
    
    # Séparation train/val
    split_idx = int(0.8 * len(X))
    X_train, X_val = X[:split_idx], X[split_idx:]
    
    y_val = {
        'output_5m': y_train['output_5m'][split_idx:],
        'output_10m': y_train['output_10m'][split_idx:],
        'output_15m': y_train['output_15m'][split_idx:]
    }
    y_train = {
        'output_5m': y_train['output_5m'][:split_idx],
        'output_10m': y_train['output_10m'][:split_idx],
        'output_15m': y_train['output_15m'][:split_idx]
    }
    
    # Construction et entraînement
    model = build_trajectory_model(X.shape[1:])
    
    callbacks = [
        ModelCheckpoint(
            os.path.join(output_dir, 'best_model.keras'),
            save_best_only=True,
            monitor='val_loss'
        ),
        EarlyStopping(patience=15, restore_best_weights=True)
    ]
    
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1
    )
    
    model.save(os.path.join(output_dir, 'final_model.keras'))
    return model, X_val, y_val


    
def plot_training_history(history, output_dir):
    """Trace et sauvegarde les courbes d'apprentissage."""
    plt.figure(figsize=(15, 10))
    
    # Loss
    plt.subplot(2, 1, 1)
    plt.plot(history.history['loss'], label='Train Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.title('Loss')
    plt.xlabel('Epoch')
    plt.ylabel('MSE')
    plt.legend()
    
    # MAE - tracer toutes les métriques MAE
    plt.subplot(2, 1, 2)
    
    # Trier les clés pour avoir un ordre cohérent
    mae_keys = sorted([k for k in history.history.keys() if 'mae' in k and 'val' not in k])
    val_mae_keys = sorted([k for k in history.history.keys() if 'mae' in k and 'val' in k])
    
    # Correspondance des horizons temporels
    time_horizons = ['5min', '10min', '15min']
    
    for i, (mae_key, val_mae_key) in enumerate(zip(mae_keys, val_mae_keys)):
        if i >= len(time_horizons):
            break
        plt.plot(history.history[mae_key], label=f'Train MAE ({time_horizons[i]})')
        plt.plot(history.history[val_mae_key], '--', label=f'Val MAE ({time_horizons[i]})')
    
    plt.title('Mean Absolute Error')
    plt.xlabel('Epoch')
    plt.ylabel('MAE')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'training_curves.png'))
    plt.close()


def haversine(lat1, lon1, lat2, lon2):
    """Calcule la distance en mètres entre deux points GPS"""
    R = 6371.0  # Rayon terrestre en km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c * 1000  # Conversion en mètres
def evaluate_model(model, X_test, y_test, scalers):
    """Version corrigée avec gestion robuste des dimensions"""
    predictions = model.predict(X_test)
    results = {}
    
    output_mapping = {
        0: ('output_5m', 5),
        1: ('output_10m', 10), 
        2: ('output_15m', 15)
    }
    
    for i, (output_name, minutes) in output_mapping.items():
        pred = predictions[i]
        true = y_test[output_name]
        
        print(f"\nDebug {minutes}m:")
        print("Pred shape:", pred.shape, "True shape:", true.shape)
        
        # Méthode robuste de dénormalisation
        def inverse_scale(scaler, data):
            # Reshape pour s'assurer d'avoir une seule feature
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            elif data.shape[1] > 1:
                data = data.reshape(-1, 1)
            return scaler.inverse_transform(data).flatten()
        
        # Dénormalisation
        try:
            pred_lat = inverse_scale(scalers['lat'], pred[:, 0])
            pred_lon = inverse_scale(scalers['lon'], pred[:, 1])
            true_lat = inverse_scale(scalers['lat'], true[:, 0])
            true_lon = inverse_scale(scalers['lon'], true[:, 1])
        except ValueError as e:
            print(f"Erreur lors de la dénormalisation: {e}")
            print("Vérifiez que les scalers ont été correctement entraînés et sauvegardés")
            continue
        
        # Calcul des distances
        distances = [haversine(tlat, tlon, plat, plon) 
                    for tlat, tlon, plat, plon in zip(true_lat, true_lon, pred_lat, pred_lon)]
        
        results[f'target_{minutes}m'] = {
            'mae_m': np.mean(distances),
            'rmse_m': np.sqrt(np.mean(np.square(distances))),
            'median_m': np.median(distances),
            'max_m': np.max(distances),
            'samples': len(distances)
        }
    
    return results

def create_prediction_script(model_path, scaler_path, output_dir):
    """
    Crée un script de prédiction qui peut être utilisé en ligne de commande.
    
    Args:
        model_path: Chemin vers le modèle sauvegardé
        scaler_path: Chemin vers les scalers sauvegardés
        output_dir: Répertoire de sortie
    """
    # Créer le répertoire s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    script_content = f'''#!/usr/bin/env python3
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
    model = load_model('{model_path}')
    with open('{scaler_path}', 'rb') as f:
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
    time_horizons = {time_horizons}
    results = []
    for i, t in enumerate(time_horizons):
        key = f'target_{{t}}m'
        lat_scaler = scalers['target_scalers'][key]['lat']
        lon_scaler = scalers['target_scalers'][key]['lon']
        
        pred = predictions[i]
        pred_denorm = np.zeros_like(pred)
        pred_denorm[:, 0] = lat_scaler.inverse_transform(pred[:, 0].reshape(-1, 1)).flatten()
        pred_denorm[:, 1] = lon_scaler.inverse_transform(pred[:, 1].reshape(-1, 1)).flatten()
        
        for j in range(len(mmsi_list)):
            results.append({{
                'MMSI': mmsi_list[j],
                'Horizon_min': t,
                'Predicted_LAT': pred_denorm[j, 0],
                'Predicted_LON': pred_denorm[j, 1]
            }})
    
    # Sauvegarder les résultats
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_csv, index=False)
    print(f"Prédictions sauvegardées dans {{output_csv}}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python predict_trajectory.py <input_csv> <output_csv>")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_csv = sys.argv[2]
    
    if not os.path.exists(input_csv):
        print(f"Le fichier d'entrée {{input_csv}} n'existe pas.")
        sys.exit(1)
    
    main(input_csv, output_csv)
'''

    # Sauvegarder le script
    script_path = os.path.join(output_dir, 'predict_trajectory.py')
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Rendre le script exécutable (Unix)
    os.chmod(script_path, 0o755)
    
    return script_path

def verify_data_shapes(data):
    """Vérifie la cohérence des shapes des données"""
    errors = []
    
    # Vérification de X
    if len(data['X'].shape) != 3:
        errors.append(f"X doit avoir 3 dimensions, shape actuelle: {data['X'].shape}")
    
    # Vérification des cibles
    expected_samples = data['X'].shape[0]
    for t in [5, 10, 15]:
        key = f'target_{t}m'
        if key not in data['y']:
            errors.append(f"Clé {key} manquante dans y")
            continue
            
        # Conversion si nécessaire
        if isinstance(data['y'][key], list):
            data['y'][key] = np.array(data['y'][key])
            
        if len(data['y'][key].shape) != 2:
            errors.append(f"{key} doit avoir 2 dimensions, shape actuelle: {data['y'][key].shape}")
        elif data['y'][key].shape[0] != expected_samples:
            errors.append(f"Nombre d'échantillons incohérent: X a {expected_samples} samples, {key} en a {data['y'][key].shape[0]}")
    
    if errors:
        raise ValueError("\n".join(["Problèmes de shape détectés:"] + errors))
    
    print("Vérification des shapes réussie!")
    return data


if __name__ == "__main__":
    # Configuration des chemins
    input_csv = "data/export_IA.csv"
    prepared_data_dir = "prepared_data_trajectory"
    model_output_dir = "trajectory_model"
    script_output_dir = "script"
    time_horizons = [5, 10, 15]

    # 1. Préparation des données
    print("Préparation des données...")
    os.makedirs(prepared_data_dir, exist_ok=True)
    prepared_data = prepare_trajectory_data(input_csv, prepared_data_dir, time_horizons)

    # Vérification des shapes et conversion en numpy arrays si nécessaire
    print("\nVérification des dimensions:")
    prepared_data['X'] = np.array(prepared_data['X'])
    print(f"X shape: {prepared_data['X'].shape}")  # Doit être (n_samples, 10, 14)

    for t in time_horizons:
        key = f'target_{t}m'
        if isinstance(prepared_data['y'][key], list):
            prepared_data['y'][key] = np.array(prepared_data['y'][key])
        print(f"{key} shape: {prepared_data['y'][key].shape}")  # Doit être (n_samples, 2)

    # 2. Sauvegarde des données préparées
    with open(os.path.join(prepared_data_dir, 'prepared_data.pkl'), 'wb') as f:
        pickle.dump(prepared_data, f)

    # 3. Chargement des scalers géographiques
    with open(os.path.join(prepared_data_dir, 'geo_scalers.pkl'), 'rb') as f:
        geo_scalers = pickle.load(f)

    # 4. Entraînement du modèle
    print("\nDémarrage de l'entraînement...")
    os.makedirs(model_output_dir, exist_ok=True)
    model, X_test, y_test = train_trajectory_model(
        prepared_data['X'],
        prepared_data['y'],
        model_output_dir,
        epochs=2,
        batch_size=64
    )

    # 5. Évaluation
    print("\nÉvaluation du modèle...")
    evaluation_results = evaluate_model(
        model=model,
        X_test=X_test,
        y_test=y_test,  # Utilise maintenant la structure dictionnaire
        scalers=geo_scalers
    )

    print("\nRésultats finaux (en mètres):")
    for horizon, metrics in evaluation_results.items():
        print(f"\n{horizon}:")
        print(f"  MAE = {metrics['mae_m']:.2f}m")
        print(f"  RMSE = {metrics['rmse_m']:.2f}m")
        print(f"  Médiane = {metrics['median_m']:.2f}m")

    # 6. Création du script de prédiction
    print("\nGénération du script de prédiction...")
    os.makedirs(script_output_dir, exist_ok=True)
    script_path = create_prediction_script(
        model_path=os.path.join(model_output_dir, 'best_model.keras'),
        scaler_path=os.path.join(prepared_data_dir, 'geo_scalers.pkl'),
        output_dir=script_output_dir
    )

    print("\nPipeline terminé avec succès!")
    print(f"Script généré: {script_path}")
    print("Utilisation: python predict_trajectory.py <input.csv> <output.csv>")