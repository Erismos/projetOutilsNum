<div class="wrap">
<?php include("includes/header.php"); ?>
<script src="js/ajax.js"></script>
<link rel="stylesheet" href="css/style.css">

<div class="box">
    <h3 class="categorie">Filtres</h3>
    <div class="form-row">
        <div class="form-filter">
            <label>MMSI :</label>
            <select id="filter-mmsi">
                <option value="all">Tous</option>
            </select>
        </div>
        <div class="form-filter">
            <label>Type :</label>
            <select id="filter-vtype">
                <option value="all">Tous</option>
            </select>
            </div>
        <div class="form-filter">
            <label>État :</label>
            <select id="filter-etat">
                <option value="all">Tous</option>
            </select>
        </div>
    </div>
    
</div>





<div class="box map">
    <h2 class="categorie">Carte des trajectoires</h2>
    <div class="carte-trajets" id="carte-trajets">
        <!-- La carte sera générée ici par Plotly -->
    </div>
</div>

<div class="box" id="predictions">
  <button id="btn-type">Prédire le type</button>
  <button id="btn-trajectory">Prédire la trajectoire</button>
  <button><a id="btn-cluster" href="prediction_cluster.php">Cluster</a></button>
</div>



<div class="box">
    <h2 class="categorie">Tableau des Navires</h2>
    
    <div class="table-container">
    <table class="boat-table" id="table-bateaux">
        <thead>
            <tr>
                <th>MMSI</th>
                <th>Horodatage</th>
                <th>Latitude</th>
                <th>Longitude</th>
                <th>SOG</th>
                <th>COG</th>
                <th>Cap réel</th>
                <th>Nom</th>
                <th>État</th>
                <th>Longueur</th>
                <th>Largeur</th>
                <th>Tirant d’eau</th>
                <th hidden>cargo</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody id="table-body">
            <!-- Rempli en JS -->
        </tbody>
    </table>
    </div>
    <div class="pagination-controls">
        <button id="prev-page" disabled>Précédent</button>
        <span id="page-info">Page 1 sur 1</span>
        <button id="next-page">Suivant</button>
    </div>
</div>

<!-- Plotly -->
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>

<!-- Scripts -->
<script src="js/load_filters.js"></script>
<script src="js/tableau.js"></script>
<script src="js/prediction.js"></script>
<script src="js/carte.js"></script>


<?php include("includes/footer.php"); ?>
</div>
