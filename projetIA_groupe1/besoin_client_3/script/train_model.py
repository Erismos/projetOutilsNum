# -*- coding: utf-8 -*-
"""
Script amélioré pour la prédiction de trajectoire des navires
Modèles : Régression Linéaire Avancée avec feature engineering
"""

# Import standards
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import zscore
import time

# Import sklearn components
from sklearn.model_selection import train_test_split, TimeSeriesSplit, GridSearchCV, RandomizedSearchCV
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet, RidgeCV, LassoCV, ElasticNetCV, MultiTaskLassoCV, MultiTaskElasticNetCV
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.preprocessing import (StandardScaler, RobustScaler, MinMaxScaler, 
                                   OneHotEncoder, PolynomialFeatures)
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import RFECV, SelectFromModel, VarianceThreshold
from sklearn.ensemble import VotingRegressor, RandomForestRegressor, GradientBoostingRegressor
from sklearn.base import clone
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.multioutput import MultiOutputRegressor


# Import joblib
import joblib

from geopy.distance import geodesic

def calculate_geographic_distance(y_true, y_pred):
    """
    Calcule la distance géographique entre les prédictions et les vraies positions
    Retourne les distances en mètres
    """
    distances = []
    for (lat_true, lon_true), (lat_pred, lon_pred) in zip(y_true.values, y_pred):
        distances.append(geodesic((lat_true, lon_true), (lat_pred, lon_pred)).meters)
    return np.array(distances)

# ----------------------------
# 1. Chargement des données amélioré
# ----------------------------
def load_enhanced_data(filepath, sample_fraction=1.0):
    """Charge les données avec gestion des types et échantillonnage optionnel"""
    dtype = {
        'MMSI': 'category',
        'VesselType': 'category',
        'Length': 'float32',
        'Draft': 'float32'
    }
    
    df = pd.read_csv(filepath, 
                     parse_dates=['BaseDateTime'],
                     dtype=dtype)
    
    if sample_fraction < 1.0:
        df = df.sample(frac=sample_fraction, random_state=42)
    
    return df

# ----------------------------
# 2. Feature engineering avancé avec gestion des NaN
# ----------------------------
def enhanced_feature_engineering(df, horizon_min=15):
    """Crée des features avancées avec gestion robuste des NaN"""
    
    # Tri obligatoire par navire et temps
    df = df.sort_values(['MMSI', 'BaseDateTime'])
    
    # Features temporelles de base
    df['hour'] = df['BaseDateTime'].dt.hour
    df['day_of_week'] = df['BaseDateTime'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype('int8')
    
    # Features laggées et différences
    group_cols = ['MMSI']
    
    lag_features = ['SOG', 'COG', 'Heading', 'LAT', 'LON']
    for feat in lag_features:
        df[f'{feat}_lag1'] = df.groupby(group_cols)[feat].shift(1)
        df[f'{feat}_diff1'] = df.groupby(group_cols)[feat].diff(1)
    
    # Remplissage des NaN créés par les opérations lag/diff
    for feat in lag_features:
        df[f'{feat}_lag1'].fillna(0, inplace=True)
        df[f'{feat}_diff1'].fillna(0, inplace=True)
    
    # Features d'interaction
    df['SOG_COG_interaction'] = df['SOG'] * df['COG']
    df['SOG_Heading_interaction'] = df['SOG'] * df['Heading']
    
    # Features dérivées avec gestion des NaN
    df['acceleration'] = df.groupby('MMSI')['SOG'].diff() / 60
    df['turn_rate'] = df.groupby('MMSI')['Heading'].diff() / 60
    df[['acceleration', 'turn_rate']] = df[['acceleration', 'turn_rate']].fillna(0)
    
    # Calcul de distance entre points consécutifs
    df['dist_prev'] = np.sqrt(df['LON_diff1']**2 + df['LAT_diff1']**2)
    df['dist_prev'].fillna(0, inplace=True)
    
    # Moyennes mobiles avec min_periods=1 pour éviter les NaN
    window_size = 3
    for feat in ['SOG', 'COG']:
        df[f'{feat}_rolling_mean'] = (df.groupby('MMSI')[feat]
                                     .rolling(window_size, min_periods=1)
                                     .mean()
                                     .reset_index(level=0, drop=True))
        df[f'{feat}_rolling_std'] = (df.groupby('MMSI')[feat]
                                    .rolling(window_size, min_periods=1)
                                    .std()
                                    .reset_index(level=0, drop=True))
    
    # Remplissage des derniers NaN éventuels
    df[['SOG_rolling_mean', 'COG_rolling_mean', 
        'SOG_rolling_std',
        'COG_rolling_std']] = df[
            ['SOG_rolling_mean', 'COG_rolling_mean', 
              'SOG_rolling_std',
             'COG_rolling_std']
        ].fillna(0)
    
    # Target engineering - décalage futur
    df['target_LAT'] = df.groupby('MMSI')['LAT'].shift(-horizon_min)
    df['target_LON'] = df.groupby('MMSI')['LON'].shift(-horizon_min)
    
    # Suppression des dernières lignes où target est NaN
    df = df.dropna(subset=['target_LAT', 'target_LON'])
    
    # Vérification finale des NaN
    if df.isna().any().any():
        print("Avertissement : Il reste des NaN dans le dataframe après le prétraitement")
        print(df.isna().sum())
        df = df.dropna()  # Suppression des lignes avec NaN restants
    
    return df

# ----------------------------
# 3. Pipeline de prétraitement avec imputation
# ----------------------------
def build_enhanced_preprocessor():
    """Construction d'un préprocesseur avec gestion des NaN"""
    
    from sklearn.impute import SimpleImputer
    
    # Colonnes numériques et catégorielles
    numeric_features = ['SOG', 'COG', 'Heading', 'Length', 'Draft', 
                       'hour', 'day_of_week', 'is_weekend',
                       'SOG_lag1', 'COG_lag1', 'Heading_lag1',
                       'SOG_diff1', 'COG_diff1', 'Heading_diff1',
                       'SOG_COG_interaction', 'SOG_Heading_interaction',
                       'acceleration', 'turn_rate', 'dist_prev',
                       'SOG_rolling_mean', 'COG_rolling_mean']
    
    categorical_features = ['VesselType']
    
    # Transformers numériques avec imputation
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value=0)),
        ('scaler', RobustScaler())
    ])
    
    # Transformers catégoriels
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    # Préprocesseur complet
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, numeric_features),
            ('cat', categorical_transformer, categorical_features)],
        remainder='drop')
    
    return preprocessor

