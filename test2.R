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


# Carte interactive Leaflet
create_interactive_map <- function(data, max_vessels = 142) {
  print("filtrage des données pour la carte interactive...")
  vessels_to_plot <- unique(data$VesselName)[1:min(max_vessels, length(unique(data$VesselName)))]
  data_filtered <- data %>%
    filter(VesselName %in% vessels_to_plot) %>%
    mutate(VesselType = ifelse(is.na(VesselType), "Inconnu", as.character(VesselType)))
  
  vessel_types <- unique(data_filtered$VesselType)
  # routes_analysis <- identify_main_routes(data_filtered, eps = 0.05, min_samples = 10)
  # main_routes <- routes_analysis$main_routes %>% head(6)
  
  type_palette <- colorFactor(palette = "Set1", domain = vessel_types)
  # route_palette <- colorFactor(palette = "Dark2", domain = main_routes$cluster)
  
  map <- leaflet() %>%
    addTiles() %>%
    setView(lng = mean(data_filtered$LON, na.rm = TRUE), lat = mean(data_filtered$LAT, na.rm = TRUE), zoom = 6) %>%
    addLayersControl(
      overlayGroups = c("Tous les bateaux", vessel_types, "Routes principales"),
      options = layersControlOptions(collapsed = FALSE),
      position = "topright"
    ) %>%
    hideGroup(c(vessel_types, "Tous les bateaux"))

  print("Ajout des trajectoires pour les bateaux...")
  for (vessel_type in vessel_types) {
    type_data <- data_filtered %>% filter(VesselType == vessel_type)
    for (vessel_name in unique(type_data$VesselName)) {
      traj <- type_data %>% filter(VesselName == vessel_name) %>% arrange(BaseDateTime)
      if (nrow(traj) > 1) {
        map <- map %>%
          addPolylines(
            lng = traj$LON, lat = traj$LAT, color = type_palette(vessel_type),
            weight = 2, opacity = 0.7, group = c("Tous les bateaux", vessel_type),
            popup = paste("<h2>Bateau:", vessel_name, "</h2><br>Type:", vessel_type,
                          "<br>Longueur (m):", round(mean(traj$Length, na.rm = TRUE), 2),
                          "<br>Largeur (m):", round(mean(traj$Width, na.rm = TRUE), 2),
                          "<hr>Distance totale (km):", round(sum(sqrt((diff(traj$LON))^2 + (diff(traj$LAT))^2), na.rm = TRUE) * 111, 2),
                          "<br>Vitesse moyenne (nœuds):", round(mean(traj$SOG, na.rm = TRUE), 2),
                          "<br>Vitesse maximale (nœuds):", round(max(traj$SOG, na.rm = TRUE), 2),
                          "<br>Date de début:", min(traj$BaseDateTime), "<br>Date de fin:", max(traj$BaseDateTime)
                          )
          ) %>%
          addPolylines(
            lng = traj$LON, lat = traj$LAT, color = "red", weight = 15,
            opacity = 0.1, group = "Routes principales"
          )
      }
    }
  }
    
  map <- map %>%
    addLegend(position = "bottomright", pal = type_palette, values = vessel_types,
              title = "Types de bateaux", opacity = 0.7) %>%
    addLegend(position = "bottomleft", colors = "red", labels = "Routes principales",
              title = "Routes principales", opacity = 0.7)

  return(map)
} 

# ===============================
# 3. EXÉCUTION ET EXPORTS
# ===============================
print("Analyse en cours...")
# print("Génération des graphiques...")
# # Visualisation statique globale
# ggsave("plots/all_trajectories.png", plot_all_trajectories(vessel_data, max_vessels = 100), width = 12, height = 8)

# # Carte statique d'un bateau spécifique
# ggsave("plots/single_trajectory.png", plot_single_trajectory(vessel_data, vessel_name = "OVERSEAS LOS ANGELES"), width = 12, height = 8)

print("Génération de la carte interactive...")
# Génération de la carte interactive
interactive_map <- create_interactive_map(vessel_data)
saveWidget(interactive_map, "outputs/interactive_map.html", selfcontained = TRUE)

# Statistiques
stats <- analyze_trajectory_stats(vessel_data)
write.csv(stats, "outputs/stats_trajectoires.csv", row.names = FALSE)

print("Terminé.")
