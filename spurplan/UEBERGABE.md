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

## 6. Fahrplan – was passiert, in welcher Reihenfolge
Dies ist die **einzige** gültige Reihenfolge (IDEEN_REVIEW.md und REGELN.md verweisen hierher). Je Schritt **ein neuer
Chat**, Einstieg = der Satz in Anführungszeichen. **Nacheinander, nie parallel** (alle Schritte ändern denselben Code).
Ein Schritt ist fertig, wenn sein «Fertig, wenn» erfüllt ist; dann trägt der Chat in «Nachträge» ein, was erledigt ist,
und hakt den Schritt in der Statusliste ab. Ist «Daniel danach» nicht leer, wartet der nächste Schritt auf Daniel.

**Gilt in jedem Schritt (feste Runde):** Hinweise holen → ändern → Workflows abwarten → `alle_plaene_pruefen.py` über alle
80 Pläne → jede Änderung erklärt (Regel nach E9 oder Fehler), Differenzbilder an Daniel → Seite veröffentlichen
(Live-Fassung vorher mit letztem Build vergleichen) → Hinweise beantworten → Nachtrag hier. Nie abnehmen, nie «erledigt».

### Statusliste
- [ ] A  Regression Olten und alle Pläne
- [ ] 0  Antworten 6.11. umsetzen
- [ ] 1  Blaupausen-Prüfstand aufbauen
- [ ] 2  Pfeile/Stummel bei schrägen Abgängen (h9o9 Sagliains)
- [ ] 3  Bahnhofsausfahrt als Ganzes (Selfranga/jxpf, Chamby)
- [ ] 4  Bündel als Einheit
- [ ] 5  Montbovon im Prüfstand, Prüflauf SBB-Bahnhöfe

### A – Regression Olten und alle Pläne
- Einstieg: «Weiter mit UEBERGABE.md – Schritt A: Regression Olten und alle Pläne»
- Warum zuerst: Topologie ist die oberste Regel, Olten ist kaputt, und ohne Prüfung aller Pläne sieht kein späterer
  Schritt, was er sonst noch verändert.
- Arbeiten, in dieser Reihenfolge:
  1. `alle_plaene_pruefen.py` in den Workflow `seite` einbauen (Tabelle + Differenzbilder nach `ergebnisse/seite/regression/`,
     Zusammenfassung im Kartenlabel). Basis = Abnahme-Export; ohne Abnahme die zuletzt veröffentlichte Fassung.
  2. Olten: Ursache bestätigen – Kette lokal mit Code 1fa061d/15afeb5 (gut) gegen 89c5d46 (schlecht), Werkstatt-Datei
     `werkstatt/olten/olten.json`, Option `--hauptgleise`; dann den schuldigen Commit eingrenzen und im Code beheben
     (kein Override). Olten muss topologisch wieder dem Stand 30.10. entsprechen.
  3. Kerzers: Gl. 2 und 5 im X – fehlen Gleise oder nur Nummern? Beheben.
  4. Zofingen, Aarburg-Oftringen, Konolfingen, Solothurn, Region Olten, Region NE: Differenzbilder ansehen, jede Stelle
     als gewollt (Regel) oder Fehler einordnen; Fehler beheben.
  5. Perrons: Differenzbilder der abgenommenen Bahnhöfe mit kürzeren/verschobenen Perrons (Thun, Murten, Schönenwerd,
     Dulliken, Aarburg-Oftringen, Zofingen …) als eine Übersicht an Daniel.
- Fertig, wenn: Olten topologisch wie 30.10.; Prüfung aller Pläne läuft in `seite`; jede geänderte Zeile der Tabelle ist
  erklärt; keine unerklärte Änderung an abgenommenen Plänen.
- Daniel danach: Perron-Übersicht beurteilen (so lassen oder zurück); Olten neu ansehen.

### 0 – Antworten 6.11. umsetzen
- Einstieg: «Weiter mit UEBERGABE.md – Schritt 0: Antworten 6.11. umsetzen»
- Arbeiten: (1) Caux: Stumpen aus Gl. 2 Richtung Rochers-de-Naye dünn (Nebengleis). (2) Pfeile an Meterspur braun – im
  Code, alle Regionen. (3) Perron beidseitig eines Gleises erlauben (Montreux: Gl. 4 zwischen offenem Mittelperron 3/5,
  Gl. 7 beidseitig; Zweisimmen; Zwillingsperrons Le Noirmont, Renens m1) – Regel im Code. (4) Danach MOB
  `gleisnummer_aus_ref` wieder an, Montreux Gl. 4 im Plan.
- Fertig, wenn: MOB mit `gleisnummer_aus_ref` an, P1 = 0, Unruhe nicht schlechter als 109; Caux und Pfeile korrekt;
  Prüfung aller Pläne ohne unerklärte Änderung.
