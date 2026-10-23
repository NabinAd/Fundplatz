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
