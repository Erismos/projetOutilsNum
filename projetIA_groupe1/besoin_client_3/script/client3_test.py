import os
import pickle
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import mixed_precision
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, LSTM, Dense, Dropout, concatenate, Bidirectional, BatchNormalization, Attention
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, CSVLogger
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler

# Configuration initiale (doit être au tout début)
os.environ['TF_NUM_INTRAOP_THREADS'] = '8'
os.environ['TF_NUM_INTEROP_THREADS'] = '8'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Réduit les logs TensorFlow

# Configuration GPU
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(e)

# Mixed precision policy
policy = mixed_precision.Policy('mixed_float16')
mixed_precision.set_global_policy(policy)

def prepare_trajectory_data(csv_path, output_dir, time_horizons=[5, 10, 15]):
    """Version optimisée avec traitement par lots"""
    print("Chargement et prétraitement des données...")
    
    # Chargement avec filtrage initial
    df = pd.read_csv(csv_path)
    df = df[(df['LAT'].between(18, 31)) & (df['LON'].between(-98, -80)) &
            (df['SOG'] > 0.1) & (df['COG'].between(0, 360))].copy()
    
    # Feature engineering
    df['dt'] = pd.to_datetime(df['BaseDateTime'])
    df = df.sort_values(['MMSI', 'dt'])
    df['time_diff'] = df.groupby('MMSI')['dt'].diff().dt.total_seconds().fillna(0)
    df = df[df['time_diff'] <= 3600].copy()
    
    # Calculs différentiels
    df['lat_diff'] = df.groupby('MMSI')['LAT'].diff().fillna(0)
    df['lon_diff'] = df.groupby('MMSI')['LON'].diff().fillna(0)
    df['speed'] = df['SOG'] * 0.514444  # Conversion en m/s
    df['accel'] = df.groupby('MMSI')['speed'].diff().fillna(0) / (df['time_diff'] + 1e-6)
    df['turn_rate'] = df.groupby('MMSI')['COG'].diff().fillna(0) / (df['time_diff'] + 1e-6)
    
    # Sélection des trajectoires valides
    traj_lengths = df.groupby('MMSI').size()
    valid_mmsi = traj_lengths[traj_lengths >= 20].index
    df = df[df['MMSI'].isin(valid_mmsi)].copy()
    
    # Préparation des séquences
    feature_cols = ['LAT', 'LON', 'speed', 'COG', 'VesselType', 
                   'Length', 'Width', 'time_diff', 'lat_diff', 
                   'lon_diff', 'accel', 'turn_rate']
    
    sequences = []
    targets = {f'target_{t}m': [] for t in time_horizons}
    
    for mmsi, group in df.groupby('MMSI'):
        group = group.sort_values('dt').reset_index(drop=True)
        if len(group) < 10 + max(time_horizons):
            continue
            
        for i in range(10, len(group)-max(time_horizons)):
            window = group.iloc[i-10:i]
            if window['speed'].mean() < 0.2:
                continue
                
            sequences.append(window[feature_cols].values.astype(np.float32))
            
            for t in time_horizons:
                target_idx = min(i + int(t*60/group['time_diff'].mean()), len(group)-1)
                targets[f'target_{t}m'].append([
                    group.iloc[target_idx]['LAT'],
                    group.iloc[target_idx]['LON']
                ])
    
    # Normalisation
    X = np.array(sequences, dtype=np.float32)
    lat_scaler = MinMaxScaler(feature_range=(-1, 1)).fit(X[:, :, 0].reshape(-1, 1))
    lon_scaler = MinMaxScaler(feature_range=(-1, 1)).fit(X[:, :, 1].reshape(-1, 1))
    
    X[:, :, 0] = lat_scaler.transform(X[:, :, 0].reshape(-1, 1)).reshape(X.shape[0], X.shape[1])
    X[:, :, 1] = lon_scaler.transform(X[:, :, 1].reshape(-1, 1)).reshape(X.shape[0], X.shape[1])
    
    # Sauvegarde des scalers
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, 'geo_scalers.pkl'), 'wb') as f:
        pickle.dump({'lat': lat_scaler, 'lon': lon_scaler}, f)
    
    # Conversion des cibles
    for t in time_horizons:
        targets[f'target_{t}m'] = np.array(targets[f'target_{t}m'], dtype=np.float32)
    
    return {'X': X, 'y': targets, 'feature_names': feature_cols}
from tensorflow.keras.layers import Lambda
def build_improved_model(input_shape):
    """Modèle optimisé avec attention corrigée"""
    strategy = tf.distribute.MirroredStrategy()
    
    with strategy.scope():
        inputs = Input(shape=input_shape, dtype=tf.float32)
        
        # Normalisation des entrées
        x = BatchNormalization()(inputs)
        
        # Couches LSTM optimisées
        x = Bidirectional(LSTM(128, return_sequences=True))(x)
        x = Dropout(0.3)(x)
        
        # Mécanisme d'attention corrigé
        # 1. Projection pour aligner les dimensions
        query_proj = Dense(256)(x[:, -1, :])  # 256 = 2*128 (bidirectional)
        query_expanded = Lambda(lambda x: tf.expand_dims(x, axis=1),
                              output_shape=(None, 1, 256))(query_proj)
        
        # 2. Attention avec dimensions compatibles
        def attention_layer(query_value):
            query, value = query_value
            # Transposition pour matmul correct
            value_transposed = tf.transpose(value, perm=[0, 2, 1])  # [batch, features, timesteps]
            attention_scores = tf.matmul(query, value_transposed)
            attention_weights = tf.nn.softmax(attention_scores, axis=-1)
            return tf.matmul(attention_weights, value)
            
        attention_output = Lambda(attention_layer,
                                output_shape=(None, 1, 256))([query_expanded, x])
        
        attention_output = Lambda(lambda x: tf.squeeze(x, axis=1),
                                output_shape=(None, 256))(attention_output)
        
        # Têtes de sortie
        output_5m = Dense(2, name='output_5m')(attention_output)
        x_context = concatenate([attention_output, output_5m])
        output_10m = Dense(2, name='output_10m')(x_context)
        x_context = concatenate([x_context, output_10m])
        output_15m = Dense(2, name='output_15m')(x_context)
        
        model = Model(inputs=inputs, outputs=[output_5m, output_10m, output_15m])
        
        # Configuration de l'optimiseur
        opt = Adam(learning_rate=0.0005)
        
        model.compile(
            optimizer=opt,
            loss={'output_5m': 'mse', 'output_10m': 'mse', 'output_15m': 'mse'},
            loss_weights={'output_5m': 0.5, 'output_10m': 0.3, 'output_15m': 0.2},
            metrics={'output_5m': ['mae'], 'output_10m': ['mae'], 'output_15m': ['mae']}
        )
    
    return model
