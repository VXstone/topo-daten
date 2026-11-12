# Übergabe Spurpläne – Stand 9.11.2026 abends

Kurz halten. Gelesen wird **nur diese Datei**, und zwar Abschnitt 0 + der eigene Schritt in Abschnitt 5. Verlauf und
Begründungen stehen in den Archiven – nur gezielt mit `grep` lesen, nie ganz:
- `UEBERGABE_ARCHIV_bis_2026-11-06.md` – Override-Schlüssel und ihr Anlass, Regeln bis 6.11.
- `UEBERGABE_ARCHIV_2026-11-06_bis_11-09.md` – Schritte A, 0, M, E, P1, 1, R1 Teil 1 im Detail (Montreux-Westende, DKW, Prüfstand-Befundliste).

Nachträge: am Ende eines Schritts **höchstens 10 Zeilen** in Abschnitt 6 und den Schritt in Abschnitt 5 abhaken.
Wird Abschnitt 6 länger als ~60 Zeilen, die ältesten Nachträge ins Archiv verschieben.

## 0. Arbeitsweise (gilt in jedem Schritt)
- **Zuerst die Zugriffe holen, solange Daniel da ist** (er bestätigt sie gleich zu Beginn): (1) Repo VXstone/topo-daten mit
  Schreibrecht anhängen (`add_repo`, access push) und `git clone --depth 1`; (2) Feedback-Seite: ArtifactData `list` der
  Sammlungen `feedback` und `abnahme` mit `out_dir`; (3) die erste Schreibfreigabe der Datenbank früh holen, z. B. eine offene
  Antwort des Schritts gleich schreiben. Veröffentlichen fragt erst am Ende – Daniel sagen, wann es so weit ist.
- **Ein Chat je Schritt**, Einstieg = Satz in Anführungszeichen. Nacheinander, nie parallel (alle ändern denselben Code).
- **Nutzung sparen:** UEBERGABE nur abschnittsweise lesen; Feedback-Seite nie ganz öffnen (1,8 MB) – Hinweise/Abnahmen mit
  ArtifactData `list` + `out_dir` als Dateien holen und mit Python filtern; Rechenläufe im Workflow statt lokal, Bilder nur als
  Ausschnitt rendern; Zahlen/Tabellen lesen statt ganze SVG.
- **Feste Runde:** offene Hinweise des Schritts holen → zuerst ein Prüfstand-Fall, der den Fehler zeigt → Code, bis der Fall
  besteht → push (Workflows `pruefstand`, `plaene`, `seite`; `regionen` nach Code-Änderung **von Hand** starten:
  `gh workflow run regionen.yml --ref main`) → Prüfstand «nicht schlechter als Basis» → Tabelle `ergebnisse/seite/regression/`
  lesen, **jede geänderte Zeile erklären** (Regel nach E9 oder Fehler) → Differenzbilder an Daniel → Seite veröffentlichen
  (Live-Fassung vorher mit letztem Build vergleichen, `veroeffentlicht.json` nachführen) → Hinweise beantworten → Nachtrag.
- **Nie abnehmen, nie «erledigt» setzen** – das macht nur Daniel. Lösungen im Code, Overrides nur, wo keine Regel passt.
- Jeder Hinweis Daniels, den der Prüfstand nicht erkennt, wird nach Möglichkeit ein neuer Prüfstand-Baustein.

## 0b. Fallstricke (aus den Archiven, nicht vergessen)
- **«gleichwertig» heisst nur «Zahlen gleich»**: eine neu erfundene Weiche oder ein verschobenes Gleis erkennt die Zählung nicht
  (Zofingen/Aarburg 6.11.). Darum jedes geänderte Plan-Differenzbild ansehen, auch bei «gleichwertig».
- Regressionsbasis: Abnahmen jede Runde neu exportieren (`spurplan/abnahmen.json`, ArtifactData `abnahme`) und committen;
  `spurplan/veroeffentlicht.json` beim Veröffentlichen nachführen; `regression_ok.json` nur auf Daniels Aussage.
