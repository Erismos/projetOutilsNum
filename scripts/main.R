############################################################
# Titre      : Script Principal d'Analyse de Trafic Maritime
# Fichier    : main.R
# Description: Ce script principal orchestre le processus 
#              complet d'analyse des données maritimes, 
#              incluant le nettoyage des données, la 
#              génération de visualisations avancées et 
#              la création de cartes interactives.
#
# Version    : 1.0
# Auteurs    : Gabriel Boucneau & Laure Warlop & Clément Auvray
# Date       : Juin 2025
# Dépendances: scripts/data_cleaning.R, scripts/data_visualization.R, 
#              scripts/interactive_map.R
############################################################

# Import des dépendances
source("scripts/data_cleaning.R")
source("scripts/data_visualization.R")
source("scripts/interactive_map.R")

# exécuter les fonctions principales
main_data_cleaning()
generate_all_plots()
main_interactive_map()


