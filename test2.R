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
  print("Filtrage des données pour la carte interactive...")
  vessels_to_plot <- unique(data$VesselName)[1:min(max_vessels, length(unique(data$VesselName)))]
  
  # Fonction pour détecter les arrêts
  detect_stops <- function(traj, speed_threshold = 1, duration_threshold = 4) {
    traj <- traj %>% arrange(BaseDateTime)
    
    stopped_points <- traj %>% 
      mutate(stopped = SOG < speed_threshold) %>%
      mutate(stop_group = cumsum(stopped != lag(stopped, default = first(stopped))))
    
    stop_durations <- stopped_points %>%
      filter(stopped) %>%
      group_by(stop_group) %>%
      summarise(
        start_time = min(BaseDateTime),
        end_time = max(BaseDateTime),
        duration = as.numeric(difftime(end_time, start_time, units = "hours")),
        mean_lon = mean(LON),
        mean_lat = mean(LAT),
        start_draft = first(Draft),
        end_draft = last(Draft),
        draft_change = end_draft - start_draft,
        .groups = 'drop'
      ) %>%
      filter(duration >= duration_threshold)
    
    return(stop_durations)
  }
  
  # Pré-traitement des données
  data_filtered <- data %>%
    filter(VesselName %in% vessels_to_plot) %>%
    mutate(VesselType = ifelse(is.na(VesselType), "Inconnu", as.character(VesselType))) %>%
    group_by(VesselName) %>%
    mutate(
      is_cargo = between(as.numeric(VesselType), 70, 80),
      draft_change_total = ifelse(is_cargo, max(Draft, na.rm = TRUE) - min(Draft, na.rm = TRUE), NA),
      loading_status = case_when(
        !is_cargo ~ "Non applicable",
        draft_change_total > 2 ~ "Chargement important (Δ > 2m)",
        draft_change_total > 0.5 ~ "Chargement modéré (Δ > 0.5m)",
        draft_change_total > 0 ~ "Chargement léger",
        TRUE ~ "Pas de chargement détecté"
      ),
      is_loaded = is_cargo & draft_change_total > 0.5,
      mean_draft = ifelse(is_cargo, mean(Draft, na.rm = TRUE), NA)
    ) %>%
    ungroup()
  
  # Détection des ports (uniquement pour les cargos)
  port_zones <- data.frame()
  cargo_vessels <- unique(data_filtered$VesselName[data_filtered$is_cargo])
  
  if(length(cargo_vessels) > 0) {
    for (vessel in cargo_vessels) {
      traj <- data_filtered %>% 
        filter(VesselName == vessel) %>% 
        arrange(BaseDateTime)
      
      stops <- detect_stops(traj)
      
      if (nrow(stops) > 0) {
        stops <- stops %>%
          mutate(
            port_activity = case_when(
              draft_change > 1 ~ "Déchargement majeur",
              draft_change > 0.3 ~ "Déchargement",
              draft_change < -1 ~ "Chargement majeur",
              draft_change < -0.3 ~ "Chargement",
              TRUE ~ "Arrêt simple"
            ),
            VesselName = vessel,
            VesselType = first(traj$VesselType)
          )
        port_zones <- bind_rows(port_zones, stops)
      }
    }
  }
  
  # Clustering des zones de port - seulement si plusieurs bateaux
  if (nrow(port_zones) > 0) {
    port_zones_sf <- st_as_sf(port_zones, coords = c("mean_lon", "mean_lat"), crs = 4326)
    
    # On augmente légèrement le eps pour mieux regrouper les points proches
    clustered <- dbscan(st_coordinates(port_zones_sf), eps = 0.15, minPts = 2)
    
    port_zones <- port_zones %>%
      mutate(cluster = clustered$cluster) %>%
      # On ne garde que les clusters avec au moins 2 bateaux différents
      group_by(cluster) %>%
      mutate(n_vessels = n_distinct(VesselName)) %>%
      ungroup() %>%
      filter(cluster > 0 & n_vessels >= 2) %>%
      # Regroupement final
      group_by(cluster) %>%
      summarise(
        mean_lon = mean(mean_lon),
        mean_lat = mean(mean_lat),
        n_operations = n(),
        n_vessels = n_distinct(VesselName),
        mean_draft_change = mean(draft_change, na.rm = TRUE),
        activities = paste(unique(port_activity), collapse = ", "),
        vessels = paste(unique(VesselName), collapse = ", "),
        .groups = 'drop'
      ) %>%
      # On filtre pour ne garder que les zones avec activité portuaire
      filter(activities != "")
  }
  
  # Préparation de la carte
  vessel_types <- unique(data_filtered$VesselType)
  type_palette <- colorFactor(palette = "Set1", domain = vessel_types)
  port_palette <- colorFactor(palette = c("blue", "red", "darkblue", "darkred", "gray"), 
                             domain = c("Chargement", "Chargement majeur", "Déchargement", "Déchargement majeur", "Arrêt simple"))
  
  map <- leaflet() %>%
    addTiles() %>%
    setView(lng = mean(data_filtered$LON, na.rm = TRUE), lat = mean(data_filtered$LAT, na.rm = TRUE), zoom = 6) %>%
    addLayersControl(
      overlayGroups = c("Tous les bateaux", vessel_types, "Cargos", "Chargé", 
                       "Zones de port", "Chargement", "Déchargement", "Routes principales"),
      options = layersControlOptions(collapsed = FALSE),
      position = "topright"
    ) %>%
    hideGroup(c(vessel_types, "Cargos", "Chargé", "Chargement", "Déchargement"))
  
  # Ajout des trajectoires (avec routes principales)
  for (vessel_type in vessel_types) {
    type_data <- data_filtered %>% filter(VesselType == vessel_type)
    for (vessel_name in unique(type_data$VesselName)) {
      traj <- type_data %>% filter(VesselName == vessel_name) %>% arrange(BaseDateTime)
      if (nrow(traj) > 1) {
        vessel_info <- traj %>% 
          slice(1) %>% 
          select(VesselName, VesselType, Length, Width, is_cargo, is_loaded, loading_status, mean_draft)
        
        popup_content <- paste(
          "<h2>Bateau:", vessel_info$VesselName, "</h2>Type:", vessel_info$VesselType,
          "<br>Longueur (m):", round(vessel_info$Length, 2),
          "<br>Largeur (m):", round(vessel_info$Width, 2)
        )
        
        if (vessel_info$is_cargo) {
          popup_content <- paste0(
            popup_content,
            "<br>Tirant d'eau moyen (m):", round(vessel_info$mean_draft, 2),
            "<br>Statut de chargement:", vessel_info$loading_status
          )
        }
        
        popup_content <- paste0(
          popup_content,
          "<hr>Distance totale (km):", round(sum(sqrt((diff(traj$LON))^2 + (diff(traj$LAT))^2), na.rm = TRUE) * 111, 2),
          "<br>Vitesse moyenne (nœuds):", round(mean(traj$SOG, na.rm = TRUE), 2),
          "<br>Vitesse maximale (nœuds):", round(max(traj$SOG, na.rm = TRUE), 2),
          "<br>Date de début:", min(traj$BaseDateTime), "<br>Date de fin:", max(traj$BaseDateTime)
        )
        
        groups <- c("Tous les bateaux", vessel_type)
        if (vessel_info$is_cargo) groups <- c(groups, "Cargos")
        if (vessel_info$is_loaded) groups <- c(groups, "Chargé")
        
        map <- map %>%
          addPolylines(
            lng = traj$LON, lat = traj$LAT, 
            color = type_palette(vessel_type),
            weight = 2, opacity = 0.7, 
            group = groups,
            popup = popup_content
          ) %>%
          # Ajout des routes principales
          addPolylines(
            lng = traj$LON, lat = traj$LAT, 
            color = "red", weight = 15,
            opacity = 0.1, group = "Routes principales"
          )
      }
    }
  }
  
  
  # Ajout des zones de port seulement si elles existent
  if (exists("port_zones") && nrow(port_zones) > 0) {
    map <- map %>%
      addCircleMarkers(
        data = port_zones,
        lng = ~mean_lon, lat = ~mean_lat,
        radius = ~sqrt(n_operations)*3,
        color = ~ifelse(mean_draft_change < 0, "red", "blue"),
        fillOpacity = 0.7,
        stroke = TRUE,
        weight = 1,
        group = "Zones de port",
        popup = ~paste(
          "<h3>Zone portuaire confirmée</h3>",
          "Nombre de bateaux:", n_vessels,
          "<br>Opérations:", n_operations,
          "<br>Activités:", activities,
          "<br>Bateaux:", substr(vessels, 1, 100), "..."
        )
      )
  
    # Ajout des points individuels
    if (exists("port_zones_sf") && nrow(port_zones_sf) > 0) {
      map <- map %>%
        addCircleMarkers(
          data = port_zones_sf,
          radius = 5,
          color = ~port_palette(port_activity),
          fillOpacity = 0.7,
          stroke = TRUE,
          weight = 1,
          group = ~ifelse(grepl("Chargement", port_activity), "Chargement", "Déchargement"),
          popup = ~paste(
            "<h3>Activité portuaire</h3>",
            "<br>Bateau:", VesselName,
            "<br>Type:", VesselType,
            "<br>Activité:", port_activity,
            "<br>Durée:", round(duration, 1), "heures",
            "<br>Δ tirant d'eau:", round(draft_change, 2), "m"
          )
        )
    }
  }
  
  # Légendes
  map <- map %>%
    addLegend(position = "bottomright", pal = type_palette, values = vessel_types,
              title = "Types de bateaux", opacity = 0.7) %>%
    addLegend(position = "bottomleft", 
              colors = c("red"), 
              labels = c("Routes principales"),
              title = "Routes", opacity = 0.7)
  
  if (exists("port_zones") && nrow(port_zones) > 0) {
    map <- map %>%
      addLegend(position = "topleft", 
                colors = c("blue", "red"), 
                labels = c("Déchargement ou Arrêt", "Chargement"),
                title = "Activités portuaires",
                opacity = 0.7)
  }
  
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
# stats <- analyze_trajectory_stats(vessel_data)
# write.csv(stats, "outputs/stats_trajectoires.csv", row.names = FALSE)

print("Terminé.")
