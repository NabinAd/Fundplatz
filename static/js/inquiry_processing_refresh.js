/* Fundplatz: Verkäuferdetail nur während queued/running automatisch aktualisieren.
 * Der Status kommt als festes HTML-Datenattribut; keine Auswertung von Kundentext.
 */
(function () {
  "use strict";
  if (!document.querySelector('[data-ai-processing-pending="true"]')) {
    return;
  }
  window.setTimeout(function () {
    window.location.reload();
  }, 5000);
}());