- E9: eine Regeländerung darf abgenommene Pläne nur mit Differenzbild und gleicher Topologie ändern.
- `merge_live.py` nur bei echten fremden Änderungen an der Live-Seite – sonst übernimmt es alte Regionalpläne.
- Neue Ordner auf `ergebnisse` in `plaene.yml` eintragen (sonst löscht der Neuaufbau sie, wie den Prüfstand am 9.11.).
- Neue Regeln zuerst mit cfg-Schalter; was in Werkstatt-Plänen (Olten/NE) greift, vor dem Veröffentlichen einzeln ansehen.
- Vor einer Änderung an einer Stelle mit Vorgeschichte `grep` im Archiv nach Bahnhof/Override/Regelnummer (z. B. R27b, R33b,
  Montreux-Westende V1–V6) – dort stehen verworfene Ansätze und warum.

## 1. Quellen
- Regeln: Doc «Regelwerk Spurpläne» und `spurplan/REGELN.md`. Ideen/Backlog: `spurplan/IDEEN_REVIEW.md`.
- Feedback-Seite https://claude.ai/artifact/CKejJqUWnbF6D6EXgA5Nvv – Sammlungen `feedback` (Hinweise) und `abnahme`.
- Bestätigte Regressionen (keine Abnahme): `spurplan/regression_ok.json` – nur auf Daniels Aussage eintragen.
- Prüfstand: `code/blaupausen_pruefstand.py` (+ `pruefstand_bausteine.py`, `pruefstand_messen.py`), Basis
  `spurplan/pruefstand_basis.json`, Ergebnis `ergebnisse/pruefstand/`. Neue Basis nur bewusst (`--basis-aus`).
- Lokal rechnen (nur wenn nötig, Rechner hat 2 Kerne): `region_lauf.py <mob|vereina> --daten <roh.json.gz aus ergebnisse/region_<r>/>`;
  Prüfstand einzelner Bausteine `blaupausen_pruefstand.py <out> --nur <baustein> --stufe osm --jobs 2 --basis …`.
  Abhängigkeiten: `pip install --break-system-packages numpy scipy shapely svgpathtools cairosvg pillow networkx`.

## 2. Woher die Pläne kommen (136 Karten auf der Seite)
| Quelle | Pläne | Workflow |
|---|---|---|
| Region Olten (Werkstatt) | Regionalplan + 13 Bahnhöfe inkl. Aarau | `seite` via `region_olten_lauf.py` |
| Region Neuchâtel (Werkstatt) | Regionalplan + NE 1–8; **ausser Ins, Kerzers, Murten, Neuchâtel, Vauseyon fest seit 21.10.** (`zusatz_plaene.json`) | `seite` |
| Referenzen | Thun, Ins, Murten, Kerzers | `seite` |
| Repo-Bahnhöfe | Neuchâtel, Konolfingen, Vauseyon, Solothurn | `plaene` |
| Linien-Regionen | MOB (45 Bahnhöfe), Vereina (10) | `regionen` (von Hand starten) |
| Fest | Blaupause, Blaupause 2, Basel, Bern (dürfen wieder aus dem Code, Schritt P2) | – |
| Werkzeugkasten | Prüfstand – Bausteine × Drehungen | `pruefstand` |

## 3. Stand (9.11.2026, Commit af9b149, Seite live v143) – Nachträge R1a/R1b in Abschnitt 6 beachten (live v144)
- **Prüfstand** 224 Fälle: T 33, PF 16, X 27, E 110, K 4, Q 20, P 2, Z 101, D 3, G2 11, G7 1 – nicht schlechter als Basis
  (R1 Teil 1: Q 40 → 20, F 16 → 0). Basis noch auf dem Stand 8.11. – nach Schritt R1a neu setzen.
- **Unruhe** MOB 105, Vereina 59; Topologie/Verkettung 0.
- **Prüfung aller Pläne nach R1 Teil 1: 10 geändert – noch nicht erklärt (→ R1a):** `region` (Region Olten) «Fehler? Topologie»
  G2 24→26, G6 7→6, **G7 5→6**; gleichwertig: thun (alter Stand seit 26.10.), olten, olten_hammer, safenwil, aarau, neuchatel,
  region_ne, region_mob, mob__montreux. Verdacht: die neue Stummel-Regel (`_stub_buendel`) greift auch in Werkstatt-Plänen.
- Fertige Regeln dieser Runde: Querabstand schräger Abgänge (`netz_lage` endinfo), Bündel-Stummel (`spurplan_schema`
  `_stub_buendel`, cfg `stub_buendel`). Details Archiv «R1, Teil 1».
- Offene Hinweise (50): Solothurn 10, Konolfingen 9, Region Olten 7, MOB 20, Vereina 3 (h9o9 = behoben-Kandidat, jxpf, fuyq).

