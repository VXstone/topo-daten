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
- [x] M  Montreux und U-Abgang (7.11., Seite v137; Unruhe-Ziel ≤ 109 geht an Schritt E)
- [x] E  DKW-Automatik nach E3 (8.11., Seite v139; MOB Unruhe 105, Westende im 60°-Gitter)
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

### M – Montreux und U-Abgang (neu 7.11.2026, vor P)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt M: Montreux und U-Abgang»
- Warum vor P: Topologie/Lage vor Perrondarstellung; Schritt 0 ist nur wegen Montreux offen (Unruhe 115); P baut die
  Montreux-Perrons um, eine spätere Lageänderung müsste sonst nachgezogen werden.
- Befund Daniel 7.11.: Knicke bis über 90°, MOB-Abstellgleise auf der falschen Seite der SBB-Gleise, Linien kreuzen sich,
  während beide im Tunnel sind. Offene Hinweise dort: 5yz7, d3r3, eyn8, j93a, mp8h.
- Arbeiten: (1) **U-Abgang** (Vorschlag Daniel): muss ein Gleis wegen der Drehung des Bahnhofs (Anschlüsse anderer Linien)
  um mehr als 90° weg, zeichnet der Code ein U mit zwei Ausrundungen statt eines Knicks; Bündel im gleichen Querabstand.
  Schalter je Region (`cfg`), vorerst nur MOB; später als Baustein in den Prüfstand (Schritt 1). (2) Abstellgleise auf die
  richtige Seite der SBB-Gleise. (3) Kreuzungen im Tunnel entflechten (keine Kreuzung ohne realen Knoten). (4) Westende Gl. 5
  (Einmündung in Gl. 4) beruhigen.
- Fertig, wenn: Montreux ohne Knick > 90°, ohne Kreuzung ohne Knoten, Abstellgleise richtig; MOB-Unruhe ≤ 109 (damit auch
  Schritt 0 fertig); Prüfung aller Pläne ohne unerklärte Änderung.
- Daniel danach: Montreux ansehen.

### E – DKW-Automatik nach E3 (neu 7.11.2026, vor P)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt E: DKW-Automatik»
- Anlass: Entscheid Daniel 7.11. (nach Schritt M). Regel E3 (REGELN.md): mehrere OSM-Elemente < 20 m (Weichen + Kreuzung),
  die zusammen ein Gleis kreuzen, sind eine DKW mit Symbol – bisher nur von Hand (`als_dkw`, `dkw_px`), «Automatik offen».
- Testfall: Montreux Westende Gl. 5 – Kreuzung 1126121469 (`railway_crossing`) mit den Kurzverbindungen 963685765 (15 m)
  und 963685766 (13 m); daneben Kreuzung 2793859963 (reine Kreuzung ohne Bogen, bleibt X). Dazu die schon von Hand
  gesetzten DKW (Rothrist `als_dkw`, Thun) als Gegenprobe: Automatik muss sie gleich erkennen.
- Arbeiten: (1) Erkennung im Code: Kreuzungsknoten + Weichen, deren Verbindungen < 20 m die beiden gekreuzten Gleise
  verbinden → ein DKW-Knoten (einfache/doppelte Kreuzungsweiche je nach Zahl der Bögen); die Kurzverbindungen werden nicht
  als eigene Gleise gezeichnet, sondern als Klammern des DKW-Symbols (E3). (2) Zeichnung über die bestehende R45-Kette
  (gerade 60°-Linie durch die DKW). (3) cfg-Schalter, zuerst nur Regionen; Werkstatt/plaene erst nach Prüfung aller Pläne.
  (4) Verbindung 963685765 endet heute zeichnerisch nicht genau auf 97211358 – mit der DKW erledigt.
  (5) Hinweise Montreux 7.11.: 6yof, afkt, 9636, 8gyi (siehe Nachtrag 7.11. 11:45).
- Ziel-Bild und Regeln: REGELN.md «Verschachtelte Weichenanlagen» (V1–V6), `vergleich/montreux_westende_skizze.png`.
- Fertig, wenn: Montreux Westende wie das Ziel-Bild (V1–V6), ohne Knubbel/Hilfsebenen, Topologie/Verkettung 0, MOB-Unruhe ≤ 109 oder jeder Rest
  ausserhalb Montreux erklärt; Rothrist/Thun unverändert; Prüfung aller Pläne ohne unerklärte Änderung.
