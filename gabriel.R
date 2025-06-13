# gabriel file

library(corrplot)
library(randomForest)
library(caret)
library(ggplot2)
library(reshape2)

# ---------------------- Partie 4 ----------------------

# Pré traitement ################################################# 

# \N remplacer par NA
vessel = data.table::fread("data/vessel-total-clean.csv", na.strings = "\\N")
vessel_final = data.table::fread("data/vessel-cleaned.csv", na.strings = "\\N")
vessel_final2 = data.table::data.table()

# supp duplicate
vessel <- vessel[!duplicated(vessel$id),]

# création des sous groupes avant le filtrage des 0 pour pouvoir ensuite remplacer par moyenne
vessel_list <- split(vessel, by = "VesselType")



u_type = sort(unique(vessel$VesselType)) # types de bateaux
# calcul du seuil sur les données originales
sog_threshold <- quantile(vessel$SOG, 0.94, na.rm = TRUE) 

for (type in u_type) {
  sub_dt <- vessel_list[[as.character(type)]]
  sub_dt[is.na(sub_dt)] <- 0

  # D'abord traiter les valeurs aberrantes de SOG
  # med_sog <- sub_dt[SOG != 0 & SOG <= sog_threshold, median(SOG)]
  # sub_dt[SOG > sog_threshold, SOG := med_sog]
  
  # Ensuite calculer les autres médianes
  med_length <- sub_dt[Length != 0, median(Length)]
  med_width  <- sub_dt[Width  != 0, median(Width)]
  med_draft  <- sub_dt[Draft  != 0, median(Draft)]
  med_cargo  <- sub_dt[Cargo  != 0, median(Cargo)]

  # Remplacement des 0 par les moyennes
  sub_dt[Length == 0, Length := med_length]
  sub_dt[Width  == 0, Width  := med_width]
  sub_dt[Draft  == 0, Draft  := med_draft]
  sub_dt[Cargo  == 0, Cargo  := med_cargo]

  # Ajout au résultat final
  vessel_final2 <- rbind(vessel_final2, sub_dt)
}

# remplacer NA par inconnu(e) dans colonne texte (qualitative)
for (col in names(vessel)) {
  if (is.character(vessel[[col]])) {
    vessel[is.na(get(col)), (col) := "inconnu(e)"]
  }
}

# Analyse corrélation ################################################# 

#png("corrplot_image.png", width = 800, height = 800)
#################
# Générer le corrplot
#corrplot(cor_matrix,
#         method = "color",
#         type = "upper",
#         tl.col = "black",
#         addCoef.col = "black")
#dev.off()
#################

num_vars <- c("VesselType","SOG", "Length", "Width", "Draft", "Cargo")

# Conversion de VesselType en facteur
vessel_final2$VesselType <- as.factor(vessel_final2$VesselType)

# Boucle pour tracer un boxplot par variable
for (var in num_vars) {
  p <- ggplot(vessel_final2, aes_string(x = "VesselType", y = var)) +
    geom_boxplot(fill = "skyblue", outlier.colour = "red", outlier.shape = 1) +
    labs(title = paste("Boîte à moustaches de", var, "par type de navire"),
         x = "VesselType", y = var) +
    theme_bw()
  print(p)
  ggsave(filename = paste0("plots/4_boxplot_", var, ".png"), plot = p, width = 8, height = 5)
}

# Matrice de correlation entre SOG, Length, Width, Draft et Cargo
cor_matrix <- cor(vessel_final[, ..num_vars], use = "complete.obs")

data <- as.data.frame(vessel_final)
vessel_num <- data[, num_vars] # Sélection des colonnes qu'on veut
# data[sapply(data, is.numeric)] si on veut toute les colonnes numériques

# Matrice de corrélation de Pearson
cor_matrix <- cor(vessel_num, use = "complete.obs")
r2_matrix <- cor_matrix^2

# Visualisation
png("plots/4_vtslwdc_cor_matrix.png", width = 800, height = 800)
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

# Tableau croisé VesselType × TranceiverClass