## 4. Offen bei Daniel
- Kreuzungen ohne Verbindung: Vorschlag Claude vom 8.11. (Lücke im unteren Gleis nach layer/bridge/tunnel, Brücke mit Flügeln,
  Tunnel nur Lücke, gleiche Ebene durchgezogen) – **Schritt K startet damit, wenn Daniel nicht widerspricht.**
- Prüfstand-Befund «abzweigende Doppelspur» (ab30/ab60, Topologie): eigener Schritt (so im Fahrplan unten, A2).
- Z5-Stumpenabstand 0,55 Ebenen in `vorlage.py` gewollt? Thun (Hinweis auf der Seite). Chamby/Rossinière/Zweisimmen (Kommentare).

## 5. Fahrplan
Grösse: ein Schritt = **ein Thema, ein Codebereich, ein Chat** (Richtwert: 1–3 Code-Änderungen, ein Workflow-Durchgang, eine
Veröffentlichung). Was grösser wird, am Ende in einen Folgeschritt abspalten statt im selben Chat weiterzumachen.

- [x] A, 0, M, E, P1, 1, R1 Teil 1 – siehe Archiv
- [x] **R1a Regression R1 Teil 1 abschliessen** (klein) – 9.11. abends, Seite v143
- [x] **R1b Bündel docken an** (mittel) – 11.11. abends, Seite v144
- [x] **R1c Doppelspur-Abstand im Bündel** (klein) – 11.11. abends, Seite v145
- [ ] **V1 Abgleich Plan gegen OSM** (mittel) – **zuerst** (Wunsch Daniel 12.11.: «wir übersehen was»)
- [ ] **V2 Ein Regelwerk für alle** (mittel, nach V1)
- [ ] **K Kreuzungen und Werfungen** (mittel; nimmt R2-Teil Unterwerfung auf) – **vor A2** (Wunsch 11.11.: Aarau-Tunnel-Hinweise)
- [ ] **A2 Abzweigende Doppelspur** (mittel, Topologie)
- [ ] **R2 Zwischengeraden und Gleissprünge** (mittel)
- [ ] **R3a Ausfahrt als Ganzes** (mittel)
- [ ] **R3b Weichenwinkel mitdrehen + Reparaturpass** (mittel)
- [ ] **P2a Perron-Modell im Code** (gross → zwei Chats nur wenn nötig)
- [ ] **P2b Bern und Basel aus dem Code** (mittel)
- [ ] **H1 Solothurn**, **H2 Konolfingen** (je klein, Hinweisrunden)
- [ ] **N1 Fenster/Abgänge automatisch (Aarau)**, **N2 NE-Bahnhöfe wieder aus dem Code** (je mittel)
- [ ] **5 Montbovon und Prüflauf SBB-Bahnhöfe** (Schluss)

### R1a – Regression R1 Teil 1 abschliessen
- Einstieg: «Weiter mit UEBERGABE.md – Schritt R1a: Regression R1 Teil 1»
- Arbeiten: Differenzbilder der 10 geänderten Pläne (Abschnitt 3) lesen; Region Olten G7 5→6 klären – wenn `_stub_buendel` einen
  Stummel auf ein anderes Gleis/eine Verbindung schiebt: Regel enger fassen (nur Stummel mit Pfeil am Planrand, nicht Werkstatt-
  Verbindungen) statt Override. Prüfstand-Basis neu setzen. Differenzbilder Sagliains, Montreux, Rossinière und jede andere
  gewollte Änderung an Daniel; Seite veröffentlichen; h9o9 beantworten (behoben).
- Fertig, wenn: keine unerklärte Änderung, Region Olten ohne neue Topologie-Befunde, Seite veröffentlicht.

### R1b – Bündel docken an
- Einstieg: «Weiter mit UEBERGABE.md – Schritt R1b: Bündel docken an»
- Arbeiten: parallele Pfeilpaare zwischen zwei Plänen als Bündel verbinden; ein nötiger Versatz gilt fürs ganze Bündel
  (netz_lage `route_geom`/`connector`, `STACK`). Zuerst Prüfstand-Baustein «Bündel mit Versatz» (zwei Bahnhöfe, Enden um ½ Ebene
  verschoben). Testfälle: Vierspur östlich Aarau (parallel bis Rupperswil), MOB/Vereina Treppen T7.
