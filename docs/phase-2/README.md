# Phase 2 – Lokales Multi-Agenten-System

[← Projektübersicht](../../README.md) · [← Phase 1](../phase-1/README.md) · [Phase 3 →](../phase-3/README.md)

## Zusammenfassung

In Phase 2 wurde das von Django getrennte [Agentensystem](../../agent_system/) aufgebaut: strukturierte Eingaben, lokaler [Ollama-Client](../../agent_system/ollama_client.py), [Router](../../agent_system/router.py), drei spezialisierte [Agenten](../../agent_system/agents.py) für Produktinformation, Preisverhandlung und Logistik sowie [Validierung und Sicherheitsregeln](../../agent_system/validation.py). Das System unterstützt eine regelbasierte Betriebsweise; LLM-Ausgaben ersetzen keine Verkäuferprüfung.

## Entwicklungsmeilensteine

| Tage | Fokus |
| --- | --- |
| 6–8 | Ollama, Eingabeschema und Orchestrator |
| 9–11 | Spezialisierte Agenten und Pipeline |
| 12–13 | Validierung, Audits und Fehlerbehandlung |
| 14–15 | Szenario-Evaluation und Regression |

**Evaluation:** [Historische Reports](../../evaluation_reports/) · **Unit-Tests:** [Agententests](../../agent_system/tests/).

> **Historischer Stand:** Die folgenden vollständigen Entwicklungsnotizen enthalten teilweise alte Installations- und Testerwartungen. Der aktuelle Stand steht in der [Haupt-README](../../README.md).

## Originalnotizen (vollständiges Archiv)

<details>
<summary><strong>PHASE2_TAG6.md</strong></summary>

# Fundplatz: Phase 2 / Tag 6 – Lokale LLM-Verbindung

Dieses Update wird **im Wurzelordner deines bestehenden Django-Projekts** entpackt.
Es ergänzt nur `agent_system/` und diese Anleitung. Die Django-Dateien und SQLite-Datenbank bleiben unverändert.

## 1. Hardware und Ollama kontrollieren (PowerShell)

```powershell
cd C:\Kleinanzeigen
ollama --version
nvidia-smi
ollama list
```

Wenn `ollama` nicht gefunden wird: Ollama öffnen und ein neues VS-Code-Terminal starten. Die Windows-App läuft normalerweise im Hintergrund.

## 2. Ein Modell lokal herunterladen und kurz testen

```powershell
ollama pull qwen3:4b-instruct
ollama run qwen3:4b-instruct "Antworte in einem Satz auf Deutsch: Funktioniert Ollama?"
ollama ps
```

Mit `ollama ps` die Spalte `PROCESSOR` prüfen (GPU/CPU-Auslastung des Modells im Speicher).

## 3. Unabhängigen Python-Test starten

Im **Repository-Wurzelordner** (`C:\Kleinanzeigen`):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s agent_system/tests -v
```

Erwartet: **4 Tests, OK**. Diese Tests brauchen keinen Ollama-Server und kosten keine Tokens.

## 4. Erste echte Modellanfrage aus Python

```powershell
.\.venv\Scripts\python.exe -m agent_system.demo
```

Alternativ:

```powershell
.\.venv\Scripts\python.exe -m agent_system.demo --frage "Ist die Abholung möglich?"
```

Die Demo sendet einen Beispielartikel und deine Frage an Ollama `/api/chat`. Sie misst die End-to-End-Antwortzeit.
**Achtung:** Die Demo ist noch kein fertig geprüfter Agent; keine externen Nachrichten versenden oder Preiszusagen automatisieren.

## 5. Git (nach erfolgreichem Test)

```powershell
git add agent_system PHASE2_TAG6.md
git commit -m "Phase 2 Tag 6: local Ollama client and smoke tests"
git push
```

## Fehlerbehebung

- `ollama` unbekannt: Windows-Anwendung starten und Terminal neu öffnen.
- `Ollama ist nicht erreichbar`: Die Ollama-App sollte unter `http://127.0.0.1:11434` erreichbar sein; andernfalls Ollama neu starten.
- `Ollama meldet HTTP 404`: Modellbezeichnung mit `ollama list` vergleichen.
- Zeitüberschreitung: Erst `ollama run` ausprobieren, gegebenenfalls längere Modellladezeit zulassen.
- `100% CPU` bei `ollama ps`: NVIDIA-Treiber/GPU-Nutzung prüfen und andere GPU-intensive Anwendungen schließen.

## Definition of Done

- Qwen3-4B-Instruct läuft lokal.
- `ollama ps` zeigt, wie das Modell CPU und/oder GPU nutzt.
- Die vier Offline-Tests bestehen.
- Die Python-Demo liefert einen Antworttext und zeigt die Zeit.
- Phase-2-Dateien sind separat vom Django-Projekt organisiert.

Nächster Schritt: Tag 7 erstellt getypte `ProductContext`- und `CustomerRequest`-Datenobjekte und prüft die Eingabedaten.

</details>

<details>
<summary><strong>PHASE2_TAG7.md</strong></summary>

# Fundplatz – Phase 2, Tag 7: Strukturierte Eingaben

**Ziel:** Produktfakten und Kundenfragen unabhängig von Django und Ollama prüfen.
Diese ZIP-Datei ist ein **Update** für dein bestehendes Tag-6-Projekt und überschreibt nur `agent_system/demo.py`. Alle anderen Tag-6-Dateien, die Django-Website und deine SQLite-Datenbank bleiben erhalten.

## 1. Installation unter Windows / VS Code

