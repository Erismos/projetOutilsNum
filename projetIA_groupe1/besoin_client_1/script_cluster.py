import joblib
import numpy as np

# Charger les modèles sauvegardés
model = joblib.load("pkl/kmeans_model.pkl")
scaler = joblib.load("pkl/scaler_kmeans.pkl")

# Demander les entrées à l'utilisateur
sog = float(input("Entrez la vitesse (SOG) : "))
cog = float(input("Entrez le cap (COG) : "))
heading = float(input("Entrez le heading : "))

# Créer l'array d'entrée
X_input = np.array([[sog, cog, heading]])

# Normalisation
X_scaled = scaler.transform(X_input)

# Prédiction
cluster = model.predict(X_scaled)[0]

print(f"\n Le navire appartient au cluster : {cluster}")