- Fertig, wenn: Baustein ohne Befund, Aarau-Vierspur parallel, T7 MOB/Vereina nicht höher, alle Pläne erklärt.

### V1 – Abgleich Plan gegen OSM (zuerst prüfen, dann Regeln)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt V1: Abgleich Plan gegen OSM»
- Anlass 12.11.: Prüfung sieht nur 26 von 61 offenen Hinweisen (ohne G2); Prüfstand-Messung läuft nur auf Bausteinen.
  Versuch Konolfingen mit Regionsregeln sah nach Zählern besser aus, war aber falsch (DKW 1689230829 weg, Gleisfeld West an
  Gl. 5 statt an 430/Gl. 4) – Zähler messen die Topologie nicht.
- Neue Prüfungen (Baustein `osm_abgleich.py`, auf allen 136 Plänen im Workflow `seite`, im Regressionsvergleich):
  (a) jede OSM-DKW (railway:switch=double_slip/single_slip) im Plan als DKW; (b) jede Berührung zweier Gleise im Plan ist in OSM
  eine Weiche/DKW/Kreuzung, und umgekehrt jede OSM-Weiche im Fenster ist gezeichnet; (c) Gleise ohne OSM-Verbindung berühren sich
  nicht; (d) «Gleis unter Gleis» (flache Kreuzung/Überdeckung) und «Perron auf Gleis»; dazu `pruefstand_messen` auf allen Plänen.
- Kennzahl «Hinweis-Abdeckung»: Anteil offener Hinweise mit Befund < 40 px (Basis 26/61 ohne G2). Testfälle: Konolfingen
  (DKW links oben, Gleisfeld West, 33fs, 3d6h), Montreux, Solothurn. Fertig, wenn: Abdeckung deutlich höher, Prüfungen im Workflow.

### V2 – Ein Regelwerk für alle
- Einstieg: «Weiter mit UEBERGABE.md – Schritt V2: Ein Regelwerk für alle»
- 15 Regeln nur in `region_lauf.py` an (hauptgleis_funktion, perron_frei, gleis_mindestlaenge, perron_abschnitt, perron_teile,
  pfeil_aussen, fenster_streckenende, spurgruppe_seite, kreuzung_schnitt, dkw_auto, randzone, haupt_fortsetzung, r28e/r28f/r36b/r49).
  Eine nach der anderen zum Standard für alle Wege machen, jede an V1 gemessen (nicht an G-Zählern); schadet eine Regel, die Regel
  verbessern statt abschalten. Fertig, wenn: alle Wege gleiche Standards, V1 nicht schlechter, Abdeckung nicht schlechter.
- Pfeile rechts unten Konolfingen (Hinweis 8bce) → Testfall R3b.

### R1c – Doppelspur-Abstand im Bündel
- Einstieg: «Weiter mit UEBERGABE.md – Schritt R1c: Doppelspur-Abstand im Bündel»
- Regel Daniel 11.11.: zwei Doppelspuren je im gleichen (einfachen) Abstand, zueinander einfach oder höchstens doppelt.
  `spurplan_schema` nach der Ebenenvergabe, vor F10 (cfg `buendel_kompakt`, `kompakt_paar_m` 5,5 m).
- Testfall Aarau (Hinweise bei lx 1480 und 3671). Fertig, wenn: Aarau so, alle Pläne erklärt, MOB/Vereina nicht schlechter.

### Aarau-Hinweise 11.11. (Zuordnung)
- K: Tunnel Aarau West «nur ein Gleis, unter den anderen durch», Eppenbergtunnel Weichen/Stummel. R2: Zwischengerade (2×).
- N1: Gl. 4/5 Hauptachsen gerade, zwei Stummel (Seite/korrekt), «was ist das für ein Gleis» (lx 830), Meterspur-Perron (P2a).

### A2 – Abzweigende Doppelspur (Topologie, oberste Regel)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt A2: Abzweigende Doppelspur»
- Befund Prüfstand: ab30 – Strecke 901 fehlt (T 2); ab60 – 901 einspurig/lose Stücke (T 1–4), X, Q 6 px, D bei −30/−60°.
- Fertig, wenn: ab30/ab60 ohne T/X/D in allen Drehungen, alle Pläne erklärt.

