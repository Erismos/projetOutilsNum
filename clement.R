############################################################
# Author       : Clément Auvray
# Date         : 2025-06-10
# Script Name  : clement.R
# Description  : Nettoyage et visualisation des données de trafic maritime
#               : Ce script nettoie les données de trafic maritime,
#               : remplace les valeurs aberrantes et les NA, et génère
#               : des graphiques optimisés pour l'analyse.
#               : Il inclut également des visualisations interactives
#               : et des statistiques descriptives.
# Version      : 1.0
# R Version    : ex: 4.4.3
# Dependencies : readr, dplyr, ggplot2, lubridate, viridis, RColorBrewer,
# Notes        : [Commentaires utiles, TODO, etc.]
############################################################

# Libraries
library(readr)
library(dplyr)
library(ggplot2)
library(cowplot)
library(lubridate)
library(viridis)
library(RColorBrewer)
library(maps)
library(mapdata)
library(ggmap)
library(sf)
library(leaflet)
library(plotly)
library(cluster)
library(dbscan)
library(htmlwidgets)

####################################################
# Nettoyage et traintement des données #
####################################################


print("Fonctionnalité 1: Nettoyage et traitement des données de trafic maritime")
# Lire le fichier CSV en remplaçant les "\\N" par NA
data <- read_csv("data/vessel-total-clean.csv", na = "\\N")
print(summary(data))  # Afficher un résumé des données
print(dim(data))  # Afficher les dimensions du jeu de données

# Identifier les colonnes qualitatives (character/factor)
qualitative_cols <- names(data)[sapply(data, function(x) is.character(x) | is.factor(x))]

# Remplacer les NA dans les colonnes qualitatives par "INC"
data <- data %>%
  mutate(across(all_of(qualitative_cols), ~ ifelse(is.na(.), "Inconnu", .)))

# Calculer le pourcentage de NA par colonne pour les colonnes numériques
na_percent <- sapply(data, function(col) mean(is.na(col)))

# Sélectionner les colonnes numériques avec moins de 5% de NA
numeric_cols <- names(data)[sapply(data, is.numeric)]
cols_to_check <- numeric_cols[na_percent[numeric_cols] < 0.05]

# Supprimer les lignes contenant des NA dans ces colonnes numériques sélectionnées
data_cleaned <- data %>% filter(across(all_of(cols_to_check), ~ !is.na(.)))

# Fonction pour détecter et remplacer les valeurs aberrantes
replace_outliers_with_mean <- function(x) {
  if (is.numeric(x)) {
    # Détection des valeurs aberrantes par l'IQR
    q1 <- quantile(x, 0.25, na.rm = TRUE)
    q3 <- quantile(x, 0.75, na.rm = TRUE)
    iqr <- q3 - q1
    lower <- q1 - 1.5 * iqr
    upper <- q3 + 1.5 * iqr
    mean_val <- mean(x[x >= lower & x <= upper], na.rm = TRUE)
    x[x < lower | x > upper] <- mean_val
  }
  return(x)
}

# Fonction pour remplacer les NA par la médiane de la colonne
replace_na_with_median <- function(x) {
  if (is.numeric(x)) {
    x[is.na(x)] <- median(x, na.rm = TRUE)
  }
  return(x)
}

# Exclure certaines données du traitement des outliers
cols_outliers <- setdiff(names(data_cleaned)[sapply(data_cleaned, is.numeric)], c("LON", "LAT", "BaseDateTime", "id", "MMSI", "VesselType"))

# Appliquer le remplacement des outliers et des NA
data_final <- data_cleaned %>%
  mutate(across(all_of(cols_outliers), replace_outliers_with_mean)) %>%
  mutate(across(where(is.numeric), replace_na_with_median))

# Afficher un aperçu
print(summary(data_final))

# Pourcentage de perte de données
loss_percentage <- (nrow(data) - nrow(data_final)) / nrow(data) * 100
print(paste("Perte de données après nettoyage :", round(loss_percentage, 2), "%"))

