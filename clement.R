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
# Notes        : Todo [reprendre partie 1 de laure et adapter à mon code;
#              :       Modifier clustering de port pour zones plus grandes;]
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

# Lire le fichier CSV
data <- read.csv("data/vessel-total-clean.csv")
print(dim(data))

# Statistiques descriptives univariées
print(summary(data))
print(names(data))
str(data)

# Conversion des colonnes quantitatives en numérique
data$LAT <- as.numeric(data$LAT)
data$LON <- as.numeric(data$LON)
data$SOG <- as.numeric(data$SOG)
data$COG <- as.numeric(data$COG)
data$Heading <- as.numeric(data$Heading)
data$Length <- as.numeric(data$Length)
data$Width <- as.numeric(data$Width)
data$Draft <- as.numeric(data$Draft)

# Définir les colonnes numériques qui peuvent prendre la médiane
colonnes_numeriques <- c("SOG", "COG", "Heading", "Length", "Width", "Draft")

# Traitement des valeurs manquantes
print("Valeurs manquantes :")
data[data == "\\N"] <- NA
print(sum(is.na(data)))

n <- nrow(data)
for (i in colnames(data)) {
    val_mq <- sum(is.na(data[[i]]))
    pourcentage <- val_mq/n
    
    if(pourcentage < 0.05) {
        data <- data[!is.na(data[[i]]), ]
        n <- nrow(data)
    } else {
        if(i %in% colonnes_numeriques) {
            med <- median(data[[i]], na.rm = TRUE)
            data[[i]][is.na(data[[i]])] <- med
        } else {
            data[[i]][is.na(data[[i]])] <- "inconnu"
        }
    }
}

print("Nombre de lignes et colonnes après traitement des NA :")
print(dim(data))

# Traitement des valeurs aberrantes
print("Valeurs aberrantes")
for(i in colonnes_numeriques) {
    q1 <- quantile(data[[i]], 0.25)
    q3 <- quantile(data[[i]], 0.75)
    iqr <- q3 - q1
    inf <- q1 - 1.5 * iqr
    sup <- q3 + 1.5 * iqr
    
    outliers <- data[[i]] < inf | data[[i]] > sup
    
    if(sum(outliers, na.rm = TRUE) / nrow(data) < 0.03) {
        data <- data[!outliers, ]
    } else {
        data[[i]][outliers] <- median(data[[i]], na.rm = TRUE)
    }
}

print("Nombre de lignes et colonnes après traitement des valeurs aberrantes :")
print(dim(data))

# Traitement des doublons
print("Nombre de doublons :")
print(sum(duplicated(data)))
data <- unique(data)

print("Nombre final de lignes et colonnes :")
print(dim(data))

# Sauvegarder les données nettoyées
write.csv(data, "data/vessel-cleaned.csv", row.names = FALSE)
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
    theme_light() +
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


# Calls
print("Fonctionnalité 3: Carte interactive")

vessel_data <- read.csv("data/vessel-cleaned.csv")
vessel_data$BaseDateTime <- as.POSIXct(vessel_data$BaseDateTime, format="%Y-%m-%d %H:%M:%S")
vessel_data <- vessel_data %>% arrange(VesselName, BaseDateTime)

print("Génération de la carte interactive...")
# Génération de la carte interactive
interactive_map <- create_interactive_map(vessel_data)
saveWidget(interactive_map, "outputs/interactive_map.html", selfcontained = TRUE)

print("Terminé.")