- Daniel danach: Montreux ansehen.

### P – Verbundene Perrons / Spezialperrons (neu 6.11. abends)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt P: Verbundene Perrons»
- Anlass: ein Perron bedient mehrere Gleise über Eck oder hängt an einem anderen Perron. Fälle: Thun Gl. 16/18 an Perron 1,
  Montreux (verbundene Perrons), Zweisimmen, Bern Gl. 49/50, Basel um Gl. 3 und um Gl. 35. Baut auf Schritt 0 (3) auf
  (Perron beidseitig eines Gleises).
- Dazu Hinweise Montreux 7.11.: 6rwy (kein Mittelperron Normalspur), 5yz7 (Perron zwischen 4 und 3), es9y (Perronnummern
  Meterspur braun).
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

### 7.11.2026 05:35 – Antworten Daniel
- Reihenfolge: 0 (Rest) → **M** → P → 1 → 2 → 3 → 4 → 5. Schritt M «Montreux und U-Abgang» eingefügt.
- Perronänderungen bestätigt (keine Abnahme): Murten, Dulliken, Däniken, Safenwil, Tecknau, Läufelfingen, Olten Hammer;
  dazu Wangen und Kerzers (Antworten 6.11. abends). Neu `spurplan/regression_ok.json`: Basis der Regression ab diesem Stand.
  Nur auf Daniels Aussage eintragen.
- Noch offen bei Daniel (in Ruhe): Thun, Schönenwerd, Neuchâtel (Perrons) und Olten, Zofingen, Aarburg-Oftringen (Topologie).

### 7.11.2026 (Morgen) – Schritt M umgesetzt (Seite v136), zwei Kriterien offen
- (1) **U-Abgang** (`cfg u_abgang`, Region MOB über `override_standard`): kehrt eine Strecke vor dem Planrand um und geht
  seitlich nach hinten weg, bleibt sie ab dem letzten Gleis mit Ebene auf dieser Ebene bis zum Wendepunkt (home/xs_over der
  Strecke) und verlässt den Plan mit einem U (zwei Ausrundungen, Rückweg bis vor andere Abgänge derselben Seite). Port
  `kind side, dy 0, u true`. Schalter `u_winkel` (180 = U; 120 = Ende unter 60° zurück, im Regionalplan ohne Ecke zur
  Linie Belmont, getestet: Unruhe 120 statt 118 – Daniel entscheidet), `u_radius_px`, `u_hoehe_lanes` (2).
- (2) **Spurgruppe auf ihrer Seite** (`cfg spurgruppe_seite`, in region_lauf für alle Linien-Regionen an): Normalspur-Block
  zwischen unverbundenen Schmalspur-Ebenen kommt an den Rand ihrer realen Seite. Montreux: MOB-Abstellgleise jetzt
  zwischen MOB und SBB. Ursache: Achse = gekrümmte SBB-Linie 100, lange gerade Abstellgleise liefen in Achskoordinaten
  scheinbar durch sie hindurch. Vereina unverändert.
- (3) **Kreuzung am U** (netz_lage `_u_kreuzungen`): Linie 121 kreuzt das U (OSM: 121 layer −2 unter 120 layer −1) →
  Lücke in 121, Flügel an 120. Flügel mit `data-fluegel`, zählen in ruhe.py/regel_pruefung.py nicht.
- (4) **Westende Gl. 5 nicht gemacht** (Gleisgewirr 963685765/97211358/97211375/1112528290, G6 152°/28°).
- MOB: Unruhe 118 (Basis 115, Ziel ≤ 109), Topologie/Verkettung 0. Montreux G2 8→7, G6 3→4 (neu: Knubbel 40° an der
  Doppelverbindung 1112528289/97211362 bei den unteren Abstellgleisen, gleiche Topologie wie vorher, nur andere Ebenen),
  Ecke +1 (Linie Belmont am Ende des U). Die Lagesuche streut ±10 Unruhe zwischen Läufen mit kleinen Änderungen.
- Prüfung aller Pläne: 4 geändert, davon nur `region_mob` durch Schritt M (Aarburg, Rothrist, Zofingen = bekannte Stände
  seit Archivbeginn, Prüfsummen vor/nach gleich).
