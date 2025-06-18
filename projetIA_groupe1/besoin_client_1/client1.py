# on importe les bibliothèque 
import pandas as pd # pour manipuler des données avec des dataframe
from sklearn.cluster import KMeans # pour le clustering avec l'algorithme kmeans
from sklearn.preprocessing import StandardScaler # pour normaliser les données
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score # pour évaluer les clusters
import plotly.express as px # pour les cartes interactives
import joblib # pour sauvegarder et charger les modèles en python
import matplotlib.pyplot as plt # pour les visualisations avec les graphiques
import time  # pour mesuer le temps d'execution

start_time = time.time()  # début du timer

# Chargement des données
df = pd.read_csv("../data/export_IA.csv") # on charge le fichier csv dans un dataframe
# vérifier le type des colonnes
print(df.dtypes)
#nombre de lignes dans le fichier 
print(len(df))
# Sélection des variables pertinentes
vars_corr = df[['SOG', 'COG', 'Heading', 'LAT', 'LON']].dropna()
# Matrice de corrélation
corr_matrix = vars_corr.corr()
# Affichage du tableau dans la console
print(" Matrice de corrélation (SOG, COG, Heading, LAT, LON) :\n")
print(corr_matrix.round(2))

# on fait un échantillonage pour trouver le nombre de clusters k
# on prend 10% des données 
df_sample = df.sample(n=20000, random_state=0)
X_sample = df_sample[['SOG', 'COG', 'Heading']] # on garde que les colonnes pertinantes à utiliser 
print("Taille de l'échantillon :", X_sample.shape) # on affiche la taille de l'échantillon

# Normalisation
scaler_sample = StandardScaler() # on initialise un objet pour normaliser
X_sample_scaled = scaler_sample.fit_transform(X_sample) # on normalise les données, on les met à la même échelle

# Méthode du coude pour choisir k
inertias = []  # Liste pour stocker l'inertie pour chaque k
k_values = range(1, 11)  # k de 1 à 10

for k in k_values:
    kmeans = KMeans(n_clusters=k, random_state=0)
    kmeans.fit(X_sample_scaled)
    inertias.append(kmeans.inertia_)

# Visualisation de la courbe d'inertie
plt.figure(figsize=(8, 5))
plt.plot(k_values, inertias, marker='o')
plt.xlabel("Nombre de clusters (k)")
plt.ylabel("Inertie (inertia)")
plt.title("Méthode du coude : inertie vs nombre de clusters")
plt.grid(True)
plt.xticks(k_values)
plt.savefig("graphique/kmeans_elbow_method.png")
plt.show()
print("Graphique de la méthode du coude enregistré dans kmeans_elbow_method.png")


# Clustering avec KMeans
# recherche du meilleur k
results = [] # liste vide pour stocker les résultats
all_models = {} # dictionnaire pour stocker tous les modèles avec leur score et random_state
# on teste k pour savoir quel nombre de clusters est bon 
# Boucle sur k et plusieurs random_state
for k in range(2, 11): # on boucle de 2 à 10 inclus
    for random_state in range(5):  # 5 initialisations différentes pour chaque k
        model = KMeans(n_clusters=k, random_state=random_state) # on crée un modèle KMeans avec k clusters et un random_state donné
        labels = model.fit_predict(X_sample_scaled) # on entraine le modèle sur les données normalisé et on récupères les étiquettes de cluster pour chaque point

        silhouette = silhouette_score(X_sample_scaled, labels) # on calcul le score silhouette
        ch_score = calinski_harabasz_score(X_sample_scaled, labels) # on calcul le score calinski-harabasz
        db_score = davies_bouldin_score(X_sample_scaled, labels) # on calcul le score davies-bouldin

        # Sauvegarde des résultats
        # results.append((k, random_state, silhouette, ch_score, db_score))
        inertia = model.inertia_
        results.append((k, random_state, silhouette, ch_score, db_score, inertia))

        # Stocke le modèle dans le dictionnaire
        all_models[(k, random_state)] = {
            "model": model,
            "labels": labels,
            "silhouette": silhouette,
            "calinski_harabasz": ch_score,
            "davies_bouldin": db_score
        }

