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
# Sorties     : map/interactive_map.html
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

#' Détecte les arrêts des navires dans une trajectoire
#'
#' @param traj DataFrame contenant les données de trajectoire d'un navire
#' @param speed_threshold Seuil de vitesse (en noeuds) pour considérer un arrêt (défaut: 1)
#' @param duration_threshold Durée minimale (en heures) pour considérer un arrêt significatif (défaut: 4)
#' @return DataFrame contenant les informations sur les arrêts détectés
detect_stops <- function(traj, speed_threshold = 1, duration_threshold = 4) {
  # Tri des points par ordre chronologique
  traj <- traj %>% arrange(BaseDateTime)
  
  # Identification des points où le navire est à l'arrêt (vitesse < seuil)
  stopped_points <- traj %>% 
    mutate(stopped = SOG < speed_threshold) %>%
    mutate(stop_group = cumsum(stopped != lag(stopped, default = first(stopped))))
  
  # Calcul des durées d'arrêt et autres métriques
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
    filter(duration >= duration_threshold)  # Filtre sur la durée minimale
  
  return(stop_durations)
}

#' Prépare les données des navires pour la visualisation
#'
#' @param data DataFrame contenant les données brutes des navires
#' @param max_vessels Nombre maximum de navires à inclure (défaut: 142)
#' @return DataFrame filtré et enrichi avec des informations supplémentaires
prepare_vessel_data <- function(data, max_vessels = 142) {
  # Sélection des navires à inclure (limité à max_vessels)
  vessels_to_plot <- unique(data$VesselName)[1:min(max_vessels, length(unique(data$VesselName)))]
  
  # Filtrage et enrichissement des données
  data_filtered <- data %>%
    filter(VesselName %in% vessels_to_plot) %>%
    mutate(VesselType = ifelse(is.na(VesselType), "Inconnu", as.character(VesselType))) %>%
    group_by(VesselName) %>%
    mutate(
      is_cargo = between(as.numeric(VesselType), 70, 89),  # Identification des cargos
      draft_change_total = ifelse(is_cargo, max(Draft, na.rm = TRUE) - min(Draft, na.rm = TRUE), NA),
      loading_status = case_when(  # Classification du statut de chargement
        !is_cargo ~ "Non applicable",
        draft_change_total > 2 ~ "Chargement important (Δ > 2m)",
        draft_change_total > 0.5 ~ "Chargement modéré (Δ > 0.5m)",
        draft_change_total > 0 ~ "Chargement léger",
        TRUE ~ "Pas de chargement détecté"
      ),
      is_loaded = is_cargo & draft_change_total > 0.5,  # Navire chargé ou non
      mean_draft = ifelse(is_cargo, mean(Draft, na.rm = TRUE), NA)  # Tirant d'eau moyen
    ) %>%
    ungroup()

  return(data_filtered)
}

