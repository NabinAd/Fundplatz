# Fundplatz – Phase 3, Tag 24

## Ziel: Ende-zu-Ende-Tests mit zwei real getrennten Verkäuferkonten

Tag 24 ergänzt **60 neue Django-Tests** in `listings/test_day24.py`.
Es werden **keine Datenbankmodelle, produktiven Views, Templates oder Migrationen verändert**.

### Welche Tests sind enthalten?

- **32 vollständige Szenarien**, die jeweils einen durchgehenden Ablauf prüfen:
  Kundenfrage per HTTP POST → Warteschlange → Worker → privater KI-Entwurf → Verkäufer-Editor → interne Freigabe → explizite Bereitstellung → Käuferpostfach.
- **4 vollständige Offline-Agentenabläufe** ohne Mock des KI-Systems: Versand und Preis für beide unterschiedlichen Anzeigen. Dabei wird die echte `AgentPipeline` mit dem Offline-Regelrouter verwendet.
- **24 weitere Negativ- und Sicherheitstests** für Besitzrechte, private Daten, XSS, CSRF, Rate-Limits, manipulierte Formulare, ungültige Eingaben, Modellfehler, doppelte Worker-Läufe, veraltete Freigabe-Token und doppelte Bereitstellung.

In den 32 simulierten Szenarien wird **nur der Modellaufruf gemockt**. Die Django-Views, Datenbankzugriffe, Formulare, Autorisierung, Ereignisse und Templates werden tatsächlich durchlaufen. Ein gemocktes `route_source="llm"` bestätigt somit **keinen echten Ollama-Lauf**. Die vier weiteren Durchläufe verwenden dagegen echte Offline-Agenten.

### Zwei Verkäufer, zwei Anzeigen, getrennte Browser

| Testkonto | Rolle | Anzeige | Preis | Versand | Verhandlungsbasis |
|---|---|---|---:|---|---|
| `tag24_seller_a` | Verkäufer A | Fahrrad von A | 5,00 € | Ja | Ja |
| `tag24_seller_b` | Verkäufer B | Notebook von B | 180,00 € | Nein | Nein |
| `tag24_buyer_a` | Käufer A | Stellt Fragen zu A und B | – | – | – |
| `tag24_buyer_b` | Käufer B | Stellt Fragen zu A und B | – | – | – |

Die Tests verwenden **vier getrennte Django-Testclients mit eigener Session** – vergleichbar mit mehreren verschiedenen Browsern oder Browserprofilen. Die Rolle ist an den authentifizierten Benutzer gebunden, nicht an den Browser.

**Sicherheitsinvarianten:**

1. Anfrage und Worker verwenden genau die `listing_id` der angefragten Anzeige.
2. Produktpreis, Versandstatus und Verhandelbarkeit stammen **nicht** aus einer fremden Anzeige.
3. Ein fremder Verkäufer erhält für eine Anfrage `404` und darf sie weder bearbeiten noch freigeben oder bereitstellen.
4. Ein anderer Käufer erhält ebenfalls `404` und darf fremde Anfragen nicht im eigenen Postfach sehen.
5. Private KI-Entwürfe und Auditwerte bleiben dem Käufer auch nach Bereitstellung verborgen.
6. Die intern freigegebene Antwort wird erst durch einen gesonderten POST mit Bestätigung sichtbar.
7. Doppelte Worker-/Bereitstellungsaufrufe erzeugen keine doppelten Ereignisse oder Antworten.
8. Die gespeicherte Käuferantwort ist ein unabhängiger Snapshot der vom Verkäufer freigegebenen Fassung.

## Installation unter Windows (VS Code / PowerShell)

**Voraussetzung:** Tag 23, die Statusanzeige-Verbesserung, die käuferfreundliche Formulierungsschicht und der zuletzt bereitgestellte Testfix für fünf Django-Fehler sind installiert.

Deine virtuelle Umgebung zeigt bereits `(.venv)`. Deshalb überall `python` verwenden.

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag24.zip" -DestinationPath "." -Force
```

Tag 24 ändert keine Datenbankmodelle: **keine Migration erforderlich**.

## Tests ausführen

Für reproduzierbare Testläufe mit ausschließlich lokalen Daten:

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="1"
$env:FUNDPLATZ_AGENT_USE_LLM="0"
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test listings.test_day24 -v 2
```

Der Test-Runner sollte für dieses Modul `Ran 60 tests` und `OK` melden. Das ist **ein Soll-Ergebnis**, keine Bestätigung, dass alle 60 Tests bereits auf deinem Windows-PC bestanden hätten.

Danach die Regressionstests:

```powershell
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
```

Vor Tag 24 hat dein letzter Log `340` Django-Tests gezeigt. Wenn dieser Stand vollständig ist und keine weiteren Tests hinzugekommen sind, sind nach Installation **400 Django-Tests** zu erwarten (340 bisherige + 60 neue).

### Optional: manuelle Browserprüfung

1. Browser A als Verkäufer A öffnen, Browser B als Verkäufer B anmelden.
2. Mit einem Käuferkonto eine Frage zur Anzeige **Fahrrad von A / 5,00 €** stellen.
3. Kontrollieren, dass **nur Verkäufer A** die interne Anfrage und den privaten Entwurf sehen kann.
4. Dasselbe bei **Notebook von B / 180,00 €** durchführen und nur Verkäufer B prüfen.
5. Im asynchronen Modus (`FUNDPLATZ_AGENT_ASYNC=1`) muss der Worker in einem **zweiten Terminal** laufen:

```powershell
$env:FUNDPLATZ_AGENT_USE_LLM="1"
python manage.py process_inquiries --loop
```

Dieser manuelle Test darf echte Ollama-Antworten erzeugen. Die automatische Testdatei benötigt dagegen **keinen** Ollama-Server.

### Fehleranalyse

Wenn `test_day24` fehlschlägt, sende bitte den Namen des ersten fehlgeschlagenen Tests und dessen `Traceback`. Nicht alle 400 Testzeilen sind nötig.

Mit `-v 2` sind die Einzelszenarien durchnummeriert, damit wir konkret eine Ursache beheben können, statt Sicherheitsprüfungen abzuschalten.

## Testausführung durch die Entwicklungsumgebung

- Die neue Datei wurde auf Python-Syntax und auf genau 60 Testmethoden bzw. generierte Fälle geprüft.
- Die vorhandenen Agententests wurden in der zusammengestellten aktuellen Codebasis mit **281 / 281 erfolgreich** ausgeführt.
- Ein echter Django-Testlauf war in dieser Erstellungsumgebung **nicht möglich**, weil Django dort nicht installiert ist; er muss auf dem Windows-Rechner ausgeführt werden.
- Für Tag 24 sind keine Produktivcode-Änderungen und keine Migration vorgesehen.

## Git-Abschluss

Nach erfolgreichen Testläufen:

```powershell
git add listings/test_day24.py PHASE3_TAG24.md
git commit -m "Phase 3 Tag 24: 60 Ende-zu-Ende- und Sicherheitstests"
git push
```

**Tag 25:** Abschlussprüfung, offene Fehler beheben, Projektdokumentation und Abnahmeprotokoll erstellen.