### K – Kreuzungen und Werfungen
- Einstieg: «Weiter mit UEBERGABE.md – Schritt K: Kreuzungen und Werfungen»
- Arbeiten: Regel aus Abschnitt 4 in `netz_lage._kreuzungen` (wie `_u_kreuzungen`); `NameError _RPT` in `_kreuzungen` beheben;
  Werfung im Bahnhofplan als Ebenenwechsel unter/über der Kreuzung (Aarau West: 540 unter 650 → im Regionalplan kein X, keine
  Stummel). Testfälle: Prüfstand «unterwerfung» (X 2 in allen Varianten), Aarau West (Regionalplan G5 4, G7 +2), Olten, NE.
- Fertig, wenn: unterwerfung ohne X, Aarau West ohne G5/G7, alle Pläne erklärt.

### R2 – Zwischengeraden und Gleissprünge
- Einstieg: «Weiter mit UEBERGABE.md – Schritt R2: Zwischengeraden und Gleissprünge»
- Arbeiten: Knicke mit kurzer Gerade dazwischen im Solver zusammenlegen (W8); durchgehendes Gleis wechselt Ebene nur an Weiche/
  Werfung (F11). Baustein «gleissprung» an Basel nachschärfen (trifft den Fall heute nicht). Testfälle: zwischengerade d90 (K 4,
  X 3, D), Vorlage-Felder bei ±60° (E/Z in allen 15), Olten.
- Fertig, wenn: Bausteine zwischengerade/gleissprung ohne Befund, Vorlage ±60° ohne E/Z, alle Pläne erklärt.

### R3a – Ausfahrt als Ganzes
- Einstieg: «Weiter mit UEBERGABE.md – Schritt R3a: Ausfahrt als Ganzes»
- Arbeiten: Bahnhofsausfahrt gleichmässig auffächern, Gleisreihenfolge bleibt. Testfälle Selfranga/jxpf (S-Kurve Klosters),
  Chamby-Knick, Sagliains Abgang Scuol.
- Fertig, wenn: Testfälle ohne Treppe/S-Kurve, jxpf behoben, Unruhe MOB/Vereina nicht schlechter.

### R3b – Weichenwinkel mitdrehen + Reparaturpass
- Einstieg: «Weiter mit UEBERGABE.md – Schritt R3b: Weichenwinkel und Reparaturpass»
- Arbeiten: Weichenwinkel in gedrehten Bahnhöfen mitdrehen (mp8h, Montreux 30° gedreht: 60°-Schrägen stehen senkrecht);
  Reparaturpass: verbleibende W8/F11/A1 korrigiert der Code selbst und prüft neu. MOB-Hinweise 8gyi, jy8r, ldwo, 3ctb mitnehmen.
- Fertig, wenn: mp8h behoben, Prüfstand ohne neue Befunde, Unruhe nicht schlechter.

### P2a – Perron-Modell im Code
- Einstieg: «Weiter mit UEBERGABE.md – Schritt P2a: Perron-Modell»
- Grundlage: `code/perron_inventar.py`, Formen von Daniel bestätigt (Archiv 8.11. 14:14/14:17). Ein Modell: Balken je bediente
  Kante + Verbindungsstücke U/L/T; Ebenen (layer/level, RBS Bern 21–24 nicht verbunden); SBB «a/b»-Hausperrons; Gleis ohne
  track_ref über Topologie (Montreux Gl. 4). Fälle: Montreux (6rwy, 5yz7, es9y) → Zweisimmen → Thun 16/18 → Aarau 1/10.
- Fertig, wenn: Baustein perronformen ohne PF, P1 = 0, die vier Fälle wie bestätigt, alle Pläne erklärt.

### P2b – Bern und Basel aus dem Code
- Einstieg: «Weiter mit UEBERGABE.md – Schritt P2b: Bern und Basel aus dem Code»
- Bern 49/50 nahtlos in 9/10; Basel liegende L/T an den Köpfen, Perron 3/4 über das Ende von Gl. 3, 33/35 U. Jede andere
  Änderung gegenüber «fest seit 23.10.» im Differenzbild.

### H1 Solothurn / H2 Konolfingen – Hinweisrunden
- Einstieg: «Weiter mit UEBERGABE.md – Schritt H1: Solothurn» (bzw. H2 Konolfingen). Skill `spurplan-feedback-runde`.
- Nur die offenen Hinweise dieses Bahnhofs; was eine allgemeine Regel braucht, als Baustein notieren und dem passenden Schritt
  oben zuordnen statt im Hinweis-Chat zu bauen. Am sinnvollsten nach R2/R3 (viele Hinweise sind Zwischengeraden/90°).