- Hinweise: eyn8, d3r3 behoben; j93a, mp8h (60°-Verbindung wirkt im 30°-gedrehten Plan senkrecht), 5yz7 Rückfrage.
- **Schritt M bleibt offen**: Unruhe ≤ 109 nicht erreicht (Westende Gl. 5 als Nächstes). **Daniel danach**: Montreux ansehen,
  U (180°) oder 120°-Ende entscheiden, Rückfragen j93a/mp8h/5yz7.

### 7.11.2026 (Vormittag) – Schritt M, Westende Gl. 5 (Seite v137), Unruhe-Ziel nicht erreicht
- **Kreuzung im Schnittpunkt** (`cfg kreuzung_schnitt`, region_lauf: an): ein `railway=railway_crossing`-Knoten, durch den
  zwei Ways schräg laufen, liegt im Schnittpunkt der beiden Schrägen (je Way eine Gruppe durch den Knoten), nicht mehr auf
  einer Hilfsebene. Nur wenn keines der vier Stücke zu einem Gleis > 15 m gehört (Gl. 4 bleibt gerade). Montreux:
  Knoten 1126121469 und 2793859963; Bahnhofplan G2 7 → 4, Regionalplan Montreux G2 7 → 6, G6 4 → 3.
- Verworfen (getestet, schlechter): Hilfsebenen ganzer Ways auflösen (Gruppen über mehrere Ways → G8, lose Stummel);
  Nachbarweiche auf ihr gerades Gleis legen (G4, G8); `als_dkw` an 1126121469.
- Das Westende bleibt unruhig: 1126121469 ist mit den Kurzverbindungen 963685765/963685766 (< 20 m) eigentlich eine DKW
  (E3, «Automatik offen»). Saubere Lösung = E3-Automatik (eigener Schritt). Verbindung 963685765 endet wie schon vorher
  zeichnerisch nicht genau auf 97211358 (keine Topologie-Meldung).
- MOB: Unruhe 119 (Workflow = lokal, Lagesuche ist deterministisch, reagiert aber auf jede Kastengrösse: Zweisimmen
  diesmal ohne −60°, dadurch G2 +2 ausserhalb Montreux). Test Zweisimmen −60 fest: 118. Montreux selbst trägt jetzt
  G2 6, G6 3, Ecke 1 bei (vorher G2 8, G6 3). Den Rest der Unruhe tragen Treppen in Glion (2), Zweisimmen (2), Lenk,
  Montbovon, Toveyre (7 × 8 = 56) – ausserhalb Montreux.
- Prüfung aller Pläne: nur `region_mob` geändert («vermutlich besser»: G6 4→3, G2 21→23 durch Zweisimmen-Drehung).
- **Schritt M bleibt offen** bis Daniel entscheidet: (a) Montreux so abnehmen bzw. Unruhe-Ziel für M aufgeben (Rest ist
  ausserhalb Montreux), oder (b) E3-DKW-Automatik als eigenen Schritt vor P einschieben. Dazu U 180° oder 120°.

### 7.11.2026 11:02 – Entscheid Daniel
- «DKW-Automatik klingt vielversprechend»: neuer Schritt **E – DKW-Automatik nach E3** vor P eingefügt. Schritt M abgehakt;
  sein Unruhe-Ziel (≤ 109) und das Westende Gl. 5 gehen an Schritt E. Reihenfolge jetzt: 0 (Rest) → E → P → 1 → 2 → 3 → 4 → 5.
- Nächster Einstieg: «Weiter mit UEBERGABE.md – Schritt E: DKW-Automatik».

### 7.11.2026 11:45 – U-Ende nach Skizze Daniel (Seite v138)
- Hinweis py1c (Skizze): U in gleichen Drehschritten ≤ 60°, Schlussgerade schon im Winkel der Fortsetzung. MOB `u_winkel`
  150 (Richtung Belmont), Schlussgerade 56 px (`u_rest_px`, < 40 px zählte als kurze Ecke T7). Port hat eigene
  Austrittsrichtung `vx/vy` (netz_lage `port_vec`, gleisenden.py lesen sie).
- Hinweis xntw: unteres Gleis im Tunnel → nur Lücke, keine Brückenflügel (vorerst nur `_u_kreuzungen`; die allgemeine
  `_kreuzungen` in netz_lage hat die Regel noch nicht – Olten/NE prüfen, bevor sie dort gilt).
