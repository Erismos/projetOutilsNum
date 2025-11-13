<?php

header('Content-Type: application/json');

$data = [
  'length' => $_POST['longueur'] ?? null,
  'width' => $_POST['largeur'] ?? null,
  'draft' => $_POST['tirant_eau'] ?? null,
  'cargo' => $_POST['cargo'] ?? null
];

$cmd = "/var/www/etu0607/venv/bin/python3.9 ../../python/script_type.py --Length " . $data['length'] . " --Draft " . $data['draft'] . " --Width " . $data['width'] . " --Cargo " . $data['cargo'];

$output = [];
$return_var = 0;
exec($cmd, $output, $return_var);

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


?>