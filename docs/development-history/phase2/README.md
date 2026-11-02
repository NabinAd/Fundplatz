# Phase 2 – Multi-Agenten-System (Tage 6–15)

[← Entwicklungsgeschichte](../README.md) · [Architektur](../../architecture.md) · [Evaluation](../../evaluation/README.md)

## Ziel und Ergebnis

Aus dem unabhängigen Python-Paket [`agent_system/`](../../../agent_system/) entstand eine **strukturierte Agenten-Pipeline** für Käuferfragen. Die Pipeline ordnet Fragen zu, erstellt datenbasierte Antwortteile, validiert sie und gibt lediglich einen *privaten* Vorschlag zur Verkäuferprüfung aus.

## Meilensteine statt Tagesberichte

| Entwicklung | Inhalt und technische Entscheidung |
| --- | --- |
| Tage 6–7: lokale Modellanbindung | [Ollama-Client](../../../agent_system/ollama_client.py) und klar validierte [Eingabeobjekte](../../../agent_system/inputs.py). Produktdaten und Kundenfrage werden getrennt übergeben; das Modell wird nicht vorausgesetzt. |
| Tag 8: Orchestrator | [Router](../../../agent_system/router.py) bestimmt, welche Agenten benötigt werden. Unterstützt regelbasierte und optional LLM-gestützte Entscheidungen. |
| Tage 9–11: Spezialagenten | [Information](../../../agent_system/agents.py) für Produkteigenschaften, **Verhandlung** für Preisfragen und **Logistik** für Versand/Abholung. Bei kombinierten Käuferfragen können mehrere Agenten antworten. |
| Tag 12: Validierung | [Validator](../../../agent_system/validation.py) überprüft definierte Risiken und fehlende Angaben. Regeln können nicht sicher beweisen, dass eine freie KI-Antwort faktisch richtig ist. |
| Tag 13: Robustheit | [Pipeline](../../../agent_system/pipeline.py) mit Gegenprüfung von Routing-Entscheidungen, Eingabe-Audit, Konflikterkennung sowie teilweisem Fehler- und Rückfrageverhalten. |
| Tag 14: Szenario-Evaluation | Vordefinierte Fälle vergleichen erwartete Agentenwahl, Blockierungen, Audit-Codes und auffällige Textmuster. |
| Tag 15: gezielte Verbesserung | Regelrouter nach identifizierten Fehlfällen verbessert; Offline-Vergleich von 36/40 auf 40/40 innerhalb derselben bekannten 40 Szenarien, zusätzliche 18/18 Entwicklerfälle. |

## Zentrale Designentscheidungen

**1. Trennung von System und Webframework.** Das Agentensystem enthält keine Django-Abhängigkeit und lässt sich in separaten Python-Unittests aufrufen. Erst Phase 3 verbindet es über die Django-Brücke mit dem Marktplatz.

**2. Kein blindes Vertrauen in die Modellantwort.** Beschreibungen und Kundenfragen sind unvertrauenswürdige Daten, keine Systemanweisungen. Die sichere Basisantwort stützt sich auf vordefinierte Regeln und Produktdaten; LLM-Ausgaben dienen optional als separate Vorschläge, nicht als automatische Freigabe.

**3. Preisverhandlung bleibt beim Verkäufer.** Ein Preisangebot wird nicht selbstständig akzeptiert. Nicht bestätigte Versandkosten, Lieferzeiten und Verfügbarkeiten dürfen nicht als Fakten zugesagt werden.

**4. Nachvollziehbare Evaluation.** Die [Berichte](../../evaluation/README.md) zeigen bei den historischen LLM-Läufen 39/40 vollständig bestandene vordefinierte Tests und dokumentieren die abweichende Agentenwahl im Fall N04. Diese Zahlen belegen keine allgemeine KI-Zuverlässigkeit.

## Relevante Dateien

- [`agent_system/inputs.py`](../../../agent_system/inputs.py): typisierte Produkt- und Anfragekontexte
- [`agent_system/router.py`](../../../agent_system/router.py): Routing / Orchestrierung
- [`agent_system/agents.py`](../../../agent_system/agents.py): drei Fachagenten
- [`agent_system/pipeline.py`](../../../agent_system/pipeline.py): Kombinieren und Auditieren
- [`agent_system/safety.py`](../../../agent_system/safety.py) und [`validation.py`](../../../agent_system/validation.py): Risikoregeln
- [`agent_system/examples/`](../../../agent_system/examples/) und [`tests/`](../../../agent_system/tests/): Szenarien und Regressionen

[Ursprüngliche detaillierte Tagesnotizen in der Git-Historie](https://github.com/NabinAd/Fundplatz/blob/4bfa6c25557b82b41a6af35e72eadc49b5ff84e1/docs/phase-2/README.md).