- MOB Unruhe 115 (Ecke Montreux weg), Topologie/Verkettung 0. Prüfung aller Pläne: nur region_mob «gleichwertig».
- py1c, xntw, j93a behoben. **Neue offene Hinweise Montreux (7.11. 08:5x UTC)** – nicht in Schritt M bearbeitet:
  - in Schritt E (Westende/Gleisgewirr): 6yof «Gleise überlappen», afkt «Mindestabstand?», 9636 «von Gl. 6 und 7 fett auf
    die Strecke» (Hauptgleis-Fortsetzung), 8gyi «Knick vor Tunnelportal» (Abgang 121 an Gl. 8).
  - in Schritt P (Perrons): 6rwy «Normalspur hat keinen Mittelperron, jetzt zwei», 5yz7 «zwischen 4 und 3 müsste ein Perron
    sein», es9y «Perronnummern bei Meterspur überall braun».
  - eigene Regel, später: mp8h «halt alles entsprechend mitdrehen» (Weichenwinkel in gedrehten Bahnhöfen, damit 60° nicht
    senkrecht wirkt); rap4 Glion «Nebengleis nicht fett?».

### 7.11.2026 (Mittag) – Schritt E begonnen (im selben Chat wie M), Zwischenstand, nichts veröffentlicht
- Code `cfg dkw_auto` (spurplan_schema, direkt nach dem Einlesen der Ways), **noch aus** (region_lauf setzt false):
  Kreuzung `railway_crossing` mit je einer Weiche ≤ `dkw_m` (20 m) vor/nach auf beiden Ways + genau zwei Bogen-Ways
  ≤ 25 m (je eine Seite des einen mit der Gegenseite des anderen) → `railway:switch=double_slip`, Fahrwege der Bögen werden
  die zwei Gleise, Bogen-Ways entfallen; im stärker geknickten Fahrweg entfallen die vier Bogenweichen (sonst Hilfsebenen).
- Montreux: erkannt (1126121469; Bögen 963685765/963685766). Real ist es keine X-Kreuzung, sondern ein «Kuss»: der eine
  Fahrweg (Gl. 6) läuft gerade durch, der andere kommt von Gl. 5 hinauf an Gl. 6 und geht gleich wieder hinunter zu den
  Abstellgleisen. Ergebnis Bahnhofplan: Gl. 6 gerade, alle 5 Perrons, G2 6/G6 1 (vorher 4/4). **Offen:** im Bare-Plan landet
  der geknickte Fahrweg nach der DKW wieder auf der Ebene von Gl. 5 (Lage von 8914081514), Regionalplan Montreux G2 +4,
  MOB-Unruhe 117 statt 115; das DKW-Symbol erscheint nicht (Zeichnung erwartet zwei sich kreuzende Gleise).
- **Frage an Daniel** (Bilder im Chat): soll so ein «Kuss» als V (zwei Weichen am selben Punkt von Gl. 6) oder als DKW-Symbol
  auf Gl. 6 gezeichnet werden? Danach: Ebene des Endpunkts nach der DKW richtig (nicht Gl. 5), dann einschalten,
  Gegenprobe Rothrist/Thun (dort `als_dkw` von Hand), Prüfung aller Pläne.

### 7.11.2026 21:00 – Daniel: Aufbau Westende Gl. 5/6 (stimmt 1:1 mit OSM), Konsequenz für Schritt E
- Beschreibung Daniel, mit OSM-Knoten (Skizze `spurplan/vergleich/montreux_westende_skizze.png`):
  - ab Prellbock je eine spitze Weiche gegen das andere Gleis: auf 6 W 1126121816 (→ 8290), auf 5 W 1126121501 (→ 1375);
  - beide Schrägen kreuzen sich im **Mittelstück** X 2793859963 (railway_crossing);
  - dann je eine **DKW in Fortsetzung der Gleise**: auf 6 X 1126121469 (Bögen 963685765/963685766, Weichen 8914106518/
    -520/-517, 1126121525), auf 5 X 207308647 (Bögen 963691444/963691445, Weichen 8914141694/-695/-696/-697);
  - die Stränge nach aussen münden je in eine **Kreuzung/Durchschneidung**: von der DKW auf 6 (1375) in X 1126121838,
    wo Gl. 7 (274706713) als DKW ins Gleis von 6 mündet; von der DKW auf 5 (97211377) in X 8914106524 über Gl. 4;
  - Gl. 4 mündet stumpf in 5 (W 2793859953); vom Gleis 6 her geht es hinüber ins Gleis von 5 (1112528289 → W 1126122400),
    das ist das Hauptgleis auf die Strecke 120; das von 6 her endet im Stumpen (1362), ebenso der Ast der 6 nach der
    Durchschneidung, dort die stumpfe Verbindungsweiche zu den Rochers-de-Naye-Gleisen (einzige Verbindung MOB–MGN);
    der Ast von 5 nach der Durchschneidung führt ins Abstellfeld (97211363 …).
