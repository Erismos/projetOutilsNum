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
#             data/expoert_IA.csv
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
# gabriel file

library(corrplot)
library(randomForest)
library(caret)
library(ggplot2)
library(reshape2)

# ---------------------- Partie 4 ----------------------
main_analysis <- function() {
# Pré traitement ################################################# 

# \N remplacer par NA
vessel = data.table::fread("data/vessel-total-clean.csv", na.strings = "\\N")
vessel_final = data.table::fread("data/export_IA.csv", na.strings = "\\N")
vessel_final2 = data.table::data.table()

# supp duplicate
vessel <- vessel[!duplicated(vessel$id),]

# création des sous groupes avant le filtrage des 0 pour pouvoir ensuite remplacer par moyenne
vessel_list <- split(vessel, by = "VesselType")
u_type = sort(unique(vessel$VesselType)) # types de bateaux

# calcul du seuil sur les données originales
sog_threshold <- quantile(vessel$SOG, 0.94, na.rm = TRUE) 

# on va remplacer les 0 ou NA dans les variables suivantes en fonction de la médiane de leur VesselType

for (type in u_type) {
  sub_dt <- vessel_list[[as.character(type)]]
  sub_dt[is.na(sub_dt)] <- 0
  
  # Calculer les médianes
  med_length <- sub_dt[Length != 0, median(Length)]
  med_width  <- sub_dt[Width  != 0, median(Width)]
  med_draft  <- sub_dt[Draft  != 0, median(Draft)]
  med_cargo  <- sub_dt[Cargo  != 0, median(Cargo)]
  med_status  <- sub_dt[Status  != 0, median(Status)]

  # Remplacement des 0 par les médianes
  sub_dt[Length == 0, Length := med_length]
  sub_dt[Width  == 0, Width  := med_width]
  sub_dt[Draft  == 0, Draft  := med_draft]
  sub_dt[Cargo  == 0, Cargo  := med_cargo]
  sub_dt[Status  == 0, Status  := med_status]

  # Ajout au résultat final
  vessel_final2 <- rbind(vessel_final2, sub_dt)
}

vessel_filtered <- vessel_final2
vessel_final2 <- vessel_final2[vessel_final2$SOG <= sog_threshold, ]

# remplacer NA par inconnu(e) dans colonne texte (qualitative)
for (col in names(vessel)) {
  if (is.character(vessel[[col]])) {
    vessel[is.na(get(col)), (col) := "inconnu(e)"]
  }
}

# Analyse corrélation ################################################# 

num_vars <- c("SOG", "Length", "Width", "Draft", "Cargo")

# Conversion de VesselType en facteur
vessel_final2$VesselType <- as.factor(vessel_final2$VesselType)

# Boucle pour tracer un boxplot par variable
for (var in num_vars) {
  p <- ggplot(vessel_filtered, aes_string(x = "VesselType", y = var)) +
    geom_boxplot(fill = "skyblue", outlier.colour = "red", outlier.shape = 1) +
    labs(title = paste("Boîte à moustaches de", var, "par type de navire"),
         x = "VesselType", y = var) +
    theme_bw()
  print(p)
  ggsave(filename = paste0("plots/4_boxplot_", var, ".png"), plot = p, width = 8, height = 5)
}

num_vars <- c("SOG", "Length", "Width", "Draft", "Cargo")

# Matrice de correlation entre SOG, Length, Width et Draft
cor_matrix <- cor(vessel_final[, ..num_vars], use = "complete.obs")

data <- as.data.frame(vessel_final)
vessel_num <- data[, num_vars] # Sélection des colonnes qu'on veut
# data[sapply(data, is.numeric)] si on veut toute les colonnes numériques

# Matrice de corrélation de Pearson
cor_matrix <- cor(vessel_num, use = "complete.obs")
r2_matrix <- cor_matrix^2

# Visualisation
png("plots/4_slwdc_cor_matrix.png", width = 800, height = 800)
corrplot(r2_matrix, 
         method = "color", 
         type = "upper", 
         tl.col = "black", 
         addCoef.col = "black")
dev.off()

######################################

num_vars <- c("SOG", "Length", "Width", "Draft", "Cargo")

# Calcul du khi2 #
cross_table <- table(vessel_final[1:33]$Cargo, vessel_final[1:33]$VesselType) 
chisq.test(cross_table)
# p-value > 0.05 -> pas de preuve qu'elles sont dépendantes

# Tableau croisé VesselType × Cargo

# Test du Chi² (indépendance)
# calcul de x² : sum((Oij - Eij)²/Eij), p-value : 
# Oij nb de bateaux i ayant statut i par ex 

# ANOVA

data_anova <- vessel_final[1:100]
anova_result <- aov(SOG ~ as.factor(VesselType), data = data_anova)
summary(anova_result)

# Visualisation (Mosaic Plot)

cross_table <- table(vessel_final[1:30]$Status, vessel_final[1:30]$VesselType) 
fisher.test(cross_table)

cross_table <- table(vessel_final2$Status, vessel_final2$VesselType) 
png("plots/4_vt_x_s.png", width = 800, height = 800)
mosaicplot(cross_table, 
           main = "Relation Type de VesselType × Status",
           color = TRUE)
dev.off()


cross_table <- table(vessel_final[1:30000]$Cargo, vessel_final[1:30000]$VesselType)
fisher.test(cross_table, simulate.p.value=TRUE)

cross_table <- table(vessel_final2$Cargo, vessel_final2$VesselType)
png("plots/4_vt_x_c.png", width = 1200, height = 1200)
mosaicplot(table(vessel_final2$Cargo, vessel_final2$VesselType),
           main = "VesselType × Cargo",
           color = TRUE)
dev.off()

# ---------------------- Partie 5 ----------------------

# Régression linéaire entre Length et Width

set.seed(42)
index <- sample(1:nrow(vessel_final2), size = 0.8 * nrow(vessel_final2))
train <- vessel_final2[index, ]
test <- vessel_final2[-index, ]


lm_l_w <- lm(Length ~ Width, data  = train)
pred <- predict(lm_l_w, newdata = test)
summary(lm_l_w)

# Régression logistique 

set.seed(42)
index <- sample(1:nrow(vessel_final2), size = 0.7 * nrow(vessel_final2))
train <- vessel_final2[index, ]
test <- vessel_final2[-index, ]

model <- nnet::multinom(VesselType ~ SOG + Length + Draft + Width + Cargo + TransceiverClass + Status, data = train) # median, factor(TClass), status 
pred <- predict(model, newdata = test)

accuracy <- mean(pred == test$VesselType)
print(accuracy)
conf_mat <- table(pred, test$VesselType)
print(conf_mat)
}

