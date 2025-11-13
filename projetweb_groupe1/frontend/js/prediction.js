function getSelectedBateauData() {
  const selectedRadio = document.querySelector('input[name="select-bateau"]:checked');
  if (!selectedRadio) {
    alert("Veuillez sélectionner un bateau !");
    return null;
  }

  const row = selectedRadio.closest("tr");
  console.log(row);
  const rawData = row.getAttribute("data-bateau");
  console.log(rawData);
  
  try {
    // Nettoyage des guillemets problématiques
    const cleanData = rawData
      .replace(/^"/, '')  // Supprime le premier "
      .replace(/"$/, ''); // Supprime le dernier "
    
    return JSON.parse(cleanData);
  } catch (e) {
    console.error("Erreur de parsing JSON :", e);
    return null;
  }
}

function sendPredictionViaPost(endpoint, requiredFields) {
  const bateau = getSelectedBateauData();
  console.log(bateau);
  if (!bateau) {
    alert("Sélectionne un bateau !");
    return;
  }

  const form = document.createElement("form");
  form.method = "POST";
  form.action = endpoint;
  form.enctype = "application/x-www-form-urlencoded";;

  requiredFields.forEach(field => { // Ajout des champs requis
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = field;
    input.value = bateau[field] ?? "";
    form.appendChild(input);
  });

  const reloadInput = document.createElement("input");
  reloadInput.type = "hidden";
  reloadInput.name = "force_reload";
  reloadInput.value = "1";
  form.appendChild(reloadInput);

  document.body.appendChild(form);
  form.submit();
}

// Lier les boutons
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-type").addEventListener("click", () => {
    sendPredictionViaPost("../backend/api/predict_type.php", ["longueur", "largeur", "tirant_eau", "cargo"]);
  });

  document.getElementById("btn-trajectory").addEventListener("click", () => {
    sendPredictionViaPost("../backend/api/predict_traj.php", [
      "mmsi", "timestamp", "latitude", "longitude", "sog", "cog", "cap_reel", "longueur", "largeur", "tirant_eau", "cargo"
    ]);
  });
});
