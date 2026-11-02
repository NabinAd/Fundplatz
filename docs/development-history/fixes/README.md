# Konsolidierte Fixes und Erkenntnisse

[← Entwicklungsgeschichte](../README.md) · [Tests](../../testing.md)

Diese Seite fasst die früheren `FIX_*`-, `README_*TESTFIX*`-, Status- und Layoutkorrekturen **thematisch** zusammen. Sie zeigt die **Fehlerursache und die beabsichtigte Lösung**, nicht einzelne Patch-ZIP-Befehle. Alte Testzahlen sind historische Zwischenstände; der aktuelle Nachweis steht in [Testing](../../testing.md).

## Oberfläche und HTML-Sicherheit

- **Header-/Layoutkorrekturen:** Skip-Link für Tastaturbedienung, verlässlicher Abstand zwischen Header und Inhalt, korrigierte responsive Darstellung sowie ein CSS-Versionsparameter zur Cache-Aktualisierung.
- **XSS-Testkollision:** Ältere Tests suchten pauschal nach einem `<script>`-Tag und meldeten dadurch legitimes Inline-JavaScript als Fehler. Die Korrektur lagerte das Seiten-Refresh-Skript nach [`static/js/inquiry_processing_refresh.js`](../../../static/js/inquiry_processing_refresh.js) aus, **ohne** die Escaping-Schutzprüfungen für Nutzertexte aufzuweichen.
- **Käuferfreundliche Formulierung:** Der ursprüngliche technische Entwurf bleibt sichtbar und unverändert; daneben wird ein besser lesbarer, regelbasierter Vorschlag angeboten. Die Verkäuferfassung kann separat bearbeitet werden.

## Zustände, Berechtigungen und Queue

- **Verkäuferpostfach und Statusfilter:** Anzeige des Queue-Status (`queued/running/ready/failed`) und Unterscheidung von technischer Verarbeitung und fachlicher Verkäuferfreigabe. Frühere Tests mit veralteten Statusformulierungen wurden angepasst.
- **Asynchrone Regressionen:** Worker-Fortschritt und Fehlerpfade sollen den Verkäuferstatus nicht fälschlich als erfolgreich markieren. `failed` statt `ready` bei unerwarteten Fehlern; relevante Zeitpunkte und Verlaufsereignisse werden ergänzt.
- **Anfrage-Limit:** Ein älterer Rate-Limit-Test wurde an die beabsichtigte Regel von höchstens fünf Anfragen pro Stunde angepasst; der Zweck ist die Begrenzung massenhafter Anfragen, kein vollständiger Missbrauchsschutz.
- **Verlaufstests:** Testannahmen an die tatsächliche getrennte Sichtbarkeit von Käufer- und Verkäuferereignissen angepasst. Bereitgestellte Antworten bleiben gespeicherte Text-Snapshots.

## Prüfungen und Reparaturstand

Die früheren Dokumente beschreiben unter anderem Zwischenstände mit **fünf fehlgeschlagenen Django-Tests**, temporäre Status-Regressionen und deren gezielte Korrekturen. Diese Fehler nicht als aktuell offen verstehen, ohne sie auf dem neuesten Code-Stand neu auszuführen. Der letzte dokumentierte lokale Nachweis vom 27. Oktober 2026 nennt 430 bestandene Django-Tests und 281 bestandene Agententests; die manuelle End-to-End-Abnahme war weiterhin offen.

Die eigentlichen Regressionstests und die Umsetzung bleiben vollständig erhalten:

- [Django-Tests](../../../listings/) · [Agenten-Tests](../../../agent_system/tests/)
- [Event-Logik](../../../listings/inquiry_timeline.py) · [Queue](../../../listings/draft_queue.py)
- [Version mit vollständigen alten Fixnotizen](https://github.com/NabinAd/Fundplatz/blob/4bfa6c25557b82b41a6af35e72eadc49b5ff84e1/docs/phase-3/README.md)
- [Originale Phase-1-Layoutnotizen](https://github.com/NabinAd/Fundplatz/blob/4bfa6c25557b82b41a6af35e72eadc49b5ff84e1/docs/phase-1/README.md)

**Hinweis zur Änderung:** Das Konsolidieren löscht die alten Rohnotizen aus dem *aktuellen* Dateibaum, nicht aus der Git-Historie und nicht den eigentlichen Code. Veraltete lokale ZIP-Patchschritte werden bewusst nicht wiederholt.
