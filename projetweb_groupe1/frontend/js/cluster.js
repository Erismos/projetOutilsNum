let allData = [];

fetch("../backend/api/predict_cluster.php")
  .then(res => res.text())
  .then(text => {
    console.log("Réponse brute PHP :", text);
    try {
      const data = JSON.parse(text);
      console.log("Nombre de points reçus :", data.length);
      console.log("Premier point :", data[0]);
      map(data);
    } catch (e) {
      console.error("Erreur de parsing JSON :", e);
    }
});

function map(data) {
    console.log("Données reçues :", data);
    const clusters = {};

    const clusterDescriptions = {
        0: "Arrêt - cap ~305°",
        1: "Quasi-immobile - cap ~158°",
        2: "Navigation rapide - cap ~277°",
        3: "Très lent - cap ~290°",
        4: "Navigation rapide - cap ~106°",
        5: "Mouvement lent - cap ~93°",
        6: "Presque à l'arrêt - cap ~269°",
        7: "Très lent - cap ~57°"
    };


    // Regroupe les points par cluster
    data.forEach(point => {
        const cluster = point.cluster;
        const mmsi = point.mmsi;
        const lat = parseFloat(point.lat);
        const lon = parseFloat(point.lon);

        if (!clusters[cluster]) {
            clusters[cluster] = {
                lat: [],
                lon: [],
                text: [],
                color: getColorForCluster(cluster)
            };
        }

        clusters[cluster].lat.push(lat);
        clusters[cluster].lon.push(lon);
        clusters[cluster].text.push(`MMSI : ${mmsi}<br>Cluster : ${cluster}<br>${clusterDescriptions[cluster] || ""}<br>LAT : ${lat}<br>LON : ${lon}`);
    });

    // Crée une trace par cluster pour permettre l'affichage de la légende
    const traces = Object.entries(clusters).map(([cluster, points]) => ({
        type: "scattermapbox",
        mode: "markers",
        name: `Cluster ${cluster}: ${clusterDescriptions[cluster] || ""}`,
        lat: points.lat,
        lon: points.lon,
        text: points.text,
        marker: {
            size: 8,
            color: points.color,
            opacity: 0.8
        },
        hoverinfo: 'text' 
    }));

    const layout = {
        mapbox: {
            style: "open-street-map",
            center: {
                lat: 25,
                lon: -89
            },
            zoom: 4
        },
        height: 500,
        margin: { t: 0, r: 0, b: 0, l: 0 },
        paper_bgcolor: 'rgba(0,0,0,0)', // transparent
        legend: {
            title: { text: "Clusters" },
            orientation: "v",
            x: 0,
            y: 1,
            bgcolor: "rgba(255,255,255,0.8)",   
            bordercolor: "#333",                
            borderwidth: 1                      
        }
    };

    Plotly.newPlot("cluster", traces, layout, { responsive: true });
}

// couleur par cluster
function getColorForCluster(cluster) {
    const colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22", "#17becf"
    ];
    return colors[cluster % colors.length] || "#000000"; // Noir si hors limite
}

