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
