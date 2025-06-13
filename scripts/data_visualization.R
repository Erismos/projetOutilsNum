############################################################
# Titre      : Visualisation des Données de l'AIS
# Fichier    : data_visualization.R
# Description: Ce script R permet de charger, analyser et 
#              générer une série de visualisations graphiques
#              à partir d’un jeu de données sur les navires
#              (vitesse, dimensions, type, statut, etc.).
#
# Auteurs     : Gabriel Boucneau & Laure Warlop & Clément Auvray
# Date       : Juin 2025
# Données    : data/export_IA.csv
# Dépendances: ggplot2, dplyr, lubridate, cowplot, viridis
# Sorties    : Graphiques au format PNG dans le dossier plots/ :
#              - Graphiques polaires (COG, Heading)
#              - Répartition par type de navire
#              - Corrélation longueur/largeur
#              - Histogramme des vitesses
#              - Diagramme circulaire des statuts
#              - Carte de densité géographique
############################################################

####################################################
# Fonctionnalité 2: Graphiques pour l'analyse des données de bateaux #
####################################################

# Chargement des bibliothèques nécessaires
library(ggplot2)
library(dplyr)
library(lubridate)
library(cowplot)
library(viridis)

# Fonction pour charger et préparer les données
load_and_prepare_data <- function(file_path) {
  data <- read.csv(file_path)
  
  # Préparation des données
  data$BaseDateTime <- as.POSIXct(data$BaseDateTime, format="%Y-%m-%d %H:%M:%S")
  data$Hour <- hour(data$BaseDateTime)
  data$Date <- as.Date(data$BaseDateTime)
  data$Length <- as.numeric(as.character(data$Length))
  data$Width <- as.numeric(as.character(data$Width))
  
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
    filter(!is.na(Length) & !is.na(Width) & 
           Length > 0 & Width > 0 & 
           Length < 500 & Width < 100) %>%
    group_by(VesselType) %>%
    filter(n() >= 50) %>%
    ungroup()
  
  ggplot(length_width_clean, aes(x = Length, y = Width, color = as.factor(VesselType))) +
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


# Fonction principale pour générer tous les graphiques
generate_all_plots <- function() {
  # Chargement des données
  print("Chargement des données...")
  data <- load_and_prepare_data("data/export_IA.csv")
  
  # Récupération du thème
  marine_theme <- get_marine_theme()
  
  print("Génération des graphiques...")
  # Création des graphiques polaires combinés
  p1 <- create_polar_plot(data, COG, "Distribution des directions (COG)", "#4e79a7")
  p2 <- create_polar_plot(data, Heading, "Distribution des caps (Heading)", "#e15759")
  combined_polar <- plot_grid(p1, p2, ncol = 2)
  ggsave("plots/combined_direction_plots.png", combined_polar, width = 12, height = 6)
  print("Graphique 1/6 : Graphiques polaires (COG et Heading) générés.")

  # Graphique de répartition par type
  vessel_type_plot <- plot_vessel_type_distribution(data, marine_theme)
  ggsave("plots/vessel_type_distribution.png", vessel_type_plot, width = 12, height = 8, dpi = 300)
  print("Graphique 2/6 : Répartition par type de bateau générée.")

  # Graphique longueur/largeur
  length_width_plot <- plot_length_width(data, marine_theme)
  ggsave("plots/length_vs_width_by_type.png", length_width_plot, width = 15, height = 12, dpi = 300)
  print("Graphique 3/6 : Relation longueur/largeur des bateaux générée.")
  
  # Histogramme des vitesses
  speed_plot <- plot_speed_distribution(data)
  ggsave("plots/histogramme_vitesses.png", speed_plot, width = 10, height = 6, dpi = 300, bg = "white")
  print("Graphique 4/6 : Histogramme des vitesses généré.")
  
  # Camembert des statuts
  status_pie <- plot_status_pie(data)
  ggsave("plots/repartition_statuts.png", status_pie, width = 12, height = 8, dpi = 300, bg = "white")
  print("Graphique 5/6 : Camembert des statuts des navires généré.")
  
  # Carte de densité
  density_map <- plot_density_map(data)
  ggsave("plots/heatmap_contours.png", density_map, width = 12, height = 8, dpi = 300, bg = "white")
  print("Graphique 6/6 : Carte de densité géographique générée.")
  
  print("Tous les graphiques ont été générés avec succès dans le dossier 'plots/'")
}

# Exécution de la fonction principale
# generate_all_plots()
