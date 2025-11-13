<?php
require_once("../db/db_connect.php");

$filename = "../../python/data/export_IA.csv";

if (!file_exists($filename)) {
    die("Fichier CSV introuvable.");
}

$handle = fopen($filename, "r");
if (!$handle) {
    die("Impossible d’ouvrir le fichier.");
}

if (isset($_POST['number_of_lines']) && is_numeric($_POST['number_of_lines'])) {
    $numberOfLines = (int)$_POST['number_of_lines'];
} else {
    $numberOfLines = 100; // Par défaut, importer 100 lignes
}

// Lire l'en-tête
$header = fgetcsv($handle, 1000, ",");

$ligne = 0;
while (($row = fgetcsv($handle, 1000, ",")) !== false) {
    $ligne++;

    // Associer les colonnes par index
    $mmsi        = $row[1];
    $timestamp   = $row[2];
    $lat         = $row[3];
    $lon         = $row[4];
    $sog         = $row[5];
    $cog         = $row[6];
    $heading     = $row[7];
    $name        = $row[8];
    $vtype       = $row[11];
    $status      = $row[12];
    $length      = $row[13];
    $width       = $row[14];
    $draft       = $row[15];
    $cargo       = $row[16];


    try {
        // Insérer état si non existant
        $stmtEtat = $pdo->prepare("SELECT id_status FROM etat WHERE id_status = ?");
        $stmtEtat->execute([$status]);
        $etatId = $stmtEtat->fetchColumn();

        if ($etatId === false) {
            $insertEtat = $pdo->prepare("INSERT INTO etat (id_status, description) VALUES (?,'Inconnue')");
            $insertEtat->execute([$status]);
            $etatId = $pdo->lastInsertId();
        }

        // Insérer navire si non existant
        $stmtNavire = $pdo->prepare("SELECT COUNT(*) FROM navire WHERE mmsi = ?");
        $stmtNavire->execute([$mmsi]);
        if ($stmtNavire->fetchColumn() == 0) {
            $insertNavire = $pdo->prepare("INSERT INTO navire (mmsi, name, length, width, draft, cargo, vtype)
                                           VALUES (?, ?, ?, ?, ?, ?, ?)");
            $insertNavire->execute([$mmsi, $name, $length, $width, $draft, $cargo, $vtype]);
        }

        // Insérer position
        $insertPos = $pdo->prepare("INSERT INTO pos (id_pos, lon, lat, time, sog, cog, heading, mmsi, id_status)
                                    VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)");
        $insertPos->execute([
            $lon, $lat, $timestamp, $sog, $cog, $heading,
            $mmsi, $etatId
        ]);
    } catch (PDOException $e) {
        echo "Ligne $ligne : " . $e->getMessage() . "<br>";
    }
    if ($ligne >= $numberOfLines && $numberOfLines > 0) break;
}

fclose($handle);
echo "Import terminé avec succès.";
