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
# R Version    : 4.4.3
# Dependencies : readr, dplyr, ggplot2, lubridate, viridis, RColorBrewer,
# Notes        : []
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
library(corrplot)
library(randomForest)
library(caret)
library(reshape2)


####################################################
# Fonctionnalité 1: Nettoyage et traintement des données #
####################################################
print("Fonctionnalité 1: Nettoyage et traitement des données de trafic maritime")

# Fonction pour lire les données
read_data <- function(file_path) {
  data <- read.csv(file_path)
  print(paste("Dimensions initiales des données :", dim(data)[1], "lignes x", dim(data)[2], "colonnes"))
  return(data)
}

# Fonction pour afficher les statistiques descriptives
display_basic_stats <- function(data) {
  print("Statistiques descriptives :")
  print(summary(data))
  print("Noms des colonnes :")
  print(names(data))
  print("Structure des données :")
  str(data)
}

# Fonction pour convertir les colonnes en numérique
convert_to_numeric <- function(data, columns) {
  for(col in columns) {
    data[[col]] <- as.numeric(data[[col]])
  }
  return(data)
}

# Fonction pour traiter les valeurs manquantes
handle_missing_values <- function(data, numeric_columns) {
  print("Traitement des valeurs manquantes...")
  data[data == "\\N"] <- NA
  print(paste("Total de valeurs manquantes :", sum(is.na(data))))
  
  n <- nrow(data)
  for (col in colnames(data)) {
    val_mq <- sum(is.na(data[[col]]))
    pourcentage <- val_mq/n
    
    if(pourcentage < 0.05) {
      data <- data[!is.na(data[[col]]), ]
      n <- nrow(data)
    } else {
      if(col %in% numeric_columns) {
        med <- median(data[[col]], na.rm = TRUE)
        data[[col]][is.na(data[[col]])] <- med
      } else {
        data[[col]][is.na(data[[col]])] <- "inconnu"
      }
    }
  }
  
  print(paste("Dimensions après traitement des NA :", dim(data)[1], "lignes x", dim(data)[2], "colonnes"))
  return(data)
}

# Fonction pour traiter les valeurs aberrantes
handle_outliers <- function(data, numeric_columns) {
  print("Traitement des valeurs aberrantes...")
  
  for(col in numeric_columns) {
    q1 <- quantile(data[[col]], 0.25)
    q3 <- quantile(data[[col]], 0.75)
    iqr <- q3 - q1
    inf <- q1 - 1.5 * iqr
    sup <- q3 + 1.5 * iqr
    
    outliers <- data[[col]] < inf | data[[col]] > sup
    
    if(sum(outliers, na.rm = TRUE) / nrow(data) < 0.03) {
      data <- data[!outliers, ]
    } else {
      data[[col]][outliers] <- median(data[[col]], na.rm = TRUE)
    }
  }
  
  print(paste("Dimensions après traitement des valeurs aberrantes :", dim(data)[1], "lignes x", dim(data)[2], "colonnes"))
  return(data)
}

# Fonction pour traiter les doublons
handle_duplicates <- function(data) {
  print("Traitement des doublons...")
  print(paste("Nombre de doublons trouvés :", sum(duplicated(data))))
  data <- unique(data)
  print(paste("Dimensions finales :", dim(data)[1], "lignes x", dim(data)[2], "colonnes"))
  return(data)
}

# Fonction pour sauvegarder les données nettoyées
save_clean_data <- function(data, file_path) {
  write.csv(data, file_path, row.names = FALSE)
  print(paste("Nettoyage des données terminé. Données sauvegardées sous :", file_path))
}

# Définition des colonnes numériques
numeric_columns <- c("SOG", "COG", "Heading", "Length", "Width", "Draft")

# Pipeline principal de nettoyage des données
main_data_cleaning <- function() {
  # Étape 1: Lecture des données
  data <- read_data("data/vessel-total-clean.csv")
  
  # Étape 2: Affichage des statistiques de base
  display_basic_stats(data)
  
  # Étape 3: Conversion des colonnes numériques
  data <- convert_to_numeric(data, c("LAT", "LON", numeric_columns))
  
  # Étape 4: Traitement des valeurs manquantes
  data <- handle_missing_values(data, numeric_columns)
  
  # Étape 5: Traitement des valeurs aberrantes
  data <- handle_outliers(data, numeric_columns)
  
  # Étape 6: Traitement des doublons
  data <- handle_duplicates(data)
  
  # Étape 7: Sauvegarde des données nettoyées
  save_clean_data(data, "data/vessel-cleaned.csv")
}

# Exécution du pipeline
main_data_cleaning()


####################################################
# Fonctionnalité 2: Graphiques optimisés pour l'analyse des données de bateaux #
####################################################

print("Fonctionnalité 2: Graphiques pour l'analyse des données de bateaux")

# Fonction pour charger et préparer les données
load_and_prepare_data <- function(file_path) {
  data <- read.csv(file_path)
  
  # Préparation des données
  data$BaseDateTime <- as.POSIXct(data$BaseDateTime, format="%Y-%m-%d %H:%M:%S")
  data$Hour <- hour(data$BaseDateTime)
  data$Date <- as.Date(data$BaseDateTime)
  data$Length_num <- as.numeric(as.character(data$Length))
  data$Width_num <- as.numeric(as.character(data$Width))
  
  return(data)
}

