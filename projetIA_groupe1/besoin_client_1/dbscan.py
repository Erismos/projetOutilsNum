# on importe les bibliothèque 
import pandas as pd # pour manipuler des données avec des dataframe
import numpy as np # pour les tableaux et opérations numériques
from sklearn.cluster import DBSCAN # pour le clustering avec l'algorithme dbscan
from sklearn.preprocessing import StandardScaler # pour normaliser les données
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score # pour évaluer les clusters
import matplotlib.pyplot as plt # pour les visualisations avec les graphiques
import plotly.express as px # pour les cartes interactives
import joblib # pour sauvegarder et charger les modèles en python
import time # pour mesuer le temps d'execution

start_time = time.time() # debut du timer

# Chargement des données
df = pd.read_csv("../data/export_IA.csv") # on charge le fichier csv dans un dataframe
print(df.dtypes) # on affiche le type de données de chaque colonne
print(f"Nombre de lignes : {len(df)}") # on affiche le nombre de ligne du dataframe

# Échantillonnage
df_sample = df.sample(n=20000, random_state=0) # on prend un échantillon de 20000 lignes et reproductable
X_sample = df_sample[['SOG', 'COG', 'Heading']] # on garde que les colonnes pertinantes à utiliser 
print("Taille de l'échantillon :", X_sample.shape) # on affiche la taille de l'échantillon

# Normalisation
scaler_sample = StandardScaler() # on initialise un objet pour normaliser
X_sample_scaled = scaler_sample.fit_transform(X_sample) # on normalise les données, on les met à la même échelle

# Test de différentes valeurs de eps et min_samples
# eps : la distance maximale entre deux points pour qu’ils soient considérés comme voisins
# min_sample : le nombre minimal de points (y compris le point lui-même) dans un voisinage pour qu’un point soit considéré comme un point central d’un cluster
eps_values = np.arange(0.1, 2.1, 0.1) # on génère des valeurs de eps de 0.1 à 2.0 avec un pas de 0.1
min_samples_values = [3, 5, 10] # liste des valeurs de min_samples à utiliser
results = [] # liste vide pour stocker les résultats

# Boucle pour tester toutes les combinaisons de paramètres
for eps in eps_values: 
    for min_samples in min_samples_values:
        dbscan = DBSCAN(eps=eps, min_samples=min_samples) # on initialise dbscan avec les paramètres
        labels = dbscan.fit_predict(X_sample_scaled) # on applique dbscan et on récupère les étiquettes des clusters

        # On ignore les cas avec tous les points en bruit ou 1 seul cluster
        # bruit : les points qui ne font parties d'aucun cluster
        if len(set(labels)) <= 1 or len(set(labels)) == len(X_sample_scaled):
            continue # on ignore les cas non pertinents 

        try:
            # Calcul des scores de qualité de clustering
            silhouette = silhouette_score(X_sample_scaled, labels) # calcul le score de silhouette
            ch_score = calinski_harabasz_score(X_sample_scaled, labels) # calcul le score de calinski-harabasz
            db_score = davies_bouldin_score(X_sample_scaled, labels) # calcul le score de davies-bouldin
            results.append((eps, min_samples, silhouette, ch_score, db_score, len(set(labels)))) # on ajoute dans la liste : eps, min_sample; les trois scores, le nombre de clusters détectés en comptant le nombre de label unique
        except Exception as e:
            print(f"Erreur pour eps={eps}, min_samples={min_samples} : {e}") # on gère les erreurs éventuelles

# Résultats
results_df = pd.DataFrame(results, columns=['eps', 'min_samples', 'silhouette', 'calinski_harabasz', 'davies_bouldin', 'n_clusters']) # on créé un dataframe avec les résultats
results_df.to_csv("csv/dbscan_metrics.csv", index=False) # on enregistre les résultats dans un fichier csv

# Pour chaque valeur de min_samples, on trace les courbes
unique_min_samples = sorted(results_df['min_samples'].unique()) # liste triée des min_samples testés

fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 14), sharex=True) # on créé trois sous graphiques verticaux 

# Boucle sur les métriques pour tracer les courbes
for i, metric in enumerate(['silhouette', 'calinski_harabasz', 'davies_bouldin']): # on aura l'indice et le nom de la metric
    ax = axes[i] # on sélectionne l’axe (sous-graphe) correspondant dans la figure 
    for ms in unique_min_samples: # pour chqaue valeur de min_sample testée, on trace une courbe différente
        subset = results_df[results_df['min_samples'] == ms] # on filtre le dataframe des résultats pour garder que les lignes avec ce min_sample spécifique
        # visualiser l’évolution du score pour chaque min_samples
        ax.plot(subset['eps'], subset[metric], marker='o', label=f"min_samples={ms}") #  On trace la courbe du score metric en fonction de eps, avec des marqueurs ronds
    ax.set_title(f"Score {metric} en fonction de eps") # titre du sous graphique avec le nom de la metrique affichée
    ax.set_ylabel(metric) # l'axe y indique la metrique utilisée
    ax.grid(True) # on affiche une une grille pour faciliter la lecture du graphique
    if i == 2: # on n’affiche l’axe X (eps) que sur le dernier graphique pour éviter la redondance visuelle sur les 3 subplots
        ax.set_xlabel("Valeur de eps")
    ax.legend() # on affiche la légende

