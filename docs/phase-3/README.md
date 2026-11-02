# Phase 3 – Django-Integration, Freigabe und Qualitätssicherung

[← Projektübersicht](../../README.md) · [← Phase 2](../phase-2/README.md)

## Zusammenfassung

Phase 3 verbindet Django mit der [Agenten-Pipeline](../../listings/agent_bridge.py). Käuferanfragen werden als private Entwürfe verarbeitet, Verkäufer können sie bearbeiten und explizit freigeben und dann getrennt im Käuferpostfach bereitstellen. Es gibt einen [Ereignisverlauf](../../listings/inquiry_timeline.py), eine optionale [Warteschlange](../../listings/draft_queue.py), [Zugriffskontrollen](../../listings/views.py) und automatisierte [Django-Tests](../../listings/).

## Entwicklungsmeilensteine

| Tage | Fokus |
| --- | --- |
| 16–18 | Brücke, Verkäuferpostfach, Entwurfsbearbeitung |
| 19–22 | Freigabe, Bereitstellung, Verlauf, Sicherheitsprüfungen |
| 23–25 | Worker, Ausfallverhalten, End-to-End-Tests, Audit |

## Abschließender Prüfstatus

Am 27. Oktober 2026 dokumentierte die Haupt-README für den Code-Stand `274086d` 430 erfolgreiche Django-Tests und 281 erfolgreiche Agententests auf Windows. Ein kompletter manueller Browserdurchlauf mit echtem Ollama blieb laut [Abnahmeprotokoll](#fundplatz_abnahme-md) offen. Die älteren Fixnotizen sind keine Aussage über den aktuellen Fehlerstatus.

> **Historischer Stand:** Die folgenden **vollständig übernommenen** Entwicklungs- und Fixnotizen enthalten teilweise überholte Installationsanweisungen, Zahlen und Dateipfade. Für den aktuellen Start und Test die [Haupt-README](../../README.md) verwenden.

## Originalnotizen (vollständiges Archiv)

<details>
<summary id="phase3-tag16-md"><strong>PHASE3_TAG16.md</strong></summary>

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

</details>

<details>
<summary id="phase3-tag17-md"><strong>PHASE3_TAG17.md</strong></summary>

# Fundplatz – Phase 3, Tag 17: Privates Verkäuferpostfach

## Heute umgesetzt

Tag 16: Käuferfrage -> `CustomerInquiry` -> private KI-Antwortvorlage.
Tag 17: **Verkäuferpostfach -> Suche/Status/Pagination -> einzelne Anfrage öffnen -> als „In Bearbeitung“ markieren.**

Noch **keine** Antwortbearbeitung, **keine** Freigabe, **kein** Versand an Käufer.
Der bestehende Agenten-Code bleibt unverändert; es gibt keinen neuen Ollama-Aufruf beim Öffnen von Postfachseiten.

## Installation (PowerShell, .venv bereits aktiviert)

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag17.zip" -DestinationPath "." -Force
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
python manage.py runserver
```

- `migrate` führt **neu** `0003_customerinquiry_in_progress.py` aus; vorhandene Anfragen bleiben erhalten.
- Bei `makemigrations --check --dry-run` ist `No changes detected` das Ziel.
- Du brauchst keine zusätzlichen Pakete.
- Der Tag-16-Stand **muss bereits installiert** sein. Das ZIP enthält nur die Änderungen von Tag 17.

## Browser-Tests mit zwei Konten

1. Als **Käufer B** eine Frage zu einer aktiven Anzeige von **Verkäufer A** stellen. Das ist die bestehende Tag-16-Funktion.
2. Als **Verkäufer A** zu `http://127.0.0.1:8000/anfragen/` gehen.
3. Nach Artikel, Käufername oder Frage suchen; Filter `Prüfung erforderlich` oder `Manuelle Bearbeitung` ausprobieren.
4. Auf **Anfrage öffnen** klicken: `/anfragen/<id>/`. Du siehst die Frage, den privaten Entwurf und Prüfhinweise.
5. Auf **Als „In Bearbeitung“ markieren** klicken. Der Status wechselt; die Frage wird **nicht** an den Käufer beantwortet.
6. Als **Käufer B** dieselbe Detail-URL öffnen: erwartet **404**. Dasselbe mit einem anderen Verkäufer.
7. Wenn du mehr als 10 Anfragen hast, prüfe den Link **Weiter** und die beibehaltenen Filter.

## Die neue Datenbankmigration

Die bestehende `CustomerInquiry.Status`-Aufzählung wird um `in_progress` ergänzt.
Die Tabelle erhält **keine neue Spalte**. Django aktualisiert die gespeicherten Auswahlwerte in der Modeldefinition, ohne bisherige Nachrichten zu löschen.

## Wie der Code aufgebaut ist

| Datei | Aufgabe |
|---|---|
| `listings/models.py` | Status `IN_PROGRESS` |
| `listings/migrations/0003_customerinquiry_in_progress.py` | Django-Migration für Status-Choices |
| `listings/forms.py` | `SellerInquiryFilterForm`: begrenzte und validierte Suchfelder |
| `listings/views.py` | `seller_inquiries`, `seller_inquiry_detail`, `seller_inquiry_start` |
| `listings/urls.py` | Detailroute und POST-only-Statusroute |
| `listings/templates/listings/seller_inquiries.html` | Dashboard, Filter, Karten, Seitennavigation |
| `listings/templates/listings/seller_inquiry_detail.html` | Vollständiger, privater Einzelfall |
| `listings/test_day17.py` | Neue Tests für Datenisolation, Berechtigungen, CSRF, Filter und Status |

### Warum `listing__seller=request.user`?

Anfragen haben einen Käufer (`buyer`), gehören aber einer **Anzeige**. Deshalb entscheidet **der Besitzer der Anzeige**, ob eine private Antwort sichtbar ist.
Die serverseitige Query ist die Sicherheitsgrenze:

```python
inquiry = get_object_or_404(
    CustomerInquiry,
    pk=pk,
    listing__seller=request.user,
)
```

Ein Käufer und ein anderer Verkäufer erhalten 404 statt eines fremden Entwurfs.

### Warum Statusänderung per POST?

GET soll nur Daten lesen. Eine Statusänderung ist eine Aktion; daher ist sie ausschließlich per POST erlaubt. Das HTML-Formular verwendet `{% csrf_token %}`. Der Endpoint prüft zusätzlich den angemeldeten Besitzer.

### Was bedeutet `in_progress`?

Nur eine organisatorische Markierung für den Verkäufer. Es ist **weder `approved` noch `sent`**. Der private KI-Text kann Fehler enthalten und wird nicht an Kunden gesendet.

## Tests und Einschränkungen

Dieses Update wurde statisch geprüft: Python-Dateien syntaktisch gültig, ZIP erfolgreich geöffnet.
**Django ist im Erstellungscontainer nicht installiert**, deswegen kann ich dir kein bestandenes Django-Ergebnis behaupten. Der Befehl `python manage.py test listings` ist auf deinem Windows-PC zwingend der entscheidende Integrationstest. Die bisherigen Phase-2-Tests werden durch die neuen Dateien nicht verändert.

## GitHub

Erst nach erfolgreichem Test:

```powershell
git add listings PHASE3_TAG17.md
git commit -m "Phase 3 Tag 17: privates Verkaeuferpostfach"
git push
```

## Ausblick

**Tag 18:** Den privaten Antwortentwurf als Verkäufer kontrolliert bearbeiten und speichern (weiterhin ohne Senden). **Tag 19:** explizite Freigabe einbauen.

</details>

<details>
<summary id="phase3-tag18-md"><strong>PHASE3_TAG18.md</strong></summary>

# Fundplatz – Phase 3, Tag 18: Antwortentwurf bearbeiten

## Ziel

Ein Verkäufer kann eine Kundenanfrage aus dem privaten Postfach öffnen, einen eigenen Antworttext verfassen, ihn beliebig oft überarbeiten und **nur privat** speichern.

Die KI-Vorlage (`private_draft`) bleibt unverändert. Die Verkäuferfassung (`seller_draft`) wird in einem **eigenen Feld** abgelegt. **Keine automatische Freigabe, kein Versand, keine Käuferansicht der Antwort.**

## Was wurde ergänzt?

| Datei | Änderung |
| --- | --- |
| `listings/models.py` | `seller_draft` (max. 3000 Zeichen) und `seller_draft_updated_at` |
| `listings/migrations/0004_customerinquiry_seller_draft.py` | Datenbankmigration für zwei neue Spalten |
| `listings/forms.py` | `SellerDraftForm`: genau ein editierbares Feld, 5–3000 Zeichen |
| `listings/views.py` | `seller_inquiry_edit`: GET zeigt Formular; POST prüft und speichert nur Verkäufertext |
| `listings/urls.py` | Neue URL `/anfragen/<id>/entwurf/` |
| `listings/templates/listings/seller_inquiry_edit.html` | Bearbeitungsseite mit Kundenfrage und KI-Original daneben |
| `listings/templates/listings/seller_inquiry_detail.html` | Bearbeiten-Link, letzte gespeicherte Fassung |
| `listings/templates/listings/seller_inquiries.html` | Bei gespeicherten Bearbeitungen erscheint eine private Vorschau |
| `listings/admin.py` | Neue Felder im Admin nur lesbar |
| `listings/test_day18.py` | 30 automatisierte Tests für Bearbeitung, Eingaben und Schutzmaßnahmen |

## Installation auf Windows (VS Code, `.venv` bereits aktiv)

**Voraussetzung:** Tag 16 und Tag 17 wurden installiert, und die zugehörigen Migrationen sind vorhanden. Die ZIP-Datei enthält nur die neuen und geänderten Tag-18-Dateien.

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag18.zip" -DestinationPath "." -Force
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
python manage.py runserver
```

**Hinweis:** Wenn `git status` vor dem Update ungespeicherte eigene Änderungen an den gleichen Dateien zeigt, sichere sie zuerst. Das Entpacken mit `-Force` überschreibt die im ZIP enthaltenen Dateien.

## Im Browser testen

1. Mit **Käuferkonto** eine Frage zu einer Anzeige eines anderen Benutzers stellen.
2. Mit **Verkäuferkonto** das Postfach `http://127.0.0.1:8000/anfragen/` öffnen.
3. Eine Anfrage auswählen und **Antwortentwurf bearbeiten** klicken.
4. Kundenfrage und unveränderten KI-Originaltext ansehen. Im Textfeld steht der Vorschlag, sofern die KI-Ausgabe nicht aufgrund eines Problems zurückgehalten wurde.
5. Antwort bearbeiten, zum Beispiel: „Hallo, laut Anzeige ist Versand möglich. Die Kosten muss ich noch prüfen.“
6. **Entwurf privat speichern** klicken. Du wirst zur Anfrage zurückgeleitet; dein eigener Text erscheint separat vom KI-Original.
7. Erneut auf **Antwortentwurf bearbeiten** klicken. Der zuvor gespeicherte Text muss wieder im Textfeld stehen.
8. Teste einen zu kurzen Text und einen leeren Text: Es darf nichts gespeichert werden.
9. Mit **Käuferkonto** die Verkäuferdetail- und Editor-URLs öffnen: Erwartet **404**. Käufer dürfen auch auf der Anzeigen-Detailseite keinen Verkäuferentwurf sehen.

## Warum zwei Textfelder?

```text
CustomerInquiry
 ├── message                  ursprüngliche Kundenfrage
 ├── private_draft            KI-Original, bleibt unverändert
 ├── seller_draft             Text des Verkäufers, editierbar
 ├── seller_draft_updated_at  letzter Speicherzeitpunkt
 └── status                   interne Bearbeitungsstufe
```

Damit kann Tag 19 später die **ausdrückliche Freigabe einer konkreten Verkäuferfassung** ergänzen, ohne den ursprünglichen KI-Vorschlag zu verlieren.

## Sicherheitsregeln

- Nur angemeldete Verkäufer dürfen Anfragen zu ihren **eigenen Anzeigen** bearbeiten (`listing__seller=request.user`). Andere erhalten 404.
- Änderungen sind ausschließlich per POST mit Django-CSRF-Token möglich; GET schreibt nichts.
- Die View übernimmt nur das validierte Feld `seller_draft`. Vom Client zusätzlich gesendete `buyer`, `listing`, `private_draft`, `status`, `audit`, `selected_agents` usw. werden ignoriert.
- Der Text muss nach Trimmen 5–3000 Zeichen enthalten. Die Templates escapen HTML standardmäßig.
- Falls die Agenten-Vorlage einen Zurückhaltungs-/Fehlerhinweis enthält, wird dieser **nicht** als vorbefüllte Antwort vorgeschlagen.
- `needs_attention` bleibt beim Speichern erhalten, damit bekannte Prüfhinweise nicht verschwinden. `review_required` wechselt beim Bearbeiten auf `in_progress`.
- Es gibt in Tag 18 **keinen** Status `approved`/`sent` und keine Antwortansicht für Käufer.

**Grenze:** Verkäufertexte werden an Tag 18 nicht semantisch validiert. Deshalb ist Speichern niemals gleichbedeutend mit fachlicher Freigabe.

## Tests und GitHub

```powershell
python manage.py test listings.test_day18 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
```

Anschließend:

```powershell
git add listings PHASE3_TAG18.md
git commit -m "Phase 3 Tag 18: private Antwortentwuerfe bearbeiten"
git push
```

## Tag 19

Der Verkäufer prüft und bestätigt eine konkrete Antwortfassung durch eine gesonderte Freigabeaktion. Wir trennen dabei Speichern, Freigeben und Anzeigen/Versenden ausdrücklich.

</details>

<details>
<summary id="phase3-tag19-md"><strong>PHASE3_TAG19.md</strong></summary>

# Fundplatz – Phase 3, Tag 19: ausdrückliche Verkäuferfreigabe

## Ziel

Der Verkäufer kann **seinen zuvor gespeicherten eigenen Entwurf** bewusst intern freigeben. Das ist **kein Versand** und macht die Antwort für den Käufer **noch nicht sichtbar**. Die Käuferanzeige und die Kundenanfrage bleiben unverändert.

## Voraussetzungen

- Tag 16, 17 und 18 sind installiert; insbesondere wurde Migration `0004_customerinquiry_seller_draft` ausgeführt.
- In VS Code ist `(.venv)` bereits aktiv.
- Der Testfix für die LLM-Umgebungsvariable aus Tag 17 ist im ZIP ebenfalls enthalten (`listings/test_day16.py`).
- Die eigene SQLite-Datenbank und eigene Uploads werden nicht überschrieben.

## Installation (PowerShell, ab Projektordner)

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag19.zip" -DestinationPath "." -Force
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py test listings.test_day19 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
python manage.py runserver
```

Die Tag-19-Migration `0005_customerinquiry_approval.py` ergänzt `approved_response`, `approved_at`, `approved_by` und den Status `approved`. Es werden **keine bestehenden Daten gelöscht**.

## Browser-Test

1. Melde dich als Verkäufer an und öffne `http://127.0.0.1:8000/anfragen/`.
2. Öffne eine Anfrage **mit zuvor vom Verkäufer gespeichertem Entwurf** (Tag 18). Ohne eigenen gespeicherten Text ist keine Freigabe möglich.
3. Klicke **„Antwort prüfen und freigeben“**.
4. Überprüfe den vollständigen Verkäufertext, die Frage und alle gespeicherten KI-Hinweise.
5. Setze die Checkbox und gib **FREIGEBEN** ein.
6. Nach dem POST siehst du **„Intern freigegebene Antwort“** mit Freigabezeit und Freigeber. Der Text kann über diese Oberfläche nicht mehr bearbeitet werden.
7. Teste denselben Vorgang als Käufer und als fremder Verkäufer: Sie dürfen die privaten Detail- und Freigabeseiten nicht öffnen.

## Neue Dateien und Änderungen

- `listings/models.py`: Status `APPROVED` und drei Freigabefelder.
- `listings/migrations/0005_customerinquiry_approval.py`: Datenbankschema.
- `listings/forms.py`: `SellerApprovalForm` mit Checkbox, Bestätigungswort und verstecktem Entwurf-Token.
- `listings/views.py`: `seller_inquiry_approve`, Snapshot-Freigabe und Sperre bereits freigegebener Anfragen.
- `listings/urls.py`: `anfragen/<pk>/freigabe/`.
- `listings/templates/listings/seller_inquiry_approve.html`: neue private Bestätigungsseite.
- `listings/templates/listings/seller_inquiry_detail.html`: Anzeige der Freigabe und des Snapshots.
- `listings/templates/listings/seller_inquiries.html`: Freigabestatus, Filter, Zähler.
- `listings/admin.py`: alle Freigabefelder nur lesbar.
- `listings/test_day19.py`: 35 neue Tests, einschließlich Berechtigungen, CSRF, veralteter Texte, Formularvalidierung, Doppelklick und fehlendem Versand.
- `listings/test_day17.py`, `listings/test_day18.py`: zwei veraltete Aussagen aktualisiert, die bisher die **Existenz** von `approved` verboten haben.
- `listings/test_day16.py`: Umgebungsunabhängiger Offline-Testfix aus Tag 17.

## Technisches Prinzip

```text
CustomerInquiry.seller_draft
    └── Verkäufer hat Text privat gespeichert (Tag 18)
        └── GET /anfragen/<id>/freigabe/  → Vorschau
            └── POST mit gültigem CSRF + Checkbox + FREIGEBEN + aktuellem Draft-Token
                └── Transaktion, Eigentümer und Text werden geprüft
                    ├── status = approved
                    ├── approved_response = seller_draft   (Snapshot)
                    ├── approved_by = request.user
                    └── approved_at = timezone.now()
```

Die Freigabe prüft, ob die im Browser bestätigte Fassung noch aktuell ist. Ist sie inzwischen verändert, wird die Anfrage mit HTTP 409 abgewiesen. Nach der Freigabe sind die Bearbeitung und das Zurücksetzen des Bearbeitungsstatus gesperrt. Wiederholtes Absenden verändert die Freigabe nicht.

**Sicherheit:** Das System erklärt keine KI-Ausgabe automatisch für wahr. Eine Freigabe bestätigt nur, dass der Verkäufer den Text eigenverantwortlich geprüft hat. KI-Prüfhinweise werden nicht gelöscht. In Tag 19 gibt es **kein** `sent` und keine Käuferansicht für die Antwort.

## Tests

```powershell
python manage.py test listings.test_day19 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
```

**Hinweis zur Prüfung:** Die neue Python-Syntax und die ZIP-Dateien wurden in der Erstellungsumgebung geprüft. Der Django-Testlauf konnte hier wegen fehlender Django-Installation nicht ausgeführt werden; die Tests auf deinem Windows-PC entscheiden über die Abnahme.

## Git

```powershell
git add listings PHASE3_TAG19.md
git commit -m "Phase 3 Tag 19: explizite Verkaeuferfreigabe"
git push
```

## Tag 20

Erst Tag 20 implementiert das Anzeigen der vom Verkäufer freigegebenen Antwort für den **jeweiligen Käufer**. Wir müssen dazu sorgfältig die Empfängerberechtigung, den Freigabestatus und die Unveränderlichkeit des freigegebenen Texts prüfen.

</details>

<details>
<summary id="phase3-tag20-md"><strong>PHASE3_TAG20.md</strong></summary>

# Fundplatz – Phase 3, Tag 20

## Ziel: Freigegebene Antworten dem richtigen Käufer anzeigen

**Wichtig:** Der bisherige Tag-19-Freigabeklick **sendet nicht automatisch**. Tag 20 ergänzt einen **zweiten, expliziten Schritt**: Der Verkäufer bestätigt auf der Detailseite „Antwort an Käufer bereitstellen“. Erst dann ist die Antwort unter `/meine-anfragen/` für genau den Käufer sichtbar. **Keine E-Mail, SMS oder Nachricht an einen externen Marktplatz wird versendet.**

## Technische Trennung

- `CustomerInquiry.private_draft`: ursprünglicher, nur für Verkäufer sichtbarer KI-Entwurf.
- `CustomerInquiry.seller_draft`: nur für Verkäufer sichtbare Bearbeitung.
- `CustomerInquiry.approved_response`: unveränderlich gedachte interne Freigabe, an Tag 19 erstellt.
- **Neu**: `InquiryDelivery.response_text`: eigene Momentaufnahme der tatsächlich bereitgestellten Antwort. Eine `OneToOneField` verhindert mehrere Zustellungen pro Anfrage; `delivered_at` und `delivered_by` dokumentieren die Bereitstellung.
- **Neu**: `buyer_inquiries` und `buyer_inquiry_detail`: nur der `buyer` der Anfrage darf sie lesen. Die Templates geben ausschließlich Kundenfrage und bereits bereitgestellten Antworttext aus.
- **Neu**: `seller_inquiry_deliver`: `@login_required`, `@require_POST`, Anzeigenbesitzer-Check, bestätigte Verkäuferfreigabe, Bestätigungs-Checkbox, Datenbanktransaktion. Erneute POST-Klicks verändern das Ergebnis nicht.

## Dateien

```text
listings/models.py                         + InquiryDelivery
listings/migrations/0006_inquirydelivery.py
listings/forms.py                          + InquiryDeliveryForm
listings/views.py                          + 3 Views
listings/urls.py                           + 3 Routen
listings/admin.py                          + gesperrte Delivery-Ansicht
listings/templates/listings/buyer_inquiries.html       NEU
listings/templates/listings/buyer_inquiry_detail.html  NEU
listings/templates/listings/seller_inquiry_detail.html ERWEITERT
listings/templates/listings/seller_inquiries.html      ERWEITERT
listings/templates/listings/listing_detail.html        Link zu eigenen Anfragen
listings/templates/listings/my_listings.html           Link zu eigenen Anfragen
templates/base.html                       Navigation ergänzt (Desktop ab XL und Mobil)
listings/test_day20.py                     44 neue Django-Tests
```

## Installation (PowerShell / VS Code mit aktivierter `.venv`)

Die Updates von Tag 16–19 müssen vorher bereits installiert sein. Wenn dein Arbeitsverzeichnis ungesicherte Änderungen enthält, sichere sie vor dem Entpacken.

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag20.zip" -DestinationPath "." -Force
python manage.py migrate
python manage.py makemigrations --check --dry-run
python manage.py test listings.test_day20 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
python manage.py runserver
```

Erwartet nach der Migration: `No changes detected`. Wie viele Django-Tests insgesamt laufen, hängt vom zuvor installierten Projektstand ab. Ohne Tag-20-Tests waren es bereits mehr als 100; dieses Paket ergänzt **44**.

## Browser-Test mit zwei Testkonten

1. Käuferkonto: Eine Anfrage stellen über die Detailseite einer **fremden** Anzeige. Unter `http://127.0.0.1:8000/meine-anfragen/` erscheint sie zunächst mit „Noch keine Antwort“.
2. Verkäuferkonto: `http://127.0.0.1:8000/anfragen/` öffnen und eine Anfrage auswählen. Eigene Antwort unter „Antwortentwurf bearbeiten“ speichern und unter „Antwort prüfen und freigeben“ intern freigeben (Tag 18/19).
3. Verkäuferkonto: Auf derselben Detailseite die neue Checkbox aktivieren und auf **„Antwort an Käufer bereitstellen“** klicken.
4. Käuferkonto: `http://127.0.0.1:8000/meine-anfragen/` erneut laden, Anfrage öffnen. Jetzt steht dort ausschließlich der veröffentlichte Antworttext – keine `private_draft`-/`seller_draft`-/`audit`-Information.
5. Anderes Käuferkonto: Dieselbe `/meine-anfragen/ID/`-Adresse muss **404** liefern. Öffentliche Anzeigenseiten zeigen keine Kundenantworten an.
6. Ältere Anfragen, die an Tag 19 lediglich intern freigegeben wurden, bleiben zunächst verborgen, bis ein Verkäufer sie ausdrücklich bereitstellt.

## Warum keine automatische Veröffentlichung?

Eine interne Freigabe aus Tag 19 ist eine menschliche Prüfung; Tag 20 ist ein separater Zustell-Entschluss. Damit können bestehende, intern freigegebene Antworten **nicht unbemerkt** durch ein Softwareupdate öffentlich werden. Außerdem bleiben alle internen Entwürfe auch nach der Zustellung ausschließlich für den Verkäufer zugänglich.

## Grenzen

- Die Antwort wird nur in der eingeloggten Fundplatz-Käuferansicht angezeigt. Keine externe Zustellung, E-Mail oder Push-Nachricht.
- Nach der Bereitstellung gibt es in dieser Version keine nachträgliche Korrektur oder Rücknahme. Solche Schritte brauchen eine eigene, protokollierte Versionierung.
- Das Python-LLM läuft nicht für die Zustellung; die schon freigegebene Antwort wird als Snapshot gespeichert.
- `response_text` ist gegen versehentliche Veränderung über die Views/Admin gesperrt, aber Datenbankadministratoren können Daten weiterhin direkt ändern. Absolute technische Unveränderlichkeit ist nicht behauptet.

## Github

```powershell
git add listings templates/base.html PHASE3_TAG20.md
git commit -m "Phase 3 Tag 20: Kaeuferpostfach und Antwortbereitstellung"
git push
```

</details>

<details>
<summary id="phase3-tag21-md"><strong>PHASE3_TAG21.md</strong></summary>

# Fundplatz – Phase 3, Tag 21: Nachrichten- und Statusverlauf

## Ziel

Nachvollziehbarer Ablauf für eine Kundenanfrage: Eingang → privater Agentenlauf → Bearbeitungsbeginn → Verkäuferentwurf → interne Freigabe → Bereitstellung an Käufer.

Wir speichern **Ereignisse** (`InquiryEvent`) zusätzlich zu `CustomerInquiry` und `InquiryDelivery`. Ein Event enthält nur: Anfrage, Ereignistyp, Sichtbarkeit, auslösender Benutzer und Zeitpunkt. Es enthält **keine Kopie von KI-Entwürfen, Kundenfragen, persönlichen Nachrichten oder Audit-Daten**.

Die Verkäufer-Detailseite zeigt alle Ereignisse der eigenen Anzeige. Die Käufer-Detailseite zeigt **nur zwei** Ereignistypen: „Kundenanfrage eingegangen“ und „Antwort für Käufer bereitgestellt“. Bei Freigabe ohne Bereitstellung sieht der Käufer noch nichts von der Verkäuferantwort.

## Installation (Windows, PowerShell, aktivierte .venv)

**Voraussetzung: Tag 20 ist installiert, Migration 0006 wurde ausgeführt.**

```powershell
cd C:\Kleinanzeigen
git status
```

Lokale Datenbank vor der Migration sichern, falls vorhanden:

```powershell
Copy-Item .\db.sqlite3 .\db_backup_vor_tag21.sqlite3
```

Dateien aus `fundplatz_phase3_tag21.zip` entpacken:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag21.zip" -DestinationPath "." -Force
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

## Tests

```powershell
python manage.py test listings.test_day21 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
```

Es gibt **40 neue Django-Tests** in `listings/test_day21.py`, unter anderem zu Zugriffsrechten, erzeugten Events, doppelten Aktionen, altem Datenbestand und Rollback beim Protokollfehler.

In der Entwicklungsumgebung, in der das ZIP erstellt wurde, ist Django nicht installiert und konnte auch nicht nachinstalliert werden. **Der Django-Testlauf konnte daher hier nicht ausgeführt werden.** Die Python-Dateien wurden auf Syntax und das ZIP auf Integrität geprüft. Bitte den Django-Teststatus auf deinem Windows-Rechner kontrollieren.

## Im Browser ausprobieren

```powershell
python manage.py runserver
```

1. Als Käufer eine Frage zu einer fremden Anzeige stellen. Die Frage erscheint unter `http://127.0.0.1:8000/meine-anfragen/`.
2. Als Verkäufer `http://127.0.0.1:8000/anfragen/` öffnen, die neue Frage auswählen und den **internen Verlauf** ansehen. „Anfrage eingegangen“ und „Interner Antwortentwurf erstellt“ (oder „Automatischer Entwurf fehlgeschlagen“) sind sichtbar.
3. „Als In Bearbeitung markieren“, privaten Verkäufertext bearbeiten und speichern. Beide Aktionen erzeugen separate Zeitpunkte.
4. Die Antwort ausdrücklich freigeben. Der Käufer sieht **noch keine** freigegebene Antwort.
5. Erst bei „Antwort an Käufer bereitstellen“ wird ein öffentlicher Verlaufseintrag erzeugt; der Käufer sieht dann auch die Antwort.
6. Eine beliebige fremde Anfragen-ID in der URL darf kein anderer Nutzer öffnen (404).

## Dateien und Architektur

```text
listings/
├── models.py                          # InquiryEvent
├── inquiry_timeline.py                # Event-Helfer und Sichtbarkeitsfilter
├── views.py                           # atomare Ereignisaufzeichnung in bestehenden Aktionen
├── admin.py                           # Ereignisse im Admin nur lesbar
├── migrations/
│   └── 0007_inquiryevent.py          # Tabelle + Übernahme alter Zeitstempel
├── test_day21.py                      # 40 neue Django-Tests
└── templates/listings/
    ├── seller_inquiry_detail.html    # vollständiger interner Verlauf
    └── buyer_inquiry_detail.html     # nur öffentlicher Verlauf
```

### Wieso getrennte Tabelle?

Eine Anfrage hat **einen aktuellen Status**, aber **mehrere historische Ereignisse**. Daher `InquiryEvent.inquiry = ForeignKey(CustomerInquiry, related_name="events")`. Ein separates Event ermöglicht eine geordnete Zeitleiste und verhindert, dass frühere Schritte bei jeder Statusänderung überschrieben werden.

### Wieso `transaction.atomic()`?

Bei Statuswechseln sollen Datenänderung und Ereigniseintrag **gemeinsam** in die Datenbank geschrieben werden. Falls das Anlegen des Events misslingt, wird die zugehörige Bearbeitungsaktion zurückgerollt. Bei einem neuen Kundenanliegen wird zuerst der Eingang gespeichert, dann der (ggf. langsame) KI-Aufruf außerhalb der Datenbanktransaktion durchgeführt und anschließend Erfolg oder Fehler protokolliert.

### Warum kein vollständiges „Audit-Log“?

Es ist ein **fachliches, append-orientiertes Ereignisprotokoll**, kein manipulationssicheres Audit-System: Administratoren mit direktem Datenbankzugriff könnten Einträge verändern. Es fehlen noch digitale Signaturen, externe Archivierung und eine Datenaufbewahrungsrichtlinie.

### Was passiert mit alten Anfragen?

Die Datenmigration legt einen Eingangs-Event zum bekannten `created_at` an. Falls vorhanden, werden die **tatsächlich gespeicherten** Zeitpunkte für die Verkäuferfassung (`seller_draft_updated_at`), Freigabe (`approved_at`) und Käuferbereitstellung (`delivered_at`) übernommen. Für ältere KI-Läufe und früheren Bearbeitungsbeginn ist kein eigener Zeitstempel vorhanden – hierfür werden **keine Zeitpunkte erfunden**.

Die neue Migration ist datenändernd: Vorher die SQLite-Datei sichern. Bei einem Rollback der Migration würde die Ereignistabelle gelöscht; die alten Anfragen/Antworten bleiben in ihren Ursprungstabellen.

## Nach erfolgreicher Abnahme

```powershell
git add listings PHASE3_TAG21.md
git commit -m "Phase 3 Tag 21: Nachrichten- und Statusverlauf"
git push
```

**Tag 22:** Sicherheitsreview der gesamten Anfragekette (CSRF, Autorisierung, Eingabevalidierung, Tests gegen unerlaubte Statuswechsel und unerwünschte Informationsfreigabe).

</details>

<details>
<summary id="phase3-tag22-md"><strong>PHASE3_TAG22.md</strong></summary>

# Fundplatz – Phase 3, Tag 22: Sicherheitsreview

## Ziel

Django-Anfragen, Verkäuferbearbeitung, Freigaben und Käuferpostfach gegen unerlaubte Zugriffe und versehentliche Datenoffenlegung absichern. Alle Antwortentwürfe bleiben privat, bis ein Verkäufer den Text **freigibt und zusätzlich bereitstellt**.

## Sicherheitsverbesserungen

1. **Private Seiten werden nicht zwischengespeichert.** `@never_cache` gilt nun für Verkäuferpostfach, Verkäuferdetail, privaten Editor, Freigabeseite, Käuferpostfach und Käuferdetail. Erwarteter HTTP-Header: `Cache-Control: max-age=0, no-cache, no-store, must-revalidate, private` (Reihenfolge/Schreibweise kann variieren).
2. **Kritischer Status darf nicht durch einen Status-Klick versteckt werden.** Bei `needs_attention` antwortet `/anfragen/<id>/bearbeitung/` mit HTTP 409. Eine manuelle Bearbeitung bleibt möglich, aber die Warnstufe bleibt erhalten.
3. **Keine automatische Vorbelegung bei kritischem KI-Lauf.** Ein gefährdeter Entwurf wird nicht als fertig wirkender Text in den Editor übernommen. Bereits gespeicherte Verkäufertexte bleiben sichtbar.
4. **Cookie- und HTTP-Schutz.** Explizite HttpOnly- und SameSite=Lax-Cookies, `nosniff`, `Referrer-Policy: same-origin`, `X-Frame-Options: DENY`. Django-Middleware für CSRF, Security und Clickjacking bleibt aktiviert.
5. **50 neue Regressionstests.** Für Berechtigungen, CSRF, HTML-Escaping, Statusinvarianten, Overposting, Rate-Limit, Freigabe- und Bereitstellungstrennung sowie Browser-Cache.

## Installation in deinem VS-Code-Terminal

Die virtuelle Umgebung `(.venv)` ist bereits aktiv – nur `python` verwenden.

```powershell
cd C:\Kleinanzeigen
git status
Copy-Item .\db.sqlite3 .\db_backup_vor_tag22.sqlite3
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag22.zip" -DestinationPath "." -Force
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test listings.test_day22 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
```

**Keine Migration** an Tag 22: Nur Views, Template, Einstellungen und Tests ändern sich.

## Manuelle Sicherheitsprüfung

1. Als Käufer anmelden. Eigene Anfrage öffnen. Interne KI-Texte, Verkäufertext und Audit dürfen **nicht** auftauchen. Eine interne Freigabe allein erzeugt keine sichtbare Antwort.
2. Als anderer Käufer dieselbe Detail-URL aufrufen – `404`.
3. Als fremder Verkäufer eine private Verkäuferdetail-URL öffnen – `404`.
4. Als richtiger Verkäufer eine Anfrage mit Status `needs_attention` öffnen. Die Statuswarnung bleibt sichtbar. Der Button „Als In Bearbeitung markieren“ fehlt; der Editor bleibt verfügbar.
5. Im Browser-Entwicklertool im Tab Netzwerk private Seiten prüfen: Response Header `Cache-Control` enthält `no-store`.
6. Eine Antwort erst dann bereitstellen, wenn die Verkäuferfassung ausdrücklich freigegeben wurde. Käufer sieht nur den ausgelieferten Snapshot.

## Wichtige Grenzen

- `DEBUG=True`, Entwicklungs-SECRET_KEY und lokales HTTP sind nur für `localhost` vertretbar, **nicht für öffentliches Hosting**. Für Deployment müssen HTTPS, sichere Secrets, Hosts, Rate-Limiting (auch für parallele Requests), Logging und Upload-Regeln gesondert gehärtet werden.
- Die bestehende Begrenzung von fünf Anfragen pro Käufer und Stunde verwendet SQLite-Zählung. Sie ist kein produktionsreifes, verteiltes oder konkurrenzsicheres Rate-Limit.
- `no-store` reduziert Browser-Caching, verhindert aber nicht Screenshots oder bewusstes Kopieren.
- `autoescape`, CSRF und Zugriffskontrolle ersetzen kein vollständiges Penetration Testing.
- Tests müssen auf deinem Rechner mit Django 5.2 in der aktiven `.venv` ausgeführt werden. Der Archiv-Build kann hier mangels Django-Paket nur statisch geprüft werden.

## Git

Nach erfolgreichen Tests:

```powershell
git add config/settings.py listings/views.py listings/templates/listings/seller_inquiry_detail.html listings/test_day22.py PHASE3_TAG22.md
git commit -m "Phase 3 Tag 22: Security hardening und Tests"
git push
```

## Nächster Schritt – Tag 23

Leistungsfähigkeit und Ausfallverhalten von Ollama bei Webanfragen verbessern: Timeout-Grenzen, Queue/Background-Jobs und Status bei längeren Generierungen. Vorher keine Hintergrundverarbeitung behaupten – Tag 22 ist noch synchron.

</details>

<details>
<summary id="phase3-tag23-md"><strong>PHASE3_TAG23.md</strong></summary>

# Fundplatz – Phase 3, Tag 23: asynchrone KI-Entwürfe und Ausfälle

## Ziel

Der Käufer soll beim Senden einer Frage nicht 5–30 Sekunden auf Ollama warten. Deshalb kann die Website eine Kundenanfrage **nur speichern**. Ein **separater Django-Worker** erstellt den privaten Entwurf. Er veröffentlicht niemals etwas an den Käufer und ändert weder die interne Freigabe noch bereitgestellte Antworten.

### Technischer Ablauf

1. HTTP-POST: Login, Formularvalidierung, 5-Anfragen-pro-Stunde-Limit, `CustomerInquiry` + `received`-Ereignis speichern.
2. Bei `FUNDPLATZ_AGENT_ASYNC=1`: `draft_processing='queued'`; sofortiges Redirect. **Kein Ollama-Aufruf** aus der HTTP-View.
3. `python manage.py process_inquiries --loop` läuft in einem **zweiten Terminal**, übernimmt wartende Einträge atomar und setzt `draft_processing='running'`.
4. Der Worker führt `generate_private_draft()` aus. Bei Erfolg: `draft_processing='ready'` und je nach Prüfresultat Verkäuferstatus `review_required`/`needs_attention`; bei Fehler: `draft_processing='failed'` und `needs_attention`. Jeweils ein internes Verlaufsereignis.
5. Verkäufer prüft und bearbeitet die Antwort wie bisher. Nur nach expliziter Freigabe und Bereitstellung wird ein Text für den Käufer sichtbar.

**Wichtig:** Ohne gestarteten Worker bleiben Jobs dauerhaft auf `queued`. Die Queue läuft nicht automatisch im Hintergrund. Das ist ein lokaler Prototyp mit SQLite, keine Produktions-Jobplattform.

## Installation (VS Code / Windows, `.venv` bereits aktiv)

Vor jeder neuen Migration optional eine lokale Sicherung erstellen:

```powershell
cd C:\Kleinanzeigen
Copy-Item .\db.sqlite3 .\db_backup_vor_tag23.sqlite3
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag23.zip" -DestinationPath "." -Force
python manage.py migrate
python manage.py makemigrations --check --dry-run
```

Die Migration `0008_inquiry_draft_queue.py` ergänzt nur Verwaltungsfelder; ältere Anfragen haben als Default `ready`.

## Tests zunächst im bisherigen Modus

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="0"
$env:FUNDPLATZ_AGENT_USE_LLM="0"
python manage.py test listings.test_day23 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
```

Erwartet: 31 neue Django-Tests und 269 Agententests. Hier wurde der Python-Agententeil ausgeführt; **Django-Tests müssen auf deinem PC ausgeführt werden**.

## Asynchronen Modus praktisch starten

**Terminal A: Webserver**

```powershell
cd C:\Kleinanzeigen
$env:FUNDPLATZ_AGENT_ASYNC="1"
python manage.py runserver
```

**Terminal B: Worker (eigene VS-Code-Terminalregisterkarte, `.venv` aktiv)**

```powershell
cd C:\Kleinanzeigen
$env:FUNDPLATZ_AGENT_USE_LLM="1"
$env:OLLAMA_TIMEOUT_SECONDS="45"
python manage.py process_inquiries --loop
```

- Stelle als Käufer eine Frage bei einer fremden aktiven Anzeige. Die Website gibt **sofort** eine Eingangsbestätigung zurück. Sie wartet nicht auf den Worker.
- Im Verkäuferpostfach `/anfragen/` erscheint zuerst `KI wartet auf Worker`, danach `KI verarbeitet` und schließlich der private Entwurf bzw. ein manueller Bearbeitungshinweis.
- Der Käufer sieht in `/meine-anfragen/` **nie** die internen KI-Texte.
- Mit `Strg+C` beendest du Webserver bzw. Worker.

Einmalig oder testweise nur eine Anfrage bearbeiten:

```powershell
python manage.py process_inquiries --once
```

Alle derzeit wartenden Anfragen (maximal 20) bearbeiten und beenden:

```powershell
python manage.py process_inquiries
```

### Fehlerbehandlung und Wiederherstellung

- Ist Ollama nicht erreichbar, kann der Router auf `fallback` (= Regeln) wechseln. In der Verkäuferansicht wird die Quelle nicht als `llm` ausgegeben.
- Schlägt die Pipeline vollständig fehl, erhält nur der Verkäufer den Hinweis `Kein automatischer Entwurf verfügbar. Bitte manuell antworten.`; die Käuferfrage bleibt gespeichert.
- `OLLAMA_TIMEOUT_SECONDS` begrenzt **jeden einzelnen HTTP-Aufruf an Ollama** auf 5–300 Sekunden, nicht die komplette mehrstufige Pipeline. Kürzere Werte können mehr Fallbacks auslösen.
- Nach einem **abgebrochenen Worker-Prozess** können Einträge in `running` bleiben. Bei ausreichend alten Einträgen (mindestens 30 Minuten empfohlen) darfst du ausdrücklich wiederherstellen:

```powershell
python manage.py process_inquiries --recover-stale --stale-minutes 30 --once
```

Die atomare Beanspruchung und ein **Versuchsticket** verhindern das Überschreiben durch einen verspäteten älteren Worker nach dem Wiederanlaufen. Ein manueller Recovery-Befehl kann trotzdem doppelte *LLM-Rechenarbeit* auslösen, wenn der alte Prozess noch lebt; daher nur nach Prüfung benutzen. Fehlgeschlagene Aufträge (`failed`) werden nicht automatisch wiederholt, damit kein Endloslauf entsteht.

### Technische Grenzen

- SQLite reicht für lokale Entwicklung; für parallele Produktionsarbeiter werden PostgreSQL und eine echte Job-Queue (z. B. Celery oder RQ), Monitoring, Backoff und Dead-Letter-Behandlung empfohlen.
- Keine automatische Antwortfreigabe, kein E-Mail-Versand, kein autonomes Preisangebot.
- Die KI erhält die **aktuellen** Angebotsdaten zur Verarbeitungszeit; ein Snapshot der ursprünglichen Anzeige wird an Tag 23 noch nicht eingeführt.
- Beim Testen die asynchrone Umgebungsvariable wieder auf `0` stellen, weil ältere Tests den synchronen Standardmodus erwarten.

## Geänderte Projektdateien

- `config/settings.py`: Feature-Flag `FUNDPLATZ_AGENT_ASYNC` (standardmäßig aus)
- `listings/models.py` und `listings/migrations/0008_inquiry_draft_queue.py`: Queue-Zustand, Start/Ende, Versuchszähler
- `listings/views.py`: schneller HTTP-POST im asynchronen Modus; Sperren gegen Bearbeitung/Freigabe während `queued/running`
- `listings/draft_queue.py`: atomare Worker-Bearbeitung, Fehlermodus, Recovery
- `listings/management/commands/process_inquiries.py`: Worker-CLI
- `listings/templates/listings/seller_inquiries.html`, `seller_inquiry_detail.html`: Fortschritt
- `listings/test_day23.py`: 31 Django-Regressionstests
- `agent_system/ollama_client.py`: konfigurierbares einzelnes HTTP-Timeout
- `agent_system/tests/test_ollama_client.py`: drei neue Timeout-Tests

## GitHub

Nach den bestandenen Tests:

```powershell
git add agent_system/ollama_client.py agent_system/tests/test_ollama_client.py config/settings.py listings PHASE3_TAG23.md
git commit -m "Phase 3 Tag 23: asynchrone KI-Verarbeitung und Worker"
git push
```

</details>

<details>
<summary id="phase3-tag24-md"><strong>PHASE3_TAG24.md</strong></summary>

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

</details>

<details>
<summary id="phase3-tag25-md"><strong>PHASE3_TAG25.md</strong></summary>

# Fundplatz – Phase 3, Tag 25: Abschlussprüfung des lokalen MVP

**Stand:** 24. Oktober 2026 · **Etappe:** Tag 25/25.

## Ziel und tatsächlicher Umfang

Das Update macht **keine neue Datenbankmigration** und verändert **keine bereits gespeicherten Kundenantworten**. Es ergänzt:

1. `listings/views.py` – ein gezielter Bugfix im synchronen Anfragepfad: Nach einer erfolgreich abgeschlossenen KI-Verarbeitung bleibt der Verarbeitungsstatus `ready`; ein unerwarteter Fehler bekommt nun **`failed` statt fälschlich `ready`**. `draft_finished_at` und das Verlaufsereignis erhalten einen Abschlusszeitpunkt. Der asynchrone Worker bleibt unverändert.
2. `listings/management/commands/fundplatz_audit.py` – **lesende** Prüfung der Freigaben, veröffentlichten Snapshots, Käufer-/Verkäuferrechte bei Freigebern und öffentlicher Verlaufsmarkierungen. Der Bericht enthält **nur Zähler**, keine Käufertexte oder privaten KI-Daten.
3. `listings/test_day25.py` – **30 neue Django-Tests** für den Audit-Befehl, private Daten, Produkttrennung und die synchrone Fehlerbehandlung.
4. `scripts/tag25_abnahme.ps1` – lokale Gesamtabnahme in VS Code/PowerShell, erstellt Protokolle.
5. `FUNDPLATZ_ABNAHME.md` – überprüfbare Checkliste und bekannte Grenzen.

### Vollständiger Projektaufbau

- **Phase 1, Tag 1–5:** Django Marketplace: Benutzerkonten, Anzeigen, Eigentümerrechte, Katalog.
- **Phase 2, Tag 6–15:** Orchestrator, Information/Negotiation/Logistics Agents, Offline-Regeln, Ollama-Einbindung, Sicherheitsvalidierung und Evaluation.
- **Phase 3, Tag 16–25:** Anfrageformular, privates Verkäuferpostfach, editierbarer Entwurf, ausdrückliche Freigabe, zusätzliche Bereitstellung ins Käuferpostfach, Ereignishistorie, Datenschutztests, optionale SQLite-Queue mit Worker, KI-Statusanzeige, käuferfreundliche Formulierungen, Ende-zu-Ende-Tests und Abschlussprüfung.

## Installation unter Windows

Voraussetzung: Tag 24 und die vorangegangenen Korrekturen sind bereits installiert; VS Code öffnet `C:\Kleinanzeigen`, und `(.venv)` ist im PowerShell-Terminal sichtbar.

```powershell
cd C:\Kleinanzeigen
git status
Copy-Item .\db.sqlite3 .\db_backup_vor_tag25.sqlite3
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_phase3_tag25.zip" -DestinationPath "." -Force
python manage.py check
python manage.py makemigrations --check --dry-run
```

Es gibt keine neue `0009`-Migration. `python manage.py migrate` ist nur erforderlich, falls du eine frühere Migration noch nicht installiert hast; dein Tag-23/24-Stand sollte bis **`0008_inquiry_draft_queue.py`** migriert sein.

### Testlauf – einzeln nachvollziehen

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="0"
$env:FUNDPLATZ_AGENT_USE_LLM="0"
python manage.py test listings.test_day25 -v 2
python manage.py test listings
python -m unittest discover -s agent_system/tests -v
python manage.py fundplatz_audit --strict
```

Wenn dein letzter Teststand tatsächlich bei **400 Django-Tests** liegt (340 vor Tag 24 und 60 neu), wären mit Tag 25 **430 Django-Tests** zu erwarten. Die Zahl ist **eine Prognose**, kein nachgewiesenes Ergebnis. Die 30 neuen Django-Tests wurden hier nicht ausgeführt, weil in der Erstellungsumgebung Django nicht installiert ist. Bitte das Windows-Ergebnis prüfen.

### Abnahme mit einem PowerShell-Skript

```powershell
.\scripts\tag25_abnahme.ps1
```

Das Skript schaltet für Tests Ollama und die Async-Queue vorübergehend aus, **stellt danach die vorherigen Umgebungsvariablen wieder her**, startet sechs Prüfungen und sammelt getrennte Logs unter `tag25_reports\<Zeitstempel>` und beendet sich mit Exitcode 0 nur, wenn alle sechs erfolgreich waren. **Achtung:** Die Logs können trotz datensparsamem Audit Testfehlerausgaben enthalten und gehören nicht in ein öffentliches GitHub-Repository.

### Audit getrennt nutzen

```powershell
python manage.py fundplatz_audit
python manage.py fundplatz_audit --json
python manage.py fundplatz_audit --strict
python manage.py fundplatz_audit --stale-minutes 45
```

`--strict` meldet einen Fehler bei echten Dateninkonsistenzen (nicht bei bloßen Warnungen). Beispiele für harte Fehler:

- Intern freigegeben, aber Freigabetext, Zeitpunkt oder Freigeber fehlen.
- Anderer Benutzer als der zuständige Anzeigenverkäufer hat freigegeben oder eine Antwort bereitgestellt.
- Käuferantwort weicht vom freigegebenen Snapshot ab.
- Bereitstellung liegt zeitlich **vor** der Freigabe.
- Internes Timeline-Ereignis ist als käufersichtbar markiert.
- Anfrage ist freigegeben, während ihr KI-Job noch `queued` oder `running` ist.

Warnungen betreffen etwa >30 Minuten alte `running`-Jobs und fehlende historische Timeline-Einträge (auch direkt per ORM angelegte Datensätze aus älteren Versionen). Solche Warnungen sind **nicht automatisch ein Fehler**; sie müssen im Kontext bewertet werden. `fundplatz_audit` behebt nichts automatisch.

## Echte Ollama-Prüfung als separater manueller Test

**Terminal A (Webserver):**

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="1"
python manage.py runserver
```

**Terminal B (Worker):**

```powershell
$env:FUNDPLATZ_AGENT_USE_LLM="1"
$env:OLLAMA_TIMEOUT_SECONDS="45"
python manage.py process_inquiries --loop
```

Stelle als Käufer eine Frage zu **Anzeige A (5 €)** und eine zu **Anzeige B (180 €)**, die zwei unterschiedlichen Verkäuferkonten gehören. Prüfe getrennt:

1. Jede Anfrage erscheint nur beim zuständigen Verkäufer.
2. Vor dem Worker-Lauf ist der Status `queued`, danach `ready` oder `failed`.
3. Der KI-Vorschlag enthält ausschließlich die Produktdaten dieser Anzeige. `Router: llm` beweist nur LLM-Routing und nicht freie Käufertextgenerierung.
4. Nach manueller Bearbeitung und ausdrücklicher Freigabe ist noch **keine Käuferantwort veröffentlicht**.
5. Erst „Antwort an Käufer bereitstellen“ macht den exakten freigegebenen Snapshot für den richtigen Käufer sichtbar.
6. Ein fremder Verkäufer/Käufer kann die Anfrage nicht lesen oder verändern.

## Projektabschluss ≠ Produktionsfreigabe

Dieses Projekt ist ein **lokales Lern-MVP**, keine öffentlich gehärtete Handelsplattform. Vor einem Internet-Deployment fehlen insbesondere sichere Deployment-Settings (`DEBUG=False`, starker Secret-Key, HTTPS, sichere Cookies, `ALLOWED_HOSTS`), Hosting-, Backup-/Restore- und Monitoring-Prozesse, skalierbares Worker-/Queue-Management, Anti-Spam-/Missbrauchsschutz sowie eine Datenschutz- und Rechtsprüfung. Der Audit-Befehl attestiert **niemals** Produktionsbereitschaft.

## Git-Sicherung nach erfolgreichem Test

```powershell
git add listings/views.py listings/management/commands/fundplatz_audit.py listings/test_day25.py scripts/tag25_abnahme.ps1 PHASE3_TAG25.md FUNDPLATZ_ABNAHME.md
git commit -m "Phase 3 Tag 25: lokale MVP-Abnahme und Audit"
git push
```

**Nicht** `tag25_reports` oder die SQLite-Backup-Datei committen.

</details>

<details>
<summary id="fix-tag17-test-md"><strong>FIX_TAG17_TEST.md</strong></summary>

# Fundplatz – Testkorrektur für Tag 17

## Ursache

`listings.test_day16.DjangoAgentBridgeTests.test_anfrage_wird_gespeichert_und_draft_bleibt_privat` erwartet den Offline-Regelrouter (`rules`).
War in PowerShell zuvor `FUNDPLATZ_AGENT_USE_LLM=1` gesetzt, wurde stattdessen real Ollama angesprochen (`llm`).
Der Test durfte nicht von einer Umgebungsvariable abhängen.

## Änderung

In `listings/test_day16.py` bekommt die ganze Testklasse den Dekorator
`@override_settings(FUNDPLATZ_AGENT_USE_LLM=False)`.
Damit sind alle normalen Tests der Klasse deterministisch und verwenden keinen echten Ollama-Aufruf.
Der bewusst eingerichtete Test `test_llm_ist_opt_in` setzt die Einstellung innerhalb der Methode explizit wieder auf `True` und testet diesen Spezialfall mit einem Mock.
Die produktive Django-App, die Datenbank, das Modell und die Agenten ändern sich nicht.

## Installation (virtuelle Umgebung bereits aktiviert)

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag17_testfix.zip" -DestinationPath "." -Force
python manage.py test listings.test_day16 -v 2
python manage.py test listings
```

Danach optional den Tag-18-Stand installieren. Der Testfix ist auch mit Tag 18 kompatibel.
Die absichtlich simulierte Fehlermeldung `RuntimeError: LLM offline` im Testlog
ist kein Testfehlschlag, solange am Ende `OK` steht.

</details>

<details>
<summary id="fix-tag22-test-md"><strong>FIX_TAG22_TEST.md</strong></summary>

# Fundplatz Tag 22 – Testfix für Rate-Limit-Test 35

**Ursache:** `setUpTestData()` legt für `self.stranger` bereits eine `CustomerInquiry` bei `self.other_listing` an. Test 35 legte zusätzlich fünf Anfragen an und erwartete danach fünf statt sechs. Die Implementierung zählt korrekt alle Anfragen desselben Käufers innerhalb einer Stunde, unabhängig von der Anzeige.

**Korrektur:** Test 35 erstellt einen separaten Käufer mit null bisherigen Anfragen, legt fünf an und prüft, dass die sechste abgewiesen und nicht gespeichert wird. Produktivcode und Rate-Limit bleiben unverändert.

## Installation bei bereits aktivierter `.venv`

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag22_testfix.zip" -DestinationPath "." -Force
python manage.py test listings.test_day22.Day22SecurityTests.test_35_inquiry_hourly_limit_rejects_sixth -v 2
python manage.py test listings.test_day22 -v 2
python manage.py test listings
```

Keine Migration. Der Patch ersetzt nur `listings/test_day22.py`.

</details>

<details>
<summary id="readme-async-testfix-md"><strong>README_ASYNC_TESTFIX.md</strong></summary>

# Fundplatz – Fix für 5 Testfehler nach Tag 24

## Ursache

Tag 24 aktiviert beim manuellen Testen `FUNDPLATZ_AGENT_ASYNC=1`. Die alten Django-Testklassen für Tag 16 und Tag 21 haben nur das LLM deaktiviert, aber nicht den asynchronen Modus. Deshalb laufen die Tests in einer noch aktiven PowerShell unerwartet im Queue-Modus. Der KI-Entwurf wird dann erst vom Worker erstellt und die Tests finden ihn nicht sofort.

## Änderung

In `listings/test_day16.py` und `listings/test_day21.py` wird jeweils der Klassendekorator erweitert auf:

```python
@override_settings(FUNDPLATZ_AGENT_USE_LLM=False, FUNDPLATZ_AGENT_ASYNC=False)
```

Das ändert ausschließlich die Testkonfiguration. Die Anwendung bleibt im gewählten Modus; der asynchrone Ablauf wird weiter in Tag 23 und Tag 24 getestet. Keine Migration erforderlich.

## Installation in PowerShell bei aktivierter .venv

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag24_async_testfix.zip" -DestinationPath "." -Force
python manage.py test listings.test_day16 listings.test_day21 -v 2
python manage.py test listings
```

Für einen sofortigen Test ohne ZIP genügt alternativ:

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="0"
$env:FUNDPLATZ_AGENT_USE_LLM="0"
python manage.py test listings
```

Das Tag-25-Skript `scripts/tag25_abnahme.ps1` setzt während der Abnahme beide Variablen selbst auf `0` und stellt sie anschließend wieder her.

## Prüfung

Python-Syntax und ZIP-Struktur geprüft. Kein Django-Paket in der Erstellungsumgebung; Testausführung in Windows erforderlich.

</details>

<details>
<summary id="readme-kaeuferfreundlich-md"><strong>README_KAEUFERFREUNDLICH.md</strong></summary>

# Käuferfreundliche Antwortentwürfe – Ergänzung nach Tag 23

## Warum?

`route_source='llm'` bedeutet nur, dass der Router Qwen benutzt hat. Die
sichtbaren Vorlagen kommen aus `agent_system/agents.py` und sind absichtlich
konservativ. Die neuen Formulierungen sind kurze, natürlich klingende **Entwürfe
für den Verkäufer**, keine freigegebenen, versendeten Kundennachrichten.

## Änderungen

- Neues Modul `agent_system/customer_tone.py`: datengebundene Formulierungen ohne weiteren Modellaufruf.
- Verkäuferdetail zeigt neben dem technischen KI-Text einen verständlicheren Vorschlag.
- Der Editor verwendet bei neuen, normalen Anfragen diese Formulierung als Ausgangstext.
- Original-KI-Text und die bisherigen Prüf- und Freigabeschritte bleiben unverändert.
- Keine automatischen Preissenkungen, Versandkostenzusagen oder Versendungen.
- Bei kritischem Status, KI-Fehler oder blockierten Antwortteilen: **kein automatischer Käufertext**.
- Bereits manuell gespeicherte Entwürfe behalten Vorrang und bleiben unverändert.

Der Tonfall-Generator ist regelbasiert und weder ein semantischer Validator noch
vollständige freie KI-Textgenerierung. Jede Antwort muss weiterhin vom Verkäufer
geprüft und ausdrücklich freigegeben und bereitgestellt werden.

## Installation (PowerShell, .venv bereits aktiv)

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_kaeuferfreundliche_antworten.zip" -DestinationPath "." -Force
python -m unittest discover -s agent_system/tests -v
python manage.py test listings.test_buyer_tone -v 2
python manage.py test listings
python manage.py runserver
```

Als Verkäufer `/anfragen/` öffnen und eine bereits verarbeitete, nicht
freigegebene Anfrage mit erkannten Agenten öffnen. Die neue Karte heißt
**Käuferfreundliche Formulierung (Vorschlag)**. Im Editor wird sie vorbefüllt.

**Keine Datenbankmigration nötig.** Änderungen bitte erst nach erfolgreichem
Django-Testlauf committen.

</details>

<details>
<summary id="readme-tag23-statusfix-md"><strong>README_TAG23_STATUSFIX.md</strong></summary>

# Fundplatz Tag 23 – KI-Status im Verkäuferpostfach sichtbar machen

Diese kleine Korrektur ersetzt nur zwei Templates. **Keine Migration, keine Änderung an Django-Views, Agenten oder Datenbank.**

- Zeigt KI-Verarbeitung getrennt vom Verkäufer-Prüfstatus: `queued`, `running`, `ready`, `failed`.
- `ready` wird dauerhaft als **Abgeschlossen** angezeigt. `Prüfung erforderlich` ist die weiterhin nötige menschliche Verkäuferprüfung.
- Während `queued`/`running` aktualisiert sich die private GET-Seite alle 5 Sekunden. Sobald sie fertig ist, stoppt die automatische Aktualisierung.
- Es wird weder eine Nachricht versendet noch ein KI-Entwurf freigegeben.

## Installation – `.venv` ist aktiviert

```powershell
cd C:\Kleinanzeigen
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag23_statusanzeige_fix.zip" -DestinationPath "." -Force
python manage.py check
python manage.py test listings
```

Danach Django neu laden und mit Strg+F5 die Browserseite öffnen.

## Echten Wartestatus zuverlässig sehen

1. Im Worker-Terminal `Strg+C` drücken, damit **kein Worker läuft**.
2. Django im Terminal A mit asynchroner Verarbeitung neu starten:

```powershell
$env:FUNDPLATZ_AGENT_ASYNC="1"
python manage.py runserver
```

3. Als Käufer **eine neue Frage** absenden, dann als Verkäufer `/anfragen/` öffnen: Die Anfrage sollte **Wartet auf Worker** zeigen. Beachte das Limit von maximal fünf Käuferfragen pro Stunde.
4. Im zweiten Terminal den Worker starten:

```powershell
$env:FUNDPLATZ_AGENT_USE_LLM="1"
python manage.py process_inquiries --loop
```

5. Die Seite aktualisiert sich während der Verarbeitung automatisch, zeigt (sofern schnell genug sichtbar) **Wird verarbeitet** und danach dauerhaft **Abgeschlossen**. Eine kurze `running`-Phase kann zwischen zwei Refreshs liegen, was normal ist.

**Wichtig:** `Router: llm` belegt nur LLM-Routing, nicht ob die Anfrage zuvor asynchron verarbeitet wurde. Ob die Webserver-Einstellung aktiv ist, prüft man in **dem Terminal, in dem `runserver` gestartet wurde**. Wenn das Webserver-Terminal noch `FUNDPLATZ_AGENT_ASYNC=0` hatte, wurden bisherige Anfragen synchron verarbeitet, ohne dass `queued/running` im Browser jemals sichtbar sein konnten.

```powershell
python manage.py shell -c "from listings.models import CustomerInquiry; print(list(CustomerInquiry.objects.order_by('-pk').values('pk','draft_processing','draft_started_at','draft_finished_at')[:6]))"
```

Eine abgeschlossene Worker-Anfrage hat im Normalfall `ready`, `draft_started_at` und `draft_finished_at`. Ältere oder synchrone Anfragen können ebenfalls `ready`, aber ohne diese Zeitstempel sein.

</details>

<details>
<summary id="readme-tag25-timeline-testfix-md"><strong>README_TAG25_TIMELINE_TESTFIX.md</strong></summary>

# Fundplatz – Tag-25-Abnahme: letzter Django-Testfehler

## Problem

Beim Abschlusslauf bestanden 30/30 Tag-25-Tests und 281/281 Agententests; der Audit berichtete `data_consistent: true` bei 0 Fehlern und 0 Warnungen. In der Django-Gesamtsuite (430 Tests) scheiterte nur:

`listings.test_day21.InquiryTimelineDay21Tests.test_39_legacy_backfill_keeps_real_timestamps`

Im ursprünglichen `setUpTestData` wird `seller_draft_updated_at=timezone.now()` bereits **vor** dem INSERT der Anfrage ausgewertet. Das Feld `created_at` wird jedoch per `auto_now_add` **erst während** des INSERT gesetzt. Dadurch liegt der künstliche Entwurfszeitpunkt gelegentlich einige Mikrosekunden vor dem künstlichen Eingangszeitpunkt. Die Ereignisse sind nach `occurred_at` sortiert; die Migration verhält sich daher korrekt, aber die Testdaten widersprechen der erwarteten Reihenfolge.

## Korrektur

Nur `listings/test_day21.py` wird ausgetauscht. Test 39 legt vier ausdrücklich chronologische Alt-Zeitstempel an (Eingang, Entwurf, Freigabe, Bereitstellung) und kontrolliert danach weiterhin, dass die Backfill-Migration alle **original gespeicherten** Zeitpunkte unverändert übernimmt.

- Kein Eingriff in `0007_inquiryevent.py`.
- Keine Migration erforderlich.
- Keine Veränderung an echten Kundenanfragen, Anzeigen, Konten oder KI-Entwürfen.
- Vorheriger Async-Testfix für Tag 16/21 bleibt erhalten.

## Installation (PowerShell, `.venv` aktiv)

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag25_timeline_testfix.zip" -DestinationPath "." -Force
python manage.py test listings.test_day21.InquiryTimelineDay21Tests.test_39_legacy_backfill_keeps_real_timestamps -v 2
python manage.py test listings
.\scripts\tag25_abnahme.ps1
```

Das Abnahmeskript schreibt den Diagnosebericht nach `tag25_reports`, siehe Tag-25-Anleitung. Diese Berichte bitte nicht in ein öffentliches GitHub-Repository hochladen.

## Verifikation

Python-Syntax, isolierter Test-Methodenunterschied und ZIP-Integrität wurden in der Erstellungsumgebung geprüft. Django ist dort nicht installiert, daher muss der wirkliche Django-Testlauf auf deinem Windows-PC erfolgen.

</details>

<details>
<summary id="readme-testfix-5-md"><strong>README_TESTFIX_5.md</strong></summary>

# Fundplatz – Testfix nach Tag 23 / käuferfreundliche Antworten

## Befund: 340 Django-Tests, 5 Fehler

1. Tag 17 `test_html_in_kundenfrage_und_draft_wird_escaped`: ein **legitimer Inline-Script-Block** am Ende der Verkäuferdetailseite löst `assertNotIn(b"<script>", ...)` aus. Die Kundeninhalte sind schon richtig escaped.
2. Tag 18 `test_html_wird_in_editor_und_detail_escaped`: gleicher Grund auf der Detailseite.
3. Tag 19 `test_html_in_antwort_wird_escaped`: gleicher Grund auf der Detailseite.
4. Tag 18 `test_ki_original_ist_erste_vorbelegung`: der neue käuferfreundliche Vorschlag wird jetzt absichtlich statt der technischen KI-Vorlage vorbefüllt. Der aktualisierte Test prüft den neuen Text und den unveränderten Originalentwurf. Die künstliche Testanzeige bietet explizit Versand an, damit Testdaten und KI-Ausgangstext nicht widersprechen.
5. Tag 23 `test_18_seller_kann_queue_status_sehen`: die Oberfläche heißt nun `Wartet auf Worker`, nicht `KI-Entwurf wartet auf Worker`.

### Korrektur

- `listings/templates/listings/seller_inquiry_detail.html`: Inline-JavaScript durch `defer`-geladenes **lokales** Skript ersetzen. Die Kundentexte bleiben Django-escaped; wir entfernen/entschärfen keine XSS-Tests.
- `static/js/inquiry_processing_refresh.js`: Reload nur bei `queued` oder `running` (über festes Datenattribut im DOM). Kein dynamischer JS-Code aus Anfragen.
- `listings/test_day18.py`: Regressionstest an neue Editor-Funktion anpassen und widersprüchliche Testdaten bereinigen.
- `listings/test_day23.py`: Statusanzeige auf den echten aktuellen Wortlaut und das Reload-Skript prüfen.

Keine Migration, keine Änderungen an Views, Business-Logik, Agenten oder echten Nutzerdaten.

### Installation (Windows / PowerShell, `.venv` aktiv)

```powershell
cd C:\Kleinanzeigen
git status
Expand-Archive -Path "$env:USERPROFILE\Downloads\fundplatz_tag23_5_django_tests_fix.zip" -DestinationPath "." -Force
python manage.py check
python manage.py test listings.test_day17 listings.test_day18 listings.test_day19 listings.test_day23 -v 2
python manage.py test listings
```

Erwartung: Die fünf vorherigen Testfehler sollten verschwinden. Ein tatsächlicher OK-Status ist erst nach deinem Django-Testlauf bestätigt.

Optionale Prüfung der JS-Datei: Starte `python manage.py runserver`, öffne als Verkäufer eine Anfrage und prüfe im Browser unter `/static/js/inquiry_processing_refresh.js`, ob das Script erreichbar ist. Bei wartender/laufender Verarbeitung wird die Detailseite alle fünf Sekunden aktualisiert.

Wenn alle Tests erfolgreich sind:

```powershell
git add listings/templates/listings/seller_inquiry_detail.html static/js/inquiry_processing_refresh.js listings/test_day18.py listings/test_day23.py
git commit -m "Fix: XSS-Testkollision und Tag23-UI-Regressionen"
git push
```

Die Logs `RuntimeError: LLM offline`, `Ollama nicht da`, `SECRET` kommen aus absichtlich simulierten Fehlerszenarien; allein die `FAIL:`-Einträge waren Testfehler. Logs mit geheimen Werten vor Veröffentlichung prüfen.

</details>

<details>
<summary id="fundplatz-abnahme-md"><strong>FUNDPLATZ_ABNAHME.md</strong></summary>

# Fundplatz – Abschluss- und Abnahmeprotokoll

**Projekt:** KI-Assistent für Marktplatz-Anfragen (Fundplatz)  
**Stand:** Tag 25/25, 24.10.2026  
**Abnahmestatus:** **NOCH OFFEN – Windows-Gesamttests und praktische Prüfung ausstehend.**

## Technischer Umfang

| Funktion | Implementiert | Nachweis/Prüfschritt |
| --- | --- | --- |
| Zwei unabhängige Benutzer/Verkäufer | Ja | Getrennte Logins und Testclients aus Tag 24 |
| Zwei Anzeigen mit getrennten Produktdaten (5 €/180 €) | Ja | `test_day24`, `test_day25` |
| Kundenfrage speichern | Ja | Django `inquiry_submit` |
| KI-Orchestrator und drei Agenten | Ja | 281 Python-Agententests waren bei Tag 24 erfolgreich |
| Optionale Worker-Queue | Ja | `process_inquiries --loop`, Test Tag 23 |
| Private und käuferfreundliche Entwurfsanzeige | Ja | Verkäuferdetail und Editor |
| Verkäufer bearbeitet selbst | Ja | `seller_inquiry_edit` |
| Freigabe und Bereitstellung getrennt | Ja | `seller_inquiry_approve` / `seller_inquiry_deliver` |
| Käufer sieht nur seinen bereitgestellten Text | Ja | Käuferdetail und Tag-20/24/25-Tests |
| Ereignis- und Statusverlauf | Ja | `InquiryEvent` und Tag-21-Tests |
| Abschluss-Datenkonsistenzprüfung | Neu an Tag 25 | `python manage.py fundplatz_audit --strict` |
| Vollständige Django-Tests auf Windows | **Offen** | `python manage.py test listings` |
| Echte Qwen-Integration im Browser | **Manuell zu prüfen** | Webserver + Worker in 2 Terminals |

## Formale Abnahmekriterien

- [ ] `python manage.py check` ohne Fehler.
- [ ] `python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
- [ ] `python manage.py test listings.test_day25 -v 2` besteht (30 Tests geplant).
- [ ] `python manage.py test listings` besteht (bei unverändertem Stand ca. 430 Tests).
- [ ] `python -m unittest discover -s agent_system/tests -v` besteht (zuletzt 281 erfolgreich an Tag 24).
- [ ] `python manage.py fundplatz_audit --strict` meldet keine Dateninkonsistenzen.
- [ ] Verkäufer A sieht weder Anfragen noch freigegebene Texte von Verkäufer B.
- [ ] Anzeige A zeigt 5 € und Anzeige B 180 €; der KI-Kontext vermischt diese Daten nicht.
- [ ] Ein noch nicht freigegebener Entwurf ist im Käuferpostfach unsichtbar.
- [ ] Nur der Anzeigenverkäufer kann bearbeiten, freigeben und bereitstellen.
- [ ] Nach Bereitstellung erscheint ausschließlich der korrekte Antwort-Snapshot beim richtigen Käufer.
- [ ] Ollama-Ausfall führt zur manuellen Prüfung, nicht zu automatischer Veröffentlichung.
- [ ] Lokale Datenbank ist gesichert; Wiederherstellung wurde geprüft.

## Nicht durch den Audit-Befehl geprüft

- Keine vollständige Sicherheitszertifizierung; insbesondere keine produktive Penetrationsprüfung.
- Kein Performance-Benchmark für gleichzeitige Nutzer oder hohe Last.
- Kein Garantiebeweis für die sachliche Richtigkeit von KI-Antworten.
- Keine Rechtsberatung oder abgeschlossene DSGVO-/Marktplatz-Compliance.
- Keine automatische Prüfung von HTTPS, Hosting, TLS, Backup-Wiederherstellung oder Überwachung.

## Testprotokoll – vom Benutzer ausfüllen

| Testlauf | Ergebnis | Datum | Anmerkung |
| --- | --- | --- | --- |
| Django Tag 25 | Offen | – | – |
| Vollständige Django-Suite | Offen | – | – |
| Python-Agententests | Tag-24-Stand: 281/281; erneute Prüfung offen | – | – |
| Datenbank-Audit (`--strict`) | Offen | – | – |
| Zwei-Browser-/Zwei-Verkäufer-Praxistest | Offen | – | – |
| Echte Qwen-Frage und Freigabe | Offen | – | – |

**Abnahmeentscheidung:** Erst nach vollständig erfolgreicher Testserie und manuellem Zwei-Verkäufer-Test „Lokales MVP abgenommen“ eintragen. Das ist ausdrücklich **keine Produktions- oder Internetfreigabe**.

</details>

