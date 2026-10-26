# Fundplatz – Phase 3, Tag 25: Abschlussprüfung des lokalen MVP

**Stand:** 24. Oktober 2026 · **Etappe:** Tag 25/25.

## Ziel und tatsächlicher Umfang

Das Update macht **keine neue Datenbankmigration** und verändert **keine bereits gespeicherten Kundenantworten**. Es ergänzt:

1. `listings/views.py` – ein gezielter Bugfix im synchronen Anfragepfad: Nach einer erfolgreich abgeschlossenen KI-Verarbeitung bleibt der Verarbeitungsstatus `ready`; ein unerwarteter Fehler bekommt nun **`failed` statt fälschlich `ready`**. `draft_finished_at` und das Verlaufsereignis erhalten einen Abschlusszeitpunkt. Der asynchrone Worker bleibt unverändert.
2. `listings/management/commands/fundplatz_audit.py` – **lesende** Prüfung der Freigaben, veröffentlichten Snapshots, Käufer-/Verkäuferrechte bei Freigebern und öffentlicher Verlaufsmarkierungen. Der Bericht enthält **nur Zähler**, keine Käufertexte oder privaten KI-Daten.
3. `listings/test_day25.py` – **30 neue Django-Tests** für den Audit-Befehl, private Daten, Produkttrennung und die synchrone Fehlerbehandlung.
4. `scripts/tag25_abnahme.ps1` – lokale Gesamtabnahme in VS Code/PowerShell, erstellt Protokolle.
5. `FUNDPLATZ_ABNAHME.md` – überprüfbare Checkliste und bekannte Grenzen.

### Vollständiger Projektaufbau

- **Phase 1, Tag 1–5:** Django Marketplace: Benutzerkonten, Anzeigen, Eigentümerrechte, Katalog.
- **Phase 2, Tag 6–15:** Orchestrator, Information/Negotiation/Logistics Agents, Offline-Regeln, Ollama-Einbindung, Sicherheitsvalidierung und Evaluation.
- **Phase 3, Tag 16–25:** Anfrageformular, privates Verkäuferpostfach, editierbarer Entwurf, ausdrückliche Freigabe, zusätzliche Bereitstellung ins Käuferpostfach, Ereignishistorie, Datenschutztests, optionale SQLite-Queue mit Worker, KI-Statusanzeige, käuferfreundliche Formulierungen, Ende-zu-Ende-Tests und Abschlussprüfung.

## Installation unter Windows

Voraussetzung: Tag 24 und die vorangegangenen Korrekturen sind bereits installiert; VS Code öffnet `C:\Kleinanzeigen`, und `(.venv)` ist im PowerShell-Terminal sichtbar.

```powershell
cd C:\Kleinanzeigen
git status
Copy-Item .\db.sqlite3 .\db_backup_vor_tag25.sqlite3
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag25.zip" -DestinationPath "." -Force
python manage.py check
python manage.py makemigrations --check --dry-run
```

Es gibt keine neue `0009`-Migration. `python manage.py migrate` ist nur erforderlich, falls du eine frühere Migration noch nicht installiert hast; dein Tag-23/24-Stand sollte bis **`0008_inquiry_draft_queue.py`** migriert sein.

