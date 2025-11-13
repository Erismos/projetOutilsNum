ajaxRequest("GET", "../backend/api/get_mmsi.php", (data) => {
    const mmsiSelect = document.getElementById("filter-mmsi");
    mmsiSelect.innerHTML = '<option value="all">Tous</option>';

    data.forEach(item => {
        const option = document.createElement("option");
        option.value = item.mmsi;
        option.textContent = item.mmsi;
        mmsiSelect.appendChild(option);
    });
}, null);

ajaxRequest("GET", "../backend/api/get_vtype.php", (data) => {
    const vtypeSelect = document.getElementById("filter-vtype");
    vtypeSelect.innerHTML = '<option value="all">Tous</option>';

    data.forEach(item => {
        const option = document.createElement("option");
        option.value = item.vtype;
        option.textContent = item.vtype;
        vtypeSelect.appendChild(option);
    });
}, null);

ajaxRequest("GET", "../backend/api/get_etats.php", (data) => {
    const etatSelect = document.getElementById("filter-etat");
    etatSelect.innerHTML = '<option value="all">Tous</option>';

    data.forEach(item => {
        const option = document.createElement("option");
        option.value = item.id_status;
        option.textContent = item.id_status;
        etatSelect.appendChild(option);
    });
}, null);

