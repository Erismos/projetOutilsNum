<div class="wrap">
<?php include("includes/header.php"); ?>
<link rel="stylesheet" href="css/style.css">
<script src="js/ajax.js"></script>
<section>
    
    <div class="box">
        <h3 class="categorie">Filtre par période</h3>
        <div class="form-row">
            <div class="form-filter">
                <label>Date de début :</label>
                <select id="filter-debut">
                    <option value="all">Toutes les dates</option>
                </select>
            </div>
            
            <div class="form-filter">
                <label>Date de fin :</label>
                <select id="filter-fin">
                    <option value="all">Toutes les dates</option>
                </select>
            </div>
        </div>
    </div>
    <div class="box map">
        <h2 class="categorie">Analyse de cluster des navires</h2>
        <div id="cluster" class="carte-trajets">
            <!-- Intégration de l'analyse de cluster ici -->
        </div>
    </div>
</section>
<!-- Plotly -->
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>

<!-- Scripts -->
<script src="js/load_period.js"></script>
<script src="js/cluster.js"></script>

<?php include("includes/footer.php"); ?>
</div>
