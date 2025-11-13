<?php

header('Content-Type: application/json');

$nb_lines = 0;

$headers = "MMSI;BaseDateTime;LAT;LON;SOG;COG;VesselType;Heading;;";

$input_csv = "../../python/csv_files/input.csv";
$output_csv = "../../python/csv_files/output.csv";

$count_i = count(file($input_csv));
$count_o = count(file($output_csv));

$handle_i = fopen($input_csv, "w");
fwrite($handle_i, "");
fwrite($handle_i, $headers . "\n");
fclose($handle_i);

$handle_o = fopen($output_csv, "w");
fwrite($handle_o, "");
fwrite($handle_o, $headers . "\n");
fclose($handle_o);


function n_float($value) {
    if (is_float((float)$value) && strpos($value, '.') !== false) {
        return true;
    } else {
        return false;
    }
}

$mmsi = $_POST['mmsi'];
$f_date = $_POST['timestamp'];
$lat = $_POST['latitude'];
$lon = $_POST['longitude'];
$sog = $_POST['sog'];
$cog = $_POST['cog'];
$heading = $_POST['cap_reel'];

$features = [
  'length' => $_POST['longueur'] ?? null,
  'width' => $_POST['largeur'] ?? null,
  'draft' => $_POST['tirant_eau'] ?? null,
  'cargo' => $_POST['cargo'] ?? null
];
$vtype = shell_exec("/var/www/etu0607/venv/bin/python3.9 /var/www/etu0607/groupe1_projetweb/python/script_type.py --Length " . $features['length'] . " --Draft " . $features['draft'] . " --Width " . $features['width'] . " --Cargo " . $features['cargo']);
$vtype_2 = $vtype;


$mmsi_2 = $mmsi;

$is_not_ok = 0;
$issues = "";

$mmsi = $_POST["mmsi"];
if ($mmsi < 0 || $mmsi > 999999999) {
  //$is_not_ok == 997;
  $issues = $issues . "- MMSI non valide (expected 0 < mmsi < 999999999)<br>";
}
    
$f_date = $_POST['timestamp'];
$day = substr($f_date,8,2);
$mth = substr($f_date,5,2);
$yr = substr($f_date,0,4);
$hr = substr($f_date,11,2);
$min = substr($f_date,14,2);

$formatted_d = $day . "/" . $mth . "/" . $yr . " " . $hr . ":" . $min;

if ((int)$min == 60) {
  $min_2 = (int)$min - 1;
}
else {
  $min_2 = (int)$min + 1;
}

$formatted_d_2 = $day . "/" . $mth . "/" . $yr . " " . $hr . ":" . $min;


$lat = $_POST["latitude"];
if ((!n_float($lat) && is_int($lat)) || $lat < -90 || $lat > 90) {
  $is_not_ok = 1;
  $issues = $issues . "- Latitude non valide (entre -90 et 90, seulement un nombre de type 1.2345 est accepté avec un '.' comme décimal)<br>";
}

if ($lat < -89.99991) {
  $lat_2 = $lat + 0.00009;
}
else {
  $lat_2 = $lat - 0.00009;
}

$lon = $_POST["longitude"];
if ((!n_float($lon) && is_int($lon)) || $lon < -180 || $lon > 180) {
  $is_not_ok = 1;
  $issues = $issues . "- Longitude non valide (entre -180 et 180, seulement de nombre de type 1.2345 est accepté avec un '.' comme décimal)<br>";
}

if ($lon < -179.99991) {
  $lon_2 = $lat + 0.00009;
}
else {
  $lon_2 = $lon - 0.00009;
}

$sog = $_POST["sog"];
if ((!n_float($sog) && is_int($sog)) || $sog < 0) {
  $is_not_ok = 1;
  $issues = $issues . "- SOG non valide (SOG > 0 et seulement un nombre de type 1.2345 est accepté avec un '.' comme décimal)<br>";
}

$sog_2 = $sog;

$cog = $_POST["cog"];
if ((!n_float($cog) && is_int($cog))|| $cog < 0 || $cog > 360) {
  $is_not_ok = 1;
  $issues = $issues . "- COG non valide (0 < COG < 360 et seulement un nombre de type 1.2345 est accepté avec un '.' comme décimal)<br>";
}

$cog_2 = $cog;

$head = $_POST["cap_reel"];
if ($head < 0 || $head > 360) {
  $is_not_ok = 1;
  $issues = $issues . "- Cap réel non valide (valeurs entre 0 et 360 acceptées.)<br>Pour une liste des types de navires ainsi qu'une brève description, consultez ce site : " . '<a href="https://api.vesselfinder.com/docs/ref-aistypes.html" target="_blank">AIS Vessel Types</a>';
}

$head_2 = $head;

if ($is_not_ok) {
  echo $issues;
  return 0;
}
else {
  $line = implode(';', [
      $mmsi,
      $formatted_d,
      $lat,
      $lon,
      $sog,
      $cog,
      trim($vtype),
      $head
  ]);

  $line_2 = implode(';', [
      $mmsi_2,
      $formatted_d_2,
      $lat_2,
      $lon_2,
      $sog_2,
      $cog_2,
      trim($vtype_2),
      $head_2
  ]);

  // Écriture avec vérification
  $handle_i = fopen($input_csv, "a");
  if ($handle_i === false) {
      die(json_encode(['error' => "Impossible d'ouvrir le fichier CSV"]));
  }
  
  fwrite($handle_i, $line . "\n");
  fwrite($handle_i, $line_2 . "\n");
  fclose($handle_i);

  // Vérification du contenu écrit
  if (!file_exists($input_csv) || filesize($input_csv) === 0) {
      die(json_encode(['error' => "Échec de l'écriture dans le CSV"]));
  }

  $cmd = "/var/www/etu0607/venv/bin/python3.9 ../../python/script_trajectoire.py ../../python/csv_files/input.csv ../../python/csv_files/output.csv";
  $output = [];
  $return_var = 0;
  exec($cmd, $output, $return_var);

  $output[0] = str_replace("'", '"', $output[0]);
  $output[1] = str_replace("'", '"', $output[1]);


  if ($return_var !== 0) {
      echo json_encode(['error' => "Erreur Python (code $return_var)", 'output' => $output]);
  } else {
      // Sauvegarde le résultat pour la page de visualisation
      file_put_contents('../../frontend/output.json', implode("\n", $output));

      if (isset($_POST['force_reload'])) {
        header("Location: ../../frontend/resultat_prediction.php");
        exit;
      }

      echo implode("\n", $output); // Renvoie directement le JSON
  }
}
?>