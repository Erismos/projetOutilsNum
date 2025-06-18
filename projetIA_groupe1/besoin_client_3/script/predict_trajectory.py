import pandas as pd
import joblib
from datetime import datetime

def predict_trajectory(input_data, model_lat_path, model_lon_path, preprocessor_path):
    """
    Prédit la position future d'un navire
    :param input_data: DataFrame avec les features nécessaires
    :return: dict avec LAT et LON prédits
    """
    # Chargement des modèles
    model_lat = joblib.load(model_lat_path)
    model_lon = joblib.load(model_lon_path)
    preprocessor = joblib.load(preprocessor_path)
    
    # Prédiction
    lat_pred = model_lat.predict(input_data)[0]
    lon_pred = model_lon.predict(input_data)[0]
    
    return {'LAT_pred': lat_pred, 'LON_pred': lon_pred}

# Exemple d'utilisation
if __name__ == "__main__":
    # Exemple de données d'entrée (à adapter)
    example_data = pd.DataFrame({
        'SOG': [12.5],
        'COG': [45.2],
        'Heading': [47.0],
        'VesselType': ['Cargo'],
        'Length': [180],
        'Draft': [8.5],
        'hour': [14],
        'day_of_week': [2],
        'is_weekend': [0]
    })
    
    # Chemins vers les modèles (à adapter)
    model_lat_path = "models/model_lat_15min_20250617_1430.pkl"
    model_lon_path = "models/model_lon_15min_20250617_1430.pkl"
    preprocessor_path = "models/preprocessor_15min_20250617_1430.pkl"
    
    # Prédiction
    prediction = predict_trajectory(example_data, model_lat_path, model_lon_path, preprocessor_path)
    print(f"Position prédite dans 15 minutes: LAT={prediction['LAT_pred']:.4f}, LON={prediction['LON_pred']:.4f}")