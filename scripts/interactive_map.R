############################################################
# Titre      : Carte Interactive des Trajectoires Maritimes
# Fichier    : interactive_map.R
# Description: Ce script R permet de générer une carte 
#              interactive des trajectoires de navires à 
#              partir de données AIS, avec détection des
#              zones portuaires, statut de chargement, et 
#              visualisation détaillée (popups, groupes, etc.).
#
# Auteurs     : Gabriel Boucneau & Laure Warlop & Clément Auvray
# Date        : Juin 2025
# Données     : data/export_IA.csv
# Dépendances : leaflet, dplyr, sf, dbscan, lubridate, htmlwidgets
# Sorties     : outputs/interactive_map.html
############################################################

####################################################
# Fonctionnalité 3: Carte interactive #
####################################################

# Chargement des bibliothèques nécessaires
library(leaflet)
library(dplyr)
library(sf)
library(dbscan)
library(lubridate)
library(htmlwidgets)

# Fonction pour détecter les arrêts des navires
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

# Fonction pour préparer les données des navires
prepare_vessel_data <- function(data, max_vessels = 142) {
  vessels_to_plot <- unique(data$VesselName)[1:min(max_vessels, length(unique(data$VesselName)))]
  
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
  
  return(data_filtered)
}

# Fonction pour détecter les zones portuaires
detect_port_zones <- function(data_filtered) {
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
              draft_change > 0.3 ~ "Déchargement",
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
  
  return(port_zones)
}

# Fonction pour regrouper les zones portuaires similaires
cluster_port_zones <- function(port_zones) {
  if (nrow(port_zones) == 0) return(data.frame())
  
  port_zones_sf <- st_as_sf(port_zones, coords = c("mean_lon", "mean_lat"), crs = 4326)
  clustered <- dbscan(st_coordinates(port_zones_sf), eps = 0.4, minPts = 3)
  
  clustered_zones <- port_zones %>%
    mutate(cluster = clustered$cluster) %>%
    group_by(cluster) %>%
    mutate(n_vessels = n_distinct(VesselName)) %>%
    ungroup() %>%
    filter(cluster > 0 & n_vessels >= 4) %>%
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
    filter(activities != "")
  
  return(list(clustered_zones = clustered_zones, port_zones_sf = port_zones_sf))
}

# Fonction pour ajouter les trajectoires à la carte
add_trajectories_to_map <- function(map, data_filtered, type_palette) {
  vessel_types <- unique(data_filtered$VesselType)
  
  for (vessel_type in vessel_types) {
    type_data <- data_filtered %>% filter(VesselType == vessel_type)
    for (vessel_name in unique(type_data$VesselName)) {
      traj <- type_data %>% filter(VesselName == vessel_name) %>%
        arrange(BaseDateTime)
      if (nrow(traj) > 1) {
        vessel_info <- traj %>% slice(1) %>%
          select(VesselName, VesselType, Length, Width, is_cargo, is_loaded,
                 loading_status, mean_draft)
        
        popup_content <- create_vessel_popup(vessel_info, traj)
        
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
          addPolylines(
            lng = traj$LON, lat = traj$LAT, 
            color = "red", weight = 15,
            opacity = 0.1, group = "Routes principales"
          )
      }
    }
  }

  return(map)
}

# Fonction pour créer le contenu des popups
create_vessel_popup <- function(vessel_info, traj) {
  popup_content <- paste(
    "<h2>Bateau:", vessel_info$VesselName, "</h2>Type:", vessel_info$VesselType,
    "Longueur (m):", round(vessel_info$Length, 2),
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
    "<hr>Distance totale (km):",
    round(sum(sqrt((diff(traj$LON))^2 + (diff(traj$LAT))^2),
        na.rm = TRUE) * 111, 2),
    "<br>Vitesse moyenne (nœuds):", round(mean(traj$SOG, na.rm = TRUE), 2),
    "<br>Vitesse maximale (nœuds):", round(max(traj$SOG, na.rm = TRUE), 2),
    "<br>Date de début:", min(traj$BaseDateTime), "<br>Date de fin:",
    max(traj$BaseDateTime)
  )

  return(popup_content)
}

