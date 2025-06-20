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
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from sklearn.svm import LinearSVR




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
    colonnes_utiles = ['MMSI', 'BaseDateTime', 'LAT', 'LON', 'SOG', 'COG', 'Heading', 'VesselType']
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
    df['COG_x'] = np.cos(df['COG'])  # Composante x de la direction
    df['COG_y'] = np.sin(df['COG'])  # Composante y de la direction
    df['Heading'] = np.deg2rad(df['Heading'])
    df['heading_x'] = np.cos(df['Heading'])  # Composante x de la direction
    df['heading_y'] = np.sin(df['Heading'])  # Composante y de la direction
    df['SOG'] = df['SOG'] * 0.514444  # Conversion noeuds -> m/s

    
    # Calcul du décalage des positions
    df['dLAT'] = df.groupby('MMSI')['LAT'].shift(-1) - df['LAT']
    df['dLON'] = df.groupby('MMSI')['LON'].shift(-1) - df['LON']

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
    df['acceleration'] = df['acceleration'].fillna(0)
    
    df.dropna(subset=['delta_t', 'acceleration', 'dLAT', 'dLON'], inplace=True)
    df.drop(df[df['delta_t'] > 3600].index, inplace=True)

    # Suppression des navires à l'arrêt
    seuil_arret = 0.5  # m/s
    df = df[df['SOG'] > seuil_arret]


    # Suppression des colonnes non utilisées
    df.drop(columns=["BaseDateTime", "COG", "Heading", "delta_v"], inplace=True)

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
    Entraîne un modèle de prédiction de trajectoire avec normalisation si nécessaire.

    Args:
        X_train (pd.DataFrame): Features d'entraînement
        y_train (pd.DataFrame): Cibles d'entraînement
        model_type (str): Type de modèle à entraîner parmi :
            - 'random_forest'
            - 'gradient_boosting'
            - 'knn'
            - 'linear_regression'
            - 'ridge'
            - 'xgboost'
            - 'svr'
        save_path (str): Chemin pour sauvegarder le modèle entraîné

    Returns:
        object: Modèle entraîné

    Raises:
        ValueError: Si le type de modèle n'est pas reconnu
    """

    # Choix du modèle
    if model_type == 'random_forest':
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        use_scaler = False
    elif model_type == 'gradient_boosting':
        model = MultiOutputRegressor(GradientBoostingRegressor(n_estimators=100, random_state=42))
        use_scaler = False
    elif model_type == 'knn':
        model = KNeighborsRegressor(n_neighbors=5)
        use_scaler = True
    elif model_type == 'linear_regression':
        model = LinearRegression()
        use_scaler = True
    elif model_type == 'ridge':
        model = Ridge(alpha=1.0)
        use_scaler = True
    elif model_type == 'xgboost':
        model = MultiOutputRegressor(XGBRegressor(objective='reg:squarederror', random_state=42))
        use_scaler = False
    else:
        raise ValueError(f"Type de modèle non supporté: {model_type}")

    # Pipeline avec scaler si nécessaire
    if use_scaler:
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('regressor', model)
        ])
    else:
        pipeline = model

    # Entraînement
    pipeline.fit(X_train, y_train)
    print("Entraînement terminé.")

    # Sauvegarde
    if save_path:
        joblib.dump(pipeline, save_path)
        print(f"Modèle sauvegardé sous {save_path}")

    return pipeline

def save_metrics_to_txt(metrics, filepath):
    result_text = (
        f"Score R²: {metrics['r2_score']:.4f}\n"
        f"Erreur quadratique moyenne: {metrics['mean_squared_error']:.2f}\n\n"
        "Erreurs géographiques:\n"
        f"- Moyenne: {metrics['mean_geo_error']:.2f} mètres\n"
        f"- Premier quartile: {metrics['q1_geo_error']:.2f} mètres\n"
        f"- Médiane: {metrics['median_geo_error']:.2f} mètres\n"
        f"- Troisième quartile: {metrics['q3_geo_error']:.2f} mètres\n"
        f"- 90 quartile: {metrics['q90_geo_error']:.2f} mètres\n"
        f"- Minimum: {metrics['min_geo_error']:.2f} mètres\n"
        f"- Maximum: {metrics['max_geo_error']:.2f} mètres\n"
    )

    # Affichage dans la console
    print(result_text)

    # Sauvegarde dans un fichier texte
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(result_text)

    print(f"Résultats sauvegardés dans {filepath}")
def evaluate_model(model: object, X_test: pd.DataFrame, y_test: pd.DataFrame,
                   model_type: str) -> dict:
    """
    Évalue les performances d'un modèle entraîné basé sur les prédictions de dLAT/dLON.

    Args:
        model (object): Modèle entraîné à évaluer
        X_test (pd.DataFrame): Features de test (normalisées ou non)
        y_test (pd.DataFrame): Cibles de test (dLAT, dLON)
        model_type (str): Nom du modèle (utilisé pour le nom du fichier de log)

    Returns:
        dict: Dictionnaire contenant les métriques d'évaluation
    """
    print("\nÉvaluation du modèle...")

    # Prédiction des deltas
    y_pred = model.predict(X_test)

    # Reconstruction des positions prédites à partir de LAT/LON + deltas
    pred_LAT = X_test['LAT'].values + y_pred[:, 0]
    pred_LON = X_test['LON'].values + y_pred[:, 1]

    true_LAT = X_test['LAT'].values + y_test['dLAT'].values
    true_LON = X_test['LON'].values + y_test['dLON'].values

    # Calcul des métriques
    r2 = model.score(X_test, y_test)
    mse = mean_squared_error(y_test, y_pred)

    errors = haversine(true_LAT, true_LON, pred_LAT, pred_LON)

    metrics = {
        'r2_score': r2,
        'mean_squared_error': mse,
        'mean_geo_error': errors.mean(),
        'median_geo_error': np.median(errors),
        'min_geo_error': errors.min(),
        'max_geo_error': errors.max(),
        'q1_geo_error': np.percentile(errors, 25),
        'q3_geo_error': np.percentile(errors, 75),
        'q90_geo_error': np.percentile(errors, 90),
    }

    save_metrics_to_txt(metrics, f'logs/{model_type}_metrics.txt')
    return metrics

def visualize_results(y_test: pd.DataFrame, y_pred: np.ndarray, mmsi_test: pd.Series,
                      futur: bool, filename: str, model=None, X_init=None, steps=15) -> None:
    """
    Visualise les trajets réels et prédits (en dLAT/dLON transformés) par MMSI.

    Args:
        y_test (pd.DataFrame): Cibles de test contenant dLAT, dLON
        y_pred (np.ndarray): Prédictions de dLAT, dLON
        mmsi_test (pd.Series): Identifiants MMSI
        futur (bool): Active la projection à plusieurs pas (non implémenté ici)
        filename (str): Chemin du fichier HTML
        model (object): Modèle (nécessaire pour prédiction future)
        X_init (pd.DataFrame): Données initiales pour prédiction future
        steps (int): Nombre de pas à prédire
    """
    print(f"Visualisation en cours... ({filename})")

    # Recalculer les vraies et les prédictions
    pred_LAT = X_test['LAT'].values + y_pred[:, 0]
    pred_LON = X_test['LON'].values + y_pred[:, 1]

    true_LAT = X_test['LAT'].values + y_test['dLAT'].values
    true_LON = X_test['LON'].values + y_test['dLON'].values

    m = folium.Map(location=[true_LAT.mean(), true_LON.mean()], zoom_start=6)

    for i in range(0, len(true_LAT), max(1, len(true_LAT) // 500)):
        folium.PolyLine(
            [(X_test['LAT'].iloc[i], X_test['LON'].iloc[i]), (true_LAT[i], true_LON[i])],
            color='green', weight=2, tooltip='Réel'
        ).add_to(m)
        folium.PolyLine(
            [(X_test['LAT'].iloc[i], X_test['LON'].iloc[i]), (pred_LAT[i], pred_LON[i])],
            color='blue', weight=2, tooltip='Prédit'
        ).add_to(m)

    m.save(f"maps/{filename}_map.html")
    print(f"Carte sauvegardée sous {filename}")

if __name__ == "__main__":
    # 1. Préparation des données
    print("Préparation des données...")
    df = prepare_data()
    df.to_csv('data/prepared_data.csv', index=False)
    
    df = pd.read_csv("data/prepared_data.csv")

    # 2. Sélection des features et target
    features = ["LAT", "LON", "SOG", "acceleration", "hour", "heading_x", "heading_y", "COG_x", "COG_y",
                "hour_sin", "hour_cos", "delta_t", "weekday", 
                "VesselType", "timestamp"]
    X = df[features]
    X_meta = df[["MMSI"]]
    
    y = df[["dLAT", "dLON"]]
    
    # 3. Séparation des données
    X_train, X_test, y_train, y_test, X_meta_train, X_meta_test = train_test_split(
        X, y, X_meta, test_size=0.2, random_state=42
    )
    
    # 4. Entraînement du modèle
    # 'random_forest', 'gradient_boosting', 'knn', 'linear_regression', 'ridge', 'xgboost'
    for model_type in ['random_forest', 'gradient_boosting', 'knn', 'linear_regression', 'ridge', 'xgboost']:
        print(f"\nEntraînement du modèle {model_type}...")
        model = train_model(
            X_train, y_train,
            model_type=model_type,
            save_path=f'models/{model_type}_model.pkl'
        )
    
        # model = joblib.load('models/random_forest_model.pkl')
        # 5. Évaluation du modèle
        metrics = evaluate_model(model, X_test, y_test, model_type)
        
        # 6. Visualisation des résultats
        y_pred = model.predict(X_test)
        visualize_results(y_test, y_pred, X_meta_test["MMSI"], futur=True, model=model, X_init = X_test, filename = f"{model_type}_predictions")