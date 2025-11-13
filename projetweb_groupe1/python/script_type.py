#!/usr/bin/env python

import argparse
import joblib
import pandas as pd
import sys
import sklearn

sys.stdout.reconfigure(line_buffering=True)
import os

# chargement des objets sérialisés
try:
    label_encoder = joblib.load('../../python/data/label_encoder.joblib') # pour décoder la sortie
    model = joblib.load('../../python/data/best_model.joblib') # pipeline complet (prétraitement + modèle)
except FileNotFoundError as e:
    cwd = os.getcwd()
    print(f"|| Dir : {cwd} Erreur: Fichier modèle manquant - {e}")
    exit(1)

def predict_vessel_type(input_data):
    try:
        input_df = pd.DataFrame([input_data])
        prediction = model.predict(input_df)
        prediction_label = label_encoder.inverse_transform(prediction)
        return prediction_label[0]
    except Exception as e:
        cwd = os.getcwd()
        print(f"|| Dir : {cwd} Erreur lors de la prédiction: {e} ")
        return None

def main():
    # lecture des arguments
    parser = argparse.ArgumentParser(description='Prédiction du type de navire')
    parser.add_argument('--Length', type=float, required=True, help='Longueur du navire (mètres)')
    parser.add_argument('--Draft', type=float, required=True, help='Tirant d\'eau (mètres)')
    parser.add_argument('--Width', type=float, required=True, help='Largeur du navire (mètres)')
    parser.add_argument('--Cargo', type=int, required=True, help='Type de cargaison (code numérique)')

    args = parser.parse_args()
    input_data = vars(args)

    prediction = predict_vessel_type(input_data)

    if prediction is None :
        print("La prédiciton a échoué")
    else :
        return(prediction)

if __name__ == "__main__":
    print(main())
