ajaxRequest("GET", "../backend/api/get_trajets.php", (data) => {
  renderMap(data);
}, "mmsi=all&vtype=all&etat=all");

function renderMap(data) {
  const trajetsParMMSI = {};
  const colors = {};
  const traces = [];

  data.forEach(point => {
    const mmsi = point.mmsi;
    if (!trajetsParMMSI[mmsi]) {
      trajetsParMMSI[mmsi] = { lat: [], lon: [], text: [], color: getColorForMMSI(mmsi) };
    }
    trajetsParMMSI[mmsi].lat.push(parseFloat(point.lat));
    trajetsParMMSI[mmsi].lon.push(parseFloat(point.lon));
    trajetsParMMSI[mmsi].text.push(
      `Nom : ${point.name}<br>MMSI : ${point.mmsi}<br>SOG : ${point.sog} kn<br>Date : ${point.time}<br>État : ${point.etat}`
    );
  });

  for (const mmsi in trajetsParMMSI) {
    const t = trajetsParMMSI[mmsi];
    traces.push({
      type: 'scattermapbox',
      mode: 'lines+markers',
      name: `MMSI ${mmsi}`,
      lat: t.lat,
      lon: t.lon,
      text: t.text,
      marker: { size: 6, color: t.color },
      line: { width: 2, color: t.color }
    });
  }

  const layout = {
    mapbox: {
      style: "open-street-map",
      center: { lat: 25, lon: -89 },
      zoom: 4
    },
    paper_bgcolor: "rgba(0, 0, 0, 0)",
    height: 500,
    showlegend: false,
    margin: {
      t: 0,
      r: 0,
      b: 0,
      l: 0
    },
  };

  Plotly.newPlot('carte-trajets', traces, layout, {responsive: true});
}

// Génère une couleur unique par MMSI
function getColorForMMSI(mmsi) {
  const seed = parseInt(String(mmsi).split('').reverse().join(''));
  const hue = seed % 360;
  const sat = 60 + (seed % 30);   // 60% à 89%
  const light = 45 + (seed % 20); // 45% à 64%
  return `hsl(${hue}, ${sat}%, ${light}%)`;
}


