# Fundplatz

**Ein lokaler Kleinanzeigen-Marktplatz mit einem Assistenten für Käuferanfragen.** Verkäufer können Anzeigen verwalten, private Antwortentwürfe prüfen und Antworten gezielt im Käuferpostfach bereitstellen.

| Auf einen Blick | |
| --- | --- |
| **Zweck** | Webentwicklung und die kontrollierte Einbindung eines lokalen Sprachmodells praktisch erproben. |
| **Funktionen** | Benutzerkonten, Anzeigen mit Bildern, Suche und Filter, Käuferanfragen, Verkäuferpostfach, Entwurfsbearbeitung, Freigabe und Antwortbereitstellung. |
| **Technologien** | Python, Django 5.2.18, SQLite, Django Templates, Bootstrap 5.3.6 und Pillow 12.3.0; optional Ollama mit Qwen. |
| **Betriebsweise** | Standardmäßig regelbasierte Entwürfe ohne Sprachmodell. Lokale Modellnutzung und Hintergrundverarbeitung sind separat zuschaltbar. |
| **Projektstatus** | Lokaler Lernprototyp: Marktplatz, Agentensystem und Website-Integration sind implementiert. Die dokumentierte praktische Gesamtabnahme ist noch offen. |

Ich bin **Nabin Adhikari**, studiere **Wirtschaftsinformatik an der THM** und suche ein **Pflichtpraktikum**. Fundplatz ist mein persönliches Lernprojekt: Ich vertiefe damit meine Kenntnisse in Datenmodellierung, Webentwicklung, Berechtigungen, automatisierten Tests und der Einbindung eines lokalen KI-Assistenten.

## Vorhandene Funktionen

| Bereich | Implementierter Umfang |
| --- | --- |
| **Anzeigen** | Erstellen, bearbeiten, aktivieren/deaktivieren und nach Bestätigung löschen; mit Titel, Beschreibung, Preis, Kategorie, Zustand, optionalem Bild, Ort sowie Angaben zu Versand, Abholung und Verhandlungsbasis. |
| **Katalog** | Öffentliche Übersicht und Detailseiten, Suche in Titel und Beschreibung, Kategorie- und Preisfilter sowie Seitennavigation. |
| **Benutzerkonten** | Registrierung, Login und Logout; Verwaltung der eigenen Anzeigen. |
| **Käuferanfragen** | Angemeldete Käufer können Fragen zu fremden aktiven Anzeigen stellen und ihre Anfragen im eigenen Postfach verfolgen. |
| **Verkäuferpostfach** | Anfragen suchen und nach Status filtern, private Entwürfe einsehen und bearbeiten sowie eine regelbasierte, käuferfreundlichere Formulierung übernehmen. |
| **Antworten** | Gespeicherte Verkäuferfassung ausdrücklich freigeben und anschließend separat als unveränderlichen Textstand im Käuferpostfach bereitstellen. |
| **Verarbeitung und Verlauf** | Statusanzeige, Ereignisverlauf, optionale Datenbankwarteschlange mit separatem Worker und ein lesender Befehl zur Datenkonsistenzprüfung. |

Der Ablauf einer Anfrage:

```text
Käuferfrage → privater Antwortentwurf → Verkäufer bearbeitet und speichert
           → interne Freigabe → separate Bereitstellung im Käuferpostfach
```

**Der Verkäufer entscheidet über die Antwort.** Eine Freigabe allein macht sie noch nicht für den Käufer sichtbar. Käufer erhalten nur den bereitgestellten Textstand; interne Entwürfe und Prüfhinweise bleiben im Verkäuferbereich. Die Bereitstellung erfolgt innerhalb von Fundplatz, ohne E-Mail oder externen Nachrichtenversand.

## Technischer Aufbau

Fundplatz ist eine serverseitig gerenderte Django-Anwendung. SQLite speichert Benutzer, Anzeigen, Anfragen, Antwortstände und Verlaufsereignisse. Django Templates, lokal eingebundenes Bootstrap-CSS und eigene Styles bilden die Oberfläche; ein kleines JavaScript aktualisiert Seiten während der Entwurfsverarbeitung.

