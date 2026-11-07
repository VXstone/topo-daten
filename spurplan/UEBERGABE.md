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
- [x] A  Regression Olten und alle Pläne (6.11. abends, Seite v133)
- [ ] 0  Antworten 6.11. umsetzen
- [ ] P  Verbundene Perrons / Spezialperrons (Thun 16/18, Montreux, Zweisimmen, Bern 49/50, Basel 3 und 35)
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
- Daniel danach: Montreux ansehen. **Ausserdem nochmals vorlegen (Wunsch 6.11. abends):** (1) Perrons kürzer in abgenommenen
  Plänen – so lassen oder zurück; (4) Olten, Zofingen, Aarburg-Oftringen ansehen (Topologie wieder wie Abnahme/30.10.).
  Übersicht: Artifact «Regression Spurpläne 6.11.».

### P – Verbundene Perrons / Spezialperrons (neu 6.11. abends)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt P: Verbundene Perrons»
- Anlass: ein Perron bedient mehrere Gleise über Eck oder hängt an einem anderen Perron. Fälle: Thun Gl. 16/18 an Perron 1,
  Montreux (verbundene Perrons), Zweisimmen, Bern Gl. 49/50, Basel um Gl. 3 und um Gl. 35. Baut auf Schritt 0 (3) auf
  (Perron beidseitig eines Gleises).
- Arbeiten: Perronflächen aus SBB Open Data/OSM als zusammenhängende Fläche erkennen, die mehrere Gleise bedient; Darstellung
  im Code (eine Regel, kein Override je Bahnhof), Prüfung «kein Perron fällt weg» (P1) über alle Pläne.
- Fertig, wenn: die fünf Fälle im Plan richtig, Prüfung aller Pläne ohne unerklärte Änderung.
- Daniel danach: die fünf Fälle und die Perronfrage aus Schritt A abschliessend beurteilen.

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

### 6.11.2026 abends – Schritt A erledigt (Seite v133)
- **Prüfung aller Pläne im Workflow `seite`**: `alle_plaene_pruefen.py ... --neu /tmp/seite/plaene --seite index.html`, Ergebnis
  `ergebnisse/seite/regression/` (tabelle.md/json, `<key>_diff.png`, `<key>_alt/neu.svg`). Basis: `spurplan/abnahmen.json`
  (Export der Sammlung `abnahme`, jede Runde neu exportieren und committen) bzw. `spurplan/veroeffentlicht.json` (Commit auf
  `ergebnisse` der veröffentlichten Seite – **beim Veröffentlichen nachführen**). Einordnung je Plan nach Rangfolge (Wunsch
  Daniel: «vorschlagen, wo ein Plan verändert, aber vielleicht verbessert wurde»): Regelprüfung G5–G8 = Topologie zuerst, dann
  G1–G4 + Ruhe T7 → «Fehler? Topologie» / «schlechter?» / «gleichwertig» / «vermutlich besser»; steht im Kartenlabel und im
  Untertitel der Seite. Achtung: eine **neu erfundene Weiche** erkennt die Zählung nicht (Zofingen, Aarburg) – «gleichwertig»
  heisst nur «Zahlen gleich», Differenzbild trotzdem ansehen.
- **Olten**: Ursache R33b (89c5d46). Fix: R33b nicht im parallelen Bündel (Nachbar < 8 m schräg, oder Nachbarn beidseitig).
  Olten byte-gleich wie 30.10.; Klosters Platz/Selfranga (Anlässe R33b) unverändert. 4 Olten-Hinweise vom 6.11. «behoben».
- **Zofingen und Aarburg-Oftringen** (abgenommen): R27b (8e58a0b, 29.10.) erfand Weichen – Zofingen Gl. 40 (Linie 504) an
  Gl. 1, Aarburg Abstellgleis an die Aarebrücke. Fix: R27b nie bei Gleis mit `railway:track_ref`, nie auf Gleis anderer
  Ebene/Brücke/Tunnel. Eine Bedingung «nicht bei service=*» wäre zu breit (änderte Sagliains, Chamby, Rossinière, Saanen) – verworfen.