Terminal in VS Code öffnen, dann:

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase2_tag7.zip" -DestinationPath "." -Force
```

Falls du `agent_system/ollama_client.py` noch nicht hast, zunächst das Tag-6-Paket installieren.
Es werden **keine zusätzlichen pip-Pakete** benötigt. Die vier Tag-6-Tests bleiben erhalten.

## 2. Strukturierte Eingaben ohne Ollama testen

```powershell
.\.venv\Scripts\python.exe -m agent_system.demo --nur-pruefen
```

Das Programm liest `agent_system/examples/tag7_input.json`. Erwarte `Eingaben gültig` und `Validierung OK. Kein Ollama-Aufruf ausgeführt.`

**Beispiel:**

```json
{
  "product": {
    "listing_id": 1,
    "title": "Lenovo ThinkPad T480",
    "description": "16 GB RAM, 512 GB SSD",
    "condition": "Gut, gebraucht",
    "price_eur": "220.00",
    "shipping_available": true,
    "pickup_available": true,
    "location": null,
    "is_negotiable": false,
    "availability": null
  },
  "request": {
    "message": "Wie viel RAM hat der Laptop und ist Versand möglich?"
  }
}
```

Bedeutung: `null` = unbekannt, `false` = ausdrücklich nein. Eine Anzeige mit `is_active=True` beweist **nicht**, dass ein Artikel noch verfügbar ist. Deswegen wird `availability` nicht automatisch aus dem Django-Modell abgeleitet.

`price_eur` ist aus Genauigkeitsgründen als String mit Punkt gespeichert, z. B. `"220.00"`, nicht als JSON-Fließkommazahl. Gültiger Preisbereich: 0 bis 9999999.99, höchstens zwei Nachkommastellen.

## 3. Einen Fehler absichtlich auslösen

Öffne `agent_system/examples/tag7_input.json` in VS Code und ändere den Preis testweise auf `"-30"`. Danach erneut:

```powershell
.\.venv\Scripts\python.exe -m agent_system.demo --nur-pruefen
```

Erwartet: `EINGABEFEHLER: product.price_eur: Preis muss zwischen 0 und 9999999.99 liegen.` und Exit-Code 1. **Danach Preis wieder auf `"220.00"` setzen.**

Du kannst auch `availability` auf `"sold"` setzen. Das ist gültig, bedeutet aber, dass ein Verkäufer den Artikel ausdrücklich als verkauft gekennzeichnet hat – nicht dass Ollama den Status bestimmen dürfte.

## 4. Erste echte Ollama-Anfrage mit geprüften Daten

Wenn Ollama läuft und dein Tag-6-Modell installiert ist:

```powershell
.\.venv\Scripts\python.exe -m agent_system.demo --frage "Ist Versand möglich?"
```

Ein alternatives Modell wählst du mit `--modell MODELLNAME`. Ohne `--modell` verwendet das Programm die Modellwahl aus `agent_system/ollama_client.py` (Tag 6).

Die Antwort ist **noch nicht vom Validator geprüft**. Diese Sicherheitskomponente implementieren wir an Tag 12; der Router kommt an Tag 8. Versende die Antwort nicht automatisiert an Kunden.

## 5. Python-Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s agent_system/tests -v
```

Erwartet: **35 Tests, OK** (31 neue Tag-7-Tests + 4 bestehende Tag-6-Tests). Die 35 Tests wurden für dieses Paket hier erfolgreich ausgeführt. Sie benötigen **kein Ollama** und **kein Django**.

Optional: Django separat weiter prüfen:

```powershell
.\.venv\Scripts\python.exe manage.py test listings
```

## 6. Dateien und Funktionen

- `agent_system/inputs.py`: `ProductContext`, `CustomerRequest`, `AgentInput`, `InputValidationError` und Feldvalidierungen; Standardbibliothek mit `dataclasses`, `decimal`, `json`.
- `agent_system/examples/tag7_input.json`: bearbeitbare Beispieldaten.
- `agent_system/demo.py`: aktualisierte Tag-6-Demo; zuerst Eingabeprüfung, optional Ollama.
- `agent_system/tests/test_inputs.py`: neue Offline-Tests für gültige/ungültige JSON-Felder.
- `PHASE2_TAG7.md`: diese Anleitung.

Die Eingaben sind **unveränderlich** (frozen dataclasses). Für eine andere Frage ein neues `CustomerRequest`-Objekt erstellen statt bestehende Daten umzuschreiben.

## 7. Definition of Done

- [ ] JSON-Beispiel wird ohne Ollama als gültig erkannt.
- [ ] Negativer Preis wird abgelehnt.
- [ ] `null` und `false` sind eindeutig voneinander unterscheidbar.
- [ ] Eine eigene Frage kann mit `--frage` geprüft werden.
- [ ] Der lokale Ollama-Aufruf funktioniert (wenn Tag 6 funktioniert hat).
- [ ] 35 Python-Tests sind grün.
- [ ] Auf GitHub gesichert.

```powershell
git add agent_system/inputs.py agent_system/demo.py agent_system/examples/tag7_input.json agent_system/tests/test_inputs.py PHASE2_TAG7.md
git commit -m "Phase 2 Tag 7: structured product and request inputs"
git push
```

**Tag 8:** Router klassifiziert Kundenanfragen und gibt eine begründete, testbare Agentenwahl zurück. Bis dahin noch keine Agentenauswahl und keine automatisierten Preiszusagen.

</details>

<details>
<summary><strong>PHASE2_TAG8.md</strong></summary>

# Fundplatz – Phase 2, Tag 8: Orchestrator / Router

**Ziel:** Kundenfragen in **Information**, **Negotiation** und/oder **Logistics** einordnen, Auswahl begründen und unklare Fragen kennzeichnen. Heute werden **keine Agentenantworten** erstellt und **keine Nachrichten versendet**. Die spezialisierte Bearbeitung beginnt an Tag 9.

## 1. Dateien des Updates

- `agent_system/router.py` – `Orchestrator`, `RouteDecision`, JSON-Schema, regelbasierter Offline-Router, Fehlerbehandlung.
- `agent_system/router_demo.py` – Terminal-App, liest die vorhandene Tag-7-Beispieldatei und überschreibt auf Wunsch die Kundenfrage.
- `agent_system/ollama_client.py` – Tag-6-Client mit optionalem `response_format` erweitert; alle bestehenden Aufrufe funktionieren unverändert.
- `agent_system/tests/test_router.py` – Router-/Fallback-/JSON-Tests ohne Ollama-Netzwerk.
- `PHASE2_TAG8.md` – diese Anleitung.

Die Tag-7-Dateien `agent_system/inputs.py` und `agent_system/examples/tag7_input.json` bleiben unberührt. Django, SQLite, HTML, CSS und die 64 Marketplace-Tests ebenfalls.

## 2. Installation in VS Code / PowerShell

