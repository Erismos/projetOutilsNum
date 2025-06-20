#!/usr/bin/env python

import argparse
import joblib
import pandas as pd

# Chargement des objets sérialisés
try:
    label_encoder = joblib.load('label_encoder.joblib')  # Pour décoder la sortie
    model = joblib.load('best_model.joblib')             # Pipeline complet (prétraitement + modèle)
    print("Modèle chargé avec succès.")
except FileNotFoundError as e:
    print(f"Erreur: Fichier modèle manquant - {e}")
    exit(1)

def predict_vessel_type(input_data):
    try:
        input_df = pd.DataFrame([input_data])
        prediction = model.predict(input_df)
        prediction_label = label_encoder.inverse_transform(prediction)
        return prediction_label[0]
    except Exception as e:
        print(f"Erreur lors de la prédiction: {e}")
        return None

def main():
    # Lecture des arguments
    parser = argparse.ArgumentParser(description='Prédiction du type de navire')
    parser.add_argument('--Length', type=float, required=True, help='Longueur du navire (mètres)')
    parser.add_argument('--Draft', type=float, required=True, help='Tirant d\'eau (mètres)')
    parser.add_argument('--Width', type=float, required=True, help='Largeur du navire (mètres)')
    parser.add_argument('--Cargo', type=int, required=True, help='Type de cargaison (code numérique)')

    args = parser.parse_args()
    input_data = vars(args)

    prediction = predict_vessel_type(input_data)

    if prediction is not None:
        print(f"\nRésultat de prédiction :")
        print(f"- Code type de navire prédit : {prediction}")
        print("\nDonnées d'entrée :")
        for k, v in input_data.items():
            print(f"  - {k}: {v}")
    else:
        print("La prédiction a échoué.")

if __name__ == "__main__":
    main()
