############################################################
# Titre      : Nettoyage et Traitement des Données de Bateaux
# Fichier    : data_cleaning.R
# Description: Ce script R implémente un pipeline complet de 
#              nettoyage et de prétraitement des données 
#              issues du trafic maritime.
#
# Auteurs     : Gabriel Boucneau & Laure Warlop & Clément Auvray
# Date        : Juin 2025
# Données     : data/vessel-total-clean.csv
# Dépendances : base R (stats, utils)
# Sorties     : Fichier nettoyé au format CSV : data/export_IA.csv
############################################################



####################################################
# Fonctionnalité 1: Nettoyage et traintement des données #
####################################################


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
  save_clean_data(data, "data/export_IA.csv")
}

# Exécution du pipeline
# main_data_cleaning()