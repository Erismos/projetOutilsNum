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
# Fonctionnalité 1: Nettoyage et traitement des données #
####################################################

#' Lit les données à partir d'un fichier CSV
#'
#' @param file_path Chemin vers le fichier CSV à lire
#' @return DataFrame contenant les données lues
#' @examples 
#' data <- read_data("data/vessel-total-clean.csv")
read_data <- function(file_path) {
  data <- read.csv(file_path)
  print(paste("Dimensions initiales des données :", dim(data)[1], "lignes x", dim(data)[2], "colonnes"))
  return(data)
}

#' Affiche les statistiques descriptives de base des données
#'
#' @param data DataFrame à analyser
#' @return Aucun (affichage dans la console uniquement)
display_basic_stats <- function(data) {
  print("Statistiques descriptives :")
  print(summary(data))
  print("Noms des colonnes :")
  print(names(data))
  print("Structure des données :")
  str(data)
}

#' Convertit des colonnes en type numérique
#'
#' @param data DataFrame contenant les données
#' @param columns Vecteur des noms de colonnes à convertir
#' @return DataFrame avec les colonnes converties en numérique
convert_to_numeric <- function(data, columns) {
  for(col in columns) {
    data[[col]] <- as.numeric(data[[col]])
  }
  return(data)
}

#' Traite les valeurs manquantes selon différentes stratégies
#'
#' @param data DataFrame à nettoyer
#' @param numeric_columns Vecteur des noms de colonnes numériques
#' @return DataFrame nettoyé
#' @details Stratégies appliquées :
#'          - Suppression si <5% de valeurs manquantes
#'          - Imputation par médiane pour les numériques
#'          - Remplacement par "inconnu" pour les autres
handle_missing_values <- function(data, numeric_columns) {
  print("Traitement des valeurs manquantes...")
  # Conversion des valeurs "\N" en NA
  data[data == "\\N"] <- NA
  print(paste("Total de valeurs manquantes :", sum(is.na(data))))
  
  n <- nrow(data)
  for (col in colnames(data)) {
    val_mq <- sum(is.na(data[[col]]))
    pourcentage <- val_mq/n
    
    if(pourcentage < 0.05) {
      # Suppression des lignes avec NA si peu de valeurs manquantes
      data <- data[!is.na(data[[col]]), ]
      n <- nrow(data)
    } else {
      if(col %in% numeric_columns) {
        # Imputation par la médiane pour les colonnes numériques
        med <- median(data[[col]], na.rm = TRUE)
        data[[col]][is.na(data[[col]])] <- med
      } else {
        # Remplacement par "inconnu" pour les autres colonnes
        data[[col]][is.na(data[[col]])] <- "inconnu"
      }
    }
  }
  
  print(paste("Dimensions après traitement des NA :", dim(data)[1], "lignes x", dim(data)[2], "colonnes"))
  return(data)
}

#' Détecte et traite les valeurs aberrantes (outliers)
#'
#' @param data DataFrame à nettoyer
#' @param numeric_columns Vecteur des noms de colonnes numériques
#' @return DataFrame nettoyé
#' @details Utilise la méthode de l'IQR (Interquartile Range) :
#'          - Suppression si <3% d'outliers
#'          - Imputation par médiane sinon
handle_outliers <- function(data, numeric_columns) {
  print("Traitement des valeurs aberrantes...")
  
  for(col in numeric_columns) {
    # Calcul des quartiles et de l'IQR
    q1 <- quantile(data[[col]], 0.25)
    q3 <- quantile(data[[col]], 0.75)
    iqr <- q3 - q1
    # Définition des bornes
    inf <- q1 - 1.5 * iqr
    sup <- q3 + 1.5 * iqr
    
    # Détection des outliers
    outliers <- data[[col]] < inf | data[[col]] > sup
    
    if(sum(outliers, na.rm = TRUE) / nrow(data) < 0.03) {
      # Suppression si peu d'outliers
      data <- data[!outliers, ]
    } else {
      # Imputation par la médiane sinon
      data[[col]][outliers] <- median(data[[col]], na.rm = TRUE)
    }
  }
  
  print(paste("Dimensions après traitement des valeurs aberrantes :", dim(data)[1], "lignes x", dim(data)[2], "colonnes"))
  return(data)
}

#' Supprime les doublons dans les données
#'
#' @param data DataFrame à nettoyer
#' @return DataFrame sans doublons
handle_duplicates <- function(data) {
  print("Traitement des doublons...")
  print(paste("Nombre de doublons trouvés :", sum(duplicated(data))))
  data <- unique(data)
  print(paste("Dimensions finales :", dim(data)[1], "lignes x", dim(data)[2], "colonnes"))
  return(data)
}

#' Sauvegarde les données nettoyées dans un fichier CSV
#'
#' @param data DataFrame à sauvegarder
#' @param file_path Chemin du fichier de sortie
#' @return Aucun (écriture du fichier uniquement)
save_clean_data <- function(data, file_path) {
  write.csv(data, file_path, row.names = FALSE)
  print(paste("Nettoyage des données terminé. Données sauvegardées sous :", file_path))
}

# Définition des colonnes numériques pour le traitement
numeric_columns <- c("SOG", "COG", "Heading", "Length", "Width", "Draft")

#' Pipeline principal de nettoyage des données
#' 
#' Exécute toutes les étapes du processus de nettoyage :
#' 1. Lecture des données
#' 2. Affichage des statistiques
#' 3. Conversion des colonnes numériques
#' 4. Traitement des valeurs manquantes
#' 5. Traitement des valeurs aberrantes
#' 6. Suppression des doublons
#' 7. Sauvegarde des données nettoyées
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

# Exécution du pipeline (décommenter pour lancer)
# main_data_cleaning()