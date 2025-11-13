<?php
ini_set('display_errors', 0);
error_reporting(0);
require_once("../db/db_connect.php");

$start = isset($_GET['start']) ? $_GET['start'] : null;
$end = isset($_GET['end']) ? $_GET['end'] : null;

// Requête SQL
// $sql = "SELECT p.mmsi, p.sog, p.cog, p.heading, p.lat, p.lon, p.time FROM pos p ORDER BY p.mmsi";
$sql = "SELECT p1.mmsi, p1.sog, p1.cog, p1.heading, p1.lat, p1.lon, p1.time
FROM pos p1
INNER JOIN (
    SELECT mmsi, MAX(time) AS maxtime
    FROM pos
    WHERE 1=1 ";
$params = [];

if ($start && $start !== 'all') {
    $params['start'] = $start;
    $sql .= " AND time >= :start ";
}
if ($end && $end !== 'all') {
    $params['end'] = $end;
    $sql .= " AND time <= :end ";
}

$sql.= "GROUP BY mmsi
) p2 ON p1.mmsi = p2.mmsi AND p1.time = p2.maxtime
ORDER BY p1.mmsi
LIMIT 140";

// $stmt = $pdo->query($sql);
$stmt = $pdo->prepare($sql);
$stmt->execute($params);
$data = $stmt->fetchAll(PDO::FETCH_ASSOC);

// Préparation des tableaux pour Python
$sogs = [];
$cogs = [];
$headings = [];
$data_mmsi_lat_lon = [];

foreach ($data as $row) {
    $sogs[] = $row['sog'];
    $cogs[] = $row['cog'];
    $headings[] = $row['heading'];
    $data_mmsi_lat_lon[] = [
        "mmsi" => $row['mmsi'],
        "lat" => $row['lat'],
        "lon" => $row['lon']
    ];
}

$sog_str = implode(',', $sogs);
$cog_str = implode(',', $cogs);
$heading_str = implode(',', $headings);

// Exécution script Python
$pred_cl = realpath("../../python/script_cluster.py");
if (!$pred_cl) {
    http_response_code(500);
    error_log(realpath("../python/script_cluster.py"));
    echo json_encode(['error' => 'Script Python introuvable']);
    exit;
}
// $cmd = escapeshellcmd("python3 $pred_cl --sog \"$sog_str\" --cog \"$cog_str\" --heading \"$heading_str\"");
$cmd = "python3 " . escapeshellarg($pred_cl) .
    " --sog " . escapeshellarg($sog_str) .
    " --cog " . escapeshellarg($cog_str) .
    " --heading " . escapeshellarg($heading_str) .
    " 2>&1";  // Important pour capturer stderr
exec($cmd, $output, $return_var);

error_log("Commande : $cmd");
error_log("Code retour : $return_var");
error_log("Sortie : " . implode("\n", $output));

// $clusters_json = implode("", $output); // Concatène les lignes de sortie
// $clusters = json_decode($clusters_json, true); // Décode le JSON

// Chercher la première ligne qui contient JSON (commence par '[')
$clusters_json = '';
foreach ($output as $line) {
    $line = trim($line);
    if (strpos($line, '[') === 0) {
        $clusters_json = $line;
        break;
    }
}

$clusters = json_decode($clusters_json, true);

if (!is_array($clusters)) {
    header('Content-Type: application/json');
    echo json_encode([
        'error' => 'Erreur de décodage JSON ou sortie vide du script Python',
        'raw_output' => $clusters_json,
    ]);
    exit;
}

// Construction des résultats
$result = [];
for ($i = 0; $i < count($clusters); $i++) {
    $result[] = [
        "mmsi" => $data[$i]["mmsi"],
        "lat" => $data[$i]["lat"],
        "lon" => $data[$i]["lon"],
        "cluster" => $clusters[$i]["cluster"] ?? null // si le cluster n'existe par pour une ligne, on met null
    ];
}

// Renvoyer JSON
header('Content-Type: application/json');
echo json_encode($result);
exit;

?>


