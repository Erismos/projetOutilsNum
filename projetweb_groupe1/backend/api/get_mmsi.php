<?php
    require_once("../db/db_connect.php");
    $stmt = $pdo->query("SELECT mmsi FROM  navire ORDER BY mmsi ASC");
    $results = $stmt->fetchAll(PDO::FETCH_ASSOC);

    header('Content-Type: application/json');
    echo json_encode($results);
?>