'use strict'

//------------------------------------------------------------------------------
//--- ajaxRequest --------------------------------------------------------------
//------------------------------------------------------------------------------
// Perform an Ajaxs request.
// \param type The type of the request (GET, DELETE, POST, PUT).
// \param url The url of the request.
// \param callback The callback to call when the request success.
// \param data The data associated with the request.
function ajaxRequest(type, url, callback, data = null)    //data = null permet de donner 3 ou 4 paramètre en entrée. Si on donne 3 paramètre, le quatrième (data) aura la valeur null
{
  // Create XML HTTP request.
  let xhr = new XMLHttpRequest();
  if (type == 'GET' && data != null) {
    url += '?' + data;
  }
  xhr.open(type, url);
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');

  // Add response handler.
  xhr.onload = () =>
  {
    switch (xhr.status)
    {
      case 200:
      case 201:
        console.log(xhr.responseText);                //affiche dans la console
        callback(JSON.parse(xhr.responseText));       //on renvoit la réponse en format JavaScript
        break;
      default:
        displayErrors(xhr.status);
    }
  };

  // Send XML HTTP request.
  xhr.send(data);
}

//------------------------------------------------------------------------------
//--- displayErrors ------------------------------------------------------------
//------------------------------------------------------------------------------
// Display an error message accordingly to an error code.
// \param errorCode The error code (HTTP status for example).
function displayErrors(errorCode)
{
  let messages = {
    400: 'Requête incorrecte',
    401: 'Authentifiez vous',
    404: 'Page non trouvée',
    500: 'Erreur interne du serveur',
    503: 'Service indisponible'
  };

  // Display error.
  if (messages[errorCode] != undefined)
    alert('Erreur : ' + messages[errorCode]);
}