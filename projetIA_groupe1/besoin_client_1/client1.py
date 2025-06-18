import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import plotly.express as px
import joblib
import matplotlib.pyplot as plt
import time

start_time = time.time()  # début du chronomètre

# Chargement des données
df = pd.read_csv("../data/export_IA.csv")

# vérifier le type des colonnes
print(df.dtypes)

#nombre de lignes dans le fichier 
print(len(df))

# on fait un échantillonage pour trouver le nombre de clusters k
# on prend 10% des données 
df_sample = df.sample(n=20000, random_state=0)
X_sample = df_sample[['SOG', 'COG', 'Heading']]
print("Taille de l'échantillon :", X_sample.shape)
print(X_sample.isnull().sum())

# Normalisation
scaler_sample = StandardScaler()
X_sample_scaled = scaler_sample.fit_transform(X_sample)

# Clustering avec KMeans
# recherche du meilleur k
results = []
all_models = {} # dictionnaire pour stocker tous les modèles avec leur score et random_state
# on teste k pour savoir quel nombre de clusters est bon 
# Boucle sur k et plusieurs random_state
for k in range(2, 11):
    for random_state in range(5):  # 5 initialisations différentes
        model = KMeans(n_clusters=k, random_state=random_state)
        labels = model.fit_predict(X_sample_scaled)

        silhouette = silhouette_score(X_sample_scaled, labels)
        ch_score = calinski_harabasz_score(X_sample_scaled, labels)
        db_score = davies_bouldin_score(X_sample_scaled, labels)

        # Sauvegarde des résultats
        results.append((k, random_state, silhouette, ch_score, db_score))

        # Stocke le modèle dans le dictionnaire
        all_models[(k, random_state)] = {
            "model": model,
            "labels": labels,
            "silhouette": silhouette,
            "calinski_harabasz": ch_score,
            "davies_bouldin": db_score
        }

# Stockage des résultats en dataframe et moyenne des scores pour chaque k
results_df = pd.DataFrame(results, columns=['k', 'random_state', 'silhouette', 'calinski_harabasz', 'davies_bouldin'])
avg_scores_df = results_df.groupby('k')[['silhouette', 'calinski_harabasz', 'davies_bouldin']].mean().reset_index()
avg_scores_df.to_csv("clustering_metrics.csv", index=False) 

# Affichage des scores / visualisation
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(8, 12), sharex=True)

# 1. Silhouette
axes[0].plot(avg_scores_df['k'], avg_scores_df['silhouette'], color='tab:blue', marker='o')
axes[0].set_ylabel("Silhouette")
axes[0].set_title("Score Silhouette")

# 2. Calinski-Harabasz
axes[1].plot(avg_scores_df['k'], avg_scores_df['calinski_harabasz'], color='tab:orange', marker='o')
axes[1].set_ylabel("Calinski-Harabasz")
axes[1].set_title("Score Calinski-Harabasz")

# 3. Davies-Bouldin
axes[2].plot(avg_scores_df['k'], avg_scores_df['davies_bouldin'], color='tab:green', marker='o')
axes[2].set_ylabel("Davies-Bouldin")
axes[2].set_title("Score Davies-Bouldin")
axes[2].set_xlabel("Nombre de clusters (k)")

# Mise en forme
plt.tight_layout()
plt.savefig("graph_scores_subplots.png")
print("Graphique enregistré dans graph_scores_subplots.png")
plt.grid(True)
plt.show()