### Testlauf – einzeln nachvollziehen

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="0"
$env:FUNDPLATZ_AGENT_USE_LLM="0"
python manage.py test listings.test_day25 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
python manage.py fundplatz_audit --strict
```

Wenn dein letzter Teststand tatsächlich bei **400 Django-Tests** liegt (340 vor Tag 24 und 60 neu), wären mit Tag 25 **430 Django-Tests** zu erwarten. Die Zahl ist **eine Prognose**, kein nachgewiesenes Ergebnis. Die 30 neuen Django-Tests wurden hier nicht ausgeführt, weil in der Erstellungsumgebung Django nicht installiert ist. Bitte das Windows-Ergebnis prüfen.

### Abnahme mit einem PowerShell-Skript

```powershell
.\scripts\tag25_abnahme.ps1
```

Das Skript schaltet für Tests Ollama und die Async-Queue vorübergehend aus, **stellt danach die vorherigen Umgebungsvariablen wieder her**, startet sechs Prüfungen und sammelt getrennte Logs unter `tag25_reports\<Zeitstempel>` und beendet sich mit Exitcode 0 nur, wenn alle sechs erfolgreich waren. **Achtung:** Die Logs können trotz datensparsamem Audit Testfehlerausgaben enthalten und gehören nicht in ein öffentliches GitHub-Repository.

### Audit getrennt nutzen

```powershell
python manage.py fundplatz_audit
python manage.py fundplatz_audit --json
python manage.py fundplatz_audit --strict
python manage.py fundplatz_audit --stale-minutes 45
```

`--strict` meldet einen Fehler bei echten Dateninkonsistenzen (nicht bei bloßen Warnungen). Beispiele für harte Fehler:

- Intern freigegeben, aber Freigabetext, Zeitpunkt oder Freigeber fehlen.
- Anderer Benutzer als der zuständige Anzeigenverkäufer hat freigegeben oder eine Antwort bereitgestellt.
- Käuferantwort weicht vom freigegebenen Snapshot ab.
- Bereitstellung liegt zeitlich **vor** der Freigabe.
- Internes Timeline-Ereignis ist als käufersichtbar markiert.
- Anfrage ist freigegeben, während ihr KI-Job noch `queued` oder `running` ist.

Warnungen betreffen etwa >30 Minuten alte `running`-Jobs und fehlende historische Timeline-Einträge (auch direkt per ORM angelegte Datensätze aus älteren Versionen). Solche Warnungen sind **nicht automatisch ein Fehler**; sie müssen im Kontext bewertet werden. `fundplatz_audit` behebt nichts automatisch.

## Echte Ollama-Prüfung als separater manueller Test

**Terminal A (Webserver):**

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="1"
python manage.py runserver
```

**Terminal B (Worker):**

```powershell
$env:FUNDPLATZ_AGENT_USE_LLM="1"
$env:OLLAMA_TIMEOUT_SECONDS="45"
python manage.py process_inquiries --loop
```

Stelle als Käufer eine Frage zu **Anzeige A (5 €)** und eine zu **Anzeige B (180 €)**, die zwei unterschiedlichen Verkäuferkonten gehören. Prüfe getrennt:

1. Jede Anfrage erscheint nur beim zuständigen Verkäufer.
2. Vor dem Worker-Lauf ist der Status `queued`, danach `ready` oder `failed`.
3. Der KI-Vorschlag enthält ausschließlich die Produktdaten dieser Anzeige. `Router: llm` beweist nur LLM-Routing und nicht freie Käufertextgenerierung.
4. Nach manueller Bearbeitung und ausdrücklicher Freigabe ist noch **keine Käuferantwort veröffentlicht**.
5. Erst „Antwort an Käufer bereitstellen“ macht den exakten freigegebenen Snapshot für den richtigen Käufer sichtbar.
6. Ein fremder Verkäufer/Käufer kann die Anfrage nicht lesen oder verändern.

## Projektabschluss ≠ Produktionsfreigabe

Dieses Projekt ist ein **lokales Lern-MVP**, keine öffentlich gehärtete Handelsplattform. Vor einem Internet-Deployment fehlen insbesondere sichere Deployment-Settings (`DEBUG=False`, starker Secret-Key, HTTPS, sichere Cookies, `ALLOWED_HOSTS`), Hosting-, Backup-/Restore- und Monitoring-Prozesse, skalierbares Worker-/Queue-Management, Anti-Spam-/Missbrauchsschutz sowie eine Datenschutz- und Rechtsprüfung. Der Audit-Befehl attestiert **niemals** Produktionsbereitschaft.

## Git-Sicherung nach erfolgreichem Test

```powershell
git add listings/views.py listings/management/commands/fundplatz_audit.py listings/test_day25.py scripts/tag25_abnahme.ps1 PHASE3_TAG25.md FUNDPLATZ_ABNAHME.md
git commit -m "Phase 3 Tag 25: lokale MVP-Abnahme und Audit"
git push
```

**Nicht** `tag25_reports` oder die SQLite-Backup-Datei committen.