# Sauvegarder les données nettoyées
write.csv(data_final, "data/vessel-cleaned.csv", row.names = FALSE)
print("Data cleaning complete. Cleaned data saved to 'data/vessel-cleaned.csv'.")




####################################################
# Graphiques optimisés pour l'analyse des données de bateaux #
####################################################

print("Fonctionnalité 2: Graphiques pour l'analyse des données de bateaux")
# Chargement des données
data <- read.csv("data/vessel-cleaned.csv")

# Préparation des données
data$BaseDateTime <- as.POSIXct(data$BaseDateTime, format="%Y-%m-%d %H:%M:%S")
data$Hour <- hour(data$BaseDateTime)
data$Date <- as.Date(data$BaseDateTime)
data$Length_num <- as.numeric(as.character(data$Length))
data$Width_num <- as.numeric(as.character(data$Width))

# Thème personnalisé
theme_marine <- theme_minimal() +
  theme(
    plot.title = element_text(size = 14, face = "bold", hjust = 0.5),
    plot.subtitle = element_text(size = 11, hjust = 0.5, color = "gray60"),
    axis.title = element_text(size = 12),
    legend.title = element_text(size = 11, face = "bold"),
    panel.grid.minor = element_blank(),
    plot.background = element_rect(fill = "white", color = NA)
  )

  
# Fonction pour créer un diagramme polaire amélioré
create_polar_plot <- function(var, title, color) {
  ggplot(data, aes(x = {{var}})) +
    geom_histogram(binwidth = 15, fill = color, color = "white", alpha = 0.8) +
    coord_polar(start = -pi/16) +
    scale_x_continuous(limits = c(0, 360), breaks = seq(0, 360, by = 45)) +
    labs(title = title, x = "", y = "") +
    theme_minimal() +
    theme(
      axis.text.y = element_blank(),
      panel.grid.major.y = element_blank(),
      plot.title = element_text(hjust = 0.5, face = "bold")
    )
}

# COG et Heading côte à côte
p1 <- create_polar_plot(COG, "Distribution des directions (COG)", "#4e79a7")
p2 <- create_polar_plot(Heading, "Distribution des caps (Heading)", "#e15759")
combined_polar <- plot_grid(p1, p2, ncol = 2)

ggsave("plots/combined_direction_plots.png", combined_polar, width = 12, height = 6)


# RÉPARTITION DES BATEAUX PAR TYPE
vessel_type_counts <- data %>%
  count(VesselType, sort = TRUE) %>%
  mutate(percentage = round(n/sum(n)*100, 1))

ggplot(vessel_type_counts, aes(x = reorder(as.factor(VesselType), n), y = n)) +
  geom_col(fill = "steelblue", color = "navy", alpha = 0.8) +
  geom_text(aes(label = paste0(n, " (", percentage, "%)")), 
            hjust = -0.1, size = 3.5) +
  coord_flip() +
  labs(title = "Répartition des bateaux par type",
       subtitle = "Nombre total et pourcentage par catégorie",
       x = "Type de bateau",
       y = "Nombre de bateaux") +
  theme_marine +
  theme(axis.text.x = element_text(angle = 0))
ggsave("plots/vessel_type_distribution_enhanced.png", width = 12, height = 8, dpi = 300)


# RELATION LONGUEUR/LARGEUR PAR TYPE
length_width_clean <- data %>%
  filter(!is.na(Length_num) & !is.na(Width_num) & 
         Length_num > 0 & Width_num > 0 & 
         Length_num < 500 & Width_num < 100) %>%  # Filtrer les valeurs aberrantes
  group_by(VesselType) %>%
  filter(n() >= 50) %>%  # Garder seulement les types avec assez de données
  ungroup()