# Définition du thème personnalisé
get_marine_theme <- function() {
  theme_minimal() +
    theme(
      plot.title = element_text(size = 14, face = "bold", hjust = 0.5),
      plot.subtitle = element_text(size = 11, hjust = 0.5, color = "gray60"),
      axis.title = element_text(size = 12),
      legend.title = element_text(size = 11, face = "bold"),
      panel.grid.minor = element_blank(),
      plot.background = element_rect(fill = "white", color = NA)
    )
}

# Fonction pour créer un diagramme polaire
create_polar_plot <- function(data, var, title, color) {
  ggplot(data, aes(x = {{var}})) +
    geom_histogram(binwidth = 15, fill = color, color = "white", alpha = 0.8) +
    coord_polar(start = -pi/16) +
    scale_x_continuous(limits = c(0, 360), breaks = seq(0, 360, by = 45)) +
    labs(title = title, x = "", y = "") +
    theme_light() +
    theme(
      axis.text.y = element_blank(),
      panel.grid.major.y = element_blank(),
      plot.title = element_text(hjust = 0.5, face = "bold")
    )
}

# Fonction pour créer le graphique de répartition par type de bateau
plot_vessel_type_distribution <- function(data, theme) {
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
    theme +
    theme(axis.text.x = element_text(angle = 0))
}

# Fonction pour créer le graphique longueur/largeur
plot_length_width <- function(data, theme) {
  length_width_clean <- data %>%
    filter(!is.na(Length_num) & !is.na(Width_num) & 
           Length_num > 0 & Width_num > 0 & 
           Length_num < 500 & Width_num < 100) %>%
    group_by(VesselType) %>%
    filter(n() >= 50) %>%
    ungroup()
  
  ggplot(length_width_clean, aes(x = Length_num, y = Width_num, color = as.factor(VesselType))) +
    geom_point(alpha = 0.6, size = 1.5) +
    geom_smooth(method = "lm", se = FALSE, linetype = "dashed", size = 0.8) +
    scale_color_viridis_d(name = "Type de\nbateau") +
    labs(title = "Relation entre longueur et largeur des bateaux",
         subtitle = "Corrélation par type de navire avec tendances",
         x = "Longueur (mètres)",
         y = "Largeur (mètres)") +
    theme +
    theme(legend.position = "right") +
    facet_wrap(~VesselType, scales = "free", ncol = 3)
}

# Fonction pour créer l'histogramme des vitesses
plot_speed_distribution <- function(data) {
  ggplot(data, aes(x = SOG)) +
    geom_histogram(bins = 30, fill = "lightblue", color = "darkblue", alpha = 0.7) +
    labs(title = "Distribution des vitesses (SOG)",
         x = "Vitesse sur le fond (nœuds)", y = "Fréquence") +
    geom_vline(aes(xintercept = mean(SOG, na.rm = TRUE)),
               color = "red", linetype = "dashed", size = 1) +
    annotate("text", x = mean(data$SOG, na.rm = TRUE) + 2, 
             y = max(table(cut(data$SOG, 30))) * 0.8,
             label = paste("Moyenne:", round(mean(data$SOG, na.rm = TRUE), 1), "nœuds"),
             color = "red")
}

# Fonction pour créer le camembert des statuts
plot_status_pie <- function(data) {
  statuts_count <- table(data$Status)
  statuts_data <- data.frame(
    Status = names(statuts_count),
    n = as.numeric(statuts_count),
    stringsAsFactors = FALSE
  )
  statuts_data$pourcentage <- statuts_data$n / sum(statuts_data$n) * 100
  
  ggplot(statuts_data, aes(x = "", y = n, fill = Status)) +
    geom_bar(stat = "identity", width = 1) +
    coord_polar("y", start = 0) +
    labs(title = "Répartition des statuts des navires") +
    theme_void() +
    geom_text(aes(label = paste0(round(pourcentage, 1), "%")), 
              position = position_stack(vjust = 0.5),
              size = 3) +
    theme(legend.position = "right",
          legend.text = element_text(size = 8))
}

# Fonction pour créer la carte de densité
plot_density_map <- function(data) {
  ggplot(data, aes(x = LON, y = LAT)) +
    geom_point(alpha = 0.4, size = 0.5, color = "steelblue") +
    stat_density_2d(color = "red", size = 0.8, bins = 10) +
    labs(title = "Carte de densité avec contours",
         subtitle = "Lignes de niveau de concentration des navires",
         x = "Longitude", y = "Latitude") +
    theme_minimal()
}