- Daniel danach: Montreux ansehen.

### 1 – Blaupausen-Prüfstand aufbauen
- Einstieg: «Weiter mit UEBERGABE.md – Schritt 1: Blaupausen-Prüfstand aufbauen»
- Ziel: Grundsatz «parallel bleibt parallel im gleichen Querabstand, in jeder Drehung und jedem Abgangswinkel» prüfbar.
- Arbeiten: Reinformen und Zusätze aus `vorlage.py` (Blaupause 2) in Drehungen 0, ±30, ±60, 90° und mit Abgängen
  gerade/30°/60° erzeugen; automatische Prüfung (Querabstand gleich, parallel bleibt parallel, Pfeile eines Bündels im
  Gleisabstand, Weichen gerundet, nichts unter 90°); zwei gedrehte Blaupausen-Bahnhöfe verbinden (Verbindung gerade).
  Der Sagliains-Fall (zwei Nebengleise unter 60°) als Baustein. Perron 80 px als Standard aufnehmen. Prüfstand als
  eigener Plan «Prüfstand» auf der Seite. Nur messen, noch nichts korrigieren.
- Fertig, wenn: Prüfstand läuft im Workflow, Befundliste vorhanden (welche Bausteine verletzen den Grundsatz).
- Daniel danach: Prüfstand ansehen und Bausteine beurteilen.

### 2 – Pfeile/Stummel bei schrägen Abgängen (h9o9)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt 2: Pfeile/Stummel bei schrägen Abgängen (h9o9 Sagliains)»
- Ursache h9o9: im Plan Sagliains · Autoverlad stehen zwei 60°-Abgänge senkrecht übereinander (13,2 px) → quer zur
  Schräge 6,6 px, im Regionalplan 2,7 px statt 10 px; der connector gleicht je Gleis einzeln aus → ein Gleis schräg.
- Arbeiten: Pfeile/Stummel bei schrägen Abgängen im Gleisabstand quer zur Schräge setzen (Code); alle Befunde des
  Prüfstands zu diesem Baustein beheben.
- Fertig, wenn: Prüfstand für Abgänge ohne Befund; Sagliains beide Nebengleise parallel; h9o9 «behoben».

### 3 – Bahnhofsausfahrt als Ganzes
- Einstieg: «Weiter mit UEBERGABE.md – Schritt 3: Bahnhofsausfahrt als Ganzes (Selfranga/jxpf, Chamby)»
- Arbeiten: Ausfahrt gleichmässig auffächern, Gleisreihenfolge bleibt (IDEEN_REVIEW Zeichenlogik 1). Testfälle
  Selfranga / jxpf S-Kurve Klosters – Selfranga, Sagliains Abgang Scuol, Chamby Knick.
- Fertig, wenn: Testfälle ohne Treppe/S-Kurve, Prüfstand ohne Befund, jxpf «behoben».

### 4 – Bündel als Einheit
- Einstieg: «Weiter mit UEBERGABE.md – Schritt 4: Bündel als Einheit»
- Arbeiten: parallele Pfeilpaare zwischen zwei Plänen als Bündel verbinden; ein nötiger Versatz gilt für das ganze Bündel
  (Schutz, wenn die Enden aus OSM-Gründen nicht passen). Treppen-Zahl (T7) in MOB/Vereina darf nicht steigen.
- Fertig, wenn: keine Einzelgleis-Schrägen in Bündeln, Unruhe MOB/Vereina nicht schlechter.

### 5 – Montbovon und Prüflauf SBB-Bahnhöfe
- Einstieg: «Weiter mit UEBERGABE.md – Schritt 5: Montbovon im Prüfstand, Prüflauf SBB-Bahnhöfe»
- Arbeiten: Montbovon +60° (scharfe Bögen) im Prüfstand nachstellen und im Code beheben statt von Hand; danach alle neuen
  Regionsregeln über die abgenommenen SBB-Bahnhöfe laufen lassen (vorher/nachher, E9: nur bei gleicher Topologie).
- Fertig, wenn: Montbovon ohne scharfe Bögen; Prüflauf-Tabelle mit Erklärung je Änderung an Daniel.
- Daniel danach: Prüflauf beurteilen.

### Offen bei Daniel (kein eigener Chat, Antwort auf der Feedbackseite oder nebenbei)
- Details zu Kreuzungen ohne Verbindung (bis dahin: Lücke nur bei Brücke/Über-/Unterführung/Tunnel, Gleisdurchschneidung
  wie Kerzers durchgezogen) – wird nach seiner Antwort ein eigener Schritt nach 5.

## Nachträge
