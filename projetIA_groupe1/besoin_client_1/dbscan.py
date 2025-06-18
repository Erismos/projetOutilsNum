import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import matplotlib.pyplot as plt
import plotly.express as px
import joblib
import time

start_time = time.time()

# Chargement des données
df = pd.read_csv("../data/export_IA.csv")
print(df.dtypes)
print(f"Nombre de lignes : {len(df)}")

# Échantillonnage
df_sample = df.sample(n=20000, random_state=0)
X_sample = df_sample[['SOG', 'COG', 'Heading']].dropna()
print("Taille de l'échantillon :", X_sample.shape)

# Normalisation
scaler_sample = StandardScaler()
X_sample_scaled = scaler_sample.fit_transform(X_sample)

# Test de différentes valeurs de eps et min_samples
eps_values = np.arange(0.1, 2.1, 0.1)
min_samples_values = [3, 5, 10]
results = []

for eps in eps_values:
    for min_samples in min_samples_values:
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        labels = dbscan.fit_predict(X_sample_scaled)

        # On ignore les cas avec tous les points en bruit ou 1 seul cluster
        if len(set(labels)) <= 1 or len(set(labels)) == len(X_sample_scaled):
            continue

        try:
            silhouette = silhouette_score(X_sample_scaled, labels)
            ch_score = calinski_harabasz_score(X_sample_scaled, labels)
            db_score = davies_bouldin_score(X_sample_scaled, labels)
            results.append((eps, min_samples, silhouette, ch_score, db_score, len(set(labels))))
        except Exception as e:
            print(f"Erreur pour eps={eps}, min_samples={min_samples} : {e}")

# Résultats
results_df = pd.DataFrame(results, columns=['eps', 'min_samples', 'silhouette', 'calinski_harabasz', 'davies_bouldin', 'n_clusters'])
results_df.to_csv("csv/dbscan_metrics.csv", index=False)

# Pour chaque valeur de min_samples, on trace les courbes
unique_min_samples = sorted(results_df['min_samples'].unique())

fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 14), sharex=True)

for i, metric in enumerate(['silhouette', 'calinski_harabasz', 'davies_bouldin']):
    ax = axes[i]
    for ms in unique_min_samples:
        subset = results_df[results_df['min_samples'] == ms]
        ax.plot(subset['eps'], subset[metric], marker='o', label=f"min_samples={ms}")
    ax.set_title(f"Score {metric} en fonction de eps")
    ax.set_ylabel(metric)
    ax.grid(True)
    if i == 2:
        ax.set_xlabel("Valeur de eps")
    ax.legend()

plt.tight_layout()
plt.savefig("graphique/dbscan_scores_subplots.png")
print("Graphiques des scores DBSCAN enregistrés dans dbscan_scores_subplots.png")
plt.show()

# Choix du meilleur modèle par score combiné
def select_best_params_by_score(df_scores):
    df = df_scores.copy()
    df['davies_bouldin_norm'] = (df['davies_bouldin'].max() - df['davies_bouldin']) / (df['davies_bouldin'].max() - df['davies_bouldin'].min())
    df['silhouette_norm'] = (df['silhouette'] - df['silhouette'].min()) / (df['silhouette'].max() - df['silhouette'].min())
    df['calinski_harabasz_norm'] = (df['calinski_harabasz'] - df['calinski_harabasz'].min()) / (df['calinski_harabasz'].max() - df['calinski_harabasz'].min())

    df['combined_score'] = (
        0.4 * df['silhouette_norm'] +
        0.4 * df['calinski_harabasz_norm'] +
        0.2 * df['davies_bouldin_norm']
    )

    best_row = df.loc[df['combined_score'].idxmax()]
    return best_row

best_result = select_best_params_by_score(results_df)
best_eps = best_result['eps']
best_min_samples = int(best_result['min_samples'])
print(f"Meilleurs paramètres DBSCAN : eps={best_eps:.2f}, min_samples={best_min_samples}")

# score combiné
plt.figure(figsize=(10, 6))
for ms in unique_min_samples:
    subset = results_df[results_df['min_samples'] == ms]
    # On recalcule le score combiné ici si ce n'est pas déjà fait
    silhouette_norm = (subset['silhouette'] - subset['silhouette'].min()) / (subset['silhouette'].max() - subset['silhouette'].min())
    ch_norm = (subset['calinski_harabasz'] - subset['calinski_harabasz'].min()) / (subset['calinski_harabasz'].max() - subset['calinski_harabasz'].min())
    db_norm = (subset['davies_bouldin'].max() - subset['davies_bouldin']) / (subset['davies_bouldin'].max() - subset['davies_bouldin'].min())
    combined = 0.4 * silhouette_norm + 0.4 * ch_norm + 0.2 * db_norm

    plt.plot(subset['eps'], combined, marker='o', label=f"min_samples={ms}")

plt.xlabel("eps")
plt.ylabel("Score combiné")
plt.title("Score combiné DBSCAN selon eps")
plt.legend()
plt.grid(True)
plt.savefig("graphique/dbscan_combined_score.png")
plt.show()

dbscan_final = DBSCAN(eps=best_eps, min_samples=best_min_samples)
clusters = dbscan_final.fit_predict(X_sample_scaled)

# Ajout des clusters dans le dataframe
df.loc[X_sample.index, 'Cluster'] = clusters
df.to_csv("csv/export_IA_with_clusters_dbscan.csv", index=False)
print("Fichier sauvegardé : export_IA_with_clusters_dbscan.csv")

# Carte
df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime'])
df_sorted = df.sort_values(by=['MMSI', 'BaseDateTime'])

fig = px.scatter_mapbox(
    df_sorted,
    lat="LAT",
    lon="LON",
    color="Cluster",
    hover_name="MMSI",
    zoom=3,
    mapbox_style="open-street-map"
)
fig.update_layout(title="Trajectoires des navires par cluster (DBSCAN)")
fig.write_html("carte/trajectoires_clusters_dbscan.html")
fig.show()
print("Carte enregistrée dans trajectoires_clusters_dbscan.html")

# Sauvegarde du modèle et du scaler
joblib.dump(dbscan_final, "pkl/dbscan_model.pkl")
joblib.dump(scaler_sample, "pkl/scaler_dbscan.pkl")

end_time = time.time()
print(f"\nTemps d'exécution total : {end_time - start_time:.2f} secondes")
