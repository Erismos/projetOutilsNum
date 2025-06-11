# laure file

library(ggplot2)
library(dplyr)
library(leaflet)
library(RColorBrewer)
library(htmlwidgets)

##############################################
########## EXPLORATION DES DONNÉES ###########
##############################################

# Chargement des données
data <- read.csv("data/vessel-total-clean.csv")
print(dim(data))

# Statistiques descrptives univariées

print(summary(data))
print(names(data))
# on peut vérifier le type des données
str(data)
# print(str(data))
# si on veut tester sur une variable numerique specifique, par exemple id
# print(summary(data$id))
# si on veut lire les données caractérielle
# print(table(data$IMO))

# Nettoyage des données

#Conversion des colonnes quantitatives en numérique
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


# valeurs manquantes
# les valeurs manquantes sont des \n et on doit les ramplacer par NA pour pouvoir après les supprimer
data[data == "\\N"] <- NA
print("valeurs manquantes :")
print(sum(is.na(data))) # on en a 326040
n <- nrow(data)
for (i in colnames(data)){
    val_mq <- sum(is.na(data[[i]]))
    pourcentage <- val_mq/n # nombre de valeurs manquante divisé par le nombre de lignes total 

    if(pourcentage < 0.05){
        data <- data[!is.na(data[[i]]), ] # supprime les lignes avec NA, la virgule pour que les lignes
        n <- nrow(data)
    }
    else{
        if(i %in% colonnes_numeriques){
            med <- median(data[[i]], na.rm = TRUE)
            data[[i]][is.na(data[[i]])] <- med # remplace les NA par la médiane
        }
        else{ # si les colonnes ne sont pas numériques
            data[[i]][is.na(data[[i]])] <- "inconnu" # remplace les NA par inconnu
        }
    }
}

print("nombre de ligne et colonnes :")
print(dim(data)) # on en a 397503 lignes et 18 colonnes

# valeurs aberrantes 
print("valeurs aberrantes")
# on prend que les valeurs numériques
for(i in colonnes_numeriques){
    # double crochet car un vecteur
    q1 <- quantile(data[[i]], 0.25) # calcul du premier quantile
    q3 <- quantile(data[[i]], 0.75) # calcul du troisième quantile
    iqr <- q3 - q1
    inf <- q1-1.5*iqr
    sup <- q3+1.5*iqr
    # si les valeurs dans la colonne i sont hors de l'intervalle allors on supprime ou on remplace par la mediane en fonction du 5%
    outliers <- data[[i]] < inf | data[[i]] > sup

    if(sum(outliers, na.rm = TRUE) / nrow(data) < 0.03){ # calcul du pourcentage et comparaison
        data <- data[!outliers, ] # on supprime les valeurs aberrantes
    }else{
        data[[i]][outliers] <- median(data[[i]], na.rm = TRUE)
    }
}

print("nombre de lignes et colonnes :")
print(dim(data)) # 392803 lignes

# doublons
# nombre de doublons
print("nombre de doublons")
print(sum(duplicated(data))) # 0 doublons
data <- unique(data) # supprime les doublons si existant

# final 
print("nombre de lignes et colonnes :")
print(dim(data)) # 392803 lignes

library(readr)
# nouveau fichier csv pour avoir le csv nettoyé
write_csv(data, "data_clean_final.csv")


##############################################
######### VISUALISATION DES DONNÉES ##########
##############################################

data <- read.csv("data_clean_final.csv")
print(dim(data))

# Créer des représentations graphiques

# graphique avev width
width <- table(data$Width) # compte le nombre d'occurences pour la largeur des bateaux
png("graph_with.png", width = 800, height = 500)
barplot(width, col="yellow", ylim= c(0,60000), 
        main="Répartition des bateaux par taille",
        xlab="Largeur des bateaux",
        ylab="Nombre de bateaux")
dev.off() 

# on donne le jeu de donnée data et on spécifie la variable à utiliser, ici : VesselType
ggplot(data, aes(x=as.factor(VesselType))) + 
    # on veut un histogramme
    geom_bar(fill="pink") +
    # on ajoute des légendes
    labs(title = "Répartition des bateaux par type",
         x = "Type de bateau",
         y = "Nombre de bateaux")
# on sauvegarde l'image avec une taille défini
ggsave("type-bateaux.png", width = 8, height = 5)

# Graphique des positions géographiques
carte_positions <- ggplot(data, aes(x = LON, y = LAT)) +
    # nuage de point
  geom_point(aes(color = VesselType, size = SOG), alpha = 0.7) +
  # définit l’échelle de taille des points (ici de 1 à 5)
  # on ajoute un nom à la légende de la taille : "Vitesse (SOG)"
  scale_size_continuous(name = "Vitesse (SOG)", range = c(1, 5)) +
  # légende
  labs(title = "Positions des navires par type",
       subtitle = "Taille des points proportionnelle à la vitesse",
       x = "Longitude", y = "Latitude") +
    # thème sobre
  theme_minimal() +
  # légende en bas
  theme(legend.position = "bottom")
# sauvegarde
ggsave("carte_positions_navires.png", carte_positions, 
       width = 12, height = 8, dpi = 300, bg = "white")

