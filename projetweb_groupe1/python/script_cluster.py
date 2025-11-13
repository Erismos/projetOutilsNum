import joblib # on importe la bibliothèque joblib pour charger et utiliser des objets python
import numpy as np # on importe la bibliothèque numpy pour manipuler des tableaux numériques
import argparse
import json
import os
import warnings

warnings.filterwarnings("ignore")

# Chemin absolu basé sur l'emplacement du script Python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(SCRIPT_DIR, "pkl", "kmeans_model.pkl")
scaler_path = os.path.join(SCRIPT_DIR, "pkl", "scaler_kmeans.pkl")

model = joblib.load(model_path)
scaler = joblib.load(scaler_path)

# # Charger les modèles sauvegardés
# model = joblib.load("pkl/kmeans_model.pkl") # on charge le modèle kmeans
# scaler = joblib.load("pkl/scaler_kmeans.pkl") # on charge l'objet de normalisation utilisé pour mettre à l'échelle les données

def main():
    parser = argparse.ArgumentParser(
        description="Prédiction du cluster d'un bateau à partir de données CSV (cog, sog, heading).",
    ) 
    parser.add_argument("--sog", type=str, required=True, help="Vitesse du bateau")
    parser.add_argument("--cog", type=str, required=True, help="cap réel du bateau")
    parser.add_argument("--heading", type=str, required=True, help="cap du bateau")

    args = parser.parse_args() # liste des arguments
    sogs = list(map(float, args.sog.split(',')))
    cogs = list(map(float, args.cog.split(',')))
    headings = list(map(float, args.heading.split(',')))
    X_input = np.array(list(zip(sogs, cogs, headings)))
    X_scaled = scaler.transform(X_input)
    clusters = model.predict(X_scaled)
    # print(f"numéro du cluster du bateau : {cluster}")
    print(json.dumps([{"cluster": int(c)} for c in clusters]))


if __name__ == "__main__":
    main()