Da `(.venv)` bereits im Terminal erscheint, **nur `python` verwenden**:

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase2_tag8.zip" -DestinationPath "." -Force
```

Falls `git status` uncommittete eigene Änderungen zeigt, diese vor dem Entpacken sichern. Dieses Update ersetzt nur den Ollama-Client; es enthält keine Datenbankdateien.

## 3. Erste Entscheidungen OHNE Ollama testen

```powershell
python -m agent_system.router_demo --offline
python -m agent_system.router_demo --offline --frage "Ist Versand möglich?"
python -m agent_system.router_demo --offline --frage "Was ist dein letzter Preis?"
python -m agent_system.router_demo --offline --frage "Ist der Laptop noch da und kannst du ihn verschicken?"
python -m agent_system.router_demo --offline --frage "Hallo!"
```

Du siehst ein JSON mit:

- `agents`: erkannte Anliegen; mehrere Agenten bei kombinierten Kundenfragen.
- `primary_agent`: erster zuständiger Agent (oder `null`).
- `reason`: kurze Begründung.
- `needs_clarification`: `true` für unklare Fragen ohne gewählten Agenten.
- `source`: `rules`, `llm` oder `fallback`.
- `warning`: wenn Ollama fehlgeschlagen ist und die lokalen Heuristiken verwendet wurden.

Der Offline-Router ist bewusst **einfach** und wird komplizierte Fragen nicht immer korrekt klassifizieren. Seine Entscheidungen sind reproduzierbar und werden als Regelentscheidung markiert.

## 4. Routing MIT lokalem Ollama testen

```powershell
ollama list
python -m agent_system.router_demo
python -m agent_system.router_demo --frage "Ist der Laptop noch verfügbar und wäre 180 Euro möglich?"
python -m agent_system.router_demo --frage "Kann ich ihn abholen?"
```

Optional anderes Modell:

```powershell
python -m agent_system.router_demo --modell qwen3:4b-instruct --frage "Ist Versand möglich?"
```

Bei erfolgreicher Modellklassifikation steht `"source": "llm"`. Steht dort `"fallback"`, konnte die LLM-Klassifikation nicht korrekt abgeschlossen werden; die Warnung nennt den Grund. Das Programm **verschweigt** den Fallback nicht.

Das Modell antwortet über Ollamas `/api/chat` mit `format` als JSON-Schema und `temperature: 0`. **Trotz Schema prüft Python den Inhalt nochmals**: unzulässige Agentennamen, Duplikate, fehlende Felder oder widersprüchliche Flags werden abgewiesen.

## 5. Python-Tests

```powershell
python -m unittest discover -s agent_system/tests -v
```

Erwartet (bei unverändertem Tag-6/7-Projekt):

```text
Ran 67 tests
OK
```

Davon sind **32 Tests für Tag 8** und **35 Tests für Tag 6/7**. Die Tests benötigen keinen laufenden Ollama-Server. Die echten Modellentscheidungen musst du separat mit dem Befehl ohne `--offline` prüfen.

**Beispiel** für die Ausgabe:

```json
{
  "agents": ["information", "logistics"],
  "primary_agent": "information",
  "reason": "Kunde fragt nach Produkteigenschaft und Versand.",
  "needs_clarification": false,
  "source": "llm",
  "warning": null
}
```

Das ist ein Beispielformat, **keine garantierte Qwen-Ausgabe**. Die Reihenfolge der Agenten kann zwischen LLM-Läufen variieren. `reason` ist eine Erklärung des Routers, kein Nachweis der sachlichen Korrektheit.

## 6. Kontrolle und Git

Prüfe mindestens eine Informations-, Preis- und Logistikfrage, eine kombinierte Anfrage und eine unklare Frage. Die ausgegebene `source` muss mit deinem tatsächlich verwendeten Modus übereinstimmen.

```powershell
git add agent_system/router.py agent_system/router_demo.py agent_system/ollama_client.py agent_system/tests/test_router.py PHASE2_TAG8.md
git commit -m "Phase 2 Tag 8: structured intent routing"
git push
```

## 7. Wichtige Grenzen

- **Keine Agenten werden aufgerufen:** Das Routing benennt zuständige Fachagenten; deren Bearbeitungslogik kommt an Tag 9–11.
- **Keine verlässliche Confidence-Zahl:** Eine vom LLM behauptete Prozentzahl wäre unkalibriert; wir zeigen stattdessen Entscheidung, Begründung und Herkunft.
- **Keine Faktenprüfung:** Produktdaten und erzeugte Antwortentwürfe werden erst später gegen Regeln validiert (Tag 12).
- **Keine Freigabe/Übermittlung:** Das System versendet keine Nachrichten und macht keine Preiszusagen.
- Eine Prompt-Injection-Abwehr per Anweisung und JSON-Eingrenzung ist keine vollständige Sicherheit; Szenariotests und Validierung folgen.

**Tag 9:** Information Agent – Fragen zu Produktbeschreibung, Zustand, Technik und Verfügbarkeit mit bekannten Fakten beantworten.

Offizielle API-Dokumentation: https://docs.ollama.com/api/chat und https://docs.ollama.com/capabilities/structured-outputs

</details>

<details>
<summary><strong>PHASE2_TAG9_11.md</strong></summary>

# Fundplatz – Phase 2, Tage 9, 10 und 11: Alle drei Agenten gemeinsam

## Ziel

Drei spezialisierte, unabhängig testbare Agenten erzeugen aus **bereits validierten** Produktdaten und einer Kundenfrage eigene **Antwortentwürfe**:

- **Tag 9 – Information Agent:** Zustand, Beschreibung, technische Details und ausdrücklich hinterlegte Verfügbarkeit
- **Tag 10 – Negotiation Agent:** Angebotspreis und Verhandlungsstatus, **keine Preisannahme oder Rabattzusage**
- **Tag 11 – Logistics Agent:** Versand, Abholung und Standort, **keine erfundenen Versandkosten oder Liefertermine**

Der **Tag-8-Router** entscheidet über zuständige Agenten; `AgentPipeline` ruft die ausgewählten Agenten nacheinander auf und kombiniert ihre *datenbasierten* Basisentwürfe. Eine kombinierte Frage kann **alle drei** auslösen. Django und SQLite werden in dieser Phase nicht aufgerufen.

## Das ist neu

```text
agent_system/
├── agents.py                 ← InformationAgent, NegotiationAgent, LogisticsAgent
├── pipeline.py               ← Router → ausgewählte Agenten → gemeinsamer Entwurf
├── agents_demo.py            ← Demo: einzeln, alle zusammen, online/offline
├── router.py                 ← einzige Tag-8-Anpassung: „Wäre 100 Euro okay?“
└── tests/
    ├── test_agents.py        ← Einzelagenten und Sicherheitsgrenzen
    └── test_pipeline.py      ← gemeinsamer End-to-End-Test
PHASE2_TAG9_11.md             ← diese Anleitung
```

Alle anderen Tag-6/7/8-Dateien, die Django-Website und die Datenbank bleiben unverändert.

## Schritt 1: Installation unter Windows / VS Code

Die virtuelle Umgebung ist bereits aktiv (`(.venv)` im Terminal), daher **nur `python` verwenden**.

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase2_tag9_11.zip" -DestinationPath "." -Force
```

Falls `git status` Änderungen zeigt, sichere sie **vor** dem Entpacken. Das ZIP überschreibt `agent_system/router.py` (kleine Regex-Erweiterung), legt ansonsten nur neue Dateien an.

## Schritt 2: Vier Agentenszenarien gemeinsam verstehen (OHNE Ollama)

```powershell
python -m agent_system.agents_demo --offline --beispiele
```

Die vier Fragen prüfen nacheinander:

1. Information: „Wie ist der Zustand des Laptops?“
2. Negotiation: „Wäre 100 Euro okay?“
3. Logistics: „Ist Versand möglich?“
4. Alle drei: „Wie ist der Zustand, ist Versand möglich und wäre 100 Euro okay?“

