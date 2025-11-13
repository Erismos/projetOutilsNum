<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Gestion Navires - Ajout & Import CSV</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="css/style.css" />
    <script src="js/ajax.js" defer></script>
    <script src="js/load_etats.js" defer></script>
</head>
<body>
<div class="wrap">

    <?php include("includes/header.php"); ?>

    <!-- Formulaire ajout bateau -->
    <form action="../backend/api/ajouter_bateau.php" method="POST" class="formulaire">
        <div>
            <h3 class="categorie">Informations du navire</h3>
            
            <div class="form-container">
                <div class="form-group">
                    <label for="mmsi">MMSI:</label>
                    <input type="number" id="mmsi" name="mmsi" required>
                </div>
                <div class="form-group">
                    <label for="nom">Nom:</label>
                    <input type="text" id="nom" name="nom" required>
                </div>
                <div class="form-group">
                    <label for="longueur">Longueur:</label>
                    <input type="text" id="longueur" name="longueur" required>
                </div>
                <div class="form-group">
                    <label for="largeur">Largeur:</label>
                    <input type="text" id="largeur" name="largeur" required>
                </div>
                <div class="form-group">
                    <label for="tirant_eau">Tirant d’eau:</label>
                    <input type="text" id="tirant_eau" name="tirant_eau" required>
                </div>
            </div>
        </div>
        <div>
            <h3 class="categorie">Données de position</h3>

            <div class="form-container">
                <div class="form-group">
                    <label for="timestamp">Horodatage:</label>
                    <input type="datetime-local" id="timestamp" name="timestamp" required>
                </div>
                <div class="form-group">
                    <label for="latitude">Latitude:</label>
                    <input type="text" id="latitude" name="latitude" required>
                </div>
                <div class="form-group">
                    <label for="longitude">Longitude:</label>
                    <input type="text" id="longitude" name="longitude" required>
                </div>
                <div class="form-group">
                    <label for="sog">SOG:</label>
                    <input type="text" id="sog" name="sog" required>
                </div>
                <div class="form-group">
                    <label for="cog">COG:</label>
                    <input type="text" id="cog" name="cog" required>
                </div>
                <div class="form-group">
                    <label for="cap_reel">Cap réel:</label>
                    <input type="text" id="cap_reel" name="cap_reel" required>
                </div>
                <div class="form-group">
                    <label for="etat">État:</label>
                    <select name="etat_id" id="etat" required>
                        <option value="">Sélectionnez un état</option>
                            <!-- Options chargées via JS -->
                    </select>
                </div>
            </div>
        </div>
        <input type="submit" value="Ajouter le bateau">
    </form>

    <!-- Section Import CSV -->
    <div class="csv">
        <h3 class="categorie">Importer un fichier CSV AIS</h3>
        <form action="../backend/tools/import_csv.php" method="post">
            <label for="number_of_lines">Nombre de lignes à importer (100 par défaut) :</label>
            <input type="number" id="number_of_lines" name="number_of_lines" value="100" min="0">
            <br><br>
            <input type="submit" value="Importer les données CSV">
        </form>
    </div>

    <?php include("includes/footer.php"); ?>

</div>
</body>
</html>