# Fonction pour afficher les statistiques résumées
display_summary_stats <- function(data) {
  summary_stats <- data %>%
    summarise(
      total_vessels = n(),
      unique_types = n_distinct(VesselType),
      avg_speed = round(mean(SOG, na.rm = TRUE), 1),
      max_speed = round(max(SOG, na.rm = TRUE), 1),
      avg_length = round(mean(Length_num, na.rm = TRUE), 1),
      date_range = paste(min(Date, na.rm = TRUE), "à", max(Date, na.rm = TRUE))
    )
  
  cat("=== RÉSUMÉ DE L'ANALYSE ===\n")
  cat("Nombre total d'observations:", summary_stats$total_vessels, "\n")
  cat("Types de navires uniques:", summary_stats$unique_types, "\n")
  cat("Vitesse moyenne:", summary_stats$avg_speed, "nœuds\n")
  cat("Vitesse maximale:", summary_stats$max_speed, "nœuds\n")
  cat("Longueur moyenne:", summary_stats$avg_length, "mètres\n")
  cat("Période d'observation:", summary_stats$date_range, "\n")
  cat("========================\n")
}

# Fonction principale pour générer tous les graphiques
generate_all_plots <- function() {
  # Chargement des données
  data <- load_and_prepare_data("data/vessel-cleaned.csv")
  
  # Récupération du thème
  marine_theme <- get_marine_theme()
  
  # Création des graphiques polaires combinés
  p1 <- create_polar_plot(data, COG, "Distribution des directions (COG)", "#4e79a7")
  p2 <- create_polar_plot(data, Heading, "Distribution des caps (Heading)", "#e15759")
  combined_polar <- plot_grid(p1, p2, ncol = 2)
  ggsave("plots/combined_direction_plots.png", combined_polar, width = 12, height = 6)
  
  # Graphique de répartition par type
  vessel_type_plot <- plot_vessel_type_distribution(data, marine_theme)
  ggsave("plots/vessel_type_distribution.png", vessel_type_plot, width = 12, height = 8, dpi = 300)
  
  # Graphique longueur/largeur
  length_width_plot <- plot_length_width(data, marine_theme)
  ggsave("plots/length_vs_width_by_type.png", length_width_plot, width = 15, height = 12, dpi = 300)
  
  # Histogramme des vitesses
  speed_plot <- plot_speed_distribution(data)
  ggsave("plots/histogramme_vitesses.png", speed_plot, width = 10, height = 6, dpi = 300, bg = "white")
  
  # Camembert des statuts
  status_pie <- plot_status_pie(data)
  ggsave("plots/repartition_statuts.png", status_pie, width = 12, height = 8, dpi = 300, bg = "white")
  
  # Carte de densité
  density_map <- plot_density_map(data)
  ggsave("plots/heatmap_contours.png", density_map, width = 12, height = 8, dpi = 300, bg = "white")
  
  # Affichage des statistiques
  display_summary_stats(data)
  
  print("Tous les graphiques ont été générés avec succès dans le dossier 'plots/'")
}

# Exécution de la fonction principale
generate_all_plots()


####################################################
# Fonctionnalité 3: Carte interactive #
####################################################

print("Fonctionnalité 3: Carte interactive")

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
  
  return(port_zones)
}

# Fonction pour regrouper les zones portuaires similaires
cluster_port_zones <- function(port_zones) {
  if (nrow(port_zones) == 0) return(data.frame())
  
  port_zones_sf <- st_as_sf(port_zones, coords = c("mean_lon", "mean_lat"), crs = 4326)
  clustered <- dbscan(st_coordinates(port_zones_sf), eps = 0.15, minPts = 2)
  
  clustered_zones <- port_zones %>%
    mutate(cluster = clustered$cluster) %>%
    group_by(cluster) %>%
    mutate(n_vessels = n_distinct(VesselName)) %>%
    ungroup() %>%
    filter(cluster > 0 & n_vessels >= 2) %>%
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
      traj <- type_data %>% filter(VesselName == vessel_name) %>% arrange(BaseDateTime)
      if (nrow(traj) > 1) {
        vessel_info <- traj %>% 
          slice(1) %>% 
          select(VesselName, VesselType, Length, Width, is_cargo, is_loaded, loading_status, mean_draft)
        
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
  
  if (nrow(port_data$port_zones_sf) > 0) {
    port_palette <- colorFactor(
      palette = c("blue", "red", "darkblue", "darkred", "gray"), 
      domain = c("Chargement", "Chargement majeur", "Déchargement", "Déchargement majeur", "Arrêt simple")
    )
    
    map <- map %>%
      addCircleMarkers(
        data = port_data$port_zones_sf,
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
                colors = c("blue", "red"), 
                labels = c("Déchargement ou Arrêt", "Chargement"),
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
                       "Zones de port", "Chargement", "Déchargement", "Routes principales"),
      options = layersControlOptions(collapsed = FALSE),
      position = "topright"
    ) %>%
    hideGroup(c(vessel_types, "Cargos", "Chargé", "Chargement", "Déchargement"))
  
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
  vessel_data <- load_and_prepare_data("data/vessel-cleaned.csv")
  
  print("Génération de la carte interactive...")
  interactive_map <- create_interactive_map(vessel_data)
  
  print("Sauvegarde de la carte...")
  saveWidget(interactive_map, "outputs/interactive_map.html", selfcontained = TRUE)
  
  print("Terminé.")
}

# Exécution du programme
main_interactive_map()