Im vierten Fall sind die Agenten `negotiation`, `logistics`, `information` ausgewählt. Ihre datenbasierten Entwürfe werden zusammengefügt. Reihenfolge stammt vom Router; sie ist keine Aussage darüber, welcher Agent „besser“ ist.

## Schritt 3: Eine kombinierte Frage als JSON-Ergebnis

```powershell
python -m agent_system.agents_demo --offline --frage "Wie ist der Zustand, ist Versand möglich und wäre 100 Euro okay?"
```

Du siehst:

- `route.agents`: Welche Agenten und aus welchem Grund (`route.reason`)?
- `route.source`: `rules` (offline), `llm` oder `fallback` (Online-Routing)
- `replies`: ein Eintrag je ausgewähltem Agenten
- `facts_used`: tatsächlich verwendete Felder wie `condition` oder `shipping_available`
- `missing_fields`: im Datensatz nicht hinterlegte Informationen
- `draft`: deterministisch aus den vorhandenen Produktdaten erstellte Antwort
- `llm_suggestion`: **optionaler, ungeprüfter** Formulierungsvorschlag des lokalen LLM
- `combined_draft`: **nur** aus den datenbasierten `draft`-Texten gebildet
- `review_status: seller_review_required`: keine automatische Freigabe
- `factual_validation: not_implemented_until_day_12`: der eigentliche Validator kommt noch

**Wichtige Trennung:** Bei Preisverhandlungen bleiben freie LLM-Formulierungen bis Tag 12 gesperrt. Der `NegotiationAgent` nennt nur die vorhandenen Preise/Verhandlungsregeln und verspricht nichts. Für Information und Logistics kann Ollama zusätzlich eine alternative Formulierung vorschlagen, die aber **nicht** in `combined_draft` gelangt und **nicht** als geprüft gilt.

## Schritt 4: Echte LLM-Bearbeitung über Ollama (online)

Erst das lokale Modell prüfen:

```powershell
ollama list
ollama ps
```

Dann:

```powershell
python -m agent_system.agents_demo --frage "Wie ist der Zustand und ist Versand möglich?"
```

Ohne `--offline` lässt der Router Qwen klassifizieren (soweit Ollama antwortet). Für Information und Logistics werden zudem **experimentelle alternative Formulierungen** angefragt. Bei Problemen mit Ollama ist `route.source` gleich `fallback`, falls der Regelrouter einspringt; dann werden weitere LLM-Anfragen ausgelassen.

Bei einer reinen Preisfrage wird der Negotiation Agent **datenbasiert** antworten. Diese bewusste Sicherheitsgrenze ändern wir erst, wenn wir nach Tag 12 geeignete Validierungsregeln entwickelt und getestet haben.

## Schritt 5: Fehlende Informationen praktisch testen

Öffne `agent_system/examples/tag7_input.json` in VS Code und ändere testweise:

```json
"shipping_available": null,
"availability": null,
"is_negotiable": false
```

Jetzt:

```powershell
python -m agent_system.agents_demo --offline --frage "Ist der Artikel noch verfügbar und ist Versand möglich?"
```

Erwartet: „keine bestätigte Angabe“ zur Verfügbarkeit und „nicht angegeben“ beim Versand. Kein Agent darf diese Unbekannten in ein „Ja“ umdeuten.

Setze die Beispieldatei danach wieder zurück, sonst ändern sich die Ergebnisse weiterer Demos.

## Schritt 6: Alle Tests

```powershell
python -m unittest discover -s agent_system/tests -v
```

Bei unverändertem Tag-8-Stand:

```text
Ran 129 tests
OK
```

Die **129 Tests** bestehen aus 67 bisherigen Tests und 62 neuen Tests für alle Agenten und die Pipeline. Die gesamte Testreihe wurde in der Erstellungsumgebung ohne Ollama-Netzwerk erfolgreich ausgeführt. Echte Modellantworten sind nicht deterministisch und müssen zusätzlich am eigenen PC geprüft werden.

Die bisherigen Django-Tests bleiben separat:

```powershell
python manage.py test listings
```

## Warum drei Agenten statt einer großen LLM-Anweisung?

- **Information** greift nur auf hinterlegte Produkteigenschaften zu, fragt bei fehlenden Daten nach.
- **Negotiation** hat eine strengere Strategie, weil er keine neuen Preise akzeptieren darf.
- **Logistics** begrenzt Antworten auf Versand-/Abholinformationen und bestätigt keine Kosten oder Zeiten.
- **Pipeline** hält die Zuständigkeiten getrennt und speichert nachvollziehbar, welcher Agent welchen Text erzeugt hat.

Alle Agenten verwenden dieselben Datenmodelle aus Tag 7. Für experimentelle Formulierungen kann ein gemeinsamer Ollama-Client eingesetzt werden. Es laufen nicht drei Modelle gleichzeitig.

## Git

```powershell
git add agent_system/agents.py agent_system/pipeline.py agent_system/agents_demo.py agent_system/router.py agent_system/tests/test_agents.py agent_system/tests/test_pipeline.py PHASE2_TAG9_11.md
git commit -m "Phase 2 Tage 9-11: drei Spezialagenten und Pipeline"
git push
```

## Abschluss und Grenzen

**Definition of Done**: Jede der drei Strategien liefert eine sinnvolle Antwort; die kombinierte Anfrage wählt und ruft alle drei Agenten auf; unbekannte Fakten bleiben unbekannt; keine Preiszusage wird im kombinierten Entwurf gemacht; alle 129 Tests bestehen.

**Noch nicht erledigt:** Freie LLM-Texte sind nicht faktisch validiert. Tag 12 wird eine explizite Validation-Schicht ergänzen; an Tag 13–15 folgen Härtung, Evaluation und weitere Tests. Die Website wird erst in Phase 3 angeschlossen. **Das aktuelle System sendet keine Nachrichten und ändert keine Produkte oder Preise.**

</details>

<details>
<summary><strong>PHASE2_TAG12.md</strong></summary>

# Fundplatz – Phase 2, Tag 12: Validation

## Ziel

Die drei Agenten aus Tag 9–11 liefern Antwortentwürfe. **Ab Tag 12 prüft**
`ResponseValidator` diese Entwürfe mit konservativen Regeln, bevor die
`AgentPipeline` daraus `combined_draft` zusammensetzt.

Kein Datenbankzugriff, kein automatischer Verkauf, keine Nachrichten an echte
Kunden. **`seller_review_required` gilt weiterhin immer.**

## Neue und geänderte Dateien