def build_simpler_model(input_shape):
    """Version alternative plus simple avec métriques correctes"""
    inputs = Input(shape=input_shape)
    
    x = Bidirectional(LSTM(128))(inputs)
    x = Dropout(0.3)(x)
    
    output_5m = Dense(2, name='output_5m')(x)
    output_10m = Dense(2, name='output_10m')(x)
    output_15m = Dense(2, name='output_15m')(x)
    
    model = Model(inputs=inputs, outputs=[output_5m, output_10m, output_15m])
    
    model.compile(
        optimizer=Adam(0.001),
        loss={
            'output_5m': 'mse',
            'output_10m': 'mse',
            'output_15m': 'mse'
        },
        metrics={
            'output_5m': ['mae'],
            'output_10m': ['mae'],
            'output_15m': ['mae']
        }
    )
    
    return model

def train_trajectory_model(X, y, output_dir, epochs=50, batch_size=64):
    """Fonction d'entraînement silencieuse optimisée"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Préparation des données
    y_train = {
        'output_5m': np.array(y['target_5m']),
        'output_10m': np.array(y['target_10m']),
        'output_15m': np.array(y['target_15m'])
    }
    
    split_idx = int(0.8 * len(X))
    X_train, X_val = X[:split_idx], X[split_idx:]
    
    y_val = {
        'output_5m': y_train['output_5m'][split_idx:],
        'output_10m': y_train['output_10m'][split_idx:],
        'output_15m': y_train['output_15m'][split_idx:]
    }
    y_train = {k: v[:split_idx] for k, v in y_train.items()}
    
    # Configuration des callbacks
    callbacks = [
        ModelCheckpoint(
            os.path.join(output_dir, 'best_model.keras'),
            save_best_only=True,
            monitor='val_loss',
            verbose=0
        ),
        EarlyStopping(
            patience=15,
            restore_best_weights=True,
            verbose=0
        ),
        CSVLogger(
            os.path.join(output_dir, 'training_log.csv'),
            append=False
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=0
        )
    ]
    
    # Création des datasets optimisés
    train_dataset = tf.data.Dataset.from_tensor_slices((X_train, y_train))
    train_dataset = train_dataset.shuffle(1024).batch(batch_size).prefetch(tf.data.AUTOTUNE)
    
    val_dataset = tf.data.Dataset.from_tensor_slices((X_val, y_val))
    val_dataset = val_dataset.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    
    # Construction et entraînement du modèle
    model = build_simpler_model(X.shape[1:])
    
    print("Début de l'entraînement (silencieux)...")
    history = model.fit(
        train_dataset,
        validation_data=val_dataset,
        epochs=epochs,
        callbacks=callbacks,
        verbose=0
    )
    
    model.save(os.path.join(output_dir, 'final_model.keras'))
    print("Entraînement terminé. Résultats sauvegardés dans", output_dir)
    
    return model, X_val, y_val

def evaluate_model(model, X_test, y_test, scalers):
    """Évaluation silencieuse avec calcul des métriques"""
    predictions = model.predict(X_test, verbose=0)
    results = {}
    
    for i, (output_name, minutes) in enumerate([('output_5m', 5), ('output_10m', 10), ('output_15m', 15)]):
        pred = predictions[i]
        true = y_test[output_name]
        
        # Dénormalisation
        pred_lat = scalers['lat'].inverse_transform(pred[:, 0].reshape(-1, 1)).flatten()
        pred_lon = scalers['lon'].inverse_transform(pred[:, 1].reshape(-1, 1)).flatten()
        true_lat = scalers['lat'].inverse_transform(true[:, 0].reshape(-1, 1)).flatten()
        true_lon = scalers['lon'].inverse_transform(true[:, 1].reshape(-1, 1)).flatten()
        
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

# Fonctions utilitaires (conservées identiques)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c * 1000

if __name__ == "__main__":
    # Configuration
    input_csv = "data/export_IA.csv"
    prepared_data_dir = "prepared_data"
    model_dir = "model_output"
    
    # Pipeline complet
    data = prepare_trajectory_data(input_csv, prepared_data_dir)
    model, X_val, y_val = train_trajectory_model(data['X'], data['y'], model_dir, epochs=100)
    
    # Évaluation
    with open(os.path.join(prepared_data_dir, 'geo_scalers.pkl'), 'rb') as f:
        scalers = pickle.load(f)
    results = evaluate_model(model, X_val, y_val, scalers)
    print("Résultats d'évaluation:", results)