Das Python-Modul `agent_system` ist von Django getrennt. Eine Übersetzungsschicht in `listings/agent_bridge.py` übergibt die Produktdaten und die Käuferfrage an die Pipeline:

1. Eingaben prüfen und die Anfrage einem oder mehreren Bereichen zuordnen.
2. Spezialisierte Agenten für **Produktinformationen**, **Preisverhandlung** und **Versand/Abholung** ausführen.
3. Entwürfe anhand von Vorlagen und Risikoregeln prüfen und einen privaten Vorschlag zurückgeben.

Die Basisentwürfe entstehen regelbasiert aus den hinterlegten Daten. Optional unterstützt Ollama das Routing und liefert zusätzliche Formulierungsvorschläge. Freie Modellvorschläge werden nicht automatisch in den zusammengeführten Entwurf übernommen; der Verhandlungsagent verwendet keine freien LLM-Formulierungen. Bei Modellproblemen ist ein gekennzeichneter Regel-Fallback vorgesehen. Diese Prüfungen ersetzen keine inhaltliche Kontrolle durch den Verkäufer.

```text
config/                      Django-Einstellungen und zentrale URLs
listings/                    Datenmodelle, Formulare, Views und Berechtigungen
  agent_bridge.py            Übergang von Django zur Agenten-Pipeline
  draft_queue.py             Optionale Warteschlange für private Entwürfe
  management/commands/       Worker und Datenkonsistenzprüfung
  migrations/                Datenbankschema
  templates/listings/        Katalog, Anzeigen und Postfächer
  tests.py, test_*.py         Django-Tests
agent_system/                Routing, drei Agenten, Validierung und Ollama-Client
  tests/                     Unittests des Agentensystems
  examples/                  Vordefinierte Evaluationsszenarien
templates/                   Basislayout, Login und Registrierung
static/                      CSS, JavaScript und lokales Bootstrap
evaluation_reports/          Bereits eingecheckte Szenarioauswertungen
scripts/tag25_abnahme.ps1    Vorhandenes lokales Prüfskript
manage.py                    Django-Verwaltungsbefehle
requirements.txt             Python-Abhängigkeiten
```

## Lokal starten

Voraussetzungen: **Git und Python 3.12**. Für den Standardbetrieb ist Ollama nicht erforderlich. Die folgenden Befehle sind für Windows PowerShell gedacht und benötigen keine Aktivierung der virtuellen Umgebung.

```powershell
git clone https://github.com/NabinAd/Fundplatz.git
cd Fundplatz
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Danach [http://127.0.0.1:8000/](http://127.0.0.1:8000/) öffnen. Die Datenbank wird lokal angelegt; Anzeigen und Konten müssen selbst erstellt werden. Registrierung: `/registrieren/`, eigene Anzeigen: `/meine-anzeigen/`, Verkäuferpostfach: `/anfragen/`, Käuferpostfach: `/meine-anfragen/`.

Für die optionale Django-Adminoberfläche unter `/admin/`:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

<details>
<summary>Start unter Linux oder macOS</summary>

Mit installiertem Python 3.12:

```bash
git clone https://github.com/NabinAd/Fundplatz.git
cd Fundplatz
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Bei den weiteren Befehlen `.\.venv\Scripts\python.exe` durch `.venv/bin/python` ersetzen. Die unten gezeigten Umgebungsvariablen werden in diesen Shells mit `export NAME=WERT` gesetzt.

</details>

### Den Anfrageablauf ausprobieren

1. Ein Verkäuferkonto anlegen und eine aktive Anzeige erstellen.
2. In einem zweiten Browserprofil ein anderes Konto als Käufer registrieren und eine Frage zur Anzeige stellen.
3. Als Verkäufer unter **Anfragen** den privaten Entwurf prüfen, bearbeiten und als Verkäuferfassung speichern.
4. Diese Fassung ausdrücklich intern freigeben. Im Käuferpostfach darf weiterhin keine Antwort erscheinen.
5. Die Antwort separat bereitstellen und als Käufer den veröffentlichten Text prüfen.

Für die Prüfung der Trennung zwischen verschiedenen Verkäufern ein weiteres Verkäuferkonto mit eigener Anzeige verwenden.

