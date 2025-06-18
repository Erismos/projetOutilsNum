import joblib # on importe la bibliothèque joblib pour charger et utiliser des objets python
import numpy as np # on importe la bibliothèque numpy pour manipuler des tableaux numériques

# Charger les modèles sauvegardés
model = joblib.load("pkl/kmeans_model.pkl") # on charge le modèle kmeans
scaler = joblib.load("pkl/scaler_kmeans.pkl") # on charge l'objet de normalisation utilisé pour mettre à l'échelle les données

# Demander les entrées à l'utilisateur
sog = float(input("Entrez la vitesse (SOG) : ")) # on demande à l'utilisateur de rentrer la vitesse et convertit l'entrée en float
cog = float(input("Entrez le cap (COG) : ")) # on demande à l'utilisateur de rentrer le cap sur le fond et convertit l'entrée en float
heading = float(input("Entrez le heading : ")) # on demande à l'utilisateur de rentrer le cap du navire et convertit l'entrée en float

# Créer l'array d'entrée
X_input = np.array([[sog, cog, heading]]) # on créé un tableau NumPy 2D avec une seule ligne contenant les trois valeurs saisies

# Normalisation
X_scaled = scaler.transform(X_input) # on applique le même scaler utilisé à l'entraînement pour normaliser les nouvelles données

# Prédiction
cluster = model.predict(X_scaled)[0] # on prédit le cluster auquel appartient la nouvelle observation et on extrait la première (et seule) valeur du résultat

print(f"\n Le navire appartient au cluster : {cluster}") # on affiche le numéro du cluster prédit pour les valeurs entrées
