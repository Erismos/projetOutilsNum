#!/usr/bin/env python

import argparse
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# Chargement des modèles
try:
    preprocessor = joblib.load('processor.joblib')
    model = joblib.load('best_model.joblib')
    print("good")
except FileNotFoundError as e:
    print(f"Erreur: Fichier modèle manquant - {e}")
    exit(1)

def predict_vessel_type(input_data):
    #Prédit le type de navire à partir des données d'entrée
    try:
        # Conversion en DataFrame
        input_df = pd.DataFrame([input_data])
        
        # Prétraitement
        processed_data = preprocessor.transform(input_df)
        
        # Prédiction
        prediction = model.predict(processed_data)
        return prediction[0]
    except Exception as e:
        print(f"Erreur lors de la prédiction: {e}")
        return None

def main():
    # Configuration des arguments CLI
    parser = argparse.ArgumentParser(description='Prédiction du type de navire')
    parser.add_argument('--SOG', type=float, required=True, help='Speed Over Ground (0-30)')
    parser.add_argument('--Length', type=float, required=True, help='Longueur du navire (mètres)')
    parser.add_argument('--Draft', type=float, required=True, help='Tirant d\'eau (mètres)')
    parser.add_argument('--Width', type=float, required=True, help='Largeur du navire (mètres)')
    parser.add_argument('--Cargo', type=int, required=True, help='Type de cargaison (code numérique)')

    args = parser.parse_args()

    # Prédiction
    prediction = predict_vessel_type(vars(args))
    
    if prediction is not None:
        vessel_type = vessel_types.get(prediction, "Inconnu")
        print(f"\nRésultat de prédiction:")
        print(f"- Type de navire: {vessel_type} (Code: {prediction})")
        print("\nCaractéristiques analysées:")
        for k, v in vars(args).items():
            print(f"- {k}: {v}")
    else:
        print("La prédiction a échoué")

if __name__ == "__main__":
    main()