# Stockage des résultats en dataframe et moyenne des scores pour chaque k
# results_df = pd.DataFrame(results, columns=['k', 'random_state', 'silhouette', 'calinski_harabasz', 'davies_bouldin'])
results_df = pd.DataFrame(results, columns=['k', 'random_state', 'silhouette', 'calinski_harabasz', 'davies_bouldin', 'inertia'])
# on groupe par k et on calcul la moyenne des scores pour chaque k
avg_scores_df = results_df.groupby('k')[['silhouette', 'calinski_harabasz', 'davies_bouldin']].mean().reset_index()
avg_scores_df.to_csv("csv/kmeans_metrics.csv", index=False) # on enregistre les résultats dans un fichier csv

# Affichage des scores / visualisation
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(8, 12), sharex=True)

# 1. Silhouette
axes[0].plot(avg_scores_df['k'], avg_scores_df['silhouette'], color='tab:blue', marker='o') # score silhouette moyen en focntion de k
axes[0].set_ylabel("Silhouette") # titre de l'axe y 
axes[0].set_title("Score Silhouette") # titre du premier graphique 
axes[0].grid(True) # on affiche une grille pour lire plus facilement sur le graphique

# 2. Calinski-Harabasz
axes[1].plot(avg_scores_df['k'], avg_scores_df['calinski_harabasz'], color='tab:orange', marker='o') # score Calinski-Harabasz moyen selon k
axes[1].set_ylabel("Calinski-Harabasz") # titre de l'axe y 
axes[1].set_title("Score Calinski-Harabasz") # titre du deuxième graphique
axes[1].grid(True) # on affiche une grille pour lire plus facilement sur le graphique

# 3. Davies-Bouldin
axes[2].plot(avg_scores_df['k'], avg_scores_df['davies_bouldin'], color='tab:green', marker='o') # score Davies-Bouldin moyen selon k
axes[2].set_ylabel("Davies-Bouldin") # titre de l'axe y 
axes[2].set_title("Score Davies-Bouldin") # titre du troisème graphique
axes[2].set_xlabel("Nombre de clusters (k)") # titre de l'axe x pour tous les graphs
axes[2].grid(True) # on affiche une grille pour lire plus facilement sur le graphique

plt.tight_layout() # on ajuste automatiquement les espacements entre les sous-graphiques*
plt.savefig("graphique/graph_scores_subplots_kmeans.png") # on sauvegarde le graphique dans un fichier png
print("Graphique enregistré dans graph_scores_subplots_kmeans.png")
plt.show() # on affiche le graphique

def select_best_k_by_combined_score(df_scores, weights=None):
    """
    Sélectionne le meilleur k en combinant les 3 métriques : silhouette, calinski_harabasz, davies_bouldin.
    
    Parameters:
    - df_scores: DataFrame contenant les colonnes ['k', 'silhouette', 'calinski_harabasz', 'davies_bouldin']
    - weights: dictionnaire des poids pour chaque métrique 
    
    Returns:
    - best_k: valeur de k ayant le meilleur score combiné
    - df_scores: DataFrame mis à jour avec les scores normalisés et combinés
    """
    if weights is None: # si pas de poids alors poids par défaut
        weights = {'silhouette': 0.4, 'calinski_harabasz': 0.4, 'davies_bouldin': 0.2}
    
    df = df_scores.copy() # créer une copie du dataframe pour ne pas modifer l'original

    # Normalisation des scores (Min-Max Scaling)
    for metric in ['silhouette', 'calinski_harabasz']: # normalisation normale pour silhouette et calinski-harabasz
        df[f"{metric}_norm"] = (df[metric] - df[metric].min()) / (df[metric].max() - df[metric].min())
    # Davies-Bouldin : score inverse 
    db = df['davies_bouldin']
    df['davies_bouldin_norm'] = (db.max() - db) / (db.max() - db.min()) # normalisation en inversant les scores avant

    # Calcul du score pondéré 
    df['combined_score'] = (
        weights['silhouette'] * df['silhouette_norm'] +
        weights['calinski_harabasz'] * df['calinski_harabasz_norm'] +
        weights['davies_bouldin'] * df['davies_bouldin_norm']
    )

    # Choix du meilleur k (le plus haut du score combiné)
    best_k = df.loc[df['combined_score'].idxmax(), 'k']
    return int(best_k), df # on retorune le meilleur k et le dataframe



# on choisi le meilleur k selon les métriques
best_k, scored_df = select_best_k_by_combined_score(avg_scores_df)
print(f"Meilleur k (combiné des métriques) : {best_k}") # on l'affiche 