### N1 / N2 – Neue Bahnhöfe nur mit Konfiguration
- N1 «… Schritt N1: Fenster und Abgänge automatisch»: Fenster aus Betriebspunkten/letzter Weiche (statt `s_min_fix`/`s_max_fix`),
  Abgänge aus `linienenden.json` + Topologie (statt `abgang`), Anbindung automatisch (statt `aarau_anhaengen.py`); Aarau ohne
  Hand-Overrides, dazu Buchs-Rohr, Spurwechsel östlich Schönenwerd (OSM vs. `zusatz_spurwechsel`), AVA-Meterspur.
- N2 «… Schritt N2: NE-Bahnhöfe aus dem Code»: die seit 21.10. festen NE-Bahnhöfe wieder erzeugen, Differenzbilder an Daniel.

### 5 – Montbovon und Prüflauf SBB-Bahnhöfe
- Einstieg: «Weiter mit UEBERGABE.md – Schritt 5: Montbovon im Prüfstand, Prüflauf SBB-Bahnhöfe»
- Montbovon +60° im Prüfstand nachstellen und im Code beheben; alle neuen Regeln über die abgenommenen SBB-Bahnhöfe
  (vorher/nachher, E9: nur bei gleicher Topologie), Tabelle mit Erklärung je Änderung an Daniel.

## 6. Nachträge (je Schritt höchstens 10 Zeilen)

### 9.11.2026 20:15 – Übergabe neu gegliedert
- Alte Fassung samt Nachträgen 6.–9.11. → `UEBERGABE_ARCHIV_2026-11-06_bis_11-09.md`. Fahrplan neu geschnitten (Wunsch Daniel:
  weniger Nutzung, gute Schrittgrössen). R1 aufgeteilt in R1a/R1b, R2-Teil Unterwerfung in K, R3 in R3a/R3b, P2 in P2a/P2b,
  N in N1/N2, neu A2 (abzweigende Doppelspur) und H1/H2 (Hinweisrunden Solothurn/Konolfingen).

### 9.11.2026 ~21:00 – Schritt R1a abgeschlossen, Seite v143
- Region Olten G7 5→6 war **Fehler aus `netz_lage` (nicht `_stub_buendel`)**: Querabstand `TG/|nv·n|` griff auch an Abzweigknoten
  → Aarburg-Verbindung Richtung Rothrist hing ½ Ebene neben dem Streckengleis. Jetzt nur noch `kind != "junction"`.
- `_stub_buendel` nur noch für Stummel mit Pfeil am Planrand (≤ `stub_buendel_rand`·lane, Standard 2): Sagliains 4 px vom Rand;
  verschobene innere Stummel (Rothrist, Safenwil, Olten, Olten Hammer, Aarau, Neuchâtel, Montreux) kollidierten mit Prellböcken.
- Regression danach 3/136, alle erklärt: thun (alter Stand seit 26.10.), region_mob/region_ne = gewollte Querabstand-Korrektur
  an Linienenden (Linie 100 Villeneuve/Lausanne, Linie 210 Yverdon/Biel) + Fusszeile. Region Olten = Stand vor R1.
- Montreux: der zufällig verbesserte Pfeil (zeigte nach innen auf Prellbock) ist wieder wie v142 → Thema für R3b/MOB-Hinweise.
- Prüfstand 224 Fälle wie R1 Teil 1, Basis neu gesetzt (19:40 UTC). h9o9 → behoben (v143). Vereina unverändert seit v142.


### 11.11.2026 ~21:30 – Schritt R1b abgeschlossen, Seite v144 (Commit 3d83eb4)
- Prüfstand-Baustein `buendel_versatz` (Vierspur, Überholgleis zwischen den Paaren nur in Alpha): vorher E 8/Z 8 je Drehung, jetzt
  E 2/Z 2 = der eine nötige Paar-Versatz (Lücke geht in Beta zu). Erwartung im Baustein, kein Fehler. 232 Fälle, Rest = Basis.