| Datei | Aufgabe |
|---|---|
| `agent_system/validation.py` | Regelvalidator, Ergebnisstatus, Prüfprobleme |
| `agent_system/pipeline.py` | Prüfschicht zwischen Agenten und kombinierter Antwort |
| `agent_system/validation_demo.py` | Vier gut sichtbare Beispielszenarien ohne Ollama |
| `agent_system/agents_demo.py` | Korrigierter Hinweis auf die Prüfschicht |
| `agent_system/tests/test_validation.py` | Neue Validierungs- und Integrationstests |
| `agent_system/tests/test_pipeline.py` | Aktualisierte Prüfung für Tag 12 |

**Keine neuen Python-Abhängigkeiten**, keine Django-Migration, keine Veränderung
der SQLite-Datenbank. Dateipfade beziehen sich auf `C:\Kleinanzeigen`.

## Installation (PowerShell, .venv bereits aktiv)

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase2_tag12.zip" -DestinationPath "." -Force
```

Die ZIP-Datei enthält ausschließlich die oben genannten Dateien und diese
Anleitung. Bisherige Git-Änderungen vor dem Überschreiben committen.

## Schritt 1: Den Validator beobachten

```powershell
python -m agent_system.validation_demo
```

Vier Ausgaben zeigen:

1. Unveränderter Logistikentwurf → `passed_template_checks`.
2. Erfundene Preis-/Lieferzusage → `suggestion_status: blocked`.
3. Andere Formulierung ohne eindeutig erkannte Risiken → `manual_review_required`.
4. Prompt Injection in der Produktbeschreibung → `draft_status: blocked` und
   eine neutrale Zurückhaltung im gemeinsamen Antwortentwurf.

**Warum blockieren wir nicht jede freie Umformulierung als Lüge?**
Die Regeln können nicht beweisen, ob sprachlich neue Behauptungen logisch aus
Produktdaten folgen. `manual_review_required` ist daher korrekter als
"automatisch genehmigt". Selbst ein `matches_template` wird nicht versendet.

## Schritt 2: Drei Agenten zusammen prüfen

```powershell
python -m agent_system.agents_demo --offline --frage "Wie ist der Zustand, ist Versand möglich und wäre 100 Euro okay?"
```

Die JSON-Ausgabe enthält neu `validation`:

```json
{
  "validation": [
    {
      "agent": "negotiation",
      "draft_status": "passed_template_checks",
      "suggestion_status": "not_present",
      "issues": []
    }
  ],
  "review_status": "seller_review_required",
  "factual_validation": "template_and_risk_rules_only"
}
```

(Das obige JSON ist **nur ein schematischer Ausschnitt** und kein vollständiges
Pipeline-Resultat.)

Mit lokalem Ollama optional:

```powershell
python -m agent_system.agents_demo --frage "Wie ist der Zustand und ist Versand möglich?"
```

Ein generierter LLM-Text wird **niemals automatisch** in `combined_draft`
eingefügt. Er erscheint höchstens als `llm_suggestion` im Prüfprotokoll.
Preisformulierungen bleiben als freie LLM-Vorschläge deaktiviert.

## Schritt 3: Alle Python-Tests

```powershell
python -m unittest discover -s agent_system/tests -v
```

Entwicklungsstand des Pakets: **166 Tests erfolgreich** (129 bestehende + 37 neue),
ohne Netzverbindung und ohne Ollama. Auf dem eigenen Rechner erneut prüfen.

Zusätzlich unveränderte Django-Tests:

```powershell
python manage.py test listings
```

## Welche Prüfungen sind implementiert?

- Stimmen Antworttext, verwendete Faktenfelder und fehlende Felder mit der
  deterministischen Antwortvorlage überein? Abweichung → blockiert.
- Ist im Produktbeschreibungstext eine typische Prompt Injection erkennbar,
  obwohl die Information Agent diese als Beschreibung wiedergeben würde?
  → Antwortteil blockiert, neutrale Meldung.
- Enthält ein **optionaler LLM-Vorschlag** eine erkennbare unautorisierte
  Preiszusage, Liefergarantie, neue Zahl oder eine unbelegte Verfügbarkeit?
  → Vorschlag blockiert.
- Ist ein LLM-Vorschlag anders formuliert, ohne dass eine der definierten
  Regeln anschlägt? → **manuelle Prüfung erforderlich**, nicht freigegeben.
- Ist ein LLM-Vorschlag identisch mit der geprüften Vorlage? →
  `matches_template`, **trotzdem Verkäuferprüfung**.

### Grenzen – unbedingt beachten

- Der Validator ist **kein vollständiger semantischer Faktenchecker**.
  Er kann unbekannte Halluzinationen, subtile Widersprüche, raffinierte
  Prompt Injections oder falsche Angaben des Verkäufers nicht sicher erkennen.
- Die deterministische Vorlage kann nur die **vorliegenden Daten** spiegeln.
  Eine falsche Verkäuferbeschreibung bleibt ohne externe Prüfung möglicherweise
  falsch. Deshalb bleiben manuelle Kontrolle und Freigabe Pflicht.
- Die Preis-, Versand- und Verfügbarkeitsregeln sind bewusst konservativ;
  weder `passed_template_checks` noch `matches_template` erteilen eine
  Sendeberechtigung.
- Die Eingabe ist bisher ein lokales JSON, keine synchronisierte Django-Anzeige;
  die Verbindung folgt erst in Phase 3.

## Abschluss und Git

```powershell
python -m unittest discover -s agent_system/tests -v
git add agent_system PHASE2_TAG12.md
git commit -m "Phase 2 Tag 12: konservative Antwortvalidierung"
git push
```

## Definition of Done

- [ ] Normale Informations-, Verhandlungs- und Logistikantworten werden geprüft
- [ ] Unerlaubte Zusagen und neue Zahlen in LLM-Vorschlägen werden blockiert
- [ ] Eine freie Umformulierung wird nicht automatisch als wahr bestätigt
- [ ] Manipulierte Produktbeschreibung wird zurückgehalten
- [ ] Keine Antwort wird ohne Verkäuferfreigabe versendet
- [ ] Alle 166 Python-Tests erfolgreich

Tag 13: Orchestrator, Agenten und Validierung mit komplexeren
Mehrfachanfragen und LLM-Fallbacks als vollständiges System härten.

</details>

<details>
<summary><strong>PHASE2_TAG13.md</strong></summary>

# Phase 2 – Tag 13: Robustheit der gesamten Multi-Agent-Pipeline

## Ziel

Wir haben jetzt **Router + Information + Negotiation + Logistics + Validator**. Heute
machen wir die Verbindung robuster. Keine neue Datenbank, keine Django-Änderung,
kein Framework für Multi-Agenten, keine automatische Kundenkommunikation.

## Installation unter Windows (PowerShell in VS Code)

Voraussetzung: Tag 12 ist installiert, die virtuelle Umgebung `(.venv)` ist aktiviert.

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase2_tag13.zip" -DestinationPath "." -Force
python -m agent_system.tag13_demo --alle
python -m unittest discover -s agent_system/tests -v
```