ggplot(length_width_clean, aes(x = Length_num, y = Width_num, color = as.factor(VesselType))) +
  geom_point(alpha = 0.6, size = 1.5) +
  geom_smooth(method = "lm", se = FALSE, linetype = "dashed", size = 0.8) +
  scale_color_viridis_d(name = "Type de\nbateau") +
  labs(title = "Relation entre longueur et largeur des bateaux",
       subtitle = "Corrélation par type de navire avec tendances",
       x = "Longueur (mètres)",
       y = "Largeur (mètres)") +
  theme_marine +
  theme(legend.position = "right") +
  facet_wrap(~VesselType, scales = "free", ncol = 3)
ggsave("plots/length_vs_width_by_type_enhanced.png", width = 15, height = 12, dpi = 300)

# RÉSUMÉ STATISTIQUE VISUEL
summary_stats <- data %>%
  summarise(
    total_vessels = n(),
    unique_types = n_distinct(VesselType),
    avg_speed = round(mean(SOG, na.rm = TRUE), 1),
    max_speed = round(max(SOG, na.rm = TRUE), 1),
    avg_length = round(mean(Length_num, na.rm = TRUE), 1),
    date_range = paste(min(Date, na.rm = TRUE), "à", max(Date, na.rm = TRUE))
  )

# Affichage des statistiques
cat("=== RÉSUMÉ DE L'ANALYSE ===\n")
cat("Nombre total d'observations:", summary_stats$total_vessels, "\n")
cat("Types de navires uniques:", summary_stats$unique_types, "\n")
cat("Vitesse moyenne:", summary_stats$avg_speed, "nœuds\n")
cat("Vitesse maximale:", summary_stats$max_speed, "nœuds\n")
cat("Longueur moyenne:", summary_stats$avg_length, "mètres\n")
cat("Période d'observation:", summary_stats$date_range, "\n")
cat("========================\n")

print("Tous les graphiques ont été générés avec succès dans le dossier 'plots/'")
print("Résolution: 300 DPI pour impression haute qualité")



####################################################
# Carte interactive #
####################################################

print("Fonctionnalité 3: Carte interactive")


# ===============================
# 1. LECTURE DES DONNÉES
# ===============================
vessel_data <- read.csv("data/vessel-cleaned.csv")
vessel_data$BaseDateTime <- as.POSIXct(vessel_data$BaseDateTime, format="%Y-%m-%d %H:%M:%S")
vessel_data <- vessel_data %>% arrange(VesselName, BaseDateTime)

# ===============================
# 2. DÉFINITION DES FONCTIONS
# ===============================

# Analyse statistique des trajectoires
analyze_trajectory_stats <- function(data) {
  stats <- data %>%
    group_by(VesselName) %>%
    summarise(
      nb_points = n(),
      duree_tracking = as.numeric(difftime(max(BaseDateTime), min(BaseDateTime), units = "hours")),
      distance_totale = sum(sqrt((LON - lag(LON))^2 + (LAT - lag(LAT))^2), na.rm = TRUE),
      vitesse_moyenne = mean(SOG, na.rm = TRUE),
      type_bateau = first(VesselType),
      .groups = 'drop'
    ) %>%
    arrange(desc(nb_points))
  return(stats)
}

# Identification des routes principales (DBSCAN)
identify_main_routes <- function(data, eps = 0.1, min_samples = 5) {
  coords <- data %>% select(LON, LAT) %>% filter(!is.na(LON) & !is.na(LAT))
  db_result <- dbscan(coords, eps = eps, minPts = min_samples)
  coords$cluster <- db_result$cluster
  
  cluster_summary <- coords %>%
    filter(cluster != 0) %>%
    group_by(cluster) %>%
    summarise(
      count = n(),
      center_lon = mean(LON),
      center_lat = mean(LAT),
      .groups = 'drop'
    ) %>%
    arrange(desc(count))
  
  return(list(
    clustered_data = coords,
    main_routes = cluster_summary
  ))
}