- **Konsequenz für Schritt E (ersetzt den Ansatz vom Mittag):** nicht die Fahrwege zusammenlegen, sondern jede erkannte DKW
  **an Ort** als DKW-Knoten markieren (wie `als_dkw`, Bögen und Bogenweichen entfallen, das Symbol zeigt sie) und die
  Schrägen über R45 als **eine gerade 60°-Linie** ziehen: Weiche → Mittelstück → DKW auf dem anderen Gleis → Kreuzung
  aussen. Erkennung muss auch die DKW auf 5 finden (X 207308647 liegt auf dem durchgehenden Gleis 5 selbst, 3 Ways am
  Knoten – die Mittags-Erkennung verlangte genau 2) und X 1838 als DKW (Gl. 7) bzw. Kreuzung behandeln. Die Ebenen 5/6
  dürfen durch die DKW nicht verspringen (Gl. 5 und 6 sind die durchgehenden Gleise, die Schrägen kreuzen sie).
- Daniel: Skizze bestätigen; dann Umsetzung im neuen Chat «Weiter mit UEBERGABE.md – Schritt E: DKW-Automatik».

### 7.11.2026 21:33 – Korrektur Daniel zum Westende (OSM bestätigt)
- **X 1126121838 ist nur eine Durchschneidung**: Gl. 7 (274706713) endet dort und läuft ohne Weiche als 1112528289 weiter
  (der «Ast von 7»), 97211375 (Ast aus der DKW auf 6) kreuzt nur. Rechts von 1838 ist keine Weiche.
- Der Ast von 7 bildet mit dem Gleis von 6 die **DKW X 1126121977** (Bögen 963685763: 8914081510→8914081511 und
  963685764: 8914081514→8914081515; Gl. 6 = 97211358 endet dort, läuft als 97211362 weiter zum Stumpen 2052) und geht dann
  stumpf in die Strecke (W 1126122400 auf 677497302/«6932»).
- 97211375 nach 1838: W 1126121532 (274706714, einzige Verbindung zur Rochers-de-Naye), dann Stumpen (Prellbock 1126122414).
- **X 8914106524 ist nur eine Durchschneidung** mit Gl. 4; im Ast von 5 (97211377) öffnet danach W 1126122358 ins
  Abstellfeld (97211363). **Gl. 4 geht nur in Gl. 5** (W 2793859953).
- DKW für die Automatik also: 1126121469 (auf 6), 207308647 (auf 5), 1126121977 (Ast von 7 × Gl. 6). Bei 1977 und 8647 läuft
  ein Gleis am Knoten als neuer Way weiter (Ende/Anfang) – die Erkennung muss das als durchgehend behandeln.
  Skizze korrigiert: `spurplan/vergleich/montreux_westende_skizze.png`.

### 7.11.2026 22:48 – Daniel: Zeichenvorgaben Westende (Fassung 3 der Skizze, gilt für Schritt E)
- **Fett** nur die Perrongleise und die Fahrwege ins Streckengleis: von 6 und von 7 (beide über DKW 1977 auf den Ast von 7,
  W 1126122400) und von 4 (W 2793859953). Schere, Diagonalen zum Abstellfeld und zum Stumpen dünn.
- Verbindung zur Rochers-de-Naye (W 1126121532, Way 274706714) zweigt **stumpf von links** ab (nicht nach rechts).
- **Einheitlicher Winkel** (alle Diagonalen 60°, nicht variieren); **jede Durchschneidung in der Mitte zwischen zwei
  Diagonalen** wie das Mittelstück 9963 – also auch X 1838 (Diagonale B × Ast von 7) und X 6524 (Diagonale A × Zufahrt
  Gl. 4 → 5), nicht auf einer Gleisebene.
- Skizze Fassung 3: `spurplan/vergleich/montreux_westende_skizze.png`. Backlog-Idee «Topologie in zwei Durchgängen» in
  IDEEN_REVIEW.md.

