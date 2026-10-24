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
