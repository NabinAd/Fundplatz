# Entwicklung von Fundplatz – zusammengefasster Verlauf

[← Zur Projektübersicht](../../README.md) · [Architektur](../../architecktur.md) · [Tests](../testing.md)

Dieser Ordner **fasst die alten Tages- und Fixdokumente inhaltlich zusammen**, statt sie unverändert hintereinanderzukopieren. Er dokumentiert die wesentlichen Schritte und Entscheidungen. **Verbindlich für Installation und aktuelle Funktionen** sind die [Haupt-README](../../README.md), die [Architektur](../../architecktur.md) und der aktuelle Code.

## Phase 1 – Web-Marktplatz (Tage 1–5)

**Ergebnis:** Die Grundlage der Django-Anwendung entstand mit Benutzerkonten, Katalog, Produktdetails, Anzeigenverwaltung, Suche/Filtern, Formularen und einer responsiven Oberfläche.

- **Tage 1–2:** Grundgerüst, Modell und erste Anzeigenübersicht und Detailseiten; Testlauf mit Django.
- **Tag 3:** Verkäuferbezogene Anzeigenverwaltung mit Erstellen, Bearbeiten und Löschen; eigene Inserate werden über Benutzerzuordnung geschützt.
- **Tag 4:** Erweiterungen an Suche, Formularen und Anzeigendarstellung; lokale Uploads, Zustands- und Filterangaben.
- **Tag 5:** Qualitätssicherung, Prüfung der Oberfläche, manueller Browserablauf und Vorbereitung der GitHub-Veröffentlichung.
- **Nacharbeiten:** Header-Abstände, Tastatur-Skip-Link, lokale statische CSS-Dateien, Cache-Busting und eine UI-/Designcheckliste.

**Heute relevante Dateien:** [`listings/models.py`](../../listings/models.py), [`listings/views.py`](../../listings/views.py), [`listings/forms.py`](../../listings/forms.py), [`templates/`](../../templates/), [`static/`](../../static/). Der Dateistand im Repository ist maßgeblich; ältere ZIP-Installationsbefehle aus den Rohnotizen sind nicht für Neuinstallationen gedacht.

## Weitere Phasen

- [**Phase 2 – Multi-Agenten-System**](phase2/README.md): lokale Ollama-Anbindung, strukturierte Eingaben, Routing, drei Agenten, Validierung und Evaluation.
- [**Phase 3 – End-to-End-Workflow**](phase3/README.md): Django-Brücke, Postfächer, menschliche Freigabe, Queue, Verlauf und Qualitätsnachweise.
- [**Fixes – konsolidierte Erkenntnisse**](fixes/README.md): konkrete Fehlerursachen, Korrekturen und verbleibende Grenzen.

## Herkunft und vollständige Rohnotizen

Die umfangreichen alten Tagesberichte wurden bereits in einem früheren Commit zusammengeführt. Ihre **Originalinhalte sind über die unveränderte Git-Historie weiter abrufbar**:

- [Frühere Phase-1-Notizen](https://github.com/NabinAd/Fundplatz/blob/4bfa6c25557b82b41a6af35e72eadc49b5ff84e1/docs/phase-1/README.md)
- [Frühere Phase-2-Notizen](https://github.com/NabinAd/Fundplatz/blob/4bfa6c25557b82b41a6af35e72eadc49b5ff84e1/docs/phase-2/README.md)
- [Frühere Phase-3- und Fixnotizen](https://github.com/NabinAd/Fundplatz/blob/4bfa6c25557b82b41a6af35e72eadc49b5ff84e1/docs/phase-3/README.md)

Hier stehen nur **konsolidierte Sachinformationen**, keine wiederholten PowerShell-/ZIP-Patchanleitungen und keine überholten Test-Erfolgsmeldungen.