Optional **eine** echte Anfrage mit Ollama:

```powershell
python -m agent_system.tag13_demo --fall mehrfach --mit-ollama
python -m agent_system.tag13_demo --fall mehrfach --mit-ollama --frage "Ist Versand möglich und wäre 180 Euro okay?"
```

Falls du Ollama nicht gestartet hast, bleibt der existierende regelbasierte
Fallback aktiv. `--alle` ist bewusst Offline, damit es schnell bleibt.

## Was wurde geändert?

| Datei | Zweck |
| --- | --- |
| `agent_system/safety.py` | Erkennt einige eindeutige Widersprüche in Produktdaten und prüft LLM-Routing auf fehlende, regelbasiert erkennbare Anliegen |
| `agent_system/pipeline.py` | Protokolliert `audit`, blockiert betroffene Antwortteile, verarbeitet partielle Agenten-/Validator-Ausfälle sicher |
| `agent_system/tag13_demo.py` | Sechs interaktive Testfälle ohne Ollama; optional einer mit Qwen |
| `agent_system/tests/test_safety.py` | Isolierte Tests für Eingabe-Audit und Routing |
| `agent_system/tests/test_integration_day13.py` | Gesamttests für mehrere Agenten, Ausfälle und Unsicherheiten |

## 1. Warum Router-Gegenprüfung?

Eine formal gültige LLM-Entscheidung kann trotzdem ein Anliegen übersehen.

**Kundenfrage:** „Zustand und Versand?“

**LLM-Router (falsche Teilantwort):** `information`

**Regelrouter erkennt:** `information`, `logistics`

**Tag 13:** `logistics` wird ergänzt. Im Feld `audit` steht
`router_missing_intent`; die Router-Ausgabe erhält einen Warnhinweis. Die
ursprüngliche Modellentscheidung ist damit **nicht** als vollständig korrekt
bewiesen. Die Gegenprüfung ist nur für *explizit erkannte* Absichten zuständig.

Der Regelrouter entfernt absichtlich keine Agenten aus der LLM-Liste, da
Heuristiken umschriebene Fragen nicht zuverlässig erkennen. Ein nicht von Regeln
bestätigter Agent wird ggf. mit `router_unconfirmed_agent` protokolliert.

## 2. Warum Eingabe-Audit?

Bei widersprüchlichen Daten dürfen wir keine scheinbar sichere Antwort geben.

**Beispiel:**

- Strukturiertes Feld: `shipping_available = false`
- Produktbeschreibung: `Versand möglich.`
- Anfrage: `Ist Versand möglich?`
- **Ergebnis:** `audit = shipping_conflict`, Antwortteil `blocked`.

Der Audit prüft außerdem einige eindeutige Widersprüche bei Abholung und
Verfügbarkeit. Unbekannte Werte (`null`) gelten **nicht** als Widerspruch.
Bei erkannten Prompt-Injection-Sätzen in Produktbeschreibung oder Kundenfrage
wird ein Warnhinweis protokolliert. Wird eine verdächtige Produktbeschreibung
für eine Informationsantwort benötigt, bleibt dieser Antwortteil blockiert.

Diese Textmuster sind **kein vollständiger semantischer Faktencheck** und
können nicht jede manipulierte oder widersprüchliche Angabe erkennen.

## 3. Warum partielle Fehlerbehandlung?

Wenn der Information Agent funktioniert, aber Logistics intern scheitert,
müssen wir nicht den ganzen Vorgang abbrechen. Die sichere Information kann als
Entwurf bleiben; der Logistikteil wird durch einen neutralen Fehlerhinweis
ersetzt. Im `audit` erscheint `agent_execution_error`.

Bei **Routerfehlern** wird keine freie Antwort erzeugt: Die Pipeline fragt nach,
protokolliert `router_error` und stellt den Vorgang zur Verkäuferprüfung.
Fehlerdetails aus internen Exceptions erscheinen absichtlich **nicht** im
Kundentext oder im JSON-Ergebnis.

## Sechs praktische Szenarien

```powershell
python -m agent_system.tag13_demo --alle
python -m agent_system.tag13_demo --fall widerspruch
python -m agent_system.tag13_demo --fall fehlend
python -m agent_system.tag13_demo --fall manipulation
python -m agent_system.tag13_demo --fall unklar
```

- **mehrfach:** drei Agenten; Preisverhandlung ohne Zusage
- **widerspruch:** Versanddaten widersprechen sich; Logistikentwurf blockiert
- **fehlend:** unbekannte Verfügbarkeit und Zustand werden nicht erfunden
- **unklar:** es kommt eine Rückfrage statt einer erfundenen Antwort
- **manipulation:** eine Steueranweisung wird protokolliert, nicht befolgt
- **verfuegbarkeit:** widersprüchliche Verfügbarkeitsdaten; Information blockiert

## Was im JSON neu ist

`PipelineResult.to_dict()` enthält zusätzlich:

```json
"audit": [
  {
    "code": "shipping_conflict",
    "detail": "Versandangabe und Produktbeschreibung widersprechen sich; Versandantwort zurückhalten.",
    "affected_agents": ["logistics"]
  }
]
```

Die bisherigen Felder (`route`, `replies`, `combined_draft`,
`review_status`, `factual_validation`, `validation`) bleiben erhalten.

**Wichtig:** `validation` meldet nun bei einem von der Eingabeprüfung
zurückgehaltenen Agenten ausdrücklich `draft_status: blocked` und zusätzlich
`conflicting_input_hold`. Der Leser muss sich also nicht allein auf die
separate `audit`-Liste verlassen.

## Definition of Done

- [ ] `python -m agent_system.tag13_demo --alle` zeigt alle sechs Fälle
- [ ] Bei „widerspruch“ erscheint `shipping_conflict` und `blocked`
- [ ] Bei „fehlend“ wird Unbekanntes nicht als Tatsache ausgegeben
- [ ] Bei „unklar“ erscheint eine Rückfrage
- [ ] Bei „manipulation“ wird keine Preiszusage gemacht
- [ ] `python -m unittest discover -s agent_system/tests -v`: **216 Tests, OK**
- [ ] Optional: eine echte Ollama-Frage auf dem eigenen Rechner geprüft

**Git nach erfolgreichen Prüfungen:**

```powershell
git add agent_system PHASE2_TAG13.md
git commit -m "Phase 2 Tag 13: robuste Agenten-Pipeline"
git push
```

## Weiter mit Tag 14

An Tag 14 bauen wir eine **reproduzierbare Szenario-Evaluation** mit
Klassifikations- und Sicherheitsmetriken. Die verpflichtenden 30 repräsentativen
Fälle für das Gesamtprojekt prüfen wir spätestens in Phase 3 zusammen mit
der echten Django-Integration.

