

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
