<?php
$result_file = "output.json";

if (!file_exists($result_file)) {
    die("<div class='error'>Aucun résultat de prédiction trouvé.</div>");
}

$result = json_decode(file_get_contents($result_file), true);
echo $result[0] . $result[1];

?>

<div class="wrap">
<?php include("includes/header.php"); ?>
<link rel="stylesheet" href="css/style.css">

<section>
    <h2>Résultat de la prédiction :</h2>
    <div id="prediction">
      <p></p>
    </div>
</section>

<?php include("includes/footer.php"); ?>
</div>