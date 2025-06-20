import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import matplotlib.pyplot as plt
import joblib

def prepare_data(filename: str = "data/export_IA.csv") -> pd.DataFrame:
    """
    Prépare les données AIS pour l'entraînement du modèle.

    Args:
        filename (str): Chemin vers le fichier CSV contenant les données AIS.

    Returns:
        pd.DataFrame: DataFrame contenant les données préparées.

    Effectue:
        - Chargement des données
        - Filtrage des colonnes
        - Conversion des types
        - Calcul des features
        - Nettoyage des données
    """
    # Import data
    df = pd.read_csv(filename)
    

    # Vérification et sélection des colonnes utiles
    colonnes_utiles = ['MMSI', 'BaseDateTime', 'LAT', 'LON', 'SOG', 'COG', "VesselType"]
    missing_cols = [col for col in colonnes_utiles if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes dans le DataFrame : {missing_cols}")
    df = df[colonnes_utiles].copy()

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
    df['dir_x'] = np.cos(df['COG'])  # Composante x de la direction
    df['dir_y'] = np.sin(df['COG'])  # Composante y de la direction
    df['SOG'] = df['SOG'] * 0.514444  # Conversion noeuds -> m/s
    
    # Calcul du décalage des positions
    df['dLAT'] = df.groupby('MMSI')['LAT'].shift(-1) - df['LAT']
    df['dLON'] = df.groupby('MMSI')['LON'].shift(-1) - df['LON']
    df.dropna(subset=['dLAT', 'dLON'], inplace=True)


    # Extraction des features temporelles
    df['hour'] = df['BaseDateTime'].dt.hour
    df['weekday'] = df['BaseDateTime'].dt.weekday
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)  # Cyclic encoding
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)  # Cyclic encoding

    # Calcul du delta temps entre les points
    df['delta_t'] = df.groupby('MMSI')['BaseDateTime'].diff().dt.total_seconds()
    df.dropna(subset=['delta_t'], inplace=True)
    df.drop(df[df['delta_t'] > 3600].index, inplace=True)  # Supprime les points trop espacés

    # Détection des navires à l'arrêt
    seuil_arret = 0.5  # m/s
    df['is_stopped'] = (df['SOG'] <= seuil_arret).astype(int)

    # Suppression des colonnes non utilisées
    df.drop(columns=["BaseDateTime", "COG"], inplace=True)

    return df


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance entre deux points géographiques en utilisant la formule haversine.

    Args:
        lat1 (float): Latitude du premier point
        lon1 (float): Longitude du premier point
        lat2 (float): Latitude du second point
        lon2 (float): Longitude du second point

    Returns:
        float: Distance en mètres entre les deux points
    """
    R = 6371000  # Rayon de la Terre en mètres
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = np.sin(delta_phi / 2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c

def prepare_sequences(df, sequence_length=10, target_length=1):
    """
    Prépare les séquences pour le LSTM
    
    Args:
        df: DataFrame préparé
        sequence_length: nombre de pas de temps dans une séquence
        target_length: nombre de pas de temps à prédire
        
    Returns:
        X, y: séquences d'entrée et cibles
    """
    features = ["LAT", "LON", "SOG", "hour", "dir_x", "dir_y", 
                "hour_sin", "hour_cos", "delta_t", "is_stopped", 
                "weekday", "VesselType"]
    
    # Normalisation des données
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df[features])
    
    X, y = [], []
    
    # Parcourir chaque navire séparément
    for mmsi in df['MMSI'].unique():
        vessel_data = df[df['MMSI'] == mmsi].sort_values('timestamp')
        vessel_scaled = scaled_data[df['MMSI'] == mmsi]
        
        # Création des séquences
        for i in range(len(vessel_data) - sequence_length - target_length + 1):
            X.append(vessel_scaled[i:i+sequence_length])
            y.append(vessel_scaled[i+sequence_length:i+sequence_length+target_length, :2])  # On ne garde que LAT et LON
            
    return np.array(X), np.array(y), scaler



def build_lstm_model(input_shape):
    """
    Construit un modèle LSTM
    
    Args:
        input_shape: forme des données d'entrée (timesteps, features)
    
    Returns:
        model: modèle compilé
    """
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(64, return_sequences=False),
        Dropout(0.2),
        Dense(64, activation='relu'),
        Dense(2)  # Sortie: dLAT et dLON
    ])
    
    model.compile(optimizer=Adam(learning_rate=0.001),
                 loss='mse',
                 metrics=['mae'])
    
    return model

def predict_multistep(model, initial_sequence, steps, scaler):
    """
    Prédit plusieurs pas en avant
    
    Args:
        model: modèle entraîné
        initial_sequence: séquence initiale
        steps: nombre de pas à prédire
        scaler: scaler utilisé pour normaliser les données
    """
    current_sequence = initial_sequence.copy()
    predictions = []
    
    for _ in range(steps):
        # Prédiction du prochain pas
        pred = model.predict(current_sequence[np.newaxis, ...])[0]
        predictions.append(pred)
        
        # Mise à jour de la séquence
        new_step = current_sequence[-1].copy()
        new_step[:2] = pred  # Mise à jour de LAT et LON
        current_sequence = np.vstack([current_sequence[1:], new_step])
    
    # Transformation inverse des prédictions
    dummy_data = np.zeros((len(predictions), scaler.n_features_in_))
    dummy_data[:, :2] = predictions
    predictions = scaler.inverse_transform(dummy_data)[:, :2]
    
    return predictions



def main():
    # 1. Préparation des données
    print("Étape 1/5: Préparation des données...")
    df = prepare_data("data/export_IA.csv")
    
    # 2. Préparation des séquences pour LSTM
    print("\nÉtape 2/5: Création des séquences LSTM...")
    sequence_length = 10  # Nombre de pas de temps dans une séquence
    target_length = 1     # Nombre de pas de temps à prédire
    
    X, y, scaler = prepare_sequences(df, sequence_length, target_length)
    
    # Sauvegarde du scaler pour plus tard
    joblib.dump(scaler, 'models/scaler_lstm.pkl')
    
    # 3. Séparation des données
    print("\nÉtape 3/5: Séparation train/test...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # 4. Construction et entraînement du modèle
    print("\nÉtape 4/5: Construction et entraînement du LSTM...")
    input_shape = (X_train.shape[1], X_train.shape[2])  # (timesteps, features)
    
    model = build_lstm_model(input_shape)
    
    history = model.fit(
        X_train, y_train,
        epochs=50,
        batch_size=64,
        validation_data=(X_test, y_test),
        verbose=1
    )
    
    # Sauvegarde du modèle
    model.save('models/lstm_trajectory.h5')
    
    # 5. Évaluation et prédictions
    print("\nÉtape 5/5: Évaluation du modèle...")
    
    # a. Évaluation sur le test set
    loss, mae = model.evaluate(X_test, y_test, verbose=0)
    print(f"\nPerformance sur le test set - MAE: {mae:.4f}, Loss: {loss:.4f}")
    
    # b. Visualisation de l'apprentissage
    plt.figure(figsize=(12, 5))
    plt.plot(history.history['loss'], label='Train Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.title('Évolution de la loss pendant l\'entraînement')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.savefig('logs/lstm_training_curve.png')
    
    # c. Exemple de prédiction multi-pas
    print("\nGénération d'une prédiction multi-pas...")
    sample_idx = np.random.randint(0, len(X_test))
    initial_sequence = X_test[sample_idx]
    
    predicted_trajectory = predict_multistep(
        model, 
        initial_sequence, 
        steps=5, 
        scaler=scaler
    )
    
    print("Prédiction terminée. Visualisez les résultats dans le dossier de sortie.")

if __name__ == "__main__":
    main()