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

# Configuration GPU
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        # Limiter la mémoire GPU si nécessaire
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        logical_gpus = tf.config.experimental.list_logical_devices('GPU')
        print(f"{len(gpus)} Physical GPUs, {len(logical_gpus)} Logical GPUs")
    except RuntimeError as e:
        print(e)
def prepare_trajectory_data(csv_path, output_dir, time_horizons=[5, 10, 15]):
    """Prépare les données de trajectoire pour l'entraînement avec optimisations GPU/CPU
    
    Args:
        csv_path: Chemin vers le fichier CSV source
        output_dir: Répertoire de sortie pour les scalers
        time_horizons: List des horizons temporels en minutes
        
    Returns:
        Dict contenant:
            - X: Séquences d'entrée (n_samples, seq_len, n_features)
            - y: Cibles pour chaque horizon
            - feature_names: Noms des features
    """
    # ======================================================
    # SECTION 1: Chargement et filtrage initial
    # (Peut être parallélisé avec dask/pandas si le fichier est très gros)
    # ======================================================
    print("Chargement des données...")
    df = pd.read_csv(csv_path)
    
    # Filtrage géographique du Golfe du Mexique
    df = df[
        (df['LAT'].between(18, 31)) & 
        (df['LON'].between(-98, -80)) &
        (df['SOG'] >= 0) & (df['COG'].between(0, 360))
    ].copy()
    
    # Filtrer les navires à l'arrêt (SOG < 0.1 noeuds)
    df = df[df['SOG'] > 0.1].copy()
    
    # ======================================================
    # SECTION 2: Feature engineering
    # (Partie la plus intensive en calcul - à paralléliser)
    # ======================================================
    print("Feature engineering...")
    df['dt'] = pd.to_datetime(df['BaseDateTime'])
    df = df.sort_values(['MMSI', 'dt'])
    
    # Calculs différentiels avec vérification de la continuité temporelle
    df['time_diff'] = df.groupby('MMSI')['dt'].diff().dt.total_seconds().fillna(0)
    
    # ICI ON PEUT AJOUTER DU PARALLELISME (optionnel)
    # from joblib import Parallel, delayed
    # def process_group(group):
    #     # Faire les calculs différentiels pour un groupe
    #     return processed_group
    # results = Parallel(n_jobs=-1)(delayed(process_group)(g) for _, g in df.groupby('MMSI'))
    # df = pd.concat(results)
    
    # Supprimer les sauts temporels trop longs (> 1 heure)
    df = df[df['time_diff'] <= 3600].copy()
    
    # Recalculer après filtrage
    df['lat_diff'] = df.groupby('MMSI')['LAT'].diff().fillna(0)
    df['lon_diff'] = df.groupby('MMSI')['LON'].diff().fillna(0)
    
    # Variables dérivées avec vitesse en m/s
    df['speed'] = df['SOG'] * 0.514444  # Conversion knots -> m/s
    df['accel'] = df.groupby('MMSI')['speed'].diff().fillna(0) / (df['time_diff'] + 1e-6)
    df['turn_rate'] = df.groupby('MMSI')['COG'].diff().fillna(0) / (df['time_diff'] + 1e-6)
    
    # ======================================================
    # SECTION 3: Préparation des séquences
    # (Partie critique pour la performance GPU)
    # ======================================================
    print("Préparation des séquences...")
    
    # Filtrer les trajectoires trop courtes (< 20 points)
    traj_lengths = df.groupby('MMSI').size()
    valid_mmsi = traj_lengths[traj_lengths >= 20].index
    df = df[df['MMSI'].isin(valid_mmsi)].copy()
    
    # Sélection des features (optimiser pour le GPU)
    feature_cols = [
        'LAT', 'LON', 'speed', 'COG',         # Position et mouvement
        'VesselType', 'Length', 'Width',      # Caractéristiques du navire
        'time_diff', 'lat_diff', 'lon_diff',  # Deltas
        'accel', 'turn_rate'                  # Dynamique
    ]
    
    # Initialisation des conteneurs
    sequences = []
    targets = {f'target_{t}m': [] for t in time_horizons}
    
    # ICI ON PEUT PARALLELISER LE TRAITEMENT DES TRAJECTOIRES
    for mmsi, group in df.groupby('MMSI'):
        group = group.sort_values('dt').reset_index(drop=True)
        
        # Vérifier que la trajectoire est assez longue
        if len(group) < 10 + max(time_horizons):
            continue
            
        # Préparer les séquences par fenêtre glissante
        for i in range(10, len(group)-max(time_horizons)):
            current_window = group.iloc[i-10:i]
            
            # Filtrer les fenêtres avec peu de mouvement
            if current_window['speed'].mean() < 0.2:
                continue
                
            # Extraire la séquence (optimisé pour TensorFlow)
            seq = current_window[feature_cols].values.astype(np.float32)  # float32 pour GPU
            sequences.append(seq)
            
            # Préparer les cibles pour chaque horizon
            for t in time_horizons:
                target_idx = min(i + int(t*60/group['time_diff'].mean()), len(group)-1)
                targets[f'target_{t}m'].append([
                    group.iloc[target_idx]['LAT'],
                    group.iloc[target_idx]['LON']
                ])
    
    # ======================================================
    # SECTION 4: Normalisation (critique pour la stabilité GPU)
    # ======================================================
    print("Normalisation...")
    X = np.array(sequences, dtype=np.float32)  # float32 pour GPU
    
    # Normalisation géographique spécifique
    lat_scaler = MinMaxScaler(feature_range=(-1, 1))
    lon_scaler = MinMaxScaler(feature_range=(-1, 1))
    
    # Entraînement des scalers sur l'ensemble des données
    lat_scaler.fit(X[:, :, 0].reshape(-1, 1))
    lon_scaler.fit(X[:, :, 1].reshape(-1, 1))
    
    # Transformation (optimisée)
    X[:, :, 0] = lat_scaler.transform(X[:, :, 0].reshape(-1, 1)).reshape(X.shape[0], X.shape[1])
    X[:, :, 1] = lon_scaler.transform(X[:, :, 1].reshape(-1, 1)).reshape(X.shape[0], X.shape[1])
    
    # Sauvegarde des scalers
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'geo_scalers.pkl'), 'wb') as f:
        pickle.dump({'lat': lat_scaler, 'lon': lon_scaler}, f)
    
    # Conversion finale des cibles en numpy (float32 pour GPU)
    for t in time_horizons:
        targets[f'target_{t}m'] = np.array(targets[f'target_{t}m'], dtype=np.float32)
    
    return {
        'X': X,  # Déjà en float32
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

from tensorflow.keras.layers import GRU, TimeDistributed, SpatialDropout1D
from tensorflow.keras.layers import Attention
def build_improved_model(input_shape):
    # Stratégie de distribution pour multi-GPU
    strategy = tf.distribute.MirroredStrategy()
    
    with strategy.scope():
        inputs = Input(shape=input_shape)
        
        x = BatchNormalization()(inputs)
        
        # Utilisation de CuDNNLSTM si disponible (optimisé pour GPU NVIDIA)
        x = Bidirectional(tf.keras.layers.LSTM(128, return_sequences=True))(x)
        x = Dropout(0.3)(x)
        
        # Mécanisme d'attention
        query = Dense(128)(x[:, -1, :])
        query = tf.expand_dims(query, axis=1)
        
        attention = Attention()([query, x])
        attention = tf.squeeze(attention, axis=1)
        
        # Têtes de sortie
        output_5m = Dense(2, name='output_5m')(attention)
        x_context = concatenate([attention, output_5m])
        output_10m = Dense(2, name='output_10m')(x_context)
        x_context = concatenate([x_context, output_10m])
        output_15m = Dense(2, name='output_15m')(x_context)
        
        model = Model(inputs=inputs, outputs=[output_5m, output_10m, output_15m])
        
        # Optimiseur avec gradient accumulation pour les grands batchs
        opt = Adam(learning_rate=0.0005)
        
        model.compile(
            optimizer=opt,
            loss={'output_5m': 'mse', 'output_10m': 'mse', 'output_15m': 'mse'},
            loss_weights={'output_5m': 0.5, 'output_10m': 0.3, 'output_15m': 0.2},
            metrics={'output_5m': ['mae'], 'output_10m': ['mae'], 'output_15m': ['mae']}
        )
    
    return model

def train_trajectory_model(X, y, output_dir, epochs=50, batch_size=64):
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
    
    # Configuration des callbacks optimisés
    callbacks = [
        ModelCheckpoint(
            os.path.join(output_dir, 'best_model.keras'),
            save_best_only=True,
            monitor='val_loss'
        ),
        EarlyStopping(patience=15, restore_best_weights=True),
        tf.keras.callbacks.TerminateOnNaN(),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6
        )
    ]
    
    # Options d'entraînement optimisées
    options = tf.data.Options()
    options.experimental_distribute.auto_shard_policy = tf.data.experimental.AutoShardPolicy.DATA
    
    # Création du dataset optimisé
    train_dataset = tf.data.Dataset.from_tensor_slices((X_train, y_train))
    train_dataset = train_dataset.with_options(options)
    train_dataset = train_dataset.shuffle(buffer_size=1024).batch(batch_size).prefetch(tf.data.AUTOTUNE)
    
    val_dataset = tf.data.Dataset.from_tensor_slices((X_val, y_val))
    val_dataset = val_dataset.with_options(options)
    val_dataset = val_dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    
    # Entraînement
    history = model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=epochs,
        callbacks=callbacks,
        verbose=1
    )
    
    model.save(os.path.join(output_dir, 'final_model.keras'))
    return model, X_val, y_val

