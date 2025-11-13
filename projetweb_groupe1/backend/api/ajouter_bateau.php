<?php
require_once("../db/db_connect.php");

if (
    isset($_POST['mmsi'], $_POST['nom'], $_POST['longueur'], $_POST['largeur'], $_POST['tirant_eau'],
          $_POST['timestamp'], $_POST['latitude'], $_POST['longitude'], $_POST['sog'],
          $_POST['cog'], $_POST['cap_reel'], $_POST['etat_id'])
) {
    $mmsi = $_POST['mmsi'];
    $nom = $_POST['nom'];
    $longueur = $_POST['longueur'];
    $largeur = $_POST['largeur'];
    $tirant_eau = $_POST['tirant_eau'];

    $timestamp = $_POST['timestamp'];
    $latitude = $_POST['latitude'];
    $longitude = $_POST['longitude'];
    $sog = $_POST['sog'];
    $cog = $_POST['cog'];
    $cap_reel = $_POST['cap_reel'];
    $etat_id = $_POST['etat_id'];

    // Vérifier si le navire existe déjà
    $check = $pdo->prepare("SELECT COUNT(*) FROM navire WHERE mmsi = ?");
    $check->execute([$mmsi]);

    if ($check->fetchColumn() == 0) {
        // Insérer dans navire
        $insertNavire = $pdo->prepare("INSERT INTO navire (mmsi, name, length, width, draft, vtype)
                                       VALUES (?, ?, ?, ?, ?, 0)");
        $insertNavire->execute([$mmsi, $nom, $longueur, $largeur, $tirant_eau]);
    }

    // Insérer dans pos
    $insertPos = $pdo->prepare("INSERT INTO pos (id_pos, etat, lon, lat, time, sog, cog, heading, mmsi, mmsi_navire, id_status)
                                VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");
    $insertPos->execute([
        $etat_id, $longitude, $latitude, $timestamp, $sog, $cog, $cap_reel,
        $mmsi, $mmsi, $etat_id
    ]);

    echo "Bateau et position ajoutés avec succès.";
    echo "<br><a href='../../frontend/ajout.php'>Retour</a>";

} else {
    echo "Erreur : données manquantes.";
}
?>