# Test du Chi² (indépendance)
# calcul de x² : sum((Oij - Eij)²/Eij), p-value : 
# Oij nb de bateaux i ayant statut i par ex 

# Visualisation (Mosaic Plot)
cross_table <- table(vessel_final2[1:50]$TransceiverClass, vessel_final2[1:50]$VesselType) # calcul de khi2 sur 50 valeurs car biaisé sinon
chisq.test(cross_table)

cross_table <- table(vessel_final2$TransceiverClass, vessel_final2$VesselType) 
png("plots/4_vt_x_tc.png", width = 800, height = 800)
mosaicplot(cross_table, 
           main = "Relation Type de VesselType × TranceiverClass",
           color = TRUE)
dev.off()

cross_table <- table(vessel_final2[1:50]$Status, vessel_final2[1:50]$VesselType) 
chisq.test(cross_table)

cross_table <- table(vessel_final2$Status, vessel_final2$VesselType) 
png("plots/4_vt_x_s.png", width = 800, height = 800)
mosaicplot(cross_table, 
           main = "Relation Type de VesselType × Status",
           color = TRUE)
dev.off()


cross_table <- table(vessel_final2[1:50]$Cargo, vessel_final2[1:50]$VesselType)
chisq.test(cross_table)

cross_table <- table(vessel_final2$Cargo, vessel_final2$VesselType)
png("plots/4_vt_x_c.png", width = 800, height = 800)
mosaicplot(cross_table, 
           main = "Relation Type de VesselType × Cargo",
           color = TRUE)
dev.off()

# qual à quant

# ---------------------- Partie 5 ----------------------
vessel_final2 <- vessel_filtered

# Régression linéaire entre Length et Width

set.seed(42)
index <- sample(1:nrow(vessel_final2), size = 0.7 * nrow(vessel_final2))
train <- vessel_final2[index, ]
test <- vessel_final2[-index, ]

lm_l_w <- lm(Length ~ Width, data  = train)
summary(lm_l_w)

# Régression logistique 

set.seed(42)
index <- sample(1:nrow(vessel_final2), size = 0.7 * nrow(vessel_final2))
train <- vessel_final2[index, ]
test <- vessel_final2[-index, ]

#model <- nnet::multinom(VesselType ~ SOG + Length + Draft + Width + Cargo + TransceiverClass + Status, data = train) # median, factor(TClass), status 
pred <- predict(model, newdata = test)

accuracy <- mean(pred == test$VesselType)
print(accuracy)
conf_mat <- table(pred, test$VesselType)
print(conf_mat)

# no train/test split : 
# 0.8178012, 0.8477001 w/ SOG, L, W, D, Cargo, 0.8543062 w/ SOG, L, W, D, Cargo, TCase, 0.8705572 : w/ SOG, L, W, D, Cargo, SOG >q0.95 removed, 

# train/test split : 

# 0.8561944 T class, SOG > 0.96 replaced by med of group, 0.8669777 Tclass sog > 0.96 removed, 0.8976656  w/ NA -> mean, SOG, L, W, D, Cargo, TClasse, Status, SOG > q0.96 removed

# med : q > 0.96 default
# factor(TClass), Status               : 0.884735
# factor(Tclass), Status, SOG filtered : 0.8817886
# TClass, Status, SOG Filtered         : 0.8857681
# TClass, factor(Status), SOG Filtered : 0.8857681
# TClass, Status                       : 0.8857681
# TClass, Status, SOG removed q>0.94   : 0.9057053 #
# f(TClass, Status), SOG removed q>0.94: 0.84019
# f(TClass), Status, SOG removed q>0.94: 0.8376588


# mean : q > 0.96 default
# factor(TClass, Status)               : 0.8208954
# mean high SOG, factor(TClass, Status): 0.7918233
# mean high SOG, TClass, Status        : 0.8682674
# TClass, Status, high SOG filtered    : 0.8745645
# no filter, no factor, high SOG meaned: 0.8667761
# no factor, high SOG removed          : 0.8745645
# no factor, high SOG removed q>0.95   : 0.8935128
# no factor, high SOG removed q>0.94   : 0.8937666
# no factor, high SOG removed q>0.93   : 0.8935556