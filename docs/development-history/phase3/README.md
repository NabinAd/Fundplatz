# Phase 3 – Website-Integration und Abnahme (Tage 16–25)

[← Entwicklungsgeschichte](../README.md) · [Architektur](../../../architecktur.md) · [Testing](../../testing.md)

## Ziel und Ergebnis

Die unabhängige Agenten-Pipeline wurde in die Django-Anwendung integriert. Käufer können Fragen stellen, während **Verkäufer** interne Entwürfe bearbeiten, ausdrücklich freigeben und in einem zweiten Schritt im jeweiligen Käuferpostfach bereitstellen. Spätere Entwicklungsschritte ergänzten Verlauf, Zugriffsschutz, asynchrone Verarbeitung und Testabdeckung.

## Zusammengefasste Meilensteine

| Zeitraum | Ergebnis |
| --- | --- |
| Tag 16 | [`agent_bridge.py`](../../../listings/agent_bridge.py) übergibt Anzeigeninformationen und Kundenfrage an die Pipeline; keine automatische Veröffentlichung. |
| Tage 17–18 | Privates Verkäuferpostfach, Statusfilter, Entwurfsdetail und Editor für eigene Antwortfassungen. |
| Tag 19 | Separater Status für ausdrückliche Verkäuferfreigabe und unveränderliche interne Momentaufnahme. |
| Tag 20 | Gesonderte Bereitstellung der freigegebenen Antwort in das Käuferpostfach über [`InquiryDelivery`](../../../listings/models.py), unabhängig vom privaten Entwurf. |
| Tag 21 | [`InquiryEvent`](../../../listings/models.py) hält Bearbeitungsschritte fest, mit getrennter Käufer-/Verkäufer-Sichtbarkeit. |
| Tag 22 | Sicherheits- und Berechtigungsprüfungen, darunter Verhinderung unberechtigter Zugriffe, Schutz vor Formularmissbrauch und Escaping. |
| Tag 23 | Optionale SQLite-Warteschlange und [Worker](../../../listings/draft_queue.py), Status `queued/running/ready/failed` und Fallback-/Ausfallbehandlung. |
| Tag 24 | Ende-zu-Ende-Tests im Django-Testclient für unterschiedliche Konten, Preise, Sichtbarkeit und Statusübergänge. |
| Tag 25 | Abschließender [Datenbank-Audit](../../../listings/management/commands/fundplatz_audit.py), zusätzliche Regressionstests und lokales [Prüfskript](../../../scripts/tag25_abnahme.ps1). |

## Wichtige Details

- **Berechtigung:** Käufer dürfen keine fremden internen Entwürfe sehen; nur der zuständige Verkäufer kann seine eigene Anzeige und Anfrage bearbeiten. Die Trennung wird an Views und gespeicherten Daten geprüft.
- **Momentaufnahmen:** Intern freigegebener Text und veröffentlichter Käufertext werden getrennt gespeichert. Eine spätere Änderung an einem privaten Entwurf veröffentlicht nicht automatisch eine neue Antwort.
- **Sichere Fehlerbehandlung:** Ein fehlgeschlagener Router oder ein Worker-Ausfall darf weder ungeprüften Text veröffentlichen noch interne Fehlermeldungen an den Käufer ausgeben.
- **Queue:** Der optionale Worker läuft außerhalb des Web-Requests. Die lokale SQLite-Lösung ist kein hochverfügbares Produktionssystem.
- **Tests:** Der historische Nachweis vom 27.10.2026 nennt **430 Django-Tests + 281 Agententests**. Die vollständige **manuelle** Abnahme mit echtem Ollama blieb laut Abschlussdokumentation offen.

## Verifikation und offene Arbeiten

Die kompakten, aktuellen Schritte stehen in [`docs/testing.md`](../../testing.md). Besonders zu prüfen sind der manuelle Zwei-Verkäufer-Browserablauf, echte Qwen-Aufrufe, Wiederanlauf der Queue, Backup-Wiederherstellung sowie Deployment-Sicherheit. **Automatische Tests sind keine Freigabe für den Produktivbetrieb.**

Die frühere Schlusscheckliste und die ausführlichen Tages- und Patchnotizen bleiben über die [Git-Historie](https://github.com/NabinAd/Fundplatz/blob/4bfa6c25557b82b41a6af35e72eadc49b5ff84e1/docs/phase-3/README.md) abrufbar. Im aktuellen Branch gelten die [Haupt-README](../../../README.md) und der aktuelle Quellcode.