# main_analysis()

# train/test split : 

# 0.8561944 T class, SOG > 0.96 replaced by med of group, 0.8669777 Tclass sog > 0.96 removed, 0.8976656  w/o NA -> mean, SOG, L, W, D, Cargo, TClasse, Status, SOG > q0.96 removed

# med : q > 0.96 default
# factor(TClass), Status                                 : 0.884735
# factor(Tclass), Status, SOG filtered                   : 0.8817886
# TClass, Status, SOG Filtered                           : 0.8857681
# TClass, factor(Status), SOG Filtered                   : 0.8857681
# TClass, Status                                         : 0.8857681
# TClass, Status, SOG removed q>0.94                     : 0.9057053
# f(TClass, Status), SOG removed q>0.94                  : 0.84019
# f(TClass), Status, SOG removed q>0.94                  : 0.8376588
# TClass, Status, SOG removed q>0.94, NA/0 Status->med   : 0.9304349 #


# mean : q > 0.96 default
# factor(TClass, Status)                                 : 0.8208954
# high SOG, factor(TClass, Status)                       : 0.7918233
# high SOG, TClass, Status                               : 0.8682674
# TClass, Status, high SOG filtered                      : 0.8745645
# no filter, no factor, high SOG meaned                  : 0.8667761
# no factor, high SOG removed                            : 0.8745645
# no factor, high SOG removed q>0.95                     : 0.8935128
# no factor, high SOG removed q>0.94                     : 0.8937666
# no factor, high SOG removed q>0.93                     : 0.8935556