# on visualise le combined score
plt.plot(scored_df['k'], scored_df['combined_score'], marker='o') # courbe du score combiné en fonction de k
plt.xlabel("Nombre de clusters (k)") # titre de l'axe x
plt.ylabel("Score combiné") # titre de l'axe y 
plt.title("Choix du meilleur k (score combiné)") # tire du graphique 
plt.grid(True) # on affiche une grille pour mieux lire le graphique
plt.savefig("graphique/kmeans_combined.png") # on sauvegarde dans une fichier png
print("Graphique enregistré dans kmeans_combined.png") 
plt.show() # on affiche le graphique

# on sélectionne le meilleur modèle pour ce k 
models_for_best_k = {
    # on extrait les modèles entrainés par le meilleur k
    key: val for key, val in all_models.items() if key[0] == best_k
}
best_model_info = max(models_for_best_k.values(), key=lambda m: m['silhouette']) # on prend le modèle avec le meilleur score silhouette
best_random_state = [key[1] for key, val in models_for_best_k.items() if val == best_model_info][0] # on trouve le random_state pour ce modèle
print(f"Meilleur random_state pour k={int(best_k)} : {best_random_state}") # on les affiche (k et random_state)
print(f"Silhouette de ce modèle : {best_model_info['silhouette']}") # on affiche le score silhouette du modèle

# Clustering final sur tout le dataset 
X_full = df[['SOG', 'COG', 'Heading']] # on sélectionne les colonnes du dataframe
scaler = StandardScaler() # on créé un objet pour normaliser
X_full_scaled = scaler.fit_transform(X_full) # on normalise 

# on applique KMeans final
model_kmeans_final = KMeans(n_clusters=int(best_k), random_state=best_random_state) # on fait un modèle kmeans avec le meilleur k et le random_state associé
clusters = model_kmeans_final.fit_predict(X_full_scaled) # on applique le modèle aux données normalisé
# on ajoute les clusters au DataFrame
df['Cluster'] = clusters
df.to_csv("csv/export_IA_with_clusters_kmeans.csv", index=False) # on sauvegarde le dataframe dans un fichier csv
print("Fichier sauvegardé : export_IA_with_clusters_kmeans.csv (avec colonnes de cluster)")

df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime']) # on convertit la colonne basedatetime en format datetime
df_sorted = df.sort_values(by=['MMSI', 'BaseDateTime']) # on trie le dataframe d'abord par identifiant du bateau et ensuite par date

# Visualisation sur carte 
fig = px.scatter_mapbox(
    df_sorted,
    lat="LAT",
    lon="LON",
    color="Cluster",
    hover_name="MMSI",
    zoom=3,
    mapbox_style="open-street-map"
)
fig.update_layout(title="Trajectoires des navires par cluster - kmeans")
fig.show() # on affiche la carte

fig.write_html("carte/trajectoires_clusters.html") # on sauvegarde la carte dans un fichier html
print("Carte des trajectoires enregistrée dans trajectoires_clusters.html")

# on affiche les scores finaux
print("\n Scores finaux (déjà calculés pour le meilleur modèle sur l'échantillon de 20000) :")
print("Silhouette Score:", best_model_info['silhouette'])
print("Calinski-Harabasz Score:", best_model_info['calinski_harabasz'])
print("Davies-Bouldin Score:", best_model_info['davies_bouldin'])

# on sauvegarde le modèle
joblib.dump(model_kmeans_final, "pkl/kmeans_model.pkl") # on sauvegarde le modèle kmeans entrainé
joblib.dump(scaler, "pkl/scaler_kmeans.pkl") # on sauvegarde le scaler entrainé

end_time = time.time() # on stop le timer
elapsed_time = end_time - start_time # on calcul le temps avec la différence entre le temps de fin et de début 
print(f"\n Temps d'exécution total : {elapsed_time:.2f} secondes") # on affiche le temps d'exécution du script

# Ce script entraîne un modèle de clustering KMeans basé sur les caractéristiques de navigation (SOG, COG, Heading). Il teste différents nombres de clusters, sélectionne automatiquement le meilleur (k), applique le clustering à tout le dataset, produit une visualisation géographique et enregistre le modèle entraîné.c

# dans chaque cluster il y a plusieurs bateaux car ils ont le même schéma de navigation (sog; heading; cog).
# les couleurs sur la carte sont les différents clusters 
# donc 2 bateaux appertenant au même cluster auront la même couleur