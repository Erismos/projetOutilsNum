<?php
    require_once("../db/db_connect.php");
    $stmt = $pdo->query("SELECT DISTINCT(p.time) AS time FROM pos p WHERE MINUTE(p.time) % 10 = 0 AND SECOND(p.time) = 0 ORDER BY p.time ASC");
    $results = $stmt->fetchAll(PDO::FETCH_ASSOC);
    header('Content-Type: application/json');
    echo json_encode($results);
?>