# Fundplatz – Phase 3 / Tag 16: Django + Agenten verbinden

## Ziel

Eine angemeldete Person kann auf einer **aktiven fremden Anzeige** eine Frage stellen.
Django speichert die Frage als `CustomerInquiry`, übergibt die Produktdaten an
`agent_system`, speichert **nur einen privaten, ungeprüften Entwurf** und zeigt
diesen ausschließlich dem Eigentümer der Anzeige im Postfach `/anfragen/`.
Es wird **keine Antwort an den Käufer versendet**, kein Preis geändert und
kein LLM-Text automatisch freigegeben.

## Architektur

```text
Käufer -> Django-Detailseite -> POST /anzeigen/<id>/anfrage/
       -> CustomerInquiry speichern
       -> listings.agent_bridge.listing_to_agent_input()
       -> agent_system.AgentPipeline (Router + 3 Agenten + Validator)
       -> privaten Entwurf und Prüfstatus speichern
       -> Käufer erhält nur eine Eingangsbestätigung

Verkäufer -> /meine-anzeigen/ -> /anfragen/
         -> eigene Anfragen + private Entwürfe (keine Sende-Funktion)
```

`agent_system` importiert **kein Django**. Die Adapterdatei
`listings/agent_bridge.py` übersetzt ein `Listing` nach `ProductContext`
und eine Frage nach `CustomerRequest`. Eine aktive Anzeige ist **nicht**
automatisch als verfügbar markiert: `availability = None`.

## Installation in PowerShell (virtuelle Umgebung bereits aktiv)

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag16.zip" -DestinationPath "." -Force
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
python manage.py runserver
```

Neue Migration: `listings/migrations/0002_customerinquiry.py`. Eine bestehende
`0001_initial.py` **nicht** löschen oder überschreiben.

## Manueller Browser-Test mit 2 Konten

1. **Verkäuferkonto A:** Eine aktive Anzeige erstellen, bei `/meine-anzeigen/`
   `Kundenanfragen ansehen` prüfen.
2. **Käuferkonto B:** Einloggen, die Detailseite von A öffnen, folgende Frage
   senden: `Ist Versand möglich und würdest du 180 Euro akzeptieren?`.
3. B sieht nur eine Eingangsbestätigung und **keinen** Antwortentwurf.
4. A loggt sich ein und öffnet `/anfragen/`. Dort ist die Frage und ein
   **nicht freigegebener, privater Entwurf** sichtbar. Es existiert
   noch kein Freigabe- oder Senden-Button.
5. A kann keine Frage zur eigenen Anzeige absenden. Bei deaktivierter Anzeige
   nimmt das System keine neue Anfrage an.

## Offline- und LLM-Modus

Standard: **Offline-Regelrouter**, kein Ollama nötig. Für ein echtes lokales
Qwen-Modell vor dem Django-Start im selben PowerShell-Terminal:

```powershell
$env:FUNDPLATZ_AGENT_USE_LLM="1"
python manage.py runserver
```

Zurück zum Offline-Modus: `Remove-Item Env:FUNDPLATZ_AGENT_USE_LLM`
und Django **neu starten**.

Hinweis: Der Tag-16-MVP verarbeitet die Agenten-Anfrage synchron im Django-
Request. Bei langsamem Qwen kann der Browser vorübergehend auf die
Bestätigung warten. Asynchrone Verarbeitung und robusterer Produktionsschutz
sind spätere Ausbaustufen. Bei unerwarteten Fehlern bleibt die Kundenfrage
in der Datenbank und bekommt den Status `needs_attention`.

## Sicherheitsentscheidungen

- Django-Login für neue Anfragen und das Verkäuferpostfach.
- POST + CSRF-Token für das Absenden.
- Keine Fragen an eigene/deaktivierte Anzeigen.
- Formular begrenzt auf 5–2000 Zeichen.
- Einfaches Limit: 5 Kundenanfragen pro Konto und Stunde (lokaler MVP,
  kein atomarer verteilter Rate Limiter).
- Postfach-Filter über `listing__seller=request.user` verhindert Zugriff
  auf fremde Entwürfe.
- Keine automatische Freigabe oder Nachricht an Kunden.
- Fehler des lokalen Modells werden Käufern nicht als technische Details angezeigt.
- LLM-Entwürfe werden durch die Phase-2-Pipeline geprüft. Diese Prüfung ist
  **kein vollständiger Faktencheck**; Verkäuferfreigabe ist Pflicht.

## Dateien verstehen

| Datei | Rolle |
|---|---|
| `listings/agent_bridge.py` | Django-Listing in reine Agenteneingabe übersetzen |
| `listings/models.py` | Neues `CustomerInquiry`-Modell |
| `listings/migrations/0002_customerinquiry.py` | Tabelle in SQLite anlegen |
| `listings/forms.py` | Validiertes Frageformular |
| `listings/views.py` | Anfrage speichern + Agentenlauf + privates Postfach |
| `listings/urls.py` | Neue POST-Route und Inbox-Route |
| `listings/templates/listings/listing_detail.html` | Fragenformular auf Detailseite |
| `listings/templates/listings/seller_inquiries.html` | Private Postfachliste |
| `listings/templates/listings/my_listings.html` | Link zum Postfach |
| `listings/test_day16.py` | 16 Django-Integrationstests |
| `agent_system/tests/test_day16_bridge.py` | 4 Python-Adaptertests ohne Django |

## Teststand

Im Paket hier ausgeführt: **266 Python-Agententests erfolgreich**
(262 Phase-2-Tests + 4 neue Adaptertests). Django ist in der Build-Umgebung
nicht installiert; deshalb müssen die 16 neuen Django-Integrationstests
mit `python manage.py test listings` auf dem Windows-PC ausgeführt werden.

## Nach erfolgreichem lokalem Test

```powershell
git add agent_system/tests/test_day16_bridge.py listings config/settings.py templates/base.html PHASE3_TAG16.md
git commit -m "Phase 3 Tag 16: Django Agenten Integration und Kundenanfragen"
git push
```

Nächster Schritt Tag 17: Verkäuferpostfach mit Detailansicht, gezielter
Rückfragenbearbeitung und Statusverwaltung erweitern. Freigabe und Versand
bleiben bis zur expliziten Implementierung gesperrt.
