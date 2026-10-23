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
