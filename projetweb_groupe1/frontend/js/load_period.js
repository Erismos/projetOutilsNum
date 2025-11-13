ajaxRequest("GET", "../backend/api/get_periode.php", (data) => {
    const periodeSelect = document.getElementById("filter-debut");
    periodeSelect.innerHTML = '<option value="all">Toutes les dates</option>';
    data.forEach(item => {
        const option = document.createElement("option");
        option.value = item.time;
        option.textContent = item.time;
        periodeSelect.appendChild(option);
    });
}, null);

ajaxRequest("GET", "../backend/api/get_periode.php", (data) => {
    const periodeSelect = document.getElementById("filter-fin");
    periodeSelect.innerHTML = '<option value="all">Toutes les dates</option>';
    data.forEach(item => {
        const option = document.createElement("option");
        option.value = item.time;
        option.textContent = item.time;
        periodeSelect.appendChild(option);
    });
}, null);

function getSelectedPeriod() {
    const debut = document.getElementById("filter-debut").value;
    const fin = document.getElementById("filter-fin").value;
    return { debut, fin };
}

function loadClusterData() {
    const { debut, fin } = getSelectedPeriod();
    if (debut !== "all" && fin !== "all") {
        if (fin < debut) {
            alert("La date de fin ne peut pas être antérieure à la date de début.");
            return; // on ne fait rien, on bloque la requête
        }
    }
    // Construire l'URL avec les paramètres GET
    const url = new URL("../backend/api/predict_cluster.php", window.location.href);
    if (debut && debut !== "all") url.searchParams.append("start", debut);
    if (fin && fin !== "all") url.searchParams.append("end", fin);

    fetch(url)
    .then(res => res.text())
    .then(text => {
        try {
            const data = JSON.parse(text);
            map(data);
        } catch (e) {
            console.error("Erreur de parsing JSON :", e);
        }
    });
}

// Au chargement, charger la carte
document.addEventListener("DOMContentLoaded", () => {
    loadClusterData();

    // Quand on change un filtre, on recharge les données
    document.getElementById("filter-debut").addEventListener("change", loadClusterData);
    document.getElementById("filter-fin").addEventListener("change", loadClusterData);
});
