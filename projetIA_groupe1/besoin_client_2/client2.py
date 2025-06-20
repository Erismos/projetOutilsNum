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
from sklearn.impute import SimpleImputer  # 🆕

data = pd.read_csv("export_IA_old.csv")
data = data.drop_duplicates(subset=["MMSI"], keep='first')

features = ["Length", "Width", "Draft", "Cargo"]
target = "VesselType"

x = data[features]
y = data[target]

# Label encoding
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Supprimer classes rares (<2 instances)
from collections import Counter
counter = Counter(y_encoded)
classes_to_keep = [cls for cls, count in counter.items() if count >= 2]
mask = np.isin(y_encoded, classes_to_keep)
x = x[mask]
y_encoded = y_encoded[mask]

# Re-encoder après filtrage
y_encoded = LabelEncoder().fit_transform(y_encoded)

# Split stratifié
x_train, x_test, y_train, y_test = train_test_split(
    x, y_encoded, test_size=0.2, stratify=y_encoded, random_state=42
)

# Preprocessing
numeric = ["Length", "Width", "Draft", "Cargo"]  # inclure toutes les features
numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])
preprocessor = ColumnTransformer(
    transformers=[('num', numeric_transformer, numeric)]
)
preprocessor.fit(x_train)

# Sauvegarde
joblib.dump(label_encoder, "label_encoder.joblib")
joblib.dump(preprocessor, "processor.joblib")

# Modèles
models = {
    'RandomForest': {
        'model': RandomForestClassifier(random_state=42, class_weight='balanced'),
        'params': {
            'classifier__n_estimators': [100, 150],
            'classifier__max_depth': [None, 10, 20]
        }
    },
    'XGBoost': {
        'model': XGBClassifier(
            tree_method='hist',          # reste rapide en CPU
            max_bin=256,
            verbosity=1,
            objective='multi:softmax',
            eval_metric='mlogloss',
            random_state=42
        ),
        'params': {
            'classifier__n_estimators': [100, 200],
            'classifier__learning_rate': [0.05, 0.1],
            'classifier__max_depth': [4, 6],
            'classifier__subsample': [0.8, 1.0],
            'classifier__colsample_bytree': [0.8, 1.0],
        }
    }
}

cv_1 = StratifiedKFold(n_splits=7, shuffle=True, random_state=42)
results = []
best_model = None
best_accuracy = 0

# Entraînement
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

    grid.fit(x_train, y_train)
    y_pred = grid.predict(x_test)

    acc_test = accuracy_score(y_test, y_pred)

    results.append({
        'model': name,
        'best_params': grid.best_params_,
        'train_accuracy': grid.best_score_,
        'test_accuracy': acc_test,
        'model_object': grid.best_estimator_
    })

    if acc_test > best_accuracy:
        best_accuracy = acc_test
        best_model = grid.best_estimator_

    print(f"Meilleurs paramètres: {grid.best_params_}")
    print(f"Accuracy (train): {grid.best_score_:.4f}")
    print(f"Accuracy (test): {acc_test:.4f}")
    print("Rapport de classification :\n", classification_report(y_test, y_pred))

    # Matrice de confusion
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title(f'Matrice de confusion - {name}')
    plt.ylabel('Vraie classe')
    plt.xlabel('Classe prédite')
    plt.tight_layout()
    plt.savefig(f'confusion_matrix_{name}.png')
    plt.show()

# Résumé
results_df = pd.DataFrame(results).sort_values('test_accuracy', ascending=False)
print("\n=== Comparaison des modèles ===")
print(results_df[['model', 'train_accuracy', 'test_accuracy']].to_string(index=False))

if best_model is not None:
    joblib.dump(best_model, 'best_model.joblib')
    print(f"\nMeilleur modèle sauvegardé: {results_df.iloc[0]['model']}")
    print(f"Accuracy sur le test: {best_accuracy:.4f}")