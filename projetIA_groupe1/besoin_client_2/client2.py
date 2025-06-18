import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import joblib
import os
import matplotlib as mpl
import seaborn as sns
import pickle

from xgboost import XGBClassifier

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler, PolynomialFeatures, LabelEncoder
from sklearn.pipeline import make_pipeline, Pipeline
from sklearn.linear_model import Ridge, Lasso, ElasticNet
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.compose import ColumnTransformer

import joblib
#from sklearnex import patch_sklearn
#patch_sklearn()

# 1: pré traitement des données 

data = pd.read_csv("export_IA.csv")

features = ["SOG", "Length", "Width", "Status", "Cargo"]
target = "VesselType"

x = data[features]
y = data[target]

label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)


x_train, x_test, y_train, y_test = train_test_split(x, y_encoded, test_size=0.2, random_state = 42)

numeric = ["SOG", "Length", "Width"]
numeric_transformer = Pipeline(steps=[('scaler', StandardScaler())])

preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric)
    ]
)

preprocessor.fit(x_train)

joblib.dump(label_encoder, "label_encoder.joblib")
joblib.dump(preprocessor, "processor.joblib")

# 2: apprentissage supervisé pour la classification

models = {
    #'RandomForest': {
    #    'model': RandomForestClassifier(random_state=42),
    #    'params': {
    #        'classifier__n_estimators': [100, 200],
    #        'classifier__max_depth': [None, 10, 20],
    #        'classifier__class_weight' : ['balanced', None]
    #    }
    #},
    'XGBoost': {
        'model': XGBClassifier(
            tree_method='hist',           # GPU training
            device='cuda',
            random_state=42
        ),
        'params': {
            'classifier__n_estimators': [100, 200],
            'classifier__learning_rate': [0.01, 0.1],
            'classifier__max_depth': [3, 6]
        }
    },
    #'SVM': {
    #    'model': SVC(random_state=42),
    #    'params': {
    #        'classifier__C': [0.1, 1, 10],
    #        'classifier__kernel': ['linear', 'rbf']
    #    }
    #},
    #'LogisticRegression': {
    #    'model': LogisticRegression(random_state=42),
    #    'params': {
    #        'classifier__C': [0.1, 1, 10],
    #        'classifier__penalty': ['l2']
    #    }
    #},
    #'KNN': {
    #    'model': KNeighborsClassifier(),
    #    'params': {
    #        'classifier__n_neighbors': [3, 5, 7]
    #    }
    #}
}

results = []
best_model_object = None
best_accuracy = 0

for name, config in models.items():
    print(f"\n=== Entraînement du modèle {name} ===")
    
    # Création du pipeline complet
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', config['model'])
    ])
    
    # Recherche des hyperparamètres
    grid = GridSearchCV(
        pipeline,
        config['params'],
        cv=5,
        scoring='accuracy',
        n_jobs=-1,
        verbose=1
    )
    
    grid.fit(x_train, y_train)
    
    # Évaluation
    y_pred = grid.predict(x_test)
    y_test_original = label_encoder.inverse_transform(y_test)
    y_pred_original = label_encoder.inverse_transform(y_pred)

    test_accuracy = accuracy_score(y_test_original, y_pred_original)
    
    # Sauvegarde des résultats
    results.append({
        'model': name,
        'best_params': grid.best_params_,
        'train_accuracy': grid.best_score_,
        'test_accuracy': test_accuracy,
        'model_object': grid.best_estimator_
    })
    
    # Mise à jour du meilleur modèle
    if test_accuracy > best_accuracy:
        best_accuracy = test_accuracy
        best_model = grid.best_estimator_
    
    # Affichage des résultats
    print(f"Meilleurs paramètres: {grid.best_params_}")
    print(f"Accuracy (train): {grid.best_score_:.4f}")
    print(f"Accuracy (test): {test_accuracy:.4f}")
    print("Rapport de classification (labels originaux):\n", classification_report(y_test_original, y_pred_original))
    
    # Matrice de confusion
    cm = confusion_matrix(y_test_original, y_pred_original, labels=label_encoder.classes_)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=label_encoder.classes_, yticklabels=label_encoder.classes_)
    plt.title(f'Matrice de confusion - {name}')
    plt.ylabel('Vraie classe')
    plt.xlabel('Classe prédite')
    plt.tight_layout()
    plt.savefig(f'confusion_matrix_{name}.png')
    plt.show()

# 7. Résumé des résultats
print("\n=== Comparaison des modèles ===")
results_df = pd.DataFrame(results).sort_values('test_accuracy', ascending=False)
print(results_df[['model', 'train_accuracy', 'test_accuracy']].to_string(index=False))

# 8. Sauvegarde du meilleur modèle
if best_model is not None:
    joblib.dump(best_model, 'best_model.joblib')
    print(f"\nMeilleur modèle sauvegardé: {results_df.iloc[0]['model']}")
    print(f"Accuracy sur le test: {best_accuracy:.4f}")