# ----------------------------
# 4. Construction de modèle avec vérification des NaN
# ----------------------------
def build_enhanced_model(model_type='ridge'):
    """Construit un pipeline avec vérification des NaN"""
    
    from sklearn.feature_selection import VarianceThreshold
    
    preprocessor = build_enhanced_preprocessor()
    
    # Choix du régresseur
    if model_type == 'ridge':
        regressor = RidgeCV(alphas=[0.1, 1.0, 10.0], cv=5)
    elif model_type == 'lasso':
        regressor = LassoCV(alphas=[0.1, 1.0, 10.0], cv=5, max_iter=10000)
    # elif model_type == 'elastic':
    #     regressor = ElasticNetCV(l1_ratio=[.1, .5, .9], cv=5, max_iter=10000)
    else:
        regressor = LinearRegression()
    
    # Pipeline complet avec étapes supplémentaires
    model = Pipeline([
        ('preprocessor', preprocessor),
        ('variance_threshold', VarianceThreshold(threshold=0.01)),  # Supprime features peu informatives
        ('poly', PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)),
        ('feature_selection', SelectFromModel(estimator=LinearRegression(), threshold='median')),
        ('regressor', regressor)
    ])
    
    return model


# ----------------------------
# 5. Entraînement avec validation croisée
# ----------------------------
def train_with_cv(X, y, model, n_splits=5):
    """Entraînement avec validation croisée temporelle"""
    
    tscv = TimeSeriesSplit(n_splits=n_splits)
    metrics = []
    models = []
    
    for train_index, test_index in tscv.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        
        # Clone le modèle pour chaque fold
        fold_model = clone(model)
        fold_model.fit(X_train, y_train)
        
        # Prédiction et évaluation
        y_pred = fold_model.predict(X_test)
        fold_metrics = {
            'r2': r2_score(y_test, y_pred),
            'mae': mean_absolute_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred))
        }
        
        metrics.append(fold_metrics)
        models.append(fold_model)
    
    # Sélection du meilleur modèle (meilleur R² moyen)
    best_idx = np.argmax([m['r2'] for m in metrics])
    best_model = models[best_idx]
    
    return best_model, metrics

# ----------------------------
# 6. Évaluation améliorée
# ----------------------------
def enhanced_evaluation(model, X_test, y_test, target_name, target_index=None):
    """Évaluation complète avec visualisations"""
    
    # Prédictions complètes
    y_pred_all = model.predict(X_test)
    
    # Détection de la colonne si non spécifiée
    if target_index is None:
        target_index = 0 if target_name == "LATITUDE" else 1
    
    # Sélection de la colonne appropriée
    y_pred = y_pred_all[:, target_index]
    y_test_values = y_test.values if hasattr(y_test, 'values') else y_test
    
    # Métriques standard
    metrics = {
        'r2': r2_score(y_test_values, y_pred),
        'mae': mean_absolute_error(y_test_values, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_test_values, y_pred))
    }
    
    # Calcul de l'erreur géographique si on évalue les deux dimensions
    if hasattr(y_test, 'columns') and len(y_test.columns) == 2:  # Si y_test est un dataframe avec LAT et LON
        geo_distances = calculate_geographic_distance(y_test, y_pred_all)
        metrics.update({
            'mean_geo_distance_m': np.mean(geo_distances),
            'median_geo_distance_m': np.median(geo_distances),
            'std_geo_distance_m': np.std(geo_distances)
        })
    
    # Affichage
    print(f"\nPerformance pour {target_name}:")
    print(f"R²: {metrics['r2']:.4f}")
    print(f"MAE: {metrics['mae']:.4f}") 
    print(f"RMSE: {metrics['rmse']:.4f}")
    
    if 'mean_geo_distance_m' in metrics:
        print("\nMétriques géographiques:")
        print(f"Distance moyenne: {metrics['mean_geo_distance_m']:.2f} m")
        print(f"Distance médiane: {metrics['median_geo_distance_m']:.2f} m")
        print(f"Écart-type: {metrics['std_geo_distance_m']:.2f} m")
        print(f"(≈ {metrics['mean_geo_distance_m']/1000:.2f} km)")
    
    # Visualisation
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    sns.scatterplot(x=y_test, y=y_pred, alpha=0.3)
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], '--r')
    plt.xlabel('Valeurs réelles')
    plt.ylabel('Prédictions')
    plt.title(f'Prédictions vs Réelles - {target_name}')
    
    plt.subplot(1, 2, 2)
    residuals = y_test - y_pred
    sns.histplot(residuals, kde=True)
    plt.xlabel('Erreurs de prédiction')
    plt.title('Distribution des erreurs')
    
    plt.tight_layout()
    plt.show()
    
    return metrics