**Unveränderte Grenzen:** kein automatischer Versand, keine automatische
Verkäuferfreigabe, keine Preisannahme, keine Änderung von Produktdaten. Die
Regelprüfungen und Beispieltests sind kein Beweis allgemeiner LLM-Zuverlässigkeit.

</details>

<details>
<summary><strong>PHASE2_TAG14.md</strong></summary>

# Fundplatz – Phase 2, Tag 14: Agentenqualität messen

## Ziel

Den Stand aus Tag 13 **mit 40 vorab beschrifteten Testfällen** auswerten. Keine
Django-Änderungen, keine zusätzlichen Python-Pakete, kein Nachrichtenversand.

Wichtig: **Unit-Tests und fachliche Evaluation sind verschieden.** Ein
bestandener Unit-Test bedeutet nicht, dass der Router jede natürliche Frage
richtig zuordnet.

## Installation unter Windows (VS Code / PowerShell)

Voraussetzung: Der Tag-13-Code ist bereits installiert; `.venv` ist aktiviert.

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase2_tag14.zip" -DestinationPath "." -Force
python -m unittest discover -s agent_system/tests -v
python -m agent_system.evaluation --mode offline
```

Ergebnisdateien liegen in `evaluation_reports/tag14_offline/`:
- `report.md` – lesbarer Bericht mit Auffälligkeiten
- `report.csv` – eine Zeile pro Testfall, gut für Excel
- `report.json` – maschinenlesbare Ergebnisse inklusive Kennzahlen

Die Datei `agent_system/examples/tag14_scenarios.json` enthält den synthetischen
Beispielartikel und **40 unabhängige Erwartungsdefinitionen**. Du kannst z. B.
`T04` nachlesen und prüfen, welche Agenten vorgesehen sind.

## Ollama gezielt prüfen (optional, aber empfohlen)

Das lokale Qwen-Modell muss gestartet und in Ollama installiert sein.

```powershell
ollama list
python -m agent_system.evaluation --mode llm --per-category 1
```

`--per-category 1` führt **zehn** Fälle aus (einen aus jeder Kategorie). Die
Ergebnisse stehen in `evaluation_reports/tag14_llm/`. So messen wir wirklich die
Modellentscheidung statt die Regelroute. Achtung: Das ist eine **kleine
Stichprobe**, nicht die vollständige LLM-Evaluation. Für alle 40:

```powershell
python -m agent_system.evaluation --mode llm
```

Wichtig: Der Router fällt bei Ollama-Problemen möglicherweise auf die Regeln
zurück. Prüfe im Bericht unbedingt `Router-Herkunft` (`llm` / `fallback`), sonst
würde man Offline-Entscheidungen irrtümlich als Qwen-Qualität interpretieren.
Auch beim LLM-Lauf werden niemals Nachrichten versendet oder Preise akzeptiert.
Ein LLM-Durchlauf kann deutlich länger dauern als der Offline-Test.

Gezielt einen schwierigen Bereich wiederholen:

```powershell
python -m agent_system.evaluation --mode offline --category availability
```

## Was ist neu?

| Datei | Zweck |
| --- | --- |
| `agent_system/examples/tag14_scenarios.json` | 40 Testfälle in zehn Kategorien, vorab festgelegte Erwartungswerte |
| `agent_system/evaluation.py` | Runner, Messgrößen, CSV-/JSON-/Markdown-Berichte |
| `agent_system/tests/test_evaluation_day14.py` | 27 neue Unit-Tests für Eingabedaten und Evaluationsmechanik |
| `evaluation_reports/tag14_offline/` | Bereits lokal erzeugter Offline-Baselinebericht |

## Baseline aus dieser Entwicklungssitzung (Offline-Regelrouter)

Ausgeführt mit dem unveränderten Tag-13-Router (keine Fehler zur Zahlenschönung
korrigiert):

- 40 synthetische Szenarien (je vier: availability, condition, technical,
  negotiation, logistics, multi, missing, unclear, conflict, injection)
- **36/40** alle pro Fall definierten Prüfpunkte bestanden
- **90,0 %** exakte Agentenmenge
- **100,0 %** Agenten-Präzision, **90,2 %** Agenten-Recall
- **8/8** Fälle mit erwarteten Audit-Meldungen erkannt
- **4/5** erwartete Sicherheitsblockierungen erkannt
- **0** entdeckte riskante Zusagemuster in den sichtbaren Entwürfen
- **0** Fälle mit durch die Zahlenheuristik erkannten neuen Zahlen
- **40/40** Ausgaben bleiben als verkäuferpflichtiger Entwurf markiert

Auffälligkeiten für Tag 15:

- **A03:** „Bereits verkauft?“ wird nicht als Information klassifiziert.
- **A04:** „Ist reserviert?“ wird nicht als Information klassifiziert.
- **T04:** „Wie alt ist der Laptop?“ wird vom Regelrouter übersehen.
- **W04:** Eine Reservierungsfrage mit widersprüchlicher Beschreibung wird
  nicht an Information weitergereicht; deshalb greift die vorgesehene
  Agentenblockierung nicht.

**Keine automatische Korrektur an Tag 14:** Erst messen wir den Ausgangszustand,
danach verbessern wir an Tag 15 den Router und vergleichen die Berichte.

## Was wird genau gemessen?

- `route_exact`: stimmen **alle** erwarteten Agenten (Menge) überein?
- Präzision: Anteil richtig ausgewählter Agenten an allen ausgewählten Agenten.
- Recall: Anteil erkannter Agenten an allen erwarteten Agenten.
- Rückfrage: bei leerer erwarteter Agentenliste sollte nachgefragt werden.
- Audit/Block: werden die **vorab erwarteten** Warnungen und Sperren erkannt?
- `text_ok`: enthält der sichtbare Entwurf vorab definierte Schlüsselphrasen?
- Zahlen-/Zusageprüfungen: erkennt eine begrenzte Heuristik neue numerische
  Angaben oder gefährliche Formulierungen?

Eine Stichwortprüfung ist keine semantische Faktenprüfung. Eine synthetische
Testdatenbasis beweist nicht, dass alle realen Anfragen sicher beantwortet
werden. Die Prüfkennzahlen sind bewusst **separat** statt als irreführende
„Gesamtintelligenz in Prozent“ ausgewiesen.

## Git / GitHub

Nach erfolgreicher lokaler Ausführung:

```powershell
git add agent_system/evaluation.py agent_system/examples/tag14_scenarios.json agent_system/tests/test_evaluation_day14.py PHASE2_TAG14.md evaluation_reports/tag14_offline/report.md
git commit -m "Phase 2 Tag 14: Szenario-Evaluation"
git push
```

`report.csv` und `report.json` bleiben zunächst lokal, damit keine später
eingetragenen realen Kundendaten versehentlich veröffentlicht werden. Für diese
Beispieltests wurden ausschließlich fiktive Daten verwendet.

## Definition of Done

1. Die Unit-Tests bestehen (hier lokal: **243** Tests).
2. 40 Szenarien wurden im Offline-Modus ausgeführt.
3. `report.md` zeigt Metriken und konkrete Fehlerfälle.
4. Eine kleine, über Kategorien verteilte Qwen-Stichprobe wurde ausgeführt und
   auf echtes `llm`-Routing statt `fallback` geprüft.
5. Offene Fehler werden für Tag 15 festgehalten, nicht als Erfolg kaschiert.

</details>

<details>
<summary><strong>PHASE2_TAG15.md</strong></summary>

# Phase 2 – Tag 15: Router verbessern und Agentensystem abnehmen

**Ziel:** Vier Schwachstellen aus Tag 14 beheben, die gleiche 40-Fälle-Evaluation unverändert wiederholen und die Qualität an 18 zusätzlichen Formulierungen prüfen. Django und SQLite werden nicht verändert.

## 1. Installation in VS Code (PowerShell, `.venv` schon aktiv)

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase2_tag15.zip" -DestinationPath "." -Force
```

