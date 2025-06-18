"""
Script de prédiction de trajectoire maritime utilisant l'apprentissage automatique

Ce script permet de :
1. Préparer et nettoyer les données AIS (Automatic Identification System)
2. Entraîner un modèle de prédiction de position future des navires
3. Évaluer les performances du modèle
4. Visualiser les résultats sur une carte

Auteur : Auvray Clément
Date : juin 2025
Version : 1.0

Dépendances :
- pandas, numpy
- scikit-learn
- matplotlib
- folium
- joblib
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import mean_squared_error, r2_score



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

    # Calcul des positions suivantes
    df['LAT_next'] = df.groupby('MMSI')['LAT'].shift(-1)
    df['LON_next'] = df.groupby('MMSI')['LON'].shift(-1)
    df.dropna(subset=['LON_next'], inplace=True)
    df.dropna(subset=['LAT_next'], inplace=True)

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

def train_model(X_train: pd.DataFrame, y_train: pd.DataFrame, 
                model_type: str = 'random_forest', 
                save_path: str = 'models/trained_model.pkl') -> object:
    """
    Entraîne un modèle de prédiction de trajectoire.

    Args:
        X_train (pd.DataFrame): Features d'entraînement
        y_train (pd.DataFrame): Cibles d'entraînement
        model_type (str): Type de modèle à entraîner ('random_forest' par défaut)
        save_path (str): Chemin pour sauvegarder le modèle entraîné

    Returns:
        object: Modèle entraîné

    Raises:
        ValueError: Si le type de modèle n'est pas reconnu
    """
    print(f"\nEntraînement d'un modèle {model_type}...")
    
    if model_type == 'random_forest':
        model = RandomForestRegressor(n_estimators=100, random_state=42)
    # Ajouter ici d'autres types de modèles si nécessaire
    # elif model_type == 'gradient_boosting':
    #     model = GradientBoostingRegressor()
    else:
        raise ValueError(f"Type de modèle non supporté: {model_type}")

    # Entraînement du modèle
    model.fit(X_train, y_train)
    print("Entraînement terminé.")

    # Sauvegarde du modèle
    if save_path:
        joblib.dump(model, save_path)
        print(f"Modèle sauvegardé sous {save_path}")

    return model

def evaluate_model(model: object, X_test: pd.DataFrame, y_test: pd.DataFrame) -> dict:
    """
    Évalue les performances d'un modèle entraîné.

    Args:
        model (object): Modèle entraîné à évaluer
        X_test (pd.DataFrame): Features de test
        y_test (pd.DataFrame): Cibles de test

    Returns:
        dict: Dictionnaire contenant les métriques d'évaluation
    """
    print("\nÉvaluation du modèle...")
    
    # Prédiction
    y_pred = model.predict(X_test)
    
    # Calcul des métriques
    r2_score = model.score(X_test, y_test)
    mse = mean_squared_error(y_test, y_pred)
    
    # Calcul des erreurs géographiques
    errors = haversine(y_test["LAT_next"], y_test["LON_next"], 
                      y_pred[:, 0], y_pred[:, 1])
    
    # Calcul des quartiles
    q1 = np.percentile(errors, 25)
    median = np.median(errors)  # déjà calculé
    q3 = np.percentile(errors, 75)
    
    # Compilation des résultats
    metrics = {
        'r2_score': r2_score,
        'mean_squared_error': mse,
        'mean_geo_error': errors.mean(),
        'median_geo_error': median,
        'min_geo_error': errors.min(),
        'max_geo_error': errors.max(),
        'q1_geo_error': q1,
        'q3_geo_error': q3
    }

    
    # Affichage des résultats
    print(f"Score R²: {metrics['r2_score']:.4f}")
    print(f"Erreur quadratique moyenne: {metrics['mean_squared_error']:.2f}")
    print("\nErreurs géographiques:")
    print(f"- Moyenne: {metrics['mean_geo_error']:.2f} mètres")
    print(f"- Premier quartile: {metrics['q1_geo_error']:.2f} mètres")
    print(f"- Médiane: {metrics['median_geo_error']:.2f} mètres")
    print(f"- Troisième quartile: {metrics['q3_geo_error']:.2f} mètres")
    print(f"- Minimum: {metrics['min_geo_error']:.2f} mètres")
    print(f"- Maximum: {metrics['max_geo_error']:.2f} mètres")
    
    
    return metrics

def visualize_results(errors: np.ndarray, y_test: pd.DataFrame, y_pred: np.ndarray, mmsi_test: pd.Series) -> None:
    """
    Visualise les trajets réels et prédits par MMSI.

    Args:
        errors (np.ndarray): Tableau des erreurs de prédiction
        y_test (pd.DataFrame): Positions réelles
        y_pred (np.ndarray): Positions prédites
        mmsi_test (pd.Series): Identifiants MMSI correspondants
    """

    # Histogramme des erreurs
    plt.hist(errors, bins=50, edgecolor='k')
    plt.xlabel("Erreur (mètres)")
    plt.ylabel("Nombre d'exemples")
    plt.title("Distribution des erreurs de position")
    plt.show()

    # Création de la carte centrée
    map_center = [y_test["LAT_next"].mean(), y_test["LON_next"].mean()]
    m = folium.Map(location=map_center, zoom_start=6)

    # Reconstitution du DataFrame complet avec MMSI
    full_df = y_test.copy()
    full_df["LAT_pred"] = y_pred[:, 0]
    full_df["LON_pred"] = y_pred[:, 1]
    full_df["MMSI"] = mmsi_test.values

    # Sélection d'un petit nombre de MMSI pour affichage (ex: 5 premiers)
    unique_mmsi = full_df["MMSI"].unique()[:50]

    for mmsi in unique_mmsi:
        df_ship = full_df[full_df["MMSI"] == mmsi].sort_index()

        # Trajet réel (bleu)
        real_coords = list(zip(df_ship["LAT_next"], df_ship["LON_next"]))
        folium.PolyLine(real_coords, color="blue", weight=2.5, opacity=0.7,
                        tooltip=f"Trajet réel MMSI {mmsi}").add_to(m)

        # Trajet prédit (rouge)
        pred_coords = list(zip(df_ship["LAT_pred"], df_ship["LON_pred"]))
        folium.PolyLine(pred_coords, color="red", weight=2.5, opacity=0.7,
                        tooltip=f"Trajet prédit MMSI {mmsi}").add_to(m)

        # Marqueurs de départ et arrivée
        folium.Marker(real_coords[0], icon=folium.Icon(color='green', icon='play'),
                      popup=f"Départ réel MMSI {mmsi}").add_to(m)
        folium.Marker(real_coords[-1], icon=folium.Icon(color='blue', icon='flag'),
                      popup=f"Arrivée réelle MMSI {mmsi}").add_to(m)

        folium.Marker(pred_coords[0], icon=folium.Icon(color='orange', icon='play'),
                      popup=f"Départ prédit MMSI {mmsi}").add_to(m)
        folium.Marker(pred_coords[-1], icon=folium.Icon(color='red', icon='flag'),
                      popup=f"Arrivée prédite MMSI {mmsi}").add_to(m)

    # Sauvegarde
    m.save("predictions_map.html")
    print("Carte enregistrée sous 'predictions_map.html'.")


    
    
"""TODO

