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
