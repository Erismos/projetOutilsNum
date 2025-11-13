// Variables globales pour la pagination
let currentPage = 1;
// let currentFilters = []; // Stocker les données filtrées

function renderTableBateaux(data){
  const tbody = document.getElementById("table-body");
  tbody.innerHTML = ""; // Clear existing rows

  data["data"].forEach(bateau => {
    const row = document.createElement("tr");
    row.setAttribute("data-bateau", JSON.stringify(bateau)); // stocke les données dans l'attribut<
    row.innerHTML = `
      <td>${bateau.mmsi}</td>
      <td>${bateau.timestamp}</td>
      <td>${bateau.latitude}</td>
      <td>${bateau.longitude}</td>
      <td>${bateau.sog ?? ""}</td>
      <td>${bateau.cog ?? ""}</td>
      <td>${bateau.cap_reel ?? ""}</td>
      <td>${bateau.nom ?? ""}</td>
      <td>${bateau.etat ?? ""}</td>
      <td>${bateau.longueur ?? ""}</td>
      <td>${bateau.largeur ?? ""}</td>
      <td>${bateau.tirant_eau ?? ""}</td>
      <td hidden>${bateau.tirant_eau ?? ""}</td>
      <td><input type="radio" name="select-bateau" data-mmsi="${bateau.mmsi}"></td>
    `;
    tbody.appendChild(row);
    
    // Ajouter un écouteur d'événement sur le radio button
    const radioBtn = row.querySelector('input[type="radio"]');
    radioBtn.addEventListener('change', function() {
      if (this.checked) {
        // Stocker les données du bateau sélectionné
        document.getElementById('selected-bateau').value = JSON.stringify(bateau);
      }
    });
  });
  document.getElementById("page-info").textContent = 'Page ' + currentPage + ' sur ' + data["total_pages"];
}

function changePage(dir){
  if (currentPage < 1) currentPage = 1;
  if (dir === 'prev' && currentPage > 1) {
    currentPage--;
  }
  else if (dir === 'next') {
    currentPage++;
    
  }
  // Requête AJAX pour récupérer les données de la page actuelle
  ajaxRequest('GET', '../backend/api/get_bateaux.php', (data) => {
    renderTableBateaux(data);
    if(currentPage == 1){
      document.getElementById("prev-page").disabled = true; // Désactiver le bouton précédent si on est à la première page
    }
    if(currentPage > 1){
      document.getElementById("prev-page").disabled = false; // Activer le bouton précédent si on n'est pas à la première page
    }
    if(currentPage >= data["total_pages"]){
      document.getElementById("next-page").disabled = true; // Désactiver le bouton suivant si on est à la dernière page
    }
    if(currentPage < data["total_pages"]){
      document.getElementById("next-page").disabled = false; // Activer le bouton suivant si on n'est pas à la dernière page
    }

  }, `page=${currentPage}&mmsi=${currentFilters[0]}&vtype=${currentFilters[1]}&etat=${currentFilters[2]}`);
  
}

ajaxRequest('GET', '../backend/api/get_bateaux.php', (data) => {
  renderTableBateaux(data);  
  currentFilters= ["all", "all", "all",50]; // Initialiser les filtres avec des valeurs par défaut
}, 'page=1&mmsi=all&vtype=all&etat=all&max_results=50');

// Écouteurs pour les boutons de pagination
document.getElementById("prev-page")?.addEventListener("click", () => changePage('prev'));
document.getElementById("next-page")?.addEventListener("click", () => changePage('next'));

document.getElementById("filter-mmsi").addEventListener("change", () => {
  currentPage = 1; // Reset to first page on filter change
  let mmsiFilter = document.getElementById("filter-mmsi").value;
  currentFilters[0] = mmsiFilter; // Update the filter value

  ajaxRequest("GET", "../backend/api/get_trajets.php", (data) => {
    renderMap(data);
  }, `mmsi=${currentFilters[0]}&vtype=${currentFilters[1]}&etat=${currentFilters[2]}`);
  ajaxRequest('GET', '../backend/api/get_bateaux.php', (data) => {
    renderTableBateaux(data);
  }, `page=${currentPage}&mmsi=${currentFilters[0]}&vtype=${currentFilters[1]}&etat=${currentFilters[2]}&max_results=50`);
});

document.getElementById("filter-vtype")?.addEventListener("change", () => {
  currentPage = 1; // Reset to first page on filter change
  let vtypeFilter = document.getElementById("filter-vtype").value;
  currentFilters[1] = vtypeFilter; // Update the filter value
  ajaxRequest("GET", "../backend/api/get_trajets.php", (data) => {
    renderMap(data);
  }, `mmsi=${currentFilters[0]}&vtype=${currentFilters[1]}&etat=${currentFilters[2]}`);
  ajaxRequest('GET', '../backend/api/get_bateaux.php', (data) => {
    renderTableBateaux(data);
  }, `page=${currentPage}&mmsi=${currentFilters[0]}&vtype=${currentFilters[1]}&etat=${currentFilters[2]}&max_results=50`);
});

document.getElementById("filter-etat")?.addEventListener("change", () => {
  currentPage = 1; // Reset to first page on filter change
  let etatFilter = document.getElementById("filter-etat").value;
  currentFilters[2] = etatFilter; // Update the filter value
  ajaxRequest("GET", "../backend/api/get_trajets.php", (data) => {
    renderMap(data);
  }, `mmsi=${currentFilters[0]}&vtype=${currentFilters[1]}&etat=${currentFilters[2]}`);
  ajaxRequest('GET', '../backend/api/get_bateaux.php', (data) => {
    renderTableBateaux(data);
  }, `page=${currentPage}&mmsi=${currentFilters[0]}&vtype=${currentFilters[1]}&etat=${currentFilters[2]}&max_results=50`);
});