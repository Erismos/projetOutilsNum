<div class="wrap">
<?php include("includes/header.php"); ?>
<!--<link rel="stylesheet" href="css/style.css">-->
<section>
    <h2>Prédiction du type des navires</h2>
    <form method="post" action="prediction_type.php">


        <label for="length"> Longeur du bateau (en mètre) :</label>
        <input type="number" id="length" name="length" step="0.1" required><br>

        <label for="width">Largeur du bateau (en mètre) :</label>
        <input type="number" id="width" name="width" step="0.1" required><br>

        <label for="draft">Tirant d'eau (en mètre) :</label>
        <input type="number" id="draft" name="draft" step="0.1" required><br>

        <label for="cargo">Code cargo :</label>
        <input type="number" id="cargo" name="cargo" step="1" required><br>
    
        
        <input type="submit" name="submit" value="Prédire le bateau">
    </form>

<?php





if(isset($_POST['submit'])) { //not args' fault 
    $length = floatval($_POST["length"]);
    $draft = floatval($_POST["draft"]);
    $width = floatval($_POST["width"]);
    $cargo = intval($_POST["cargo"]);

    $script = "../python/script_type.py";
    $cmd = "/var/www/etu0607/venv/bin/python3.9 $script  --Length $length --Draft $draft --Width $width --Cargo $cargo 2>&1";

    echo "<pre>Commande : $cmd\n</pre>";

    $output = [];
    $return_var = 0;
    exec($cmd, $output, $return_var);
    $res = exec($cmd);

    echo $res;
}


?>

    <div id="prediction">
    </div>

</section>

<?php include("includes/footer.php"); ?>
</div>