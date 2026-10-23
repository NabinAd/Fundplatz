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