### 7.11.2026 23:00 – Daniel bestätigt Skizze Fassung 3
- Westende Montreux als Referenz in `REGELN.md` («Verschachtelte Weichenanlagen», Aufbau 1–7, Zeichenregeln V1–V6) und im
  Doc «Regelwerk Spurpläne» dokumentiert. Schritt E setzt das um; Ziel-Bild `spurplan/vergleich/montreux_westende_skizze.png`.
- Nächster Einstieg: «Weiter mit UEBERGABE.md – Schritt E: DKW-Automatik».

### 7.11.2026 23:30 – Schritt E, Teil 1: Erkennung «DKW an Ort» (V4) gebaut, noch aus, nichts veröffentlicht
- `spurplan_schema.py` (cfg `dkw_auto`, region_lauf setzt weiter false): Ansatz vom Mittag (Fahrwege zusammenlegen) ersetzt.
  Am `railway_crossing` werden zwei **Linien** gebildet – durchlaufender Way oder zwei Way-Enden, die sich gerade fortsetzen
  (≤ 30° Abweichung) –, je Arm eine Weiche ≤ `dkw_m`, zwei Bogen-Ways ≤ dkw_m+5 über alle vier Arme → Knoten wird
  `railway=switch` + `double_slip` an Ort, Bögen entfallen, die vier Bogenweichen werden gewöhnliche Punkte. Linien bleiben.
- Montreux: alle drei DKW erkannt (1126121469, 207308647, 1126121977); 9963, 1838, 6524 bleiben Kreuzungen (richtig).
  Check-Befunde Bahnhofplan A6/B6/D6/F1 → A1/B4/D6.
- Mit `dkw_auto` laufen R45-Ketten auch durch `railway_crossing` (V3): Schräge A 1816→9963→8647→6524→2358 und
  Schräge B 1501→9963→1469→1838 werden je eine Linie; Kette «Ast von 7» 1838→1977→2400 wird verworfen (Kette beginnt an
  der Durchschneidung, Gl. 7 274706713 gehört noch nicht dazu).
- **Offen (Teil 2, Lage):** Bilder `vergleich/montreux_e_ohne.png` / `montreux_e_dkw_an_ort.png`. Die ganze Anlage liegt
  noch auf ~20 px in x zusammengedrückt (reale Abstände 8–20 m): Mittelstück 9963 und DKW 1469/8647 fast am gleichen x,
  Symbole überlagern sich. Nötig: (a) V2 – Kreuzungsknoten ohne Verbindung auf halbe Ebene zwischen die zwei Gleise
  (ypos), Gl. 7 und Gl. 4 werden dafür selbst Diagonale; (b) x-Abstand entlang einer Schräge aus 60° und Ebenenabstand
  (Δx = Δy / tan 60°) als Mindestabstand in der Warp-Anforderung (`*_req.json`) statt aus Metern; (c) Kette Ast von 7 ab
  Gl. 7 beginnen lassen; (d) V5 fett/dünn, V6 Rochers-de-Naye stumpf von links prüfen. Danach Regionalplan MOB,
  Gegenprobe Rothrist/Thun (dort `als_dkw` von Hand), Prüfung aller Pläne.
- Nächster Einstieg: «Weiter mit UEBERGABE.md – Schritt E: DKW-Automatik, Teil 2 Lage».

### 8.11.2026 – Schritt E, Teil 2: Weichenanlage im 60°-Gitter (Montreux Westende), Regionen eingeschaltet
- `region_lauf.py`: `dkw_auto` jetzt **true** für Linien-Regionen (MOB, Vereina). Werkstatt (Olten, NE, Referenzen) und
  `plaene` unverändert (Schalter dort aus; alle neuen Teile hängen an `dkw_auto`).
