ajaxRequest('GET', '../backend/api/get_etats.php', function(etats) {
    const select = document.getElementById("etat");
    etats.forEach(etat => {
        console.log(etat);
        const option = document.createElement("option");
        option.value = etat.id_status;
        option.textContent = etat.description;
        select.appendChild(option);
    });
}, null);