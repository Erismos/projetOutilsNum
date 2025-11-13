# Interface Client - Serveur

## GET

### ***Récupération des bateaux***

> **GET** `/backend/api/get_bateaux.php`

➤ Aucun paramètre requis

➤ **Réponse :**

```json
[
  {
    "mmsi": ...,
    "timestamp": ...,
    "latitude": ...,
    "longitude": ...,
    "sog": ...,
    "cog": ...,
    "cap_reel": ...,
    "nom": ...,
    "etat": ...,
    "longueur": ...,
    "largeur": ...,
    "tirant_eau": ...
  },
  ...
]
```

---


### ***Récupération des états***

> `/backend/api/get_etats.php`

  ➤ **Requête** : *(aucun paramètre nécessaire)*

  ➤ **Réponse attendue** :

```json
[
    { "id_status": 1, "description": "En mer" },
    { "id_status": 2, "description": "Au port" },
    { "id_status": 3, "description": "En maintenance" },
    ...
]
```

---

### ***Prédire cluster bateau***

> **GET** `/backend/api/predict_cluster.php`

➤ Aucun paramètre requis (ou selon ton backend, potentiellement mmsi/lat/lon)

➤ **Réponse :**

```json
[
  {
    "mmsi": ...,
    "lon": ...,
    "lat": ...,
    "cluster": ...
  },
  ...
]
```

---

## POST

### ***Ajouter un bateau manuellement***

> **POST** `/backend/api/ajouter_bateau.php`

➤ Resultat formulaire :

```
mmsi=...&
nom=...&
longueur=...&
largeur=...&
tirant_eau=...&
timestamp=...&
latitude=...&
longitude=...&
sog=...&
cog=...&
cap_reel=...&
etat_id=...
```

➤ **Réponse :**

```json
{ "success": true }
// ou
{ "success": false, "error": "message" }
```

---

### ***Prédire trajectoire bateau***

> **POST** `/backend/api/predict_traj.php`

➤ Paramètres :

```
mmsi=...&
time=...&
lat=...&
lon=...&
sog=...&
cog=...&
vtype=...&
heading=...
```

➤ **Réponse :**

```json
[
  { "lat": ..., "lon": ... },
  ...
]
```

---

### ***Prédire type bateau***

> **POST** `/backend/api/predict_type.php`

➤ Paramètres :

```
length=...&
width=...&
draft=...&
cargo=...
```

➤ **Réponse :**

```json
[
  { "type": ... }
]
```

---

### ***Importer des données depuis un fichier CSV***

> **POST** `/backend/tools/import_csv.php`

➤ Paramètres :

```
number_of_lines=... // (optionnel, valeur par défaut = 100)
```

➤ **Réponse :**

```json
{ "status": "ok" }
// ou
{ "status": "error", "message": "..." }
```