def select_best_k_by_combined_score(df_scores, weights=None):
    """
    Sélectionne le meilleur k en combinant les 3 métriques : silhouette, calinski_harabasz, davies_bouldin.
    
    Parameters:
    - df_scores: DataFrame contenant les colonnes ['k', 'silhouette', 'calinski_harabasz', 'davies_bouldin']
    - weights: dictionnaire des poids pour chaque métrique (facultatif)
    
    Returns:
    - best_k: valeur de k ayant le meilleur score combiné
    - df_scores: DataFrame mis à jour avec les scores normalisés et combinés
    """
    if weights is None:
        weights = {'silhouette': 0.4, 'calinski_harabasz': 0.4, 'davies_bouldin': 0.2}
    
    df = df_scores.copy()

    # Normalisation des scores (Min-Max Scaling)
    for metric in ['silhouette', 'calinski_harabasz']:
        df[f"{metric}_norm"] = (df[metric] - df[metric].min()) / (df[metric].max() - df[metric].min())
    # Davies-Bouldin : score inverse (plus c'est bas, mieux c'est)
    db = df['davies_bouldin']
    df['davies_bouldin_norm'] = (db.max() - db) / (db.max() - db.min())

    # Calcul du score pondéré
    df['combined_score'] = (
        weights['silhouette'] * df['silhouette_norm'] +
        weights['calinski_harabasz'] * df['calinski_harabasz_norm'] +
        weights['davies_bouldin'] * df['davies_bouldin_norm']
    )

    # Choix du meilleur k
    best_k = df.loc[df['combined_score'].idxmax(), 'k']
    return int(best_k), df


# on choisi le meilleur k selon les métriques
best_k, scored_df = select_best_k_by_combined_score(avg_scores_df)
print(f"Meilleur k (combiné des métriques) : {best_k}")

# on visualise le combined score
plt.plot(scored_df['k'], scored_df['combined_score'], marker='o')
plt.xlabel("Nombre de clusters (k)")
plt.ylabel("Score combiné")
plt.title("Choix du meilleur k (score combiné)")
plt.grid(True)
plt.show()

# on sélectionne le meilleur modèle pour ce k 
models_for_best_k = {
    key: val for key, val in all_models.items() if key[0] == best_k
}
best_model_info = max(models_for_best_k.values(), key=lambda m: m['silhouette'])
best_random_state = [key[1] for key, val in models_for_best_k.items() if val == best_model_info][0]
print(f"Meilleur random_state pour k={int(best_k)} : {best_random_state}")
print(f"Silhouette de ce modèle : {best_model_info['silhouette']}")

# Clustering final sur tout le dataset 
X_full = df[['SOG', 'COG', 'Heading']]
scaler = StandardScaler()
X_full_scaled = scaler.fit_transform(X_full)

# on applique KMeans final
model_kmeans_final = KMeans(n_clusters=int(best_k), random_state=best_random_state)
clusters = model_kmeans_final.fit_predict(X_full_scaled)
# on ajoute les clusters au DataFrame
df['Cluster'] = clusters
df.to_csv("export_IA_with_clusters.csv", index=False)
print("Fichier sauvegardé : export_IA_with_clusters.csv (avec colonnes de cluster)")

df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime'])
df_sorted = df.sort_values(by=['MMSI', 'BaseDateTime'])

# Visualisation sur carte
fig = px.line_mapbox(
    df_sorted,
    lat="LAT",
    lon="LON",
    color="Cluster",
    line_group="MMSI",
    hover_name="MMSI",
    zoom=3,
    mapbox_style="open-street-map"
)
fig.update_layout(title="Trajectoires des navires par cluster")
fig.show()

fig.write_html("trajectoires_clusters.html")
print("Carte des trajectoires enregistrée dans trajectoires_clusters.html")

# Scores finaux
print("\n Scores finaux (déjà calculés pour le meilleur modèle sur l'échantillon de 20000) :")
print("Silhouette Score:", best_model_info['silhouette'])
print("Calinski-Harabasz Score:", best_model_info['calinski_harabasz'])
print("Davies-Bouldin Score:", best_model_info['davies_bouldin'])

# on sauvegarde le modèle
joblib.dump(model_kmeans_final, "kmeans_model.pkl")
joblib.dump(scaler, "scaler_kmeans.pkl")

end_time = time.time()
elapsed_time = end_time - start_time
print(f"\n Temps d'exécution total : {elapsed_time:.2f} secondes")

# Ce script entraîne un modèle de clustering KMeans basé sur les caractéristiques de navigation (SOG, COG, Heading). Il teste différents nombres de clusters, sélectionne automatiquement le meilleur (k), applique le clustering à tout le dataset, produit une visualisation géographique et enregistre le modèle entraîné.c

# dans chaque cluster il y a plusieurs bateaux car ils ont le même schéma de navigation (sog; heading; cog).
# les couleurs sur la carte sont les différents clusters 
# donc 2 bateaux appertenant au même cluster auront la même couleur