# Carte statique - tous les bateaux
plot_all_trajectories <- function(data, max_vessels = NULL) {
  if (!is.null(max_vessels)) {
    vessels_to_plot <- unique(data$VesselName)[1:min(max_vessels, length(unique(data$VesselName)))]
    data <- data %>% filter(VesselName %in% vessels_to_plot)
  }
  world_map <- map_data("world")
  ggplot() +
    geom_polygon(data = world_map, aes(x = long, y = lat, group = group), fill = "lightgray", color = "white", size = 0.2) +
    geom_path(data = data, aes(x = LON, y = LAT, group = VesselName, color = VesselName), alpha = 0.7, size = 0.5) +
    coord_fixed(1.3, xlim = c(min(data$LON, na.rm = TRUE) - 1, max(data$LON, na.rm = TRUE) + 1),
                ylim = c(min(data$LAT, na.rm = TRUE) - 1, max(data$LAT, na.rm = TRUE) + 1)) +
    theme_minimal() + theme(legend.position = "none") +
    labs(title = "Trajectoires des bateaux", x = "Longitude", y = "Latitude")
}

# Carte statique - un seul bateau
plot_single_trajectory <- function(data, vessel_name) {
  vessel_data_filtered <- data %>% filter(VesselName == vessel_name)
  if (nrow(vessel_data_filtered) == 0) {
    stop(paste("Aucune donnée trouvée pour le bateau:", vessel_name))
  }
  world_map <- map_data("world")
  ggplot() +
    geom_polygon(data = world_map, aes(x = long, y = lat, group = group), fill = "lightgray", color = "white", size = 0.2) +
    geom_path(data = vessel_data_filtered, aes(x = LON, y = LAT), color = "red", size = 1, alpha = 0.8) +
    geom_point(data = vessel_data_filtered[1,], aes(x = LON, y = LAT), color = "green", size = 3, alpha = 0.8) +
    geom_point(data = vessel_data_filtered[nrow(vessel_data_filtered),], aes(x = LON, y = LAT), color = "blue", size = 3, alpha = 0.8) +
    coord_fixed(1.3, xlim = c(min(vessel_data_filtered$LON, na.rm = TRUE) - 0.5, max(vessel_data_filtered$LON, na.rm = TRUE) + 0.5),
                ylim = c(min(vessel_data_filtered$LAT, na.rm = TRUE) - 0.5, max(vessel_data_filtered$LAT, na.rm = TRUE) + 0.5)) +
    theme_minimal() +
    labs(title = paste("Trajectoire du bateau:", vessel_name),
         subtitle = "Vert = Départ, Bleu = Arrivée", x = "Longitude", y = "Latitude")
}

# Carte statique - routes principales
plot_main_routes <- function(clustering_result, top_n = 5) {
  coords <- clustering_result$clustered_data
  main_routes <- clustering_result$main_routes %>% head(top_n)
  coords_filtered <- coords %>% filter(cluster %in% main_routes$cluster)
  world_map <- map_data("world")
  ggplot() +
    geom_polygon(data = world_map, aes(x = long, y = lat, group = group), fill = "lightgray", color = "white", size = 0.2) +
    geom_point(data = coords_filtered, aes(x = LON, y = LAT, color = factor(cluster)), alpha = 0.6, size = 0.8) +
    geom_point(data = main_routes, aes(x = center_lon, y = center_lat), color = "black", size = 4, shape = 21, fill = "yellow") +
    coord_fixed(1.3, xlim = c(min(coords$LON, na.rm = TRUE) - 1, max(coords$LON, na.rm = TRUE) + 1),
                ylim = c(min(coords$LAT, na.rm = TRUE) - 1, max(coords$LAT, na.rm = TRUE) + 1)) +
    scale_color_viridis_d(name = "Route") +
    theme_light() +
    labs(title = paste("Top", top_n, "Routes principales"),
         subtitle = "Points jaunes = centres des routes principales", x = "Longitude", y = "Latitude")
}