#' Détecte les zones portuaires à partir des trajectoires des navires
#'
#' @param data_filtered DataFrame contenant les données préparées des navires
#' @return DataFrame contenant les zones portuaires détectées
detect_port_zones <- function(data_filtered) {
  port_zones <- data.frame()
  cargo_vessels <- unique(data_filtered$VesselName[data_filtered$is_cargo])

  if(length(cargo_vessels) > 0) {
    # Analyse des trajectoires de chaque cargo
    for (vessel in cargo_vessels) {
      traj <- data_filtered %>% 
        filter(VesselName == vessel) %>%
        arrange(BaseDateTime)

      # Détection des arrêts
      stops <- detect_stops(traj)

      if (nrow(stops) > 0) {
        stops <- stops %>%
          mutate(
            port_activity = case_when(  # Classification des activités portuaires
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

#' Regroupe les zones portuaires similaires en clusters
#'
#' @param port_zones DataFrame contenant les zones portuaires détectées
#' @return Liste contenant deux éléments:
#'          - clustered_zones: les zones portuaires regroupées
#'          - port_zones_sf: les zones portuaires en format sf
cluster_port_zones <- function(port_zones) {
  if (nrow(port_zones) == 0) return(data.frame())

  # Conversion en objet spatial pour le clustering
  port_zones_sf <- st_as_sf(port_zones, coords = c("mean_lon", "mean_lat"),
                            crs = 4326)
  clustered <- dbscan(st_coordinates(port_zones_sf), eps = 0.4, minPts = 3)

  # Regroupement des zones similaires
  clustered_zones <- port_zones %>%
    mutate(cluster = clustered$cluster) %>%
    group_by(cluster) %>%
    mutate(n_vessels = n_distinct(VesselName)) %>%
    ungroup() %>%
    filter(cluster > 0 & n_vessels >= 3) %>%  # Filtre des clusters significatifs
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
    filter(activities != "")  # Filtre des zones sans activité

  return(list(clustered_zones = clustered_zones, port_zones_sf = port_zones_sf))
}

#' Ajoute les trajectoires des navires à la carte Leaflet
#'
#' @param map Objet Leaflet auquel ajouter les trajectoires
#' @param data_filtered DataFrame contenant les données préparées des navires
#' @param type_palette Palette de couleurs pour les types de navires
#' @return Objet Leaflet mis à jour
add_trajectories_to_map <- function(map, data_filtered, type_palette) {
  vessel_types <- unique(data_filtered$VesselType)

  # Ajout des trajectoires par type de navire
  for (vessel_type in vessel_types) {
    type_data <- data_filtered %>% filter(VesselType == vessel_type)
    for (vessel_name in unique(type_data$VesselName)) {
      traj <- type_data %>% filter(VesselName == vessel_name) %>%
        arrange(BaseDateTime)
      if (nrow(traj) > 1) {
        # Préparation des informations du navire
        vessel_info <- traj %>% slice(1) %>%
          select(VesselName, VesselType, Length, Width, is_cargo, is_loaded,
                 loading_status, mean_draft)

        # Création du contenu du popup
        popup_content <- create_vessel_popup(vessel_info, traj)

        # Définition des groupes pour le contrôle des couches
        groups <- c("Tous les bateaux", vessel_type)
        if (vessel_info$is_cargo) groups <- c(groups, "Cargos & Tankers")
        if (vessel_info$is_loaded) groups <- c(groups, "Chargé")

        # Ajout des trajectoires à la carte
        map <- map %>%
          addPolylines(
            lng = traj$LON, lat = traj$LAT, 
            color = type_palette(vessel_type),
            weight = 2, opacity = 0.7, 
            group = groups,
            popup = popup_content
          ) %>%
          # Ajout d'une version épaisse pour les routes principales
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

#' Crée le contenu HTML des popups pour les navires
#'
#' @param vessel_info DataFrame contenant les informations du navire
#' @param traj DataFrame contenant la trajectoire du navire
#' @return Chaîne HTML formatée pour le popup
create_vessel_popup <- function(vessel_info, traj) {
  popup_content <- paste(
    "<h2>Bateau: ", vessel_info$VesselName, "</h2>Type: ",
    vessel_info$VesselType, ifelse(vessel_info$VesselType < 70, " - Passenger",
                                   ifelse(vessel_info$VesselType < 80,
                                          " - Cargo", " - Tanker")),
    "<br>Longueur (m): ", round(vessel_info$Length, 2),
    "<br>Largeur (m): ", round(vessel_info$Width, 2)
  )

  # Ajout des informations spécifiques aux cargos
  if (vessel_info$is_cargo) {
    popup_content <- paste0(
      popup_content,
      "<br>Tirant d'eau moyen (m): ", round(vessel_info$mean_draft, 2),
      "<br>Statut de chargement: ", vessel_info$loading_status
    )
  }

  # Ajout des informations sur la trajectoire
  popup_content <- paste0(
    popup_content,
    "<hr>Distance totale (km): ",
    round(sum(sqrt((diff(traj$LON))^2 + (diff(traj$LAT))^2),
              na.rm = TRUE) * 111, 2),
    "<br>Vitesse moyenne (nœuds): ", round(mean(traj$SOG, na.rm = TRUE), 2),
    "<br>Vitesse maximale (nœuds): ", round(max(traj$SOG, na.rm = TRUE), 2),
    "<br>Date de début: ", min(traj$BaseDateTime), "<br>Date de fin: ",
    max(traj$BaseDateTime)
  )

  return(popup_content)
}

#' Ajoute les zones portuaires à la carte Leaflet
#'
#' @param map Objet Leaflet auquel ajouter les zones portuaires
#' @param port_data Liste contenant les données des zones portuaires
#' @return Objet Leaflet mis à jour
add_port_zones_to_map <- function(map, port_data) {
  if (nrow(port_data$clustered_zones) == 0) return(map)

  # Ajout des zones portuaires clusterisées
  map <- map %>%
    addCircleMarkers(
      data = port_data$clustered_zones,
      lng = ~mean_lon, lat = ~mean_lat,
      radius = ~sqrt(n_operations)*3,  # Taille proportionnelle au nombre d'opérations
      color = "#3f3f3f",
      fillOpacity = 0.7,
      stroke = TRUE,
      weight = 1,
      group = "Zones de port",
      popup = ~paste("<h3>Zone Portuaire</h3>",
        "Nombre de bateaux: ", n_vessels,
        "<br>Opérations: ", n_operations, "<br>Activités: ", activities,
        "<br>Bateaux: ", substr(vessels, 1, 5), "..."
      )
    )

  # Ajout des zones portuaires individuelles
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
                        ifelse(grepl("Déchargement", port_activity),
                               "Déchargement", "Arrêt simple")),
        popup = ~paste(
          "<h3>Activité portuaire</h3>",
          "Bateau: ", VesselName,
          "<br>Type: ", VesselType,
          "<br>Activité: ", port_activity,
          "<br>Durée: ", round(duration, 1), "heures",
          "<br>Δ tirant d'eau: ", round(draft_change, 2), "m"
        )
      )
  }
  
  return(map)
}

#' Ajoute les légendes à la carte Leaflet
#'
#' @param map Objet Leaflet auquel ajouter les légendes
#' @param vessel_types Vecteur des types de navires présents
#' @param port_zones_exist Booléen indiquant si des zones portuaires existent
#' @return Objet Leaflet mis à jour
add_map_legends <- function(map, vessel_types, port_zones_exist = FALSE) {
  type_palette <- colorFactor(palette = "Set1", domain = vessel_types)

  # Légende pour les types de navires
  map <- map %>%
    addLegend(position = "bottomleft", pal = type_palette, 
              values = vessel_types, title = "Types de bateaux", opacity = 0.7,
              group = c(vessel_types, "Tous les bateaux", "Cargos & Tankers",
                        "Chargés")) %>%
    # Légende pour les routes principales
    addLegend(position = "bottomleft",
              colors = c("red"),
              labels = c("Routes principales"),
              title = "Routes", opacity = 0.7, group = "Routes principales") %>%
    # Légende pour les zones portuaires
    addLegend(position = "bottomleft",
              colors = "#3f3f3f",
              labels = c("Zones portuaires"),
              title = "Zones portuaires",
              opacity = 0.7, group = "Zones de port") %>%
    # Légende pour les activités portuaires spécifiques
    addLegend(position = "bottomleft",
              colors = c("blue", "red", "#ffff86"), 
              labels = c("Déchargement", "Chargement", "Arrêt simple"),
              title = "Type d'arret",
              opacity = 0.7, group = c("Chargement", "Déchargement",
                                       "Arrêt simple"))

  return(map)
}

#' Fonction principale pour créer la carte interactive
#'
#' @param data DataFrame contenant les données brutes des navires
#' @param max_vessels Nombre maximum de navires à inclure (défaut: 142)
#' @return Objet Leaflet contenant la carte interactive
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
    addTiles() %>%  # Ajout des tuiles de base
    setView(lng = mean(data_filtered$LON, na.rm = TRUE), lat = mean(data_filtered$LAT, na.rm = TRUE), zoom = 6) %>%
    addLayersControl(  # Contrôle des couches
      overlayGroups = c("Tous les bateaux", vessel_types, "Cargos & Tankers", "Chargé", 
                       "Zones de port", "Chargement", "Déchargement", "Arrêt simple", "Routes principales"),
      options = layersControlOptions(collapsed = FALSE),
      position = "topright"
    ) %>%
    hideGroup(c(vessel_types, "Cargos & Tankers", "Chargé", "Chargement", "Déchargement", "Arrêt simple", "Routes principales"))
  
  # Ajout des éléments à la carte
  map <- add_trajectories_to_map(map, data_filtered, type_palette)
  map <- add_port_zones_to_map(map, port_data)
  map <- add_map_legends(map, vessel_types, nrow(port_data$clustered_zones) > 0)
  
  return(map)
}

#' Charge et prépare les données à partir d'un fichier CSV
#'
#' @param file_path Chemin vers le fichier CSV contenant les données
#' @return DataFrame préparé avec les données chargées
load_and_prepare_data <- function(file_path) {
  data <- read.csv(file_path)
  data$BaseDateTime <- as.POSIXct(data$BaseDateTime, format="%Y-%m-%d %H:%M:%S")
  data <- data %>% arrange(VesselName, BaseDateTime)  # Tri par nom de navire et date
  return(data)
}

#' Fonction principale pour exécuter tout le processus
main_interactive_map <- function() {
  print("Chargement des données...")
  vessel_data <- load_and_prepare_data("data/export_IA.csv")
  
  print("Génération de la carte interactive...")
  interactive_map <- create_interactive_map(vessel_data)
  
  print("Sauvegarde de la carte...")
  saveWidget(interactive_map, "map/interactive_map.html", selfcontained = TRUE)
  
  print("Carte sauvegardée.")
}

# Exécution du programme (décommenter pour lancer)
main_interactive_map()