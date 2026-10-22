# Fundplatz – Design-Abnahme

Diese Aktualisierung verändert nur Templates, CSS und README. Die Datenbank, Modelle, Views und Tests bleiben unverändert.

1. Auf `http://127.0.0.1:8000/` Startseite bei 1440 px, 1024 px und 375 px Breite prüfen.
2. Bei 375 px **Menü** öffnen: Startseite, Anzeigen, Login/Registrieren bzw. Meine Anzeigen und Abmelden müssen erreichbar sein.
3. Unter **Alle Anzeigen** bei etwa 1024 px kontrollieren, dass der Button **Suchen** nicht abgeschnitten wird.
4. Anzeige mit langem Titel erstellen: Produktkarte und Detailseite dürfen nicht horizontal überlaufen.
5. Unter **Meine Anzeigen** auf dem Smartphone alle Aktionen (Ansehen, Deaktivieren, Bearbeiten, Löschen) prüfen.
6. Tastaturtest mit Tab / Enter: Menü, Links, Formularfelder und Buttons müssen bedienbar sein.
7. Tests ausführen: `.\.venv\Scripts\python.exe manage.py test listings` (64 Tests erwartet).
8. Bei Problemen CSS/HTML aus `git diff` prüfen; mit `git restore` lassen sich uncommittete Änderungen rückgängig machen.

**GitHub-Auftritt:** Nach erfolgreichem lokalen Test README + UI-Dateien committen und pushen. In GitHub unter *About → Edit* zusätzlich Beschreibung `Responsiver Django-Marketplace mit SQLite – Projektbasis für ein lokales Multi-Agent-System` und Themen `django`, `python`, `sqlite`, `bootstrap`, `marketplace`, `ollama`, `multi-agent` eintragen (die letzten beiden sind als Projektplanung zu verstehen).

**Für echte Screenshots:** Seite lokal im Browser öffnen, Desktop und Mobilansicht aufnehmen und später im Repository als `docs/screenshots/` hinzufügen. Nicht das Admin-Passwort oder private Benutzer-/Anzeigendaten abbilden.