plt.tight_layout() # on ajuste automatiquement les espacements entre les sous-graphiques
plt.savefig("graphique/dbscan_scores_subplots.png") # on sauvegarde le graphique dans un fichier png
print("Graphiques des scores DBSCAN enregistrés dans dbscan_scores_subplots.png") 
plt.show() # on affiche le graphique

# Choix du meilleur modèle par score combiné
def select_best_params_by_score(df_scores):
    # df_score : dataframe des metriques calculées pour chaque combinaison eps/min_sample
    df = df_scores.copy() # on créer une copie du dataframe d'origine piur éviter de le modifier
    # normalisation des scores entre 0 et 1 
    df['davies_bouldin_norm'] = (df['davies_bouldin'].max() - df['davies_bouldin']) / (df['davies_bouldin'].max() - df['davies_bouldin'].min()) # meilleur quand il est faible donc on l'inverse (plus proche de 1 du coup ok)
    df['silhouette_norm'] = (df['silhouette'] - df['silhouette'].min()) / (df['silhouette'].max() - df['silhouette'].min()) # meilleur élevé donc normalisation classique (min/max)
    df['calinski_harabasz_norm'] = (df['calinski_harabasz'] - df['calinski_harabasz'].min()) / (df['calinski_harabasz'].max() - df['calinski_harabasz'].min()) # meilleur élevé donc normalisation classique (min/max)
    # Score combiné pondéré
    # on calcul des poids pour obtenir un score global
    df['combined_score'] = (
        0.4 * df['silhouette_norm'] + # 40%
        0.4 * df['calinski_harabasz_norm'] + # 40%
        0.2 * df['davies_bouldin_norm'] # moins fiable ques les 2 autres donc 20%
    )

    best_row = df.loc[df['combined_score'].idxmax()] # on sélectionne la meilleure combinaison
    return best_row, df # on retourne la ligne entière contenant les meilleurs paramètre et le score associé

# on sélectionne les meilleurs paramètre
best_result, mieux_results_df = select_best_params_by_score(results_df)
best_eps = best_result['eps'] # meilleur eps
best_min_samples = int(best_result['min_samples']) # meilleur min_samples
print(f"Meilleurs paramètres DBSCAN : eps={best_eps:.2f}, min_samples={best_min_samples}") # on les affiches

# score combiné
plt.figure(figsize=(10, 6)) # nouvelle figure avec une taille prédéfini
for ms in unique_min_samples: # on boucle sur toutes les valeurs de min_sample, courbe différente pour chaque valeur
    # on trace une courbe combined_score vs eps pour chaque valeur de min_samples
    subset = mieux_results_df[mieux_results_df['min_samples'] == ms] # on extrait les lignes correspondant à ce min_sample
    plt.plot(subset['eps'], subset['combined_score'], marker='o', label=f"min_samples={ms}") # on trace la courbe du score combiné en fonction de eps

plt.xlabel("eps")
plt.ylabel("Score combiné")
plt.title("Score combiné DBSCAN selon eps")
plt.legend()
plt.grid(True)
plt.savefig("graphique/dbscan_combined_score.png") # on sauvegarde le graphique
plt.show() # on affiche le graphique

# Entraînement final avec les meilleurs paramètres
dbscan_final = DBSCAN(eps=best_eps, min_samples=best_min_samples)
clusters = dbscan_final.fit_predict(X_sample_scaled)

# Ajout des clusters dans le dataframe original
df.loc[X_sample.index, 'Cluster'] = clusters
df.to_csv("csv/export_IA_with_clusters_dbscan.csv", index=False) # on suavegarde dans un fichier csv
print("Fichier sauvegardé : export_IA_with_clusters_dbscan.csv")

# Carte
df['BaseDateTime'] = pd.to_datetime(df['BaseDateTime']) # on covertit les données en format de datetime
df_sorted = df.sort_values(by=['MMSI', 'BaseDateTime']) # on trie les données par leur identifiant de bateau et date
 
# Moyennes SOG, COG, Heading par cluster
cluster_means = df.groupby('Cluster')[['SOG', 'COG', 'Heading']].mean()
print(cluster_means) # on affiche le tableau des moyennesichier sauvegardé : export_IA_with_clusters_birch.csv (avec colonnes de cluster)

dbscan_cluster_legend = {
    -1.0: "bruit : navire très rapide cap au nord-nord-ouest",
    0.0: "vitesse modérée, cap vers le sud-ouest, bien aligné",
    1.0: "lent, cap vers l'ouest-sud-ouest, désaligné"
}

df_sorted['Interprétation'] = df_sorted['Cluster'].map(dbscan_cluster_legend)

# Création d'une carte interactive avec Plotly
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
fig.update_layout(title="Trajectoires des navires par cluster - DBSCAN ")
fig.write_html("carte/trajectoires_clusters_dbscan.html") # on sauvegarde la carte dans un fichier html
fig.show() # on affiche la carte
print("Carte enregistrée dans trajectoires_clusters_dbscan.html")

# Sauvegarde du modèle et du scaler
joblib.dump(dbscan_final, "pkl/dbscan_model.pkl") # on sauvegarde le modèle dbscan entrainé
joblib.dump(scaler_sample, "pkl/scaler_dbscan.pkl") # on sauvegarde le scaler entrainé

end_time = time.time() # fin du timer
print(f"\nTemps d'exécution total : {end_time - start_time:.2f} secondes") # on affiche le temps d'exécution du script