- `netz_lage`: (1) `route_geom` – Abgang (exit, eine Strecke) übernimmt die Querlage des Plans, wenn dessen Anschlüsse nicht im
  Regelabstand liegen (Option `buendel_andocken`); ungleich verteilte Bündel gegenüber: Achse folgt dem geraden Teilbündel, Spuren
  = echte Querlage. (2) F11b `buendel_ausrichten`: Plan rückt quer ≤ 1 Ebene, damit das grösste Teilbündel gerade läuft.
  (3) Pfeilpaare gleich gerichtet und nebeneinander → gemeinsame Achse (`pfeile_buendel`); greift in MOB/Vereina heute nirgends.
- Regression 2/136: Region Olten nur Aarau Ost (Vierspur parallel bis Rupperswil, G5 4→3) – dafür G8 1: drei Anschluss-Komponenten
  Buchs-Rohr unter Gl. 4 auf t = 0,03 geklemmt, fast deckungsgleich (`_nebengleise`). Versuch «nicht über gezeichnetes Nebengleis»
  gab Schleifen + G5 → zurückgenommen; gehört zu N1. Thun = alter Stand. MOB 105 / Vereina 59, T7 unverändert, Pläne identisch.

### 11.11.2026 ~22:30 – Schritt R1c abgeschlossen, Seite v145 (Commit a8075cc)
- `spurplan_schema` vor F10 (cfg `buendel_kompakt`): je Paar Hauptgleise (≥ 150 m Überlappung, kein Hauptgleis dazwischen)
  Soll-Ebenenabstand 1 (real < 5,5 m) bzw. 2; verschoben wird die ganze Kette, wenn die Ebenen bis zum Ziel über ihre Länge frei
  sind, sonst das Randstück ab der äussersten Weiche (nie neben einen Perron, Weiche dann auf der neuen Ebene, `KOMPAKT_HOME`);
  kurze Verbindungsstücke an verschobenen Gleisen rücken mit («mitzug», sonst Badewanne Aarau West).
- Wirkung nur Aarau (540 an die 650, Gl. 5 nach der letzten Weiche an Gl. 4), Region Olten (gleiche Befundzahlen) und
  **Konolfingen** Ost (Gl. 3 nach der letzten Weiche an Gl. 2, Doppelspur Luzern benachbart) – Daniel beurteilt Konolfingen.
  MOB/Vereina/NE identisch, Prüfstand 232 = R1b. Kein eigener Prüfstand-Baustein (Lücke entsteht nur aus Ebenen anderer
  s-Bereiche; Aarau ist der Testfall) – Kandidat für einen Baustein, wenn die Regel nochmals angefasst wird.
- GitHub-Runner 21:19–21:50 gestört (queued/startup_failure): hängende Läufe abbrechen, neu starten (`gh workflow run …`).
- Hinweise: 2 Abstand-Hinweise Aarau behoben (v145), 9 Aarau-Hinweise beantwortet und K/R2/N1 zugeordnet (Abschnitt 5).

### 12.11.2026 ~06:30 – R1c Nachtrag Konolfingen, Seite v146 (Commit 7783c31)
- Hinweis Daniel: Zwischengerade verhindert einfachen Abstand 2/3. Ursache: Way 156705005 (siding, 80 m, 4,7 m quer, Gl. 2 → 3)
  galt als flach und bekam eigene Ebene. Neu im R1c-Block (cfg `verbindung_schraeg`): Kette aus genau einem Verbindungsgleis
  ohne Nummer, allein auf einer Ebene zwischen den Ebenen der zwei verbundenen Hauptgleise → Schräge; leere Ebene fällt weg
  (alles darüber eine Ebene tiefer). Nicht, wenn ein Perron zwischen den beiden Gleisen liegt (Montbovon Mittelperron 2/3).
- Verworfen: Regel auf Segment-Ebene (vor der Ketten-Bildung) – traf Olten (2 Ways) und Solothurn (3), G7 +5 im Regionalplan.
- Wirkung nur Konolfingen (2/3/4 einfacher Abstand, kein Versatz Luzern); MOB/Vereina/Olten/NE/Repo-Bahnhöfe identisch,
  Prüfstand = Basis. nreb und 2ch8 (Konolfingen) → behoben.

### 12.11.2026 ~21:20 – Diagnose «wir übersehen was», neue Schritte V1/V2
- Befund: 15 Regeln nur in MOB/Vereina an; Prüfung deckt 26/61 offene Hinweise ab. Versuch Konolfingen mit Regionsregeln
  verworfen (Daniel: DKW links oben fehlt, Gleisfeld West von Gl. 5 erreichbar – OSM bestätigt beides). Reihenfolge: V1, V2, K, A2 …