# histogramme des vitesses
hist_vitesses <- ggplot(data, aes(x = SOG)) +
  geom_histogram(bins = 30, fill = "lightblue", color = "darkblue", alpha = 0.7) +
  # légende
  labs(title = "Distribution des vitesses (SOG)",
       x = "Vitesse sur le fond (nœuds)", y = "Fréquence") +
  geom_vline(aes(xintercept = mean(SOG, na.rm = TRUE)), # on ajoute une ligne verticale pointillée rouge à la moyenne des vitesses
             color = "red", linetype = "dashed", size = 1) +
    # on ajoute une annotation texte près de la ligne moyenne, avec la valeur moyenne arrondie à 1 décimale
  annotate("text", x = mean(data$SOG, na.rm = TRUE) + 2, 
           y = max(table(cut(data$SOG, 30))) * 0.8,
           label = paste("Moyenne:", round(mean(data$SOG, na.rm = TRUE), 1), "nœuds"),
           color = "red")

ggsave("histogramme_vitesses.png", hist_vitesses, 
       width = 10, height = 6, dpi = 300, bg = "white")

# Graphique en secteurs (camemberts)
statuts_count <- table(data$Status) # calcul le nombre d'occurence de chaque status
# créer un dataframe avec les status et leurs comptes
statuts_data <- data.frame( 
  Status = names(statuts_count),
  n = as.numeric(statuts_count),
  stringsAsFactors = FALSE
)
# on calcul les pourcentages pour chaque status
statuts_data$pourcentage <- statuts_data$n / sum(statuts_data$n) * 100

# Graphique en secteurs (camemberts)
# on initialise un graphique vide pour faire un camembert 
statuts_pie <- ggplot(statuts_data, aes(x = "", y = n, fill = Status)) +
    # on ajoute une barre pleine pour chaque status
  geom_bar(stat = "identity", width = 1) +
  # on convertit les barres en graphiques circulaires
  coord_polar("y", start = 0) +
  # ajout du titre
  labs(title = "Répartition des statuts des navires") +
  # on supprime tous les axes
  theme_void() +
  # on ajoute le pourcentage à l'intérieur du graphique
  geom_text(aes(label = paste0(round(pourcentage, 1), "%")), 
            position = position_stack(vjust = 0.5),
            size = 3) +
    # on met la légende à droite et on change la taille du texte
  theme(legend.position = "right",
        legend.text = element_text(size = 8))
# on suavegarde le graphique en une image de format png
ggsave("repartition_statuts.png", statuts_pie, 
       width = 12, height = 8, dpi = 300, bg = "white")

# Carte de densité des positions avec ggplot2
# graphique avec les longitudes et les lattitudes
heatmap_positions_simple <- ggplot(data, aes(x = LON, y = LAT)) +
    # on ajoute une carte de densité (niveaux de concentration), remplie et sans contours
  stat_density_2d_filled(alpha = 0.8, contour = FALSE, bins = 15) +
  # on affiche les points de données en surimpression, en blanc
  geom_point(size = 0.3, alpha = 0.3, color = "white") +
    # on ajoute titres, axes, thème épuré, légende à droite
  labs(title = "Carte de densité du trafic maritime",
       subtitle = "Zones de forte concentration des navires",
       x = "Longitude", y = "Latitude") +
  theme_minimal() +
  theme(legend.position = "right")
# on sauvegarde
ggsave("heatmap_positions.png", heatmap_positions_simple, 
       width = 12, height = 8, dpi = 300, bg = "white")

# Version avec contours uniquement 
# on affiche les points des navires en bleu acier
heatmap_contours <- ggplot(data, aes(x = LON, y = LAT)) +
  geom_point(alpha = 0.4, size = 0.5, color = "steelblue") +
  # on superpose les lignes de niveau de densité (contours rouges)
  stat_density_2d(color = "red", size = 0.8, bins = 10) +
  # légende
  labs(title = "Carte de densité avec contours",
       subtitle = "Lignes de niveau de concentration des navires",
       x = "Longitude", y = "Latitude") +
  theme_minimal()
# sauvegarde
ggsave("heatmap_contours.png", heatmap_contours, 
       width = 12, height = 8, dpi = 300, bg = "white")


##############################################
################### CARTE ####################
##############################################

# Filtrer et trier les données
data_sorted <- data %>%
  filter(!is.na(LAT), !is.na(LON)) %>%
  arrange(VesselName, BaseDateTime)

# Calcul des bornes pour le zoom automatique
bounds <- data_sorted %>%
  summarise(
    min_lat = min(LAT, na.rm = TRUE),
    max_lat = max(LAT, na.rm = TRUE),
    min_lon = min(LON, na.rm = TRUE),
    max_lon = max(LON, na.rm = TRUE)
  )

# Types de navires uniques
types_uniques <- unique(data_sorted$VesselType)
navires_uniques <- unique(data_sorted$VesselName)

# Palette de couleurs
pal_type <- colorFactor(rainbow(length(types_uniques)), domain = types_uniques)

# Initialisation de la carte avec les bornes 
carte_leaflet <- leaflet() %>%
  addTiles() %>%
  fitBounds(
    lng1 = bounds$min_lon,
    lat1 = bounds$min_lat,
    lng2 = bounds$max_lon,
    lat2 = bounds$max_lat
  )

# Ajouter les polylignes une par une
# Ajouter les lignes navire par navire
for (navire in navires_uniques) {
  trajet <- data_sorted %>% filter(VesselName == navire)
  carte_leaflet <- carte_leaflet %>%
    addPolylines(data = trajet,
                 lng = ~LON, lat = ~LAT,
                 color = pal(navire),
                 weight = 2, opacity = 0.7,
                 group = navire)
}

# Ajouter une légende
# Légende par type de navire
carte_leaflet <- carte_leaflet %>%
  addLegend("bottomright", pal = pal_type, values = types_uniques,
            title = "Type de navire")

# Sauvegarde
saveWidget(carte_leaflet, file = "carte_trajectoires_navires.html", selfcontained = TRUE)


