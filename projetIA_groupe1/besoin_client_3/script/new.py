import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
import joblib
from geopy.distance import geodesic
import matplotlib.pyplot as plt

class EnhancedTrajectoryPredictor:
    def __init__(self):
        self.models = {}
        self.preprocessor = None
        self.features = ['SOG', 'COG', 'Heading', 'VesselType', 'Length', 'Draft', 'hour', 'day_of_week']
        self.targets = ['LAT', 'LON']
        self.horizons = [5, 10, 15]  # en minutes
        
    def calculate_distance_error(self, y_true, y_pred):
        """Calcule l'erreur de distance en mètres"""
        errors = []
        for (lat_true, lon_true), (lat_pred, lon_pred) in zip(y_true.values, y_pred):
            true_pos = (lat_true, lon_true)
            pred_pos = (lat_pred, lon_pred)
            errors.append(geodesic(true_pos, pred_pos).meters)
        return np.mean(errors)
    
    def prepare_data(self, filepath):
        """Amélioration de la préparation des données"""
        data = pd.read_csv(filepath)
        
        # Conversion et tri
        data['BaseDateTime'] = pd.to_datetime(data['BaseDateTime'])
        data.sort_values(['MMSI', 'BaseDateTime'], inplace=True)
        
        # Features temporelles
        data['hour'] = data['BaseDateTime'].dt.hour
        data['day_of_week'] = data['BaseDateTime'].dt.dayofweek
        data['time_sin'] = np.sin(2 * np.pi * data['hour']/24)
        data['time_cos'] = np.cos(2 * np.pi * data['hour']/24)
        
        # Features supplémentaires
        data['speed_heading_x'] = data['SOG'] * np.cos(np.radians(data['Heading']))
        data['speed_heading_y'] = data['SOG'] * np.sin(np.radians(data['Heading']))
        
        # Normalisation des angles circulaires
        data['Heading_sin'] = np.sin(np.radians(data['Heading']))
        data['Heading_cos'] = np.cos(np.radians(data['Heading']))
        data['COG_sin'] = np.sin(np.radians(data['COG']))
        data['COG_cos'] = np.cos(np.radians(data['COG']))
        
        self.features.extend(['time_sin', 'time_cos', 'speed_heading_x', 'speed_heading_y',
                            'Heading_sin', 'Heading_cos', 'COG_sin', 'COG_cos'])
        
        # Séparation par navire
        vessels = data.groupby('MMSI')
        
        X, y = [], []
        
        for mmsi, vessel_data in vessels:
            if len(vessel_data) < 20:  # minimum de points
                continue
            
            vessel_data = vessel_data.copy()
                
            # Calcul des différences de position
            vessel_data['delta_lat'] = vessel_data['LAT'].diff()
            vessel_data['delta_lon'] = vessel_data['LON'].diff()
            vessel_data['time_diff'] = vessel_data['BaseDateTime'].diff().dt.total_seconds() / 60
            
            # Suppression de la première ligne avec NaN
            vessel_data = vessel_data.iloc[1:]
            
            for horizon in self.horizons:
                # Sélection des points où l'horizon est disponible
                future_data = vessel_data.shift(-horizon)
                valid_idx = future_data.notna().all(axis=1)
                
                if not valid_idx.any():
                    continue
                    
                # Features avec historique
                for lag in [1, 2, 3]:  # ajout de retards
                    for col in ['LAT', 'LON', 'SOG', 'COG', 'Heading']:
                        vessel_data[f'{col}_lag{lag}'] = vessel_data[col].shift(lag)
                
                X.append(vessel_data[valid_idx][self.features])
                y.append(future_data[valid_idx][self.targets])
        
        if not X:
            raise ValueError("Pas assez de données temporelles valides.")
        
        X = pd.concat(X).fillna(0)
        y = pd.concat(y)
        
        # Prétraitement
        numeric_features = [f for f in self.features if f not in ['VesselType']]
        categorical_features = ['VesselType']
        
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numeric_features),
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
            ])
        
        return X, y
    
    def train_models(self, X, y):
        """Entraînement avec des modèles plus sophistiqués"""
        tscv = TimeSeriesSplit(n_splits=3)
        
        for target in self.targets:
            print(f"\nEntraînement du modèle pour {target}...")
            
            # Pipeline avec modèle Gradient Boosting
            pipeline = Pipeline([
                ('preprocessor', self.preprocessor),
                ('regressor', GradientBoostingRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=5,
                    random_state=42
                ))
            ])
            
            # Recherche d'hyperparamètres
            param_grid = {
                'regressor__n_estimators': [50, 100, 150],
                'regressor__max_depth': [3, 5, 7],
                'regressor__learning_rate': [0.05, 0.1, 0.2]
            }
            
            grid_search = GridSearchCV(
                pipeline,
                param_grid,
                cv=tscv,
                scoring='neg_mean_squared_error',
                n_jobs=-1,
                verbose=1
            )
            
            grid_search.fit(X, y[target])
            self.models[target] = grid_search.best_estimator_
            
            print(f"Meilleurs paramètres pour {target}: {grid_search.best_params_}")
            print(f"MSE (cross-val): {-grid_search.best_score_:.4f}")
    
    def evaluate_models(self, X, y):
        """Évaluation améliorée avec métrique en mètres"""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        results = {}
        
        for target in self.targets:
            model = self.models[target]
            y_pred = model.predict(X_test)
            
            mse = mean_squared_error(y_test[target], y_pred)
            rmse_deg = np.sqrt(mse)
            
            # Calcul de l'erreur en mètres
            if target == 'LAT':
                rmse_m = rmse_deg * 111320
            else:
                # Approximation à latitude moyenne 45°
                rmse_m = rmse_deg * (111320 * np.cos(np.radians(45)))
            
            results[target] = {
                'MSE': mse,
                'RMSE_deg': rmse_deg,
                'RMSE_m': rmse_m
            }
            
            print(f"\nPerformance pour {target}:")
            print(f"- MSE: {mse:.6f}")
            print(f"- RMSE (degrés): {rmse_deg:.6f}")
            print(f"- RMSE (mètres): {rmse_m:.2f}")
            
            # Visualisation
            plt.figure(figsize=(12, 6))
            plt.plot(y_test[target].values[:100], label='Vraies valeurs')
            plt.plot(y_pred[:100], label='Prédictions')
            plt.title(f"Prédictions vs Réelles pour {target}")
            plt.xlabel("Échantillons")
            plt.ylabel(target)
            plt.legend()
            plt.grid(True)
            plt.show()
        
        # Calcul de l'erreur de distance globale
        y_pred_lat = self.models['LAT'].predict(X_test)
        y_pred_lon = self.models['LON'].predict(X_test)
        y_pred = np.column_stack((y_pred_lat, y_pred_lon))
        
        distance_error = self.calculate_distance_error(y_test, y_pred)
        print(f"\nErreur de distance moyenne: {distance_error:.2f} mètres")
        results['distance_error'] = distance_error
        
        return results

# Utilisation
if __name__ == "__main__":
    predictor = EnhancedTrajectoryPredictor()
    
    print("Préparation des données...")
    X, y = predictor.prepare_data('../data/export_IA.csv')
    
    print("\nEntraînement des modèles...")
    predictor.train_models(X, y)
    
    print("\nÉvaluation des modèles...")
    results = predictor.evaluate_models(X, y)
    
    print("\nRésultats finaux:")
    print(f"- Erreur LAT: {results['LAT']['RMSE_m']:.2f} m")
    print(f"- Erreur LON: {results['LON']['RMSE_m']:.2f} m")
    print(f"- Erreur de distance moyenne: {results['distance_error']:.2f} m")
    
    # Sauvegarde des modèles
    import os
    os.makedirs('improved_models', exist_ok=True)
    joblib.dump(predictor.models['LAT'], 'improved_models/model_lat.pkl')
    joblib.dump(predictor.models['LON'], 'improved_models/model_lon.pkl')
    joblib.dump(predictor.preprocessor, 'improved_models/preprocessor.pkl')
    print("Modèles améliorés sauvegardés")