<details>
<summary>Optional: Ollama und Hintergrundverarbeitung</summary>

Der Standardbetrieb verwendet `FUNDPLATZ_AGENT_USE_LLM=0` und `FUNDPLATZ_AGENT_ASYNC=0`: Die Entwurfsverarbeitung läuft synchron und regelbasiert.

Für Modellnutzung muss Ollama lokal unter `http://127.0.0.1:11434` laufen. Das im Code voreingestellte Modell herunterladen:

```powershell
ollama pull qwen3:4b-instruct
```

Falls der Ollama-Dienst noch nicht läuft, diesen mit `ollama serve` in einem eigenen Terminal starten. Die optionale Warteschlange hält die Modellverarbeitung aus der Webanfrage heraus. Dafür im Repository zwei Terminals verwenden:

**Terminal A – Webserver:**

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="1"
.\.venv\Scripts\python.exe manage.py runserver
```

**Terminal B – Worker:**

```powershell
$env:FUNDPLATZ_AGENT_USE_LLM="1"
$env:OLLAMA_MODEL="qwen3:4b-instruct"
$env:OLLAMA_TIMEOUT_SECONDS="45"
.\.venv\Scripts\python.exe manage.py process_inquiries --loop
```

Ohne laufenden Worker bleiben eingereihte Anfragen im Status `queued`. Der Worker liest `FUNDPLATZ_AGENT_USE_LLM` aus seiner eigenen Umgebung. Ohne diese Aktivierung verarbeitet er die Queue regelbasiert. Das Ollama-Zeitlimit gilt pro HTTP-Aufruf, nicht für den gesamten Ablauf.

Die Einstellungen werden beim Prozessstart gelesen. Für den synchronen Modellbetrieb `FUNDPLATZ_AGENT_ASYNC="0"` und `FUNDPLATZ_AGENT_USE_LLM="1"` im Webserver-Terminal setzen und den Server neu starten. Eine `.env`-Datei wird vom vorhandenen Code nicht automatisch geladen.

</details>

## Tests und Überprüfung

Vorhanden sind Django-Tests für Anzeigen, Formulare, Suche, Eigentümerrechte, Anfrageverarbeitung, Postfächer, Freigabe, Antwortbereitstellung, Verlauf und Queue. Die separaten Python-Unittests prüfen Eingaben, Routing, Agenten, Validierung, Fehlerfälle und die Evaluationslogik. Modellaufrufe werden in den entsprechenden Tests durch simulierte Antworten ersetzt; ein bestandener Testlauf belegt keine echte Ollama-Integration.

Nach der Installation im Repository ausführen:

```powershell
$env:FUNDPLATZ_AGENT_USE_LLM="0"
$env:FUNDPLATZ_AGENT_ASYNC="0"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test listings --noinput
.\.venv\Scripts\python.exe -m unittest discover -s agent_system/tests
.\.venv\Scripts\python.exe manage.py fundplatz_audit --strict --json
```

`fundplatz_audit` liest die lokale Datenbank und prüft unter anderem Freigaben, Antwort-Snapshots und die Sichtbarkeit von Verlaufsereignissen. Ein fehlerfreier Audit einer leeren Datenbank bestätigt keinen durchgespielten Anfrageablauf.

### Nachweisstand

Am **27. Oktober 2026** am [Code-Stand `274086d`](https://github.com/NabinAd/Fundplatz/commit/274086d598af84f2b49684987ae16ca4f6f5d922) unter **Windows mit Python 3.12.10** geprüft. Modellnutzung und Async-Modus waren für die automatisierten Läufe deaktiviert.

| Prüfung | Ergebnis |
| --- | --- |
| Django-Systemprüfung | Ohne Befunde. |
| Migrationsabgleich | Keine ausstehenden Modelländerungen erkannt. |
| Migrationen auf frischer lokaler Datenbank | Erfolgreich angewendet. |
| Django-Tests | **430 Tests erfolgreich.** |
| Separate Agententests | **281 Tests erfolgreich.** |
| Strenger Datenbank-Audit | Auf der frisch angelegten, leeren Datenbank ohne Inkonsistenzen. |

Ein manueller Browserdurchlauf, echte Ollama-Aufrufe und der Start unter Linux/macOS wurden bei dieser Prüfung nicht durchgeführt. Die [bestehende Abnahmecheckliste](FUNDPLATZ_ABNAHME.md) führt die praktische Gesamtabnahme weiterhin als offen. Automatisierte Prüfungen, historische Szenarioberichte und ein manueller Browserdurchlauf sind unterschiedliche Nachweise.

<details>
<summary>Szenarioauswertungen und vorhandenes Prüfskript</summary>

Unter [`evaluation_reports/`](evaluation_reports/) liegen historische Offline- und LLM-Berichte. Sie prüfen vordefinierte Erwartungen an Routing, Stichwörter, Zahlen und Risikomuster. Die zusätzlichen Tag-15-Fälle wurden bereits zur Verbesserung verwendet und sind kein unabhängiger Blindtest. Die Berichte belegen weder allgemeine Antwortqualität noch Fehlerfreiheit bei beliebigen Fragen.

Eine eigene Offline-Auswertung mit neuem Ausgabeordner starten:

```powershell
.\.venv\Scripts\python.exe -m agent_system.evaluation --mode offline --out-dir tag25_reports/local_offline
```

Mit laufendem Ollama ist eine kleine Modellstichprobe möglich:

```powershell
.\.venv\Scripts\python.exe -m agent_system.evaluation --mode llm --per-category 1 --out-dir tag25_reports/local_llm
```

Das Programm schreibt Markdown-, JSON- und CSV-Berichte. Qualitätsabweichungen stehen im Bericht; der Exitcode allein zeigt sie nicht an. Neue Auswertungen in einem eigenen Ausgabeordner ablegen, damit bestehende Berichte erhalten bleiben.

Das vorhandene [`scripts/tag25_abnahme.ps1`](scripts/tag25_abnahme.ps1) bündelt Django-Prüfungen, Agententests und Datenbank-Audit. Es erwartet `python` aus einer aktivierten virtuellen Umgebung und schreibt lokale Protokolle nach `tag25_reports/`. Diese Protokolle gehören nicht ins öffentliche Repository.

</details>

## Projektgrenzen und dokumentierte nächste Schritte

Fundplatz ist ein **lokales Lernprojekt mit begrenztem Funktionsumfang**. Die Konfiguration enthält `DEBUG=True`, einen Entwicklungs-Secret-Key als Fallback, lokale Hosts und SQLite. Der Entwicklungsserver und die optionale lokale Queue sind keine fertig eingerichtete Produktionsumgebung.

- **Antwortqualität:** Regeln können unvollständige oder falsche Produktdaten nicht verlässlich erkennen. Auch ein Modellvorschlag braucht eine manuelle Prüfung. Das System trifft keine autonomen Preiszusagen.
- **Funktionsumfang:** Kein Bezahlsystem, kein externer Nachrichtenversand und kein fortlaufender Echtzeit-Chat.
- **Lokale Daten:** Die Queue verwendet Produktdaten zum Verarbeitungszeitpunkt. Beim Löschen einer Anzeige werden zugehörige Bilddateien nicht automatisch vom Datenträger entfernt.
- **Prüfgrenzen:** Automatisierte Tests ersetzen keine Browser-, Last-, Sicherheits- oder Backup-Wiederherstellungsprüfung.

Die aktuellen nächsten Schritte sind in [`PHASE3_TAG25.md`](PHASE3_TAG25.md) und [`FUNDPLATZ_ABNAHME.md`](FUNDPLATZ_ABNAHME.md) dokumentiert:

1. Die lokale Gesamtabnahme einschließlich getrennter Käufer-/Verkäuferkonten, echter Ollama-Verarbeitung im Browser und Ausfallverhalten abschließen.
2. Vor einem öffentlichen Betrieb Deployment-Einstellungen, Secrets, HTTPS und Cookies härten sowie Hosting, Backups, Wiederherstellung und Monitoring klären.
3. Für einen größeren Betrieb Datenbank und Worker-/Queue-Verwaltung ausbauen, Missbrauchsschutz verbessern und Datenschutz sowie rechtliche Anforderungen prüfen.

Diese Punkte sind offene Arbeiten, keine zugesagten Funktionen oder abgeschlossenen Nachweise.
