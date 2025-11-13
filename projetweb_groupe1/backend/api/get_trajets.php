<?php
require_once("../db/db_connect.php");

$conditions = [];
$params = [];

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

$sql = "
SELECT 
    p.mmsi,
    p.lat,
    p.lon,
    p.time,
    n.name,
    n.vtype,
    e.description AS etat,
    p.sog
FROM pos p
JOIN navire n ON p.mmsi = n.mmsi
JOIN etat e ON p.id_status = e.id_status
WHERE 1 = 1
$whereClause
ORDER BY p.mmsi, p.time
";

$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$data = $stmt->fetchAll(PDO::FETCH_ASSOC);

header('Content-Type: application/json');
echo json_encode($data);
?>

