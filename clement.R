# clement file


data <- read.csv(file = "data/vessel-total-clean.csv", header = TRUE)

print("Initial data dimensions:")
print(dim(data))
data[data == "\\N"] <- NA # Replace "\\N" with NA

# Check missing values
print("Checking for missing values...")
print(sum(is.na(data)))
data <- na.omit(data)


# Check for duplicates
print("Checking for duplicates...")
print(sum(duplicated(data)))
data <- unique(data)
print("Duplicates removed. New dimensions:")
print(dim(data))

# Convert numeric columns to numeric type
num_cols <- sapply(data, is.numeric)

# Remove outliers using IQR method
print("Removing outliers using IQR method...")
for (col in names(data)[num_cols]) {
  Q1 <- quantile(data[[col]], 0.25)
  Q3 <- quantile(data[[col]], 0.75)
  IQR <- Q3 - Q1
  lower <- Q1 - (1.5 * IQR )
  upper <- Q3 + (1.5 * IQR)
  data[[col]][data[[col]] < lower | data[[col]] > upper] <- NA
}
data <- na.omit(data)
print("Outliers removed. New dimensions:")
print(dim(data))


# Data summary
print(summary(data))

# Save the cleaned data
write.csv(data, "data/vessel-cleaned.csv", row.names = FALSE)
# Save the cleaned data for further analysis
print("Data cleaning complete. Cleaned data saved to 'data/vessel-cleaned.csv'.")

library(ggplot2)

data <- read.csv("data/vessel-cleaned.csv")

# Plotting the Distribution of Vessel Types
ggplot(data, aes(x = as.factor(VesselType))) +
  geom_bar(fill = "steelblue") +
  labs(title = "Répartition des bateaux par type",
       x = "Type de bateau",
       y = "Nombre de bateaux") +
  theme_minimal()
ggsave("figures/vessel_type_distribution.png", width = 8, height = 6)

# Plotting the Length of Vessels
ggplot(data, aes(x = Length)) +
  geom_histogram(binwidth = 10, fill = "darkgreen", color = "black") +
  labs(title = "Distribution des longueurs de bateaux",
       x = "Longueur (mètres)",
       y = "Nombre de bateaux") +
  theme_minimal()
ggsave("figures/vessel_length_distribution.png", width = 8, height = 6)

# Plotting the Width of Vessels
ggplot(data, aes(x = Width)) +
  geom_histogram(binwidth = 2, fill = "orange", color = "black") +
  labs(title = "Distribution des largeurs de bateaux",
       x = "Largeur (mètres)",
       y = "Nombre de bateaux") +
  theme_minimal()
ggsave("figures/vessel_width_distribution.png", width = 8, height = 6)

# Plotting the Density of Vessel Positions
ggplot(data, aes(x = LON, y = LAT)) +
  stat_density2d(aes(fill = ..level..), geom = "polygon") +
  scale_fill_viridis_c() +
  labs(title = "Carte de densité des positions de bateaux",
       x = "Longitude", y = "Latitude") +
  theme_minimal()
ggsave("figures/vessel_density_map.png", width = 8, height = 6)

# Plotting the Speed Over Ground (SOG) by Vessel Type
ggplot(data, aes(x = as.factor(VesselType), y = SOG)) +
  geom_boxplot(fill = "lightblue") +
  labs(title = "Vitesse (SOG) par type de bateau",
       x = "Type de bateau",
       y = "SOG (Speed Over Ground)") +
  theme_minimal()
ggsave("figures/vessel_sog_by_type.png", width = 8, height = 6)

# Plotting the distribution of vessel statuses
ggplot(data, aes(x = Status)) +
  geom_bar(fill = "darkred") +
  labs(title = "Répartition des statuts des bateaux",
       x = "Statut",
       y = "Nombre de bateaux") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))
ggsave("figures/vessel_status_distribution.png", width = 8, height = 6)



library(ggplot2)
library(dplyr)
library(lubridate)
library(viridisLite)
# Boat distribution by hour of the day
data$BaseDateTime <- as.POSIXct(data$BaseDateTime, format="%Y-%m-%d %H:%M:%S")
data$Hour <- hour(data$BaseDateTime)
data$Date <- as.Date(data$BaseDateTime)