model = GradientBoostingRegressor()
model.fit(X_train, y_train)

model = MultiOutputRegressor(GradientBoostingRegressor())

model = KNeighborsRegressor(n_neighbors=5)
model.fit(X_train, y_train)

from sklearn.linear_model import LinearRegression
model = LinearRegression()

from sklearn.linear_model import Ridge
model = Ridge(alpha=1.0)

from xgboost import XGBRegressor
from sklearn.multioutput import MultiOutputRegressor

model = MultiOutputRegressor(XGBRegressor())
model.fit(X_train, y_train)

from sklearn.svm import SVR
from sklearn.multioutput import MultiOutputRegressor

model = MultiOutputRegressor(SVR(kernel='rbf'))

"""

if __name__ == "__main__":
    # # 1. Préparation des données
    print("Préparation des données...")
    # df = prepare_data()
    # df.to_csv('data/prepared_data.csv', index=False)
    
    df = pd.read_csv("data/prepared_data.csv")
    print(df.head(50))
    # # 2. Sélection des features et target
    features = ["LAT", "LON", "SOG", "hour", "dir_x", "dir_x",
                "hour_sin", "hour_cos", "delta_t", "is_stopped", "weekday", 
                "VesselType", "timestamp"]
    X = df[features]
    X_meta = df[["MMSI"]]
    
    y = df[["LAT_next", "LON_next"]]
    
    # # 3. Séparation des données
    X_train, X_test, y_train, y_test, X_meta_train, X_meta_test = train_test_split(
        X, y, X_meta, test_size=0.2, random_state=42
    )
    
    # 4. Entraînement du modèle
    # model = train_model(
    #     X_train, y_train,
    #     model_type='random_forest',
    #     save_path='models/random_forest_model.pkl'
    # )
    
    model = joblib.load('models/random_forest_model.pkl')
    # 5. Évaluation du modèle
    metrics = evaluate_model(model, X_test, y_test)
    
    # 6. Visualisation des résultats
    y_pred = model.predict(X_test)
    errors = haversine(y_test["LAT_next"], y_test["LON_next"], y_pred[:, 0], y_pred[:, 1])
    visualize_results(errors, y_test, y_pred, X_meta_test["MMSI"])






