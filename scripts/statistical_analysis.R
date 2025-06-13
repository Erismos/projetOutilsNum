############################################################
# Titre      : Analyse des Données Maritimes AIS
# Fichier    : maritime_analysis.R
# Description: Ce script effectue une analyse complète des
#              données AIS (Automatic Identification System)
#              incluant :
#              - Nettoyage et prétraitement des données
#              - Analyse exploratoire (corrélations, boxplots)
#              - Tests statistiques (Khi-deux)
#              - Modélisation (régression linéaire et logistique)
#
# Méthodologie :
#              - Traitement des valeurs manquantes et aberrantes
#              - Visualisation des distributions
#              - Analyse des relations variables qual/quant
#              - Validation croisée des modèles
#
# Auteurs    : Gabriel Boucneau & Laure Warlop & Clément Auvray
# Date       : Juin 2025
# Données    : data/vessel-total-clean.csv
#             data/vessel-cleaned.csv
# Dépendances: 
#              - data.table
#              - ggplot2
#              - corrplot
#              - nnet
#              - caret
#              - randomForest
# Sorties    : 
#              - Graphiques dans plots/
#              - Modèles de prédiction
# Historique :
#              v1.0 - Analyse initiale
#              v1.1 - Optimisation des modèles
############################################################

library(data.table)
library(ggplot2)
library(corrplot)
library(nnet)
library(caret)
library(randomForest)

# ---------------------- 1. Pré-traitement ----------------------
preprocess_data <- function() {
  # Chargement des données
  vessel <- fread("data/vessel-total-clean.csv", na.strings = "\\N")
  vessel_final <- fread("data/vessel-cleaned.csv", na.strings = "\\N")
  
  # Nettoyage initial
  vessel <- vessel[!duplicated(id), ]
  vessel_list <- split(vessel, by = "VesselType")
  u_type <- sort(unique(vessel$VesselType))
  sog_threshold <- quantile(vessel$SOG, 0.94, na.rm = TRUE)
  
  # Traitement par type de navire
  vessel_final2 <- rbindlist(lapply(u_type, function(type) {
    sub_dt <- vessel_list[[as.character(type)]]
    sub_dt[is.na(sub_dt)] <- 0
    
    # Calcul des médianes
    meds <- sub_dt[, lapply(.SD, function(x) median(x[x != 0])), 
                   .SDcols = c("Length", "Width", "Draft", "Cargo")]
    
    # Remplacement des 0
    sub_dt[Length == 0, Length := meds$Length]
    sub_dt[Width == 0, Width := meds$Width]
    sub_dt[Draft == 0, Draft := meds$Draft]
    sub_dt[Cargo == 0, Cargo := meds$Cargo]
    
    return(sub_dt)
  }))
  
  # Filtrage et traitement des NA
  vessel_filtered <- vessel_final2[SOG <= sog_threshold, ]
  char_cols <- names(vessel)[sapply(vessel, is.character)]
  vessel[, (char_cols) := lapply(.SD, function(x) fifelse(is.na(x), "inconnu(e)", x)), 
         .SDcols = char_cols]
  
  return(list(raw = vessel, filtered = vessel_filtered, clean = vessel_final))
}

# ---------------------- 2. Analyse Exploratoire ----------------------
perform_eda <- function(data) {
  # Boxplots par type de navire
  num_vars <- c("SOG", "Length", "Width", "Draft", "Cargo")
  data$filtered$VesselType <- as.factor(data$filtered$VesselType)
  
  lapply(num_vars, function(var) {
    p <- ggplot(data$filtered, aes_string(x = "VesselType", y = var)) +
      geom_boxplot(fill = "skyblue", outlier.colour = "red") +
      labs(title = paste("Distribution de", var), x = "Type de navire") +
      theme_bw()
    ggsave(paste0("plots/boxplot_", var, ".png"), p, width = 8, height = 5)
  })
  
  # Matrice de corrélation
  cor_vars <- c("VesselType", num_vars)
  cor_matrix <- cor(data$clean[, ..cor_vars], use = "complete.obs")^2
  png("plots/correlation_matrix.png", width = 800, height = 800)
  corrplot(cor_matrix, method = "color", type = "upper", 
           tl.col = "black", addCoef.col = "black")
  dev.off()
}

# ---------------------- 3. Tests Statistiques ----------------------
perform_stat_tests <- function(data) {
  # Fonction helper pour les tests Khi-deux
  run_chi2_test <- function(var1, var2, data, sample_size = NULL) {
    if (!is.null(sample_size)) data <- data[sample(.N, sample_size)]
    ct <- table(data[[var1]], data[[var2]])
    test <- chisq.test(ct)
    
    png(paste0("plots/mosaic_", var1, "_", var2, ".png"), width = 800, height = 800)
    mosaicplot(ct, main = paste("Relation", var1, "×", var2), color = TRUE)
    dev.off()
    
    return(test)
  }
  
  # Tests sur différents croisements
  tests <- list(
    cargo_vtype = run_chi2_test("Cargo", "VesselType", data$raw, 33),
    transceiver_vtype = run_chi2_test("TransceiverClass", "VesselType", data$raw, 50),
    status_vtype = run_chi2_test("Status", "VesselType", data$raw, 50)
  )
  
  return(tests)
}

# ---------------------- 4. Modélisation ----------------------
perform_modeling <- function(data) {
  set.seed(42)
  index <- sample(1:nrow(data), size = 0.7 * nrow(data))
  train <- data[index, ]
  test <- data[-index, ]
  
  # Régression linéaire
  lm_model <- lm(Length ~ Width, data = train)
  print(summary(lm_model))
  
  # Régression logistique
  logit_model <- multinom(
    VesselType ~ SOG + Length + Draft + Width + Cargo + TransceiverClass + Status, 
    data = train
  )
  
  pred <- predict(logit_model, newdata = test)
  accuracy <- mean(pred == test$VesselType)
  conf_mat <- table(pred, test$VesselType)
  
  print(paste("Accuracy:", accuracy))
  print("Matrice de confusion:")
  print(conf_mat)
  
  return(list(lm = lm_model, logit = logit_model, accuracy = accuracy))
}

# ---------------------- Exécution ----------------------
main <- function() {
  # 1. Pré-traitement
  data <- preprocess_data()
  
  # 2. Analyse exploratoire
  perform_eda(data)
  
  # 3. Tests statistiques
  stat_results <- perform_stat_tests(data)
  
  # 4. Modélisation
  model_results <- perform_modeling(data$filtered)
  
  return(list(data = data, stats = stat_results, models = model_results))
}

# Lancement de l'analyse
analysis_results <- main()