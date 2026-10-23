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
