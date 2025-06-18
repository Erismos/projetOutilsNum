import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

cv_1 = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# 1: pré traitement des données 
data = pd.read_csv("export_IA_old.csv")
data = data.drop_duplicates(subset=["MMSI"], keep='first')

features = ["Length", "Width", "Draft", "Status", "Cargo"]
target = "VesselType"

x = data[features]
y = data[target]

# Encodage une seule fois ici
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Nettoyage : garder seulement les classes avec au moins 2 exemples
from collections import Counter
counter = Counter(y_encoded)
classes_to_keep = [cls for cls, count in counter.items() if count >= 2]

mask = np.isin(y_encoded, classes_to_keep)
x = x[mask]
y_encoded = y_encoded[mask]

# Ré-encoder pour labels contigus
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y_encoded)

# Stratify sur y_encoded (labels numériques)
x_train, x_test, y_train, y_test = train_test_split(
    x, y_encoded, test_size=0.2, stratify=y_encoded, random_state=42
)

print("Toutes classes :", np.unique(y_encoded))
print("Classes dans y_train :", np.unique(y_train))

numeric = ["Length", "Width", "Draft"]
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
    'RandomForest': {
        'model': RandomForestClassifier(random_state=42),
        'params': {
            'classifier__n_estimators': [100, 200],
            'classifier__max_depth': [None, 10, 20],
            'classifier__class_weight': ['balanced', None]
        }
    },
    #'XGBoost': {
    #    'model': XGBClassifier(
    #        tree_method='hist',
    #        device='gpu',
    #        predictor='gpu_predictor',
    #        gpu_id=0,
    #        max_bin=256,
    #        verbosity=1,
    #        use_label_encoder=False,
    #        objective='multi:softmax',
    #        eval_metric='mlogloss',
    #        random_state=42
    #    ),
    #    'params': {
    #        'classifier__n_estimators': [200, 300],
    #        'classifier__learning_rate': [0.05, 0.1],
    #        'classifier__max_depth': [4, 6, 8],
    #        'classifier__subsample': [0.8, 1.0],
    #        'classifier__colsample_bytree': [0.8, 1.0],
    #    }
    #},
}

results = []
best_accuracy = 0
best_model = None

for name, config in models.items():
    print(f"\n=== Entraînement du modèle {name} ===")

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', config['model'])
    ])

    grid = GridSearchCV(
        pipeline,
        config['params'],
        cv=cv_1,
        scoring='accuracy',
        n_jobs=-1,
        verbose=1
    )

    grid.fit(x_train, y_train)  # PAS de double encodage ici

    y_pred = grid.predict(x_test)
    y_test_original = label_encoder.inverse_transform(y_test)
    y_pred_original = label_encoder.inverse_transform(y_pred)

    test_accuracy = accuracy_score(y_test_original, y_pred_original)

    results.append({
        'model': name,
        'best_params': grid.best_params_,
        'train_accuracy': grid.best_score_,
        'test_accuracy': test_accuracy,
        'model_object': grid.best_estimator_
    })

    if test_accuracy > best_accuracy:
        best_accuracy = test_accuracy
        best_model = grid.best_estimator_

    print(f"Meilleurs paramètres: {grid.best_params_}")
    print(f"Accuracy (train): {grid.best_score_:.4f}")
    print(f"Accuracy (test): {test_accuracy:.4f}")
    print("Rapport de classification (labels originaux):\n", classification_report(y_test_original, y_pred_original))

    cm = confusion_matrix(y_test_original, y_pred_original, labels=label_encoder.classes_)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=label_encoder.classes_, yticklabels=label_encoder.classes_)
    plt.title(f'Matrice de confusion - {name}')
    plt.ylabel('Vraie classe')
    plt.xlabel('Classe prédite')
    plt.tight_layout()
    plt.savefig(f'confusion_matrix_{name}.png')
    plt.show()

# Résumé des résultats
print("\n=== Comparaison des modèles ===")
results_df = pd.DataFrame(results).sort_values('test_accuracy', ascending=False)
print(results_df[['model', 'train_accuracy', 'test_accuracy']].to_string(index=False))

# Sauvegarde du meilleur modèle
if best_model is not None:
    joblib.dump(best_model, 'best_model.joblib')
    print(f"\nMeilleur modèle sauvegardé: {results_df.iloc[0]['model']}")
    print(f"Accuracy sur le test: {best_accuracy:.4f}")