ggplot(data, aes(x = Hour)) +
  geom_histogram(binwidth = 1, fill = "navy", color = "white") +
  labs(title = "Activité des bateaux par heure de la journée",
       x = "Heure (0-23)",
       y = "Nombre d'observations") +
  theme_minimal() +
  scale_x_continuous(breaks = seq(0, 23, 2))
ggsave("figures/vessel_activity_by_hour.png", width = 10, height = 6)

# Correlation between COG and SOG
# ggplot(data, aes(x = COG, y = SOG)) +
#   geom_point(alpha = 0.3, color = "darkblue") +
#   geom_smooth(method = "loess", color = "red") +
#   labs(title = "Relation entre la direction (COG) et la vitesse (SOG)",
#        x = "Course Over Ground (degrés)",
#        y = "Speed Over Ground (nœuds)") +
#   theme_minimal()
# ggsave("figures/sog_vs_cog_correlation.png", width = 10, height = 6)

# position heatmap
ggplot(data, aes(x = LON, y = LAT)) +
  geom_hex(bins = 50) +
  scale_fill_viridis_c(name = "Nombre\nd'observations") +
  labs(title = "Heatmap des positions de bateaux",
       x = "Longitude", y = "Latitude") +
  theme_minimal() +
  coord_fixed()
ggsave("figures/vessel_position_heatmap.png", width = 10, height = 8)

# Speed distribution by status
ggplot(data, aes(x = Status, y = SOG, fill = Status)) +
  geom_violin(alpha = 0.7) +
  geom_boxplot(width = 0.1, fill = "white", alpha = 0.8) +
  labs(title = "Distribution de la vitesse par statut du bateau",
       x = "Statut du bateau",
       y = "Speed Over Ground (nœuds)") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1),
        legend.position = "none") +
  scale_fill_viridis_d()
ggsave("figures/sog_distribution_by_status.png", width = 12, height = 7)

# Boat length vs width by type
data$Length_num <- as.numeric(as.character(data$Length))
data$Width_num <- as.numeric(as.character(data$Width))

ggplot(data[!is.na(data$Length_num) & !is.na(data$Width_num),], 
       aes(x = Length_num, y = Width_num, color = as.factor(VesselType))) +
  geom_point(alpha = 0.6) +
  labs(title = "Relation entre longueur et largeur des bateaux par type",
       x = "Longueur (mètres)",
       y = "Largeur (mètres)",
       color = "Type de bateau") +
  theme_minimal() +
  scale_color_viridis_d()
ggsave("figures/length_vs_width_by_type.png", width = 12, height = 8)

# Boat observations over time
# daily_counts <- data %>%
#   group_by(Date) %>%
#   summarise(count = n(), .groups = 'drop')

# ggplot(daily_counts, aes(x = Date, y = count)) +
#   geom_line(color = "steelblue", size = 1) +
#   geom_smooth(method = "loess", color = "red", se = TRUE) +
#   labs(title = "Évolution du nombre d'observations de bateaux dans le temps",
#        x = "Date",
#        y = "Nombre d'observations par jour") +
#   theme_minimal() +
#   theme(axis.text.x = element_text(angle = 45, hjust = 1))
# ggsave("figures/vessel_observations_over_time.png", width = 12, height = 6)

# Directional distributions (COG and Heading)
library(ggplot2)

# COG (Course Over Ground)
p1 <- ggplot(data, aes(x = COG)) +
  geom_histogram(binwidth = 10, fill = "lightblue", color = "black") +
  coord_polar(start = 0) +
  labs(title = "Distribution circulaire - Course Over Ground (COG)",
       x = "COG (degrés)", y = "Fréquence") +
  theme_minimal() +
  scale_x_continuous(breaks = seq(0, 360, 45))

# Heading
p2 <- ggplot(data, aes(x = Heading)) +
  geom_histogram(binwidth = 10, fill = "lightcoral", color = "black") +
  coord_polar(start = 0) +
  labs(title = "Distribution circulaire - Heading",
       x = "Heading (degrés)", y = "Fréquence") +
  theme_minimal() +
  scale_x_continuous(breaks = seq(0, 360, 45))

ggsave("figures/cog_circular_distribution.png", plot = p1, width = 8, height = 8)
ggsave("figures/heading_circular_distribution.png", plot = p2, width = 8, height = 8)

