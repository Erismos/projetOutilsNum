<div class="wrap">
<?php include("includes/header.php"); ?>
<link rel="stylesheet" href="css/style.css">
<section>
    <h2>Prédiction de la trajectoire d'un navire</h2>
    <br>
    <h3>Veuillez saisir au moins 2 fois l'entiereté des données</h3>

    <form method="post" action="prediction_trajectoire.php">

        <label>MMSI: <input type="number" name="mmsi" placeholer="série de 9 chiffres" required></label><br>
        <label>Horodatage: <input type="datetime-local" name="timestamp" required></label><br>
        <label>Latitude: <input type="float" name="latitude" placeholder="Sous la forme 1.23456" required></label><br>
        <label>Longitude: <input type="float" name="longitude" placeholder="Sous la forme 1.23456" required></label><br>
        <label>SOG: <input type="float" name="sog" placeholder="Sous la forme 1.23456" required></label><br>
        <label>COG: <input type="float" name="cog" placeholder="Sous la forme 1.23456" required></label><br>
        <label>VesselType: <input type="number" name="vtype" required></label><br>
        <label>Cap réel: <input type="number" name="cap_reel" required></label><br>

        <input type="submit" name="submit" value="Ajouter au csv">
    </form>



    <div id="prediction">

<?php
$nb_lines = 0;

$headers = "MMSI;BaseDateTime;LAT;LON;SOG;COG;VesselType;Heading;;";

$input_csv = "../python/csv_files/input.csv";
$output_csv = "../python/csv_files/output.csv";

echo "bonjour";
$count_i = count(file(filename: $input_csv));
$count_o = count(file(filename: $output_csv));

if ($count_i < 3) {
    echo "<p>" . "Il manque " . (3 - $count_i) . " ligne(s).</p>";
}

if ($count_i == 0) {
    $handle_i = fopen($input_csv, "w");
    fwrite($handle_i, $headers . "\n");
    fclose($handle_i);
}
if ($count_o == 0) {
    $handle_o = fopen($output_csv, "w");
    fwrite($handle_o, $headers . "\n");
    fclose($handle_o);
}


function n_float($value) {
    if (is_float((float)$value) && strpos($value, '.') !== false) {
        return true;
    } else {
        return false;
    }
}

//what we want : 29/05/2023 00:00
//what we have : 2025-05-30T11:11

if(isset($_POST['submit'])) {
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
    
    $lat = $_POST["latitude"];
    if ((!n_float($lat) && is_int($lat)) || $lat < -90 || $lat > 90) {
        $is_not_ok = 1;
        $issues = $issues . "- Latitude non valide (entre -90 et 90, seulement un nombre de type 1.2345 est accepté avec un '.' comme décimal)<br>";
    }

    $lon = $_POST["longitude"];
    if ((!n_float($lon) &&  is_int($lon)) || $lon < -180 || $lon > 180) {
        $is_not_ok = 1;
        $issues = $issues . "- Longitude non valide (entre -180 et 180, seulement de nombre de type 1.2345 est accepté avec un '.' comme décimal)<br>";
    }

    $sog = $_POST["sog"];
    if ((!n_float($sog) &&  is_int($sog)) || $sog < 0) {
        $is_not_ok = 1;
        $issues = $issues . "- SOG non valide (SOG > 0 et seulement un nombre de type 1.2345 est accepté avec un '.' comme décimal)<br>";
    }

    $cog = $_POST["cog"];
    if ((!n_float($cog) &&  is_int($cog))|| $cog < 0 || $cog > 360) {
        $is_not_ok = 1;
        $issues = $issues . "- COG non valide (0 < COG < 360 et seulement un nombre de type 1.2345 est accepté avec un '.' comme décimal)<br>";
    }

    $vtype = $_POST["vtype"];
    if ($vtype < 0 || $vtype > 99) {
        $is_not_ok = 1;
        $issues = $issues . "- VesselType non valide (valeurs entre 0 et 99 acceptées.)<br>";
    }

    $head = $_POST["cap_reel"];
    if ($head < 0 || $head > 360) {
        $is_not_ok = 1;
        $issues = $issues . "- Cap réel non valide (valeurs entre 0 et 360 acceptées.)<br>Pour une liste des types de navires ainsi qu'une brève description, consultez ce site : " . '<a href="https://api.vesselfinder.com/docs/ref-aistypes.html" target="_blank">AIS Vessel Types</a>';
    }

    if ($is_not_ok) {
        echo $issues;
        return 0;
    }
    else {
            $line = $mmsi . ";" . $formatted_d . ";" . $lat . ";" . $lon . ";" . $sog . ";" . $cog . ";" . $vtype . ";" . $head . ";;";
            echo $line;
            $handle_i = fopen($input_csv, "a");
            fwrite($handle_i, $line . "\n");
            fclose($handle_i);

            $pred_traj = "../python/script_trajectoire.py";
            $res = exec("python $pred_traj ../python/csv_files/input.csv ../python/csv_files/output.csv");
            echo "resultat : " . $res;
    }

    //../python/script_type.py
}
?>

    </div>
</section>


<?php include("includes/footer.php"); ?>
</div>