# clement file

# Charger les bibliothèques nécessaires
library(readr)

# Lire le fichier CSV en remplaçant les "\\N" par NA
data <- read_csv("data/vessel-total-clean.csv", na = "\\N")

print(dim(data))  # Afficher les dimensions du jeu de données
# Calculer le pourcentage de NA par colonne
na_percent <- sapply(data, function(col) mean(is.na(col)))

# Sélectionner les colonnes avec moins de 5% de NA
cols_to_check <- names(na_percent[na_percent < 0.05])

# Supprimer les lignes contenant des NA dans ces colonnes
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

# Fonction pour remplacer les NA par la moyenne de la colonne
replace_na_with_mean <- function(x) {
  if (is.numeric(x)) {
    x[is.na(x)] <- mean(x, na.rm = TRUE)
  }
  return(x)
}

# Appliquer cette fonction aux colonnes numériques
data_final <- data_cleaned %>% 
    mutate(across(where(is.numeric), replace_outliers_with_mean)) %>%
    mutate(across(where(is.numeric), replace_na_with_mean))

# Afficher un aperçu
print(head(data_final))
print(summary(data_final))

write.csv(data_final, "data/vessel-cleaned.csv", row.names = FALSE)
# Save the cleaned data for further analysis
print("Data cleaning complete. Cleaned data saved to 'data/vessel-cleaned.csv'.")


####################################################
# Graphiques optimisés pour l'analyse des données de bateaux #
####################################################

# Chargement des librairies
library(ggplot2)
library(dplyr)
library(lubridate)
library(viridis)
library(RColorBrewer)
library(maps)
library(mapdata)
library(ggmap)

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

ggsave("figures/combined_direction_plots.png", combined_polar, width = 12, height = 6)



# Détermination des limites de la carte basées sur les données
bbox <- c(
  left = min(data$LON, na.rm = TRUE) - 1,
  bottom = min(data$LAT, na.rm = TRUE) - 1,
  right = max(data$LON, na.rm = TRUE) + 1,
  top = max(data$LAT, na.rm = TRUE) + 1
)

# Création de la carte de base
base_map <- ggplot() +
  geom_sf(data = world, fill = "gray80", color = "gray60") +
  coord_sf(xlim = c(bbox["left"], bbox["right"]), 
           ylim = c(bbox["bottom"], bbox["top"])) +
  theme_minimal()

# Heatmap superposée
heatmap_plot <- base_map +
  stat_density2d(
    data = data,
    aes(x = LON, y = LAT, fill = ..level.., alpha = ..level..),
    geom = "polygon",
    bins = 50
  ) +
  scale_fill_viridis_c(option = "plasma", name = "Densité") +
  scale_alpha_continuous(range = c(0.1, 0.7), guide = "none") +
  labs(title = "Densité du trafic maritime avec fond cartographique",
       subtitle = "Visualisation des zones à forte concentration de navires",
       x = "Longitude", y = "Latitude") +
  theme(
    legend.position = "right",
    plot.title = element_text(size = 14, face = "bold"),
    plot.subtitle = element_text(size = 10)
  )

ggsave("figures/improved_density_map.png", heatmap_plot, width = 12, height = 9)


# 1. RÉPARTITION DES BATEAUX PAR TYPE (amélioré)
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
ggsave("figures/vessel_type_distribution_enhanced.png", width = 12, height = 8, dpi = 300)


# 4. RELATION LONGUEUR/LARGEUR PAR TYPE (amélioré)
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
ggsave("figures/length_vs_width_by_type_enhanced.png", width = 15, height = 12, dpi = 300)

# 8. RÉSUMÉ STATISTIQUE VISUEL
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

print("Tous les graphiques ont été générés avec succès dans le dossier 'figures/'")
print("Résolution: 300 DPI pour impression haute qualité")