# Fonction pour ajouter les zones portuaires à la carte
add_port_zones_to_map <- function(map, port_data) {
  if (nrow(port_data$clustered_zones) == 0) return(map)
  
  map <- map %>%
    addCircleMarkers(
      data = port_data$clustered_zones,
      lng = ~mean_lon, lat = ~mean_lat,
      radius = ~sqrt(n_operations)*3,
      color = ~ifelse(mean_draft_change == 0, "#ffff86", 
               ifelse(mean_draft_change < 0, "blue", "red")),
      fillOpacity = 0.7,
      stroke = TRUE,
      weight = 1,
      group = "Zones de port",
      popup = ~paste("<h3>", ifelse(mean_draft_change == 0, "Zone d'arrêt",
        "Zone Portuaire"),"</h3>", "Nombre de bateaux:", n_vessels,
        "<br>Opérations:", n_operations, "<br>Activités:", activities,
        "<br>Bateaux:", substr(vessels, 1, 5), "..."
      )
    )
  
  if (nrow(port_data$port_zones_sf) > 0) {
    port_palette <- colorFactor(
      palette = c( "#ffff86", "blue", "red"), 
      domain = c("Chargement", "Déchargement", "Arrêt simple")
    )
    
    map <- map %>%
      addCircleMarkers(
        data = port_data$port_zones_sf,
        radius = 5,
        color = ~port_palette(port_activity),
        fillOpacity = 0.7,
        stroke = TRUE,
        weight = 1,
        group = ~ifelse(grepl("Chargement", port_activity), "Chargement", 
                ifelse(grepl("Déchargement", port_activity), "Déchargement", "Arrêt simple")),
        popup = ~paste(
          "<h3>Activité portuaire</h3>",
          "Bateau:", VesselName,
          "<br>Type:", VesselType,
          "<br>Activité:", port_activity,
          "<br>Durée:", round(duration, 1), "heures",
          "<br>Δ tirant d'eau:", round(draft_change, 2), "m"
        )
      )
  }
  
  return(map)
}

# Fonction pour ajouter les légendes à la carte
add_map_legends <- function(map, vessel_types, port_zones_exist = FALSE) {
  type_palette <- colorFactor(palette = "Set1", domain = vessel_types)
  
  map <- map %>%
    addLegend(position = "bottomright", pal = type_palette, values = vessel_types,
              title = "Types de bateaux", opacity = 0.7) %>%
    addLegend(position = "bottomleft", 
              colors = c("red"), 
              labels = c("Routes principales"),
              title = "Routes", opacity = 0.7)
  
  if (port_zones_exist) {
    map <- map %>%
      addLegend(position = "topleft", 
                colors = c("blue", "red", "#ffff86"), 
                labels = c("Déchargement", "Chargement", "Arrêt simple"),
                title = "Activités portuaires",
                opacity = 0.7)
  }
  
  return(map)
}

# Fonction principale pour créer la carte interactive
create_interactive_map <- function(data, max_vessels = 142) {
  print("Filtrage des données pour la carte interactive...")
  
  # Préparation des données
  data_filtered <- prepare_vessel_data(data, max_vessels)
  
  # Détection des zones portuaires
  port_zones <- detect_port_zones(data_filtered)
  port_data <- cluster_port_zones(port_zones)
  
  # Initialisation de la carte
  vessel_types <- unique(data_filtered$VesselType)
  type_palette <- colorFactor(palette = "Set1", domain = vessel_types)
  
  map <- leaflet() %>%
    addTiles() %>%
    setView(lng = mean(data_filtered$LON, na.rm = TRUE), lat = mean(data_filtered$LAT, na.rm = TRUE), zoom = 6) %>%
    addLayersControl(
      overlayGroups = c("Tous les bateaux", vessel_types, "Cargos", "Chargé", 
                       "Zones de port", "Chargement", "Déchargement", "Arrêt simple", "Routes principales"),
      options = layersControlOptions(collapsed = FALSE),
      position = "topright"
    ) %>%
    hideGroup(c(vessel_types, "Cargos", "Chargé", "Chargement", "Déchargement", "Arrêt simple", "Routes principales"))
  
  # Ajout des éléments à la carte
  map <- add_trajectories_to_map(map, data_filtered, type_palette)
  map <- add_port_zones_to_map(map, port_data)
  map <- add_map_legends(map, vessel_types, nrow(port_data$clustered_zones) > 0)
  
  return(map)
}

# Fonction pour charger et préparer les données
load_and_prepare_data <- function(file_path) {
  data <- read.csv(file_path)
  data$BaseDateTime <- as.POSIXct(data$BaseDateTime, format="%Y-%m-%d %H:%M:%S")
  data <- data %>% arrange(VesselName, BaseDateTime)
  return(data)
}

# Fonction principale pour exécuter tout le processus
main_interactive_map <- function() {
  print("Chargement des données...")
  vessel_data <- load_and_prepare_data("data/export_IA.csv")
  
  print("Génération de la carte interactive...")
  interactive_map <- create_interactive_map(vessel_data)
  
  print("Sauvegarde de la carte...")
  saveWidget(interactive_map, "outputs/interactive_map.html", selfcontained = TRUE)
  
  print("Carte sauvegardée.")
}

# Exécution du programme
# main_interactive_map()