def check_gpu_usage():
    print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))
    tf.debugging.set_log_device_placement(True)
    
    # Créer des tensors
    a = tf.constant([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    b = tf.constant([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    
    # Exécuter une opération
    c = tf.matmul(a, b)
    print(c)
    
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

def temporal_train_test_split(X, y, test_size=0.2):
    """Séparation temporelle (pas aléatoire)"""
    split_idx = int(len(X) * (1 - test_size))
    return X[:split_idx], X[split_idx:], y[:split_idx], y[split_idx:]

def baseline_prediction(X):
    """Prédiction basée sur la vitesse et cap actuels"""
    last_pos = X[:, -1, 0:2]  # Dernière position
    speed = X[:, -1, 2]       # Vitesse en m/s
    cog = np.radians(X[:, -1, 3])  # Cap en radians
    
    # Conversion en déplacement en degrés
    # (Approximation: 111km par degré)
    delta = speed * 60 * 5 / (111000)  # Pour 5 minutes
    
    pred_5m = last_pos + np.column_stack([
        delta * np.cos(cog),
        delta * np.sin(cog)
    ])
    
    return pred_5m

import folium

def plot_trajectory(actual, predicted, zoom=10):
    """Visualisation interactive sur carte"""
    m = folium.Map(location=actual[0], zoom_start=zoom)
    
    folium.PolyLine(actual, color='blue', weight=2.5, opacity=1).add_to(m)
    folium.PolyLine(predicted, color='red', weight=2.5, opacity=0.6).add_to(m)
    
    # Ajout des points clés
    folium.Marker(actual[0], icon=folium.Icon(color='green')).add_to(m)
    folium.Marker(actual[-1], icon=folium.Icon(color='blue')).add_to(m)
    folium.Marker(predicted[-1], icon=folium.Icon(color='red')).add_to(m)
    
    return m

def verify_units(data):
    """Vérifie que les coordonnées sont bien en degrés décimaux"""
    assert data['LAT'].between(-90, 90).all(), "Latitude hors limites"
    assert data['LON'].between(-180, 180).all(), "Longitude hors limites"
    
    # Vérification des vitesses (en noeuds)
    assert data['SOG'].between(0, 50).all(), "Vitesse improbable (en noeuds)"

from geopy.distance import geodesic  # Plus précis que haversine

def calculate_distance(row):
    """Version améliorée avec geopy"""
    return geodesic(
        (row['true_lat'], row['true_lon']), 
        (row['pred_lat'], row['pred_lon'])
    ).meters
    
def add_advanced_features(df):
    """Ajoute des features dynamiques critiques"""
    # Conversion des angles en radians pour les calculs
    df['COG_rad'] = np.radians(df['COG'])
    df['Heading_rad'] = np.radians(df['Heading'])
    
    # Calcul des composantes de vitesse
    df['speed_x'] = df['speed'] * np.sin(df['COG_rad'])
    df['speed_y'] = df['speed'] * np.cos(df['COG_rad'])
    
    # Dérivées secondes
    df['accel_x'] = df.groupby('MMSI')['speed_x'].diff().fillna(0)
    df['accel_y'] = df.groupby('MMSI')['speed_y'].diff().fillna(0)
    
    # Features temporelles
    df['hour'] = df['dt'].dt.hour
    df['day_of_week'] = df['dt'].dt.dayofweek
    
    return df

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
    
    check_gpu_usage()
    tf.keras.mixed_precision.set_global_policy('mixed_float16')
    
    # Configurer le parallélisme des threads
    tf.config.threading.set_intra_op_parallelism_threads(8)  # Pour les opérations individuelles
    tf.config.threading.set_inter_op_parallelism_threads(8)  # Pour le parallélisme entre opérations
    
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
        epochs=1000,
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