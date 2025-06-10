# laure file

##############################################
########## EXPLORATION DES DONNÉES ###########
##############################################

# chargement des données
data <- read.csv("data/vessel-total-clean.csv")
print(dim(data))

# statistiques descrptives univariées

print(summary(data))
# on peut vérifier le type des données 
print(str(data))
# si on veut tester sur une variable numerique specifique, par exemple id
print(summary(data$id))
# si on veut lire les données caractérielle 
print(table(data$IMO))

# nettoyage des données

# valeurs manquantes
# les valeurs manquantes sont des \n et on doit les ramplacer par NA pour pouvoir après les supprimer
data[data == "\\N"] <- NA
print("valeurs manquantes :")
print(sum(is.na(data))) # on en a 326040
# on va les supprimer 
data <- na.omit(data)
# print(data_clean)
print("nombre de ligne et colonnes :")
print(dim(data)) # on en a 243530 lignes et 18 colonnes

# valeurs aberrantes 
# on prend que les valeurs numériques
data_numeric <- names(data)[sapply(data, is.numeric)]
for(i in data_numeric){
    # double crochet car un vecteur 
    q1 <- quantile(data[[i]], 0.25) # calcul du premier quantile
    q3 <- quantile(data[[i]], 0.75) # calcul du troisième quantile
    iqr <- q3 - q1
    inf <- q1-1.5*iqr
    sup <- q3+1.5*iqr
    # si les valeurs dans la colonne i sont hors de l'intervalle allors on remplace par NA
    data[[i]][data[[i]] < inf | data[[i]] > sup] <- NA # on remplace par NA pour pouvoir supprimer
}
# nombre de valeurs aberrrantes
print("valeurs aberrantes :")
print(sum(is.na(data))) # 45418 valeurs aberrantes
# on supprime les lignes avec les valeurs aberrantes 
data <- na.omit(data)
print(dim(data)) # 201729 lignes 

# doublons
duplicated(data)  # Renvoie TRUE pour les lignes dupliquées
# nombre de doublons
print("nombre de doublons")
print(sum(duplicated(data))) # 0 doublons 