# Carte interactive Leaflet
create_interactive_map <- function(data, max_vessels = 142) {
  vessels_to_plot <- unique(data$VesselName)[1:min(max_vessels, length(unique(data$VesselName)))]
  data_filtered <- data %>%
    filter(VesselName %in% vessels_to_plot) %>%
    mutate(VesselType = ifelse(is.na(VesselType), "Inconnu", as.character(VesselType)))
  
  vessel_types <- unique(data_filtered$VesselType)
  routes_analysis <- identify_main_routes(data_filtered, eps = 0.05, min_samples = 10)
  main_routes <- routes_analysis$main_routes %>% head(5)
  
  type_palette <- colorFactor(palette = "Set1", domain = vessel_types)
  route_palette <- colorFactor(palette = "Dark2", domain = main_routes$cluster)
  
  map <- leaflet() %>%
    addTiles() %>%
    setView(lng = mean(data_filtered$LON, na.rm = TRUE), lat = mean(data_filtered$LAT, na.rm = TRUE), zoom = 6) %>%
    addLayersControl(
      overlayGroups = c(vessel_types, "Routes principales"),
      options = layersControlOptions(collapsed = FALSE),
      position = "topright"
    ) %>%
    hideGroup("Routes principales")
  
  for (vessel_type in vessel_types) {
    type_data <- data_filtered %>% filter(VesselType == vessel_type)
    for (vessel_name in unique(type_data$VesselName)) {
      traj <- type_data %>% filter(VesselName == vessel_name) %>% arrange(BaseDateTime)
      if (nrow(traj) > 1) {
        map <- map %>%
          addPolylines(
            lng = traj$LON, lat = traj$LAT, color = type_palette(vessel_type),
            weight = 2, opacity = 0.7, group = vessel_type,
            popup = paste("Bateau:", vessel_name, "<br>Type:", vessel_type)
          )
      }
    }
  }
  
  clustered_data <- routes_analysis$clustered_data %>% filter(cluster %in% main_routes$cluster)
  for (route_id in main_routes$cluster) {
    points <- clustered_data %>% filter(cluster == route_id)
    center <- main_routes %>% filter(cluster == route_id)
    map <- map %>%
      addCircleMarkers(data = points, lng = ~LON, lat = ~LAT, radius = 3,
                       color = route_palette(route_id), stroke = FALSE,
                       fillOpacity = 0.7, group = "Routes principales") %>%
      addLabelOnlyMarkers(lng = center$center_lon, lat = center$center_lat,
                          label = paste("Route", route_id), group = "Routes principales",
                          labelOptions = labelOptions(noHide = TRUE, textOnly = TRUE,
                            style = list("color" = "black", "font-weight" = "bold",
                                         "background" = "rgba(255,255,255,0.7)")))
  }
  
  map <- map %>%
    addLegend(position = "bottomright", pal = type_palette, values = vessel_types,
              title = "Types de bateaux", opacity = 0.7) %>%
    addLegend(position = "bottomleft", pal = route_palette, values = main_routes$cluster,
              title = "Routes principales", opacity = 0.7, group = "Routes principales")
  
  return(map)
}

# ===============================
# 3. EXÉCUTION ET EXPORTS
# ===============================
print("Analyse en cours...")
print("Génération des graphiques et cartes...")
# Visualisation statique globale
ggsave("plots/all_trajectories.png", plot_all_trajectories(vessel_data, max_vessels = 100), width = 12, height = 8)

# Carte statique d'un bateau spécifique
ggsave("plots/single_trajectory.png", plot_single_trajectory(vessel_data, vessel_name = "OVERSEAS LOS ANGELES"), width = 12, height = 8)

# Analyse des routes principales
print("Identification des routes principales...")
routes_result <- identify_main_routes(vessel_data, eps = 0.05, min_samples = 10)
ggsave("plots/main_routes.png", plot_main_routes(routes_result), width = 12, height = 8)

print("Génération de la carte interactive...")
# Génération de la carte interactive
interactive_map <- create_interactive_map(vessel_data)
saveWidget(interactive_map, "outputs/interactive_map.html", selfcontained = TRUE)

# Statistiques
stats <- analyze_trajectory_stats(vessel_data)
write.csv(stats, "outputs/stats_trajectoires.csv", row.names = FALSE)

print("Terminé.")
