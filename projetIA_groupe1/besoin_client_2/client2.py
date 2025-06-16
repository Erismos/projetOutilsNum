import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import joblib
import os
import matplotlib as mpl

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.compose import ColumnTransformer

# 1: pré traitement des données 

data = pd.read_csv("export_IA.csv")

features = ["SOG", "Length", "Draft", "Width", "Cargo"]
target = "VesselType"

x = data[features]
y = data[target]

x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state = 42)

numeric = ["SOG", "Length", "Draft", "Width"]
numeric_transformer = Pipeline(steps=[('scaler', StandardScaler())])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric)
    ]
)

joblib.dump(preprocessor, "processor.joblib")

# 2: apprentissage supervisé pour la classification

models = {
    'RandomForest': {
        'model': RandomForestClassifier(n_jobs=-1, random_state=42),
        'params': {
            'model__n_estimators': [100, 200],
            'model__max_depth': [None, 10]
        }
    }
    #'XGBoost': {
    #    'model': GradientBoostingClassifier(),
    #    'params': {'n_estimators': [100, 200], 'learning_rate': [0.01, 0.1]}
    #},
    #'SVM': {
    #    'model': SVC(),
    #    'params': {'C': [0.1, 1, 10], 'kernel': ['linear', 'rbf']}
    #},
    #'LogisticRegression': {
    #    'model': LogisticRegression(),
    #    'params': {'C': [0.1, 1, 10]}
    #},
    #'KNN': {
    #    'model': KNeighborsClassifier(),
    #    'params': {'n_neighbors': [3, 5, 7]}
    #}
}

results = []

for name, config in models.items():
    print(f"\n🔄 Entraînement du modèle : {name}")
    
    pipe = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('model', config['model'])
    ])
    
    grid = GridSearchCV(pipe, config['params'], cv=5, scoring='accuracy', n_jobs=-1)
    grid.fit(x_train, y_train)
    
    best_model = grid.best_estimator_
    y_pred = best_model.predict(x_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"✅ Meilleur score CV ({name}): {grid.best_score_:.4f}")
    print(f"✅ Accuracy sur test : {acc:.4f}")
    print(f"📊 Meilleurs paramètres : {grid.best_params_}")
    print(f"📈 Rapport de classification :\n{classification_report(y_test, y_pred)}")
    print(f"🧱 Matrice de confusion :\n{confusion_matrix(y_test, y_pred)}")
    
    results.append({
        'model': name,
        'cv_score': grid.best_score_,
        'test_accuracy': acc,
        'best_params': grid.best_params_
    })

# 7. Résumé des résultats
print("\n📋 Résumé des modèles testés :")
for res in results:
    print(f"{res['model']}: CV = {res['cv_score']:.4f}, Test = {res['test_accuracy']:.4f}, Params = {res['best_params']}")

# 8. Sauvegarde du meilleur modèle
best_result = max(results, key=lambda x: x['test_accuracy'])
print(f"\n🏆 Meilleur modèle : {best_result['model']}")
joblib.dump(grid.best_estimator_, f"{best_result['model']}_classifier.pkl")