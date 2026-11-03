# Tests, Nachweise und offene Abnahme

[← Projektübersicht](../README.md) · [Architektur](../architecktur.md) · [Evaluation](evaluation/README.md)

## Testarten und Aussagegrenzen

| Ebene | Abgedeckte Bereiche | Aussage |
| --- | --- | --- |
| Django-Suite | Katalog, Formulare, Anmeldung, Eigentümerrechte, Käufer- und Verkäuferanfragen, Bereitstellung, Ereignisverlauf, Worker- und Fehlerpfade | Prüft definierte Web- und Datenbankabläufe in einer Testdatenbank |
| Agenten-Unittests | Eingabeschema, Router, drei Agenten, Pipeline, Validierung, Fallback, Szenario-Auswertung | Modellaufrufe werden in bestimmten Tests simuliert |
| Datenbank-Audit | Freigabetext, Freigabeberechtigung, Bereitstellungs-Snapshot, Zeitfolge, Sichtbarkeit von Verlaufsereignissen | Prüft vorhandene DB-Konsistenz, nicht den Browser oder Ollama |
| Historische Szenarioevaluation | Erwartete Agenten, Audit-Codes, bestimmte Text- und Risikomuster | Keine vollständige semantische KI-Richtigkeitsmessung |
| Manuelle Ende-zu-Ende-Prüfung | Zwei Konten, echte Ollama-Nutzung, tatsächliche Browseransichten, Ausfälle | **Laut bisheriger Abnahmedokumentation noch offen** |

## Dokumentierter Teststand

Die bisherige [Haupt-README am Commit `4bfa6c2`](https://github.com/NabinAd/Fundplatz/commit/4bfa6c25557b82b41a6af35e72eadc49b5ff84e1) gibt für **27. Oktober 2026** unter Windows mit **Python 3.12.10** auf dem Code-Stand [`274086d`](https://github.com/NabinAd/Fundplatz/commit/274086d598af84f2b49684987ae16ca4f6f5d922) an: Django-Systemprüfung und Migrationsabgleich erfolgreich, frische Migrationen angewendet, **430 Django-Tests**, **281 Agententests** bestanden sowie ein leerer Datenbank-Audit ohne Befund. LLM und Async-Verarbeitung waren für die automatisierten Tests deaktiviert.

**Das ist ein dokumentierter lokaler Nachweis, kein in dieser Dokumentationsänderung neu ausgeführter Testlauf.** Ein leerer DB-Audit sagt nichts über real durchgespielte Käufer-/Verkäuferfälle aus.

## Tests lokal ausführen (Windows PowerShell)

Nach Installation laut [Haupt-README](../README.md):

```powershell
$env:FUNDPLATZ_AGENT_USE_LLM="0"
$env:FUNDPLATZ_AGENT_ASYNC="0"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test listings --noinput
.\.venv\Scripts\python.exe -m unittest discover -s agent_system/tests
.\.venv\Scripts\python.exe manage.py fundplatz_audit --strict --json
```

Unter Linux/macOS den Pythonpfad durch `.venv/bin/python` ersetzen und Variablen mit `export` setzen. Das vorhandene [`scripts/tag25_abnahme.ps1`](../scripts/tag25_abnahme.ps1) bündelt lokale Prüfungen (in aktivierter virtueller Umgebung aufrufen) und schreibt Protokolle nach `tag25_reports/`, die nicht veröffentlicht werden sollen.

## Manuelle Abnahme – überprüfbare Schritte

- [ ] System neu starten und Migrationen auf einer **frischen lokalen Testdatenbank** anwenden.
- [ ] Zwei separate Verkäufer und mindestens einen Käufer mit getrennten Browserprofilen verwenden.
- [ ] Verkäufer A und B mit unterschiedlichen Preisen und Versandangaben testen; keine Produktdaten dürfen sich vermischen.
- [ ] Käuferfrage erzeugen; Entwurf intern sichtbar, aber im Käuferpostfach nicht vorhanden.
- [ ] Entwurf bearbeiten, speichern, intern freigeben – Käufer sieht **noch keine** Antwort.
- [ ] Separat bereitstellen; ausschließlich korrekter Snapshot für den zugehörigen Käufer sichtbar.
- [ ] Zugriffe auf fremde Anzeigen und Verkäuferanfragen ausdrücklich ablehnen.
- [ ] Mit laufendem Ollama eine reale Modellanfrage und den Verkäuferworkflow durchlaufen.
- [ ] Ollama-/Worker-Ausfall testen: Keine ungeprüfte automatische Veröffentlichung.
- [ ] Bei aktiviertem Worker: Queue-Zustandswechsel, Wiederanlauf und ausbleibenden Worker nachvollziehen.
- [ ] Backup- und Wiederherstellungsweg sowie Medienverzeichnis prüfen.
- [ ] Responsive Darstellung, Formularfehler, Accessibility und Browserfluss manuell prüfen.

## Grenzen und offene Punkte

Die Anwendung wurde im Zuge dieser Repository-Umstrukturierung nicht gestartet. Die Dokumentation der früheren Abschlussprüfung unterschied zwischen erfolgreichen automatisierten Testläufen und **ausstehender manueller Gesamtabnahme**. Lasttests, produktive Sicherheitsprüfungen, DSGVO-Bewertung und öffentliche Deployments sind ebenfalls nicht als abgeschlossen dokumentiert.

Weitere Unterlagen: [Szenario-Reports](evaluation/README.md) · [Historische Testkorrekturen](development-history/fixes/README.md).
