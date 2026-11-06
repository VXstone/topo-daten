# Übergabe Spurpläne – neu geschrieben 6.11.2026

Kurz und aktuell. Der ganze Verlauf bis 6.11. steht in `UEBERGABE_ARCHIV_bis_2026-11-06.md` (nur gezielt mit grep lesen,
z. B. Override-Schlüssel und ihr Anlass). Nachträge hier unten anhängen (`cat >>`), Abschnitt 6 bei jedem Chat nachführen.

## 1. Quellen
- Regeln: Doc «Regelwerk Spurpläne» (Grundsätze in Rangfolge, B/N, E1–E12, R1–R14, Entscheide 6.11.) und `spurplan/REGELN.md`.
- Arbeitsliste und Plan: `spurplan/IDEEN_REVIEW.md` (Standards / Blaupausen-Prüfstand, Zeichenlogik).
- Hinweise und Abnahmen: Feedback-Seite, Datenbank-Sammlungen `feedback` und `abnahme`. Nur Daniel nimmt ab und setzt «erledigt».

## 2. Woher jeder Plan kommt (80 Pläne auf der Seite)
| Quelle | Pläne | Workflow | Daten | Eigene Regression bisher |
|---|---|---|---|---|
| Region Olten (Werkstatt) | Regionalplan + 12 Bahnhöfe (Olten, Aarburg-Oftringen, Rothrist, Zofingen, Safenwil, Wangen, Dulliken, Däniken, Schönenwerd, Tecknau, Läufelfingen, Olten Hammer) | `seite` via `region_olten_lauf.py` | Werkstatt-Ausschnitte; 10 Bahnhöfe aus dem Release (`osm_bbox`), **Olten selbst aus der Werkstatt (23.10.)** | **keine** |
| Region Neuchâtel (Werkstatt) | Regionalplan + 55 Bahnhöfe NE 1–8 | `seite` via `region_olten_lauf.py --konfig werkstatt/ne/region_ne.json` | Werkstatt | **keine** |
| Referenzen | Thun, Ins, Murten, Kerzers | `seite` (Werkstatt `reg/`) | Werkstatt | **keine** |
| Repo-Bahnhöfe | Neuchâtel, Konolfingen, Neuchâtel Vauseyon, Solothurn | `plaene` | Release | Differenzbild je Bahnhof |
| Linien-Regionen | MOB, Vereina | `regionen` | Release | Basis + Unruhe-Wert |
| Fest | Blaupause, Blaupause 2, Basel, Bern (Entwurf 2) | – | – | unverändert seit 23.10. |

**Daraus folgt:** Aussagen wie «Olten/NE/SBB byte-gleich» in früheren Übergaben galten nur für `plaene` und die beiden Regionen.
Ab jetzt prüft **jede Runde alle 80 Pläne** mit `spurplan/code/alle_plaene_pruefen.py <abnahme-export> <ordner>`
(Abnahmen vorher mit ArtifactData `list` Sammlung `abnahme`, `out_dir`). Jede geänderte Zeile muss erklärt sein (gewollte
Regel nach E9 oder Fehler); unerklärte Änderungen gehen an Daniel, bevor die Runde als fertig gilt.

## 3. Befund 6.11.2026: Regressionen, die keiner Prüfung aufgefallen sind
Prüflauf 6.11. abends (alle 80 Pläne, Basis = Fassung zur Abnahme bzw. Archivbeginn 23.10.): **22 geändert, 58 gleich**
(alle NE-Bahnhöfe ausser Neuchâtel unverändert).
- **Olten – Fehler, Topologie (oberste Regel).** Bis Build 30.10. 19:38 (1fa061d) in Ordnung; ab Seitenaufbau 3.11. 05:43
  (8465a2c, Code-Stand 89c5d46) unterbrochene Gleise (Gl. 3, Gl. 7, Streckengleis Richtung Basel oben), loses Gleisstück
  Richtung Aarau, Gleisnummern 9–12 verschoben. Daten scheiden aus (Olten nutzt die Werkstatt-Datei vom 23.10.). Verdacht:
  Code-Änderung 89c5d46 (Strangprüfer, +24 Zeilen spurplan_schema.py) oder ein Commit 30.10.–3.11.; nicht bestätigt.
  Olten war nie abgenommen; Daniel hat Olten am 6.11. zurückgezogen.
