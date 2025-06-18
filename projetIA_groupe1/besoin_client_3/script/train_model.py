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

# Import sklearn components
from sklearn.model_selection import train_test_split, TimeSeriesSplit, GridSearchCV, RandomizedSearchCV
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet, RidgeCV, LassoCV, ElasticNetCV
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.preprocessing import (StandardScaler, RobustScaler, MinMaxScaler, 
                                   OneHotEncoder, PolynomialFeatures)
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import RFECV, SelectFromModel
from sklearn.ensemble import VotingRegressor
from sklearn.base import clone

# Import joblib
import joblib

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
    elif model_type == 'elastic':
        regressor = ElasticNetCV(l1_ratio=[.1, .5, .9], cv=5, max_iter=10000)
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
def enhanced_evaluation(model, X_test, y_test, target_name):
    """Évaluation complète avec visualisations"""
    
    # Prédictions
    y_pred = model.predict(X_test)
    
    # Métriques
    metrics = {
        'r2': r2_score(y_test, y_pred),
        'mae': mean_absolute_error(y_test, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred))
    }
    
    # Affichage
    print(f"\nPerformance pour {target_name}:")
    print(f"R²: {metrics['r2']:.4f}")
    print(f"MAE: {metrics['mae']:.4f}")
    print(f"RMSE: {metrics['rmse']:.4f}")
    
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

# ----------------------------
# 7. Fonction principale améliorée
# ----------------------------
def main():
    # Configuration
    DATA_PATH = '../data/export_IA.csv'
    HORIZON_MIN = 5  # Prédiction 15 minutes dans le futur
    MODEL_TYPE = 'ridge'  # 'ridge', 'lasso', 'elastic', 'linear'
    
    print("=== Chargement des données ===")
    df = load_enhanced_data(DATA_PATH, sample_fraction=1.0)
    
    print("\n=== Feature engineering ===")
    df = enhanced_feature_engineering(df, HORIZON_MIN)
    
    # Vérification des NaN
    print("\n=== Vérification des valeurs manquantes ===")
    print(df.isna().sum())
    
    # Sélection des features et target
    feature_cols = [col for col in df.columns if col not in 
                   ['BaseDateTime', 'MMSI', 'LAT', 'LON', 'target_LAT', 'target_LON']]
    X = df[feature_cols]
    y_lat = df['target_LAT']
    y_lon = df['target_LON']
    
    # Vérification finale
    assert not X.isna().any().any(), "Il reste des NaN dans les features!"
    assert not y_lat.isna().any(), "Il reste des NaN dans y_lat!"
    assert not y_lon.isna().any(), "Il reste des NaN dans y_lon!"
    
    # Sélection des features et target
    feature_cols = [col for col in df.columns if col not in 
                   ['BaseDateTime', 'MMSI', 'LAT', 'LON', 'target_LAT', 'target_LON']]
    X = df[feature_cols]
    y_lat = df['target_LAT']
    y_lon = df['target_LON']
    
    # Split train/test en conservant l'ordre temporel
    test_size = 0.2
    split_idx = int(len(X) * (1 - test_size))
    
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_lat_train, y_lat_test = y_lat.iloc[:split_idx], y_lat.iloc[split_idx:]
    y_lon_train, y_lon_test = y_lon.iloc[:split_idx], y_lon.iloc[split_idx:]
    
    print(f"\n=== Entraînement modèle LATITUDE ({MODEL_TYPE.upper()}) ===")
    model_lat, lat_metrics = train_with_cv(
        X_train, y_lat_train, 
        build_enhanced_model(MODEL_TYPE)
    )
    
    print("\n=== Entraînement modèle LONGITUDE ===")
    model_lon, lon_metrics = train_with_cv(
        X_train, y_lon_train, 
        build_enhanced_model(MODEL_TYPE)
    )
    
    print("\n=== Évaluation finale ===")
    print("\nModèle Latitude - Scores CV:")
    for i, m in enumerate(lat_metrics):
        print(f"Fold {i+1}: R²={m['r2']:.4f}, MAE={m['mae']:.4f}")
    
    lat_metrics_test = enhanced_evaluation(model_lat, X_test, y_lat_test, "LATITUDE")
    
    print("\nModèle Longitude - Scores CV:")
    for i, m in enumerate(lon_metrics):
        print(f"Fold {i+1}: R²={m['r2']:.4f}, MAE={m['mae']:.4f}")
    
    lon_metrics_test = enhanced_evaluation(model_lon, X_test, y_lon_test, "LONGITUDE")
    
    # Sauvegarde des modèles
    print("\n=== Sauvegarde des modèles ===")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_prefix = f"enhanced_{MODEL_TYPE}_{HORIZON_MIN}min_{timestamp}"
    
    joblib.dump(model_lat, f'{model_prefix}_lat.pkl')
    joblib.dump(model_lon, f'{model_prefix}_lon.pkl')
    
    print(f"\nModèles sauvegardés avec préfixe: {model_prefix}")

if __name__ == "__main__":
    main()