def compare_models(X_train, y_train, X_test, y_test, horizon_min):
    """Compare plusieurs modèles et retourne leurs performances"""
    
    # Liste des modèles à tester
    models = {
        'Ridge': RidgeCV(alphas=[0.1, 1.0, 10.0], cv=5),
        'Lasso': MultiTaskLassoCV(alphas=[0.1, 1.0, 10.0], cv=5, max_iter=10000),
        # 'ElasticNet': MultiTaskElasticNetCV(l1_ratio=[.1, .5, .9], cv=5, max_iter=10000),
        'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42),
        'GradientBoosting': MultiOutputRegressor(GradientBoostingRegressor(random_state=42, n_estimators=50)),
        'SVR': MultiOutputRegressor(SVR()),
        'KNeighbors': KNeighborsRegressor()
    }
    
    results = []
    
    for name, model in models.items():
        print(f"\n=== Entraînement du modèle {name} ===")
        
        # Construction du pipeline complet
        pipeline = Pipeline([
            ('preprocessor', build_enhanced_preprocessor()),
            ('variance_threshold', VarianceThreshold(threshold=0.01)),
            ('poly', PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)),
            ('feature_selection', SelectFromModel(estimator=LinearRegression(), threshold='median')),
            ('regressor', model)
        ])
        
        # Entraînement
        start_time = time.time()
        pipeline.fit(X_train, y_train)
        train_time = time.time() - start_time
        
        # Prédiction
        y_pred = pipeline.predict(X_test)
        
        # Calcul des métriques
        geo_distances = calculate_geographic_distance(y_test, y_pred)
        
        metrics = {
            'Modèle': name,
            'Temps d\'entraînement (s)': train_time,
            'R2_LAT': r2_score(y_test['target_LAT'], y_pred[:, 0]),
            'R2_LON': r2_score(y_test['target_LON'], y_pred[:, 1]),
            'MAE_LAT': mean_absolute_error(y_test['target_LAT'], y_pred[:, 0]),
            'MAE_LON': mean_absolute_error(y_test['target_LON'], y_pred[:, 1]),
            'Distance moyenne (m)': np.mean(geo_distances),
            'Distance médiane (m)': np.median(geo_distances),
            'Distance max (m)': np.max(geo_distances)
        }
        
        results.append(metrics)
        
        # Sauvegarde du modèle
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = f"model_{name}_{horizon_min}min_{timestamp}.pkl"
        joblib.dump(pipeline, model_path)
        print(f"Modèle {name} sauvegardé sous {model_path}")
    
    return pd.DataFrame(results)

# ----------------------------
# 7. Fonction principale améliorée
# ----------------------------
def main():
    # Configuration
    DATA_PATH = '../data/export_IA.csv'
    HORIZON_MIN = 5  # Prédiction 15 minutes dans le futur
    
    print("=== Chargement des données ===")
    df = load_enhanced_data(DATA_PATH, sample_fraction=0.1)  # Réduisez pour les tests
    
    print("\n=== Feature engineering ===")
    df = enhanced_feature_engineering(df, HORIZON_MIN)
    
    # Sélection des features et target
    feature_cols = [col for col in df.columns if col not in 
                   ['BaseDateTime', 'MMSI', 'LAT', 'LON', 'target_LAT', 'target_LON']]
    X = df[feature_cols]
    y = df[['target_LAT', 'target_LON']]
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False, random_state=42)
    
    # Comparaison des modèles
    results_df = compare_models(X_train, y_train, X_test, y_test, HORIZON_MIN)
    
    # Affichage des résultats
    print("\n=== Résultats comparés ===")
    pd.set_option('display.float_format', '{:.2f}'.format)
    print(results_df.sort_values('Distance moyenne (m)'))
    
    # Sauvegarde des résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_df.to_csv(f'model_comparison_{HORIZON_MIN}min_{timestamp}.csv', index=False)
    print("\nRésultats sauvegardés dans un fichier CSV")

if __name__ == "__main__":
    main()