- **Kerzers (Referenz, abgenommen 14.10.)** seit 27.10. als X neu gelegt (gewollt, Hinweis eojeak, Status «kontrolle»).
  Zu prüfen: im X stehen nur noch die Nummern 1, 3, 4, 6 – fehlen Gl. 2 und 5 oder nur ihre Nummern?
- **Perrons überall kürzer/verschoben** (Thun Gl. 1, Murten, Schönenwerd, Dulliken, Aarburg-Oftringen, Zofingen …) seit
  26.10. (B13 Perrons aus SBB Open Data, B14 Perron 110 px + Nummer, Perron-Multipolygone). Regelgewollt, aber Daniel nie
  gezeigt – Differenzbilder vorlegen.
- **Zofingen (28 Stellen), Aarburg-Oftringen (16), Konolfingen (20), Solothurn (10), Region Olten (24)**: noch nicht
  einzeln angesehen.
- Ursache der Lücke: Regression nur in `plaene`/`regionen`; die Werkstatt-Pläne werden in `seite` jedes Mal neu
  gerechnet, ohne Vergleich. Abgenommene Pläne ändern sich so unbemerkt (E9 erlaubt das nur mit Differenzbild).

## 4. Stand je Bereich
- Vereina: Unruhe 59, Topologie/Verkettung 0. Portal mit Nebengleisen und Susch behoben (Seite v132).
- MOB: Unruhe 109, Topologie/Verkettung 0. `gleisnummer_aus_ref: false` bis Montreux Gl. 4 umgesetzt ist.
- Region Olten: siehe Befund. Region Neuchâtel: Bahnhöfe unverändert seit 23.10., Regionalplan 9 Stellen (prüfen).
- Feedback-Seite: Version 132 (6.11. 00:21). Lokal rechnen ohne Release: `region_lauf.py <r> --daten <roh.json.gz aus
  ergebnisse/region_<r>/>`; Olten: Kette `spurplan_schema --nowarp`, `spurplan_warp`, 2× wiederholen, mit `--hauptgleise`.
- Vor dem Veröffentlichen: Live-Fassung mit dem letzten Build vergleichen; `merge_live.py` nur bei echten fremden
  Änderungen (es übernimmt sonst alte Regionalpläne).

## 5. Entscheide Daniel 6.11. (Details REGELN.md «Antworten D. Eckenstein 6.11.2026»)
Parallel bleibt parallel (Querabstand, jede Drehung) · Caux stimmt, Stumpen Gl. 2 dünn · Montreux Gl. 4 rein, Perrons
beidseitig (Mittelperron 3/5 offen, Gl. 7; Zweisimmen; Zwillingsperrons Le Noirmont, Renens m1) · Perron 80 px ok ·
Nebengleise bleiben, Meterspur-Pfeile braun · Kreuzung: Lücke nur bei Niveautrennung, Gleisdurchschneidung (Kerzers)
durchgezogen – Details folgen.

## 6. Nächste Chats (je einer, nacheinander, nicht parallel)
| # | Einstieg | Inhalt |
|---|---|---|
| A | «Weiter mit UEBERGABE.md – Schritt A: Regression Olten und alle Pläne» | Ursache Olten bestätigen (Code 1fa061d vs 8465a2c lokal, dann Commits dazwischen) und beheben; Kerzers Gl. 2/5; Zofingen, Aarburg, Konolfingen, Solothurn, Region Olten/NE ansehen; Perron-Differenzbilder für Daniel; `alle_plaene_pruefen.py` in den Workflow `seite` einbauen (Bericht auf der Seite) |
| 0 | «… Schritt 0: Antworten 6.11. umsetzen» | Caux Stumpen dünn, Meterspur-Pfeile braun, Montreux Gl. 4 + Perrons beidseitig, dann MOB `gleisnummer_aus_ref` an (P1 = 0) |
| 1 | «… Schritt 1: Blaupausen-Prüfstand aufbauen» | IDEEN_REVIEW «Standards» |
| 2 | «… Schritt 2: Pfeile/Stummel bei schrägen Abgängen (h9o9 Sagliains)» | |
| 3 | «… Schritt 3: Bahnhofsausfahrt als Ganzes (Selfranga/jxpf, Chamby)» | |
| 4 | «… Schritt 4: Bündel als Einheit» | |
| 5 | «… Schritt 5: Montbovon im Prüfstand, Prüflauf SBB-Bahnhöfe» | |
Offen bei Daniel: Details Kreuzungen; Urteil Perron-Differenzbilder (nach Schritt A).

## Nachträge