- Neu in `spurplan_schema.py` (alles nur mit `dkw_auto`):
  - Linien je `railway_crossing` (`LINIEN_X`, auch ohne DKW). An einer erkannten DKW ist die Linie **ohne** Kreuzung in der
    Nähe das durchgehende Gleis (`X_DURCH`, Gl. 5/6), die andere die Schräge; Ketten laufen durch die DKW (FW_PAARE).
  - Kreuzung: Ketten verbinden nur Stücke derselben Linie (Gl. 7 nicht mehr in den Ast zur Rochers-de-Naye). Wechselt eine
    Linie über die Kreuzung die Ebene, wird ihr kürzeres Stück Schräge (Gl. 4 → W 9953 über X 6524).
  - V2 `_x_halb`: Kreuzung ohne Verbindung auf halbe Ebene (9963 5½, 1838 6½, 6524 4½). Endknoten einer Schrägen, an dem
    ein Gleis beginnt, auf die Ebene des Gleises nächst der Anlage (W 2358 Abstellfeld).
  - V1/V3 `_x_gitter`: alle Knoten der Anlage im 60°-Gitter (Δx = ΔY/tan 60°), als `xs_over`; Lage der Anlage so weit
    östlich wie möglich, ohne vor/hinter einen Nachbarknoten ausserhalb zu geraten (Spielraum), sonst Nachbarn mitschieben.
  - Zeichnung `ANLAGE_IDS`: jede Schräge eine gerade Linie durch ihre Knoten; endet sie an einer Durchschneidung, an der
    ihre Linie als Gleis weiterläuft, läuft sie bis auf dessen Ebene (Gl. 7, Gl. 4, Ast Rochers-de-Naye).
  - V5 `V5_FETT`: fett nur Fahrwege Perrongleis → Personengleis gegenüber (wenigste Schrägen): Gl. 6 und 7 über DKW 1977,
    Gl. 4 über W 9953; Schere, Abstellfeld, Stumpen dünn.
  - DKW-Klammern in dichten Anlagen höchstens 45 % des Abstands zum nächsten DKW-Symbol; Gleisnummer nicht in die Anlage.
  - Diagnose: `KNOTDBG=<ids>`, `CHAINDBG=<s0>,<s1>`, `DKWDBG=1`.
- Montreux Bahnhofplan: Check-Befunde A6/B5/D6/F1 → D6 (D = Abstellfeld-Reihenfolge, schon vorher).
- `regel_pruefung.py` G2: liegt ein Linienende auf einer fremden Linie und läuft am selben Punkt ein anderes Stück gerade
  weiter (> 176°), ist das eine Kreuzung, keine Weiche ohne Ausrundung. Wirkt auch auf lage_suche und alle_plaene_pruefen
  (nur Zählung): im Regionalplan MOB fallen so auch Chamby, Rossinière und Zweisimmen (1 von 2 an derselben Stelle) weg –
  dort enden zwei Stücke kollinear auf der Linie; Plan dort unverändert. Daniel ansehen, ob das dort wirklich eine Kreuzung
  ist.
- Workflow `regionen` (7742a52): MOB Unruhe **105** (Basis 115; mit neuer Prüfung auf der Basis wären es 99), Topologie und
  Verkettung 0, Lage-Suche Montbovon 60 / Montreux 30; Vereina 59 unverändert.
- `alle_plaene_pruefen.py` gegen v138 (b1630ff): 80 Pläne, **1 geändert** – region_mob «schlechter?» G2 15→18. Erklärt:
  Westende neu (gewollt, Schritt E); +3 G2: zwei an den Abstellfeld-Weichen gleich hinter W 2358 (Fächer liegt jetzt an der
  Anlage, 31° im gedrehten Plan) und eine an W 2400; übrige Pläne der Region um 5–10 px verschoben (Lage). Alle anderen 79
  Pläne unverändert. Seite **v139** veröffentlicht (Live war = v138).
- Hinweise: 9636 (fett auf die Strecke) und 6yof (Überlappung) behoben; afkt (Mindestabstand) Antwort + Rückfrage, offen;
  8gyi (Knick vor Tunnelportal) nicht Teil von E, offen.
- **Offen / für später:** (1) Im Regionalplan ist Montreux um 30° gedreht – die 60°-Schrägen der Anlage stehen dort senkrecht
  (mp8h «Weichenwinkel mitdrehen»). (2) Ast zur Rochers-de-Naye liegt auf der Ebene von Gl. 7 (Skizze: eine Ebene höher);
  Gl. 8 belegt die Ebene darüber. (3) Die drei G2 oben. (4) Werkstatt/plaene weiter ohne `dkw_auto` (Rothrist/Thun
  unverändert, `als_dkw` von Hand); einschalten erst nach eigener Prüfung.
- Nächster Schritt: «Weiter mit UEBERGABE.md – Schritt P: Verbundene Perrons».
