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
# description des données
description = df[["SOG", "COG", "Heading"]].describe()
print(description)

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

def select_best_model(results_df, weights=None):
    """
    Sélectionne le meilleur modèle parmi tous les (k, random_state) selon un score combiné.

    Parameters:
    - results_df: DataFrame avec les scores pour chaque (k, random_state)
    - weights: dictionnaire de pondération des scores (default = {'silhouette':0.4, 'calinski_harabasz':0.4, 'davies_bouldin':0.2})

    Returns:
    - best_k: nombre optimal de clusters
    - best_random_state: valeur du random_state associée au meilleur modèle
    - best_model_info: dictionnaire avec le modèle et ses scores
    - scored_df: dataframe avec les scores normalisés et combinés
    """
    if weights is None: # on définit des poids par défaut 
        weights = {'silhouette': 0.4, 'calinski_harabasz': 0.4, 'davies_bouldin': 0.2}
    
    df = results_df.copy() # on copie le datafrale pour éviter de modifier l'original
    
    # Normalisation
    for metric in ['silhouette', 'calinski_harabasz']: # normalisation min-max pour silhouette et calinski-harabasz
        df[f"{metric}_norm"] = (df[metric] - df[metric].min()) / (df[metric].max() - df[metric].min())
    db = df['davies_bouldin'] # on inverse la normalisation min-max
    df['davies_bouldin_norm'] = (db.max() - db) / (db.max() - db.min())

    # Score combiné
    # calcul d’un score global pondéré qui combine les trois métriques normalisées selon les poids définis
    df['combined_score'] = (
        weights['silhouette'] * df['silhouette_norm'] +
        weights['calinski_harabasz'] * df['calinski_harabasz_norm'] +
        weights['davies_bouldin'] * df['davies_bouldin_norm']
    )

    best_row = df.loc[df['combined_score'].idxmax()] # recupère la ligne avec le meilleur score combiné
    best_k = int(best_row['k']) # on trouve le meilleur k
    best_random_state = int(best_row['random_state']) # on trouve le meilleur random_state
    return best_k, best_random_state, all_models[(best_k, best_random_state)], df

best_k, best_random_state, best_model_info, scored_df = select_best_model(results_df) # on appele la fonction avec le dataframe des resultatss
# on affiche les résultats
print(f"Meilleur modèle : k = {best_k}, random_state = {best_random_state}")
print(f"Silhouette Score : {best_model_info['silhouette']}")
print(f"Calinski-Harabasz Score : {best_model_info['calinski_harabasz']}")
print(f"Davies-Bouldin Score : {best_model_info['davies_bouldin']}")

# Visualisation
plt.plot(scored_df['k'], scored_df['combined_score'], marker='o')
plt.xlabel("Nombre de clusters (k)")
plt.ylabel("Score combiné")
plt.title("Choix du meilleur modèle (score combiné)")
plt.grid(True)
plt.savefig("graphique/kmeans_combined.png")
plt.show()
print("Graphique enregistré dans kmeans_combined.png")

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

# Moyennes SOG, COG, Heading par cluster
cluster_means = df.groupby('Cluster')[['SOG', 'COG', 'Heading']].mean()
print(cluster_means) # on affiche le tableau des moyennes

cluster_legend = {
    0: "à l'arrêt ou très lent, cap vers l'ouest, non aligné",
    1: "à l'arrêt ou très lent, cap vers le sud, non aligné",
    2: "rapide, cap vers l'ouest, aligné",
    3: "à l'arrêt ou très lent, cap vers l'ouest, aligné",
    4: "rapide, cap vers l'est, aligné",
    5: "à l'arrêt ou très lent, cap vers l'est, non aligné",
    6: "à l'arrêt ou très lent, cap vers l'ouest, aligné",
    7: "à l'arrêt ou très lent, cap vers l'est, aligné"
}

df_sorted['Interprétation'] = df_sorted['Cluster'].map(cluster_legend)

# Visualisation sur carte 
fig = px.scatter_mapbox(
    df_sorted,
    lat="LAT",
    lon="LON",
    color="Interprétation",
    hover_name="MMSI",
    hover_data={"Cluster": True},
    zoom=3,
    mapbox_style="open-street-map"
)
fig.update_layout(title="Trajectoires des navires par cluster - kmeans")
fig.show() # on affiche la carte

fig.write_html("carte/trajectoires_clusters_kmeans.html") # on sauvegarde la carte dans un fichier html
print("Carte des trajectoires enregistrée dans trajectoires_clusters_kmeans.html")

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

# Ce script entraîne un modèle de clustering KMeans basé sur les caractéristiques de navigation (SOG, COG, Heading). Il teste différents nombres de clusters, sélectionne automatiquement le meilleur (k), applique le clustering à tout le dataset, produit une visualisation géographique et enregistre le modèle entraîné

# dans chaque cluster il y a plusieurs bateaux car ils ont le même schéma de navigation (sog; heading; cog).
# les couleurs sur la carte sont les différents clusters 
# donc 2 bateaux appertenant au même cluster auront la même couleur

# results_df = tableau avec toutes les combinaisons (k, random_state) testées, et les scores de clustering associés pour chacune.