- Vereina (Unruhe 59) und MOB (109) lokal und im Workflow byte-gleich, Verkettung 0.
- **Kerzers**: im X alle 6 Gleise vorhanden; Gl. 2 und 5 ohne Nummer, weil ohne Perron (R6/E10). Frage an Daniel offen.
- Regression 16/80 geändert: 4 Topologie zurück (Olten, Zofingen, Aarburg, Regionalplan Olten = Stand 30.10. inkl. 4 alter G6),
  1 vermutlich besser (Wangen, nur Perron), Kerzers, 10 nur Perrons (B13/B14). Konolfingen, Solothurn, Region NE: gleich wie v132.
- Übersicht für Daniel: Artifact «Regression Spurpläne 6.11.» (https://claude.ai/artifact/P88qVKqSjntvYvJCgchdDv).
- **Daniel danach**: Perrons so lassen oder zurück; Kerzers Gl. 2/5 Nummern; Olten, Zofingen, Aarburg ansehen.
- Nächster Schritt: «Weiter mit UEBERGABE.md – Schritt 0: Antworten 6.11. umsetzen» (wartet nicht auf die Perron-Antwort).

### 6.11.2026 22:54 – Antworten Daniel zu Schritt A
- Wangen passt. Kerzers: Gl. 2/5 ohne Nummer bleibt (nur Perrongleise). Perronfrage (1) und Olten/Zofingen/Aarburg (4)
  nach Schritt 0 nochmals vorlegen. Neuer Schritt P «Verbundene Perrons» eingefügt (nach 0).

### 7.11.2026 (Nacht) – Schritt 0 umgesetzt (Seite v134), ein Kriterium offen
- (1) **Caux**: Stumpen aus Gl. 2 Richtung Rochers-de-Naye jetzt dünn. Ursache: Regel «Perron mit einer Nummer gibt sie dem
  nächsten Gleis ohne Nummer» schenkte Perron «1» einem Abstellgleis. Neu: nur an Gleise ohne `service`-Tag (Susch unverändert).
- (2) **Pfeile an Meterspur braun**: reine Schmalspurbahnhöfe waren schon braun; im gemischten Bahnhof (Montreux, Zweisimmen)
  bekommt jeder Pfeil jetzt die Farbe der Spur, deren Gleis seiner Wurzel am nächsten liegt (`_pfeil_farbe`).
- (3) **Perron beidseitig** (`cfg perron_beidseitig`, Standard an): Perron mit ≥ 3 Gleisnummern (OSM `ref` «3;4;5»), deren
  Gleise auf direkt benachbarten Ebenen liegen → je Gleispaar ein Balken. Montreux 3;4;5 und 6;7;8. Eine geometrische
  Variante (Gleis im Perronquerschnitt) wurde verworfen: Gl. 4 endet in der Öffnung, in der Kurve wandert der Querschnitt.
  Le Noirmont / Renens m1 sind in keinem Plan – beim Ausbau prüfen.
- (4) **MOB `gleisnummer_aus_ref` an**: Montreux Gl. 4 im Plan, P1 = 0, Verkettung 0. **Offen:** Unruhe 115 statt ≤ 109 –
  +3 G2 im Gleisgewirr am Westende von Gl. 5 (Gl. 5 mündet in Gl. 4), das erst mit Gl. 4 sichtbar wird. Keine Folge der
  Perronregel. Gehört zur Montreux-Durchsicht (offene Hinweise 5yz7, d3r3, eyn8, j93a, mp8h liegen dort).
- Prüfung aller Pläne: ausser MOB (Montreux, Caux, Zweisimmen, Regionalplan G2 20→23) keine Änderung durch Schritt 0.
- **Daniel danach**: Montreux ansehen; Fragen aus Schritt A nochmals: (1) Perrons kürzer – so lassen oder zurück (mit Blick
  auf Schritt P), (4) Olten, Zofingen, Aarburg-Oftringen. Übersicht «Regression Spurpläne 6.11.» aktualisiert.
- Schritt 0 bleibt offen, bis Montreux die Unruhe ≤ 109 erreicht oder Daniel 115 akzeptiert.