Die ZIP-Datei enthält **nur geänderte/neue Dateien**. Keine Migration und keine weiteren Pakete.

## 2. Was wurde geändert?

- `agent_system/router.py`: Der Regelrouter erkennt jetzt *verkauft*, *reserviert*, *schon weg*, *wie alt*, *Baujahr* und zusätzliche Formulierungen. Auch *wären 150 €* wird als Verhandlung erkannt.
- `agent_system/agents.py`: Der Information Agent versteht weitere Verfügbarkeits-/Altersformulierungen; veraltete Codekommentare wurden aktualisiert. Seine Antworten stützen sich weiterhin nur auf vorhandene Angaben.
- `agent_system/tests/test_evaluation_day14.py`: Ein alter Test hatte den Tag-14-Fehler A03 ausdrücklich als weiterhin vorhanden vorausgesetzt. Nun wird absichtlich ein falsches Testlabel verwendet, um die Fehlerdarstellung des Berichts zu testen.
- `agent_system/tests/test_day15_regression.py`: 19 zusätzliche Unit-Tests.
- `agent_system/examples/tag15_additional_scenarios.json`: 18 zusätzliche, manuell beschriftete Szenarien. Diese dienten während Tag 15 als zusätzliche Regressionstests, sind also **kein unverbrauchter Blindtest**.
- `agent_system/tag15_compare.py`: Druckt Vorher-Nachher-Kennzahlen aus gespeicherten Berichten; ruft kein LLM auf.
- `evaluation_reports/tag15_*`: Getrennte Berichte mit Vorher-/Nachher-Stand und zusätzlichen Fällen.

## 3. Python-Tests

```powershell
python -m unittest discover -s agent_system/tests -v
```

**Im bereitgestellten Stand lokal geprüft:** `Ran 262 tests` / `OK` (ohne echtes Ollama).

## 4. 40 Szenarien – Vorher-/Nachher-Vergleich

```powershell
python -m agent_system.evaluation --mode offline --out-dir evaluation_reports/tag15_after
python -m agent_system.tag15_compare
```

Gemessen mit **demselben Tag-14-Datensatz**:

| Messgröße | Vorher | Nachher |
|---|---:|---:|
| Exaktes Routing | 90,0 % | 100,0 % |
| Vollständig bestandene Fälle | 36/40 | 40/40 |
| Fehlfälle | A03, A04, T04, W04 | keine |

Diese Zahlen beschreiben nur das **regelbasierte Offline-Routing und die implementierten Checks**, keine allgemeine Garantie.

## 5. Weitere 18 Regressionstests

```powershell
python -m agent_system.evaluation --mode offline --cases agent_system/examples/tag15_additional_scenarios.json --out-dir evaluation_reports/tag15_additional
```

**Gemessen:** 18/18 Fälle bestanden. Eine Preisvariante („Wären 150 € ...“) fiel im ersten Durchlauf auf und wurde vor dem endgültigen Ergebnis korrigiert.

## 6. Integrierten Ablauf testen

```powershell
python -m agent_system.tag13_demo --alle
```

Sechs integrierte Szenarien wurden in der bereitgestellten Umgebung ausgeführt. Bei widersprüchlichen Daten wird der betreffende Teil zurückgehalten; bei unklaren Fragen erfolgt eine Rückfrage.

## 7. Echte LLM-Abnahme auf deinem PC

```powershell
ollama list
python -m agent_system.evaluation --mode llm --per-category 1 --out-dir evaluation_reports/tag15_llm_smoke
python -c "import json; r=json.load(open('evaluation_reports/tag15_llm_smoke/report.json', encoding='utf-8')); print(r['summary']['sources'])"
```

Hier werden **10 Qwen-/Ollama-Anfragen** aus verschiedenen Kategorien durchgeführt. Wichtig ist die Herkunft: `llm` bedeutet Modellentscheidung, `fallback` bedeutet Fehler-/Fallbackpfad. Achte auf die Spalten `actual_agents`, `expected_agents` und die Fälle unter `failures` im Bericht. Bei Abweichungen darf Phase 2 nicht als vollständig modellgetestet gelten.

Wenn es praktikabel ist, alle 40 echten LLM-Fälle prüfen:

```powershell
python -m agent_system.evaluation --mode llm --out-dir evaluation_reports/tag15_llm_full
```

**Aussagegrenzen:** Regex- und Stichwortprüfungen können nicht jede Halluzination oder jede subtile Preiszusage erkennen; Antworten werden niemals selbstständig verschickt oder freigegeben. Produktbeschreibungen sind unbestätigte Eingaben. Weitere Sicherheitsprüfungen folgen während der Integration in Phase 3.

## 8. Git-Commit nach erfolgreicher lokaler Prüfung

```powershell
git add agent_system PHASE2_TAG15.md evaluation_reports/tag15_before evaluation_reports/tag15_after evaluation_reports/tag15_additional
git commit -m "Phase 2 Tag 15: Routing verbessern und Evaluation abschliessen"
git push
```

Das lokale `evaluation_reports/tag15_llm_smoke` musst du nicht veröffentlichen, wenn du es nicht bewusst teilen möchtest.

**Definition of Done:** 262 Tests grün; die 40 unveränderten Offline-Szenarien und die 18 Zusatzfälle erneut ausgewertet; die sechs Integrationsdemos laufen; mindestens 10 echte LLM-Fälle inkl. Herkunft `llm/fallback` geprüft; Git aktualisiert. Erst danach Phase 3 beginnen.

</details>