# Vessel concentration zones
ggplot(data, aes(x = LON, y = LAT)) +
  geom_point(alpha = 0.1, size = 0.5) +
  stat_density2d_filled(alpha = 0.6, contour_var = "ndensity") +
  labs(title = "Zones de forte concentration de bateaux",
       x = "Longitude", y = "Latitude") +
  theme_minimal() +
  theme(legend.position = "right") +
  coord_fixed()
ggsave("figures/vessel_concentration_zones.png", width = 12, height = 9)

# Average speed by vessel type and status
speed_summary <- data %>%
  group_by(VesselType, Status) %>%
  summarise(
    mean_sog = mean(SOG, na.rm = TRUE),
    median_sog = median(SOG, na.rm = TRUE),
    count = n(),
    .groups = 'drop'
  ) %>%
  filter(count >= 100)  # Filtrer pour avoir des groupes significatifs

ggplot(speed_summary, aes(x = as.factor(VesselType), y = mean_sog, fill = Status)) +
  geom_bar(stat = "identity", position = "dodge") +
  labs(title = "Vitesse moyenne par type de bateau et statut",
       x = "Type de bateau",
       y = "Vitesse moyenne (nœuds)",
       fill = "Statut") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))
ggsave("figures/mean_speed_by_type_status.png", width = 12, height = 7)


# Graphiques simples pour l'analyse des données de bateaux
library(ggplot2)

data <- read.csv("data/vessel-cleaned.csv")

# 1. Vitesse moyenne par type de bateau (barres simples)
speed_by_type <- aggregate(SOG ~ VesselType, data = data, mean)

ggplot(speed_by_type, aes(x = as.factor(VesselType), y = SOG)) +
  geom_bar(stat = "identity", fill = "lightblue", color = "black") +
  labs(title = "Vitesse moyenne par type de bateau",
       x = "Type de bateau",
       y = "Vitesse moyenne (nœuds)") +
  theme_minimal()
ggsave("figures/mean_speed_by_type.png", width = 8, height = 6)

# 2. Nombre de bateaux par zone géographique (découpage simple)
data$Zone <- ifelse(data$LAT > 30, "Nord", 
                   ifelse(data$LAT < 27, "Sud", "Centre"))

ggplot(data, aes(x = Zone)) +
  geom_bar(fill = "darkgreen", color = "black") +
  labs(title = "Nombre de bateaux par zone géographique",
       x = "Zone",
       y = "Nombre de bateaux") +
  theme_minimal()
ggsave("figures/boats_by_zone.png", width = 6, height = 5)

# 3. Bateaux en mouvement vs à l'arrêt
data$Moving <- ifelse(data$SOG > 1, "En mouvement", "À l'arrêt")

ggplot(data, aes(x = Moving)) +
  geom_bar(fill = "orange", color = "black") +
  labs(title = "Bateaux en mouvement vs à l'arrêt",
       x = "État",
       y = "Nombre de bateaux") +
  theme_minimal()
ggsave("figures/moving_vs_stationary.png", width = 6, height = 5)

# 4. Top 5 des types de bateaux les plus fréquents
vessel_counts <- table(data$VesselType)
top5_vessels <- names(sort(vessel_counts, decreasing = TRUE)[1:5])
data_top5 <- data[data$VesselType %in% top5_vessels, ]

ggplot(data_top5, aes(x = as.factor(VesselType))) +
  geom_bar(fill = "purple", color = "black") +
  labs(title = "Top 5 des types de bateaux",
       x = "Type de bateau",
       y = "Nombre") +
  theme_minimal()
ggsave("figures/top5_vessel_types.png", width = 8, height = 6)

# 5. Distribution simple des vitesses (avec ligne verticale pour la moyenne)
mean_sog <- mean(data$SOG)

ggplot(data, aes(x = SOG)) +
  geom_histogram(bins = 30, fill = "lightcoral", color = "black") +
  geom_vline(xintercept = mean_sog, color = "red", linetype = "dashed", size = 1) +
  labs(title = "Distribution des vitesses",
       subtitle = paste("Ligne rouge = vitesse moyenne (", round(mean_sog, 1), " nœuds)"),
       x = "Vitesse (nœuds)",
       y = "Nombre de bateaux") +
  theme_minimal()
ggsave("figures/speed_distribution_simple.png", width = 8, height = 6)

print("5 graphiques simples créés et sauvegardés dans le dossier 'figures/'")