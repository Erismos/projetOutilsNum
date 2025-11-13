<?php
require_once("../db/db_connect.php");

$page = (isset($_GET["page"]) && is_numeric($_GET["page"]) && $_GET["page"] >= 1) ? (int)$_GET["page"] : 1;

$conditions = [];
$params = [];

if(isset($_GET["max_results"]) && $_GET["max_results"] === "all"){
    $limit = "";
}
else {
    $limit = " LIMIT 25 OFFSET " . (($page - 1) * 25);
}

if ($_GET["mmsi"] != "all" && !empty($_GET["mmsi"])) {
    $conditions[] = "p.mmsi = :mmsi";
    $params["mmsi"] = $_GET["mmsi"];
}

if ($_GET["vtype"] != "all" && !empty($_GET["vtype"])) {
    $conditions[] = "n.vtype = :vtype";
    $params["vtype"] = $_GET["vtype"];
}

if ($_GET["etat"] !== "all" && !empty($_GET["etat"])) {
    $conditions[] = "p.id_status = :etat";
    $params["etat"] = $_GET["etat"];
}

$whereClause = "";
if (!empty($conditions)) {
    $whereClause = " AND " . implode(" AND ", $conditions);
}

// Requête pour récupérer les données paginées
$sql = "
SELECT 
    p.mmsi AS mmsi,
    p.time AS timestamp,
    p.lat AS latitude,
    p.lon AS longitude,
    p.sog AS sog,
    p.cog AS cog,
    p.heading AS cap_reel,
    n.name AS nom,
    p.id_status AS etat,
    n.length AS longueur,
    n.width AS largeur,
    n.draft AS tirant_eau,
    n.cargo AS cargo
FROM pos p
JOIN navire n ON p.mmsi = n.mmsi
WHERE 1 = 1
$whereClause
ORDER BY p.time DESC" . $limit;

$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$bateaux = $stmt->fetchAll(PDO::FETCH_ASSOC);

// Requête pour compter le nombre total de résultats
$countSql = "
SELECT COUNT(*) 
FROM pos p
JOIN navire n ON p.mmsi = n.mmsi
WHERE 1 = 1
$whereClause";

$countStmt = $pdo->prepare($countSql);
$countStmt->execute($params);
$totalCount = $countStmt->fetchColumn();

// Retour JSON
header('Content-Type: application/json');
echo json_encode([
    "total_pages" => ceil($totalCount/25),
    "data" => $bateaux
]);
?>
