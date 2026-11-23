# Übergabe Spurpläne – Stand 9.11.2026 abends

Kurz halten. Gelesen wird **nur diese Datei**, und zwar Abschnitt 0 + der eigene Schritt in Abschnitt 5. Verlauf und
Begründungen stehen in den Archiven – nur gezielt mit `grep` lesen, nie ganz:
- `UEBERGABE_ARCHIV_bis_2026-11-06.md` – Override-Schlüssel und ihr Anlass, Regeln bis 6.11.
- `UEBERGABE_ARCHIV_2026-11-06_bis_11-09.md` – Schritte A, 0, M, E, P1, 1, R1 Teil 1 im Detail (Montreux-Westende, DKW, Prüfstand-Befundliste).

Nachträge: am Ende eines Schritts **höchstens 10 Zeilen** in Abschnitt 6 und den Schritt in Abschnitt 5 abhaken.
Wird Abschnitt 6 länger als ~60 Zeilen, die ältesten Nachträge ins Archiv verschieben.

## 0. Arbeitsweise (gilt in jedem Schritt)
- **Einstieg (Daniel kopiert):** «Weiter mit UEBERGABE.md – Schritt X, mit Artefakt und Repo schreibend» = Freigabe für: Repo
  anhängen mit Schreibrecht + push auf main, Feedback-Datenbank lesen und schreiben (Antworten, prio), Seite veröffentlichen, wenn
  die Sperren grün sind. Die Werkzeug-Freigaben der App kommen trotzdem als Klicks – darum alle **in den ersten Minuten** auslösen.
- **Berichten wie Daniel schaut (21.11.):** zuerst, was er im Regionalplan der Seite sieht – mit Vorher/Nachher-Ausschnitt der Stelle
  (wie Vauseyon 20.11.); Technik und Gründe nur auf Nachfrage. Was nur angenommen statt angesehen ist, so benennen
  («angenommen, nicht geprüft»). Hinweise **prio zuerst** (REGELN 0.10).
- **Zuerst die Zugriffe holen, solange Daniel da ist** (er bestätigt sie gleich zu Beginn): (1) Repo VXstone/topo-daten mit
  Schreibrecht anhängen (`add_repo`, access push) und `git clone --depth 1`; (2) Feedback-Seite: ArtifactData `list` der
  Sammlungen `feedback` und `abnahme` mit `out_dir`; (3) die erste Schreibfreigabe der Datenbank früh holen, z. B. eine offene
  Antwort des Schritts gleich schreiben. Veröffentlichen fragt erst am Ende – Daniel sagen, wann es so weit ist.
- **Ein Chat je Schritt**, Einstieg = Satz in Anführungszeichen. **Am Ende jedes Berichts den Einstieg für den nächsten Chat als
  Code-Block zum Kopieren** (Daniel 22.11.). Nacheinander, nie parallel (alle ändern denselben Code).
- **Nutzung sparen:** UEBERGABE nur abschnittsweise lesen; Feedback-Seite nie ganz öffnen (1,8 MB) – Hinweise/Abnahmen mit
  ArtifactData `list` + `out_dir` als Dateien holen und mit Python filtern; Rechenläufe im Workflow statt lokal, Bilder nur als
  Ausschnitt rendern; Zahlen/Tabellen lesen statt ganze SVG.
- **Feste Runde:** offene Hinweise des Schritts holen → zuerst ein Prüfstand-Fall, der den Fehler zeigt → Code, bis der Fall
  besteht → push (Workflows `pruefstand`, `plaene`, `seite`; `regionen` nach Code-Änderung **von Hand** starten:
  `gh workflow run regionen.yml --ref main`) → Prüfstand «nicht schlechter als Basis» → Tabelle `ergebnisse/seite/regression/`
  lesen, **jede geänderte Zeile erklären** (Regel nach E9 oder Fehler), **Sperre G0 grün** (Spalte G0) → Differenzbilder an Daniel → Seite veröffentlichen
  (Live-Fassung vorher mit letztem Build vergleichen, `veroeffentlicht.json` nachführen) → Hinweise beantworten → Nachtrag.
- **Sichtbar zuerst (12.11. spät, Daniel: «das Sichtbare hat sich wenig verändert»):** jeder Schritt hat einen **Zielplan** mit
  benannter Stelle. Zu Beginn Vorher-Ausschnitt + «so soll es aussehen» an Daniel; am Ende Differenzbild, Seite veröffentlichen,
  Daniel nickt ab/widerspricht. **Ohne sichtbare Wirkung am Zielplan ist der Schritt nicht fertig.** Prüfstand, OSM-Abgleich,
  Regression sind Leitplanke, nicht Ziel. Die übrigen Schritte im Fahrplan beim Start ebenso mit Zielplan versehen.
- **Regeln nur in `REGELN.md`** an ihrer Stelle der Hierarchie (13.11., Daniel: «keine Ergänzungs-md-Sachen mehr»); Nachträge
  hier verweisen auf «REGELN x.y». `regeln_lint.py` / Workflow `regeln` muss grün sein; Hinweise H1 (Schalter ohne Regel) abbauen.
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
- Kreuzungen ohne Verbindung: **entschieden 13.11.** (REGELN 2.5) – Schritt K setzt es um.
- Offene Entscheide stehen nur noch auf der Karte «Fragen an Dani» (`spurplan/fragen/fragen.json`, REGELN 7). Beantwortete Fragen
  dort löschen und in REGELN.md eintragen.
- Prüfstand-Befund «abzweigende Doppelspur» (ab30/ab60, Topologie): eigener Schritt (so im Fahrplan unten, A2).
- Chamby/Rossinière/Zweisimmen: Daniels Hinweise auf der Seite (an Claude, kein offener Entscheid). Z5-Abstand: REGELN 1.5 (13.11.).

## 5. Fahrplan
Grösse: ein Schritt = **ein Thema, ein Codebereich, ein Chat** (Richtwert: 1–3 Code-Änderungen, ein Workflow-Durchgang, eine
Veröffentlichung). Was grösser wird, am Ende in einen Folgeschritt abspalten statt im selben Chat weiterzumachen.

- [x] A, 0, M, E, P1, 1, R1 Teil 1 – siehe Archiv
- [x] **R1a Regression R1 Teil 1 abschliessen** (klein) – 9.11. abends, Seite v143
- [x] **R1b Bündel docken an** (mittel) – 11.11. abends, Seite v144
- [x] **R1c Doppelspur-Abstand im Bündel** (klein) – 11.11. abends, Seite v145
- [x] **V1 Abgleich Plan gegen OSM** (mittel) – 12.11. abends, Commit d5f52c5 (Seite nicht neu veröffentlicht: kein Plan geändert)
- [x] **S1 Sagliains parallel durch den Knick** (klein) – 13.11. früh, Commit 08022dd, Seite v147
- [x] **B1 Basis-Paket** – 17.11. nachmittags: V0-Rest und G1 fertig; S2/S3 abgespalten (Befund in Abschnitt 6, B1)
- [x] **S2 Konolfingen DKW / Ostkopf** – 17.11. abends (Nachtrag S2); Gleisfeld West abgespalten → S2b
- [x] **G0 Grundprüfung als Sperre** – 18.11. vormittags, Commits 404ca61 + Basis Prüfstand (Seite nicht neu veröffentlicht: kein Plan geändert)
- [x] **T-SZU Testregion SZU** – 18.11. mittags, Commits 114156c/1d587e8, Seite v155 (Befundliste in Abschnitt 6)
- [x] **HT Hauptgleis-Topologie als Sperre (REGELN 0.1, Kopf «HT»)** – 18.11. spät, `code/hauptgleis.py`, Basis gesetzt (Nachtrag HT); Seite nicht neu veröffentlicht (kein Plan geändert)
- [x] **K0 Sichtbar: Ins im Regionalplan + Zwischengeraden im Bahnhofplan** – 19.11. nachmittags, Commits 83a0dc2/64a3fa4, Seite v156 (Nachtrag K0)
- [x] **K0b Zwischengeraden Rest (REGELN 1.9)** (v157, 20.11.)
- [x] **V3 Bahnhofregister + OSM-Verdacht + Sperre «veraltet»** – 20.11. abends, Commits 5e32a01/ce5b16c, Seite v158 (Nachtrag V3)
- [x] **V4 NE in den gemeinsamen Bauweg** (REGELN 0.9/4.11) – 20.11. spät Bauweg (d979b78, 0c47dd1), mit V4b veröffentlicht (v160)
- [x] **V4b G0 grün + veröffentlichen** – 21.11. vormittags, Commit 16ca65c, Seite v160 (Nachtrag V4b)
- [x] **V4c NE: HT-Befunde abbauen** – 21.11. (v161/v162)
- [x] **V4e NE: HT-Rest** – 21./22.11. (v164–v170), alle NE-Pläne HT 0 bzw. Ausnahme Courtepin (Nachträge V4e Teil 1–5)
- [x] **V4f Neuchâtel im Regionalplan wie im Bahnhofplan** – 23.11. vormittags, Commit 43a3919, Seite v172 (Nachtrag V4f)
- [ ] **V4d NE ruhig + Nebengleise kürzen** (mittel, REGELN 4.5/5.9): 23.11. Teil 1 v173 – pjyb/zlwn behoben, Onnens kürzer, W59 neu; **offen: vpkw Muntelier (Rückfrage A/B)**, Rest W59-Liste – siehe Nachtrag V4d
- [ ] **K0c Selnau parallel (REGELN 2.2, `r34_kette`)** (klein) – siehe Nachtrag 20.11. ~19:15; nach V3/V4, vor T-SZU1
- [ ] **V5 ein Lauf für alle Regionen** / **V6 Netz West (Neuchâtel–Biel–Solothurn–Olten)** – danach – Zweisimmen (dünn→dick am Knick), Solothurn (Weiche am Knick, doppelter Abstand), Selnau (ZL ~4 Ebenen, nur auf Daniels Antwort); Liste `ergebnisse/seite/zwischengeraden.md` – vor oder nach T-SZU1, wie Daniel will
- [ ] **T-SZU1 DKW aus 4-Arm-Weiche (REGELN 2.4) und Güterverkehr schwarz (REGELN 1.21)** (klein, Entscheid Daniel 18.11.) – nach K0
- [ ] **T-SZU2 Achse knickt im Fenster (REGELN 2.15), Zielplan Giesshübel · Saalsporthalle** (Entscheid Daniel 18.11.: Variante C) – nach S2b/R4/S3 oder wenn Daniel es vorzieht
- [ ] **S2b Konolfingen Gleisfeld West** (Zielbild Daniel 18.11.), **R4 Rothrist im Regionalplan** und **S3 Aarau
  Zwischengeraden mit Weiche** – nach T-SZU, je eigener Chat, alle gegen die G0-Sperre geprüft
- [x] **S1b Sagliains-Bündel durchgehend** (klein) – 16.11. früh, Commits af2a110/21556d3, Seite v150
- [ ] **V2 Ein Regelwerk für alle** (mittel, Rest nach S2)
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

### S1 – Sagliains parallel durch den Knick
- Einstieg: «Weiter mit UEBERGABE.md – Schritt S1: Sagliains parallel durch den Knick»
- Zielplan **vereina__sagliains**, Portal links oben: zwei Nebengleise (y 110 / 123,2, Abstand 13,2 px = 0,55 Ebene) knicken
  60° zum Pfeil; Knick des oberen 20 px versetzt → Treppe, schräg 24 px Querabstand. Ursache: `_stub_buendel` (R1a) zielt fest auf
  `lane_px` 24.
- Regel Daniel 12.11.: **parallel bleibt parallel auch beim Knicken** – Querabstand nach dem Knick = Abstand davor; Knickversatz
  des äusseren Gleises d·tan(θ/2) (60°: 0,58·d = 7,6 px). Gilt für jedes Bündel, das gemeinsam knickt (Ausfahrten, Spurwechsel-
  paare, Abgänge), nicht nur Stummel; `_stub_buendel` darauf umstellen. Offene Frage 0,55 Ebenen (Abschnitt 4) davon getrennt.
- Zuerst Prüfstand-Baustein «Bündel knickt» (Abstand 0,55 und 1 Ebene, Knick 30°/60°; Messung P/Q muss anschlagen).
- Fertig, wenn: Sagliains-Portal als Bündel mit 13,2 px durch den Knick, Baustein ohne Befund, alle geänderten Pläne erklärt,
  Seite veröffentlicht (nimmt die Vereina-Änderung aus V1 mit).

### B1 – Basis-Paket (Wunsch Daniel 17.11.: V0-Rest, G1, S2, S3 als ein Schritt)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt B1: Basis-Paket»
- Vier Teile **in dieser Reihenfolge, im selben Chat**, Beschreibung je Teil in den Abschnitten V0, G1, S2, S3 unten:
  (1) V0-Rest: Messungen 5.3 S-Kurve / 5.5 Bahnhofsabstand / 5.6 Bahnhofslänge mit Einordnung «besser» in alle_plaene_pruefen,
      Liste der Overrides (REGELN 6), Herkunft je Plan auf der Seite («aus Code <Commit/Datum>» / «fest seit <Datum>»);
  (2) G1 Glion; (3) S2 Konolfingen; (4) S3 Aarau.
- Je Teil: Zielplan-Vorher an Daniel → Code → eigener Commit/Push + Workflows → Regression erklärt → Vorher/Nachher an Daniel.
  **Einmal veröffentlichen am Schluss** (oder früher, wenn Daniel es will). Ein Teil, der hängt, wird als Folgeschritt
  abgespalten statt die anderen aufzuhalten. Nutzung: nur die Abschnitte des laufenden Teils lesen.
- Fertig, wenn: alle vier Teile nach ihren eigenen «Fertig, wenn» erfüllt oder sauber abgespalten, Seite veröffentlicht.

### V0 – Ein Regelwerk auf GitHub (Entscheid Daniel 13.11.2026)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt V0: Ein Regelwerk auf GitHub»
- Daniel: «Regeln sollen überall gelten, alle Bahnhöfe gleich erstellen – sonst weiss ich beim Prüfen nicht, ob ein Ort erfasst
  wurde.» Heute: Master-Text im Doc «Regelwerk Spurpläne» (Stand ~25.10.), neuere Regeln in REGELN.md/Archiven/Daniels
  Vorgaben; 15 Regeln nur in `region_lauf.py`; NE-Bahnhöfe (53), Referenzen, Basel/Bern fest.
- Arbeiten: (1) `REGELN.md` = einzige Quelle: Doc-Inhalt + Entscheide aus Archiven/Vorgaben übernehmen, je Regel Nr., Text,
  Rang, Code-Ort/cfg, Prüfung; Doc nur noch Verweis. (2) Liste der Widersprüche (Review 13.11.: Abstand 0,55 vs. Grundsatz 5/Q;
  Randzone E5 vs. S1; Randzone vs. F11/E; Versatz auf Strecke vs. R10; 60° vs. r49/Kippen) mit Daniels Entscheid.
  (3) Je Plan auf der Seite sichtbar, woher er kommt: «aus Code <Commit/Datum>» oder «fest seit <Datum>».
- **13.11. ~08:30 erledigt:** REGELN.md hierarchisch neu (Ebenen 0 Grundsätze, 1 Grundform, 2 Muster, 3 Knoten, 4 Region,
  5 Wünsche, 6 Ausnahmen, 7 Widersprüche; Regel vs. Wunsch; Spalte «heute aktiv in»). Alte Fassung → REGELN_ARCHIV_bis_2026-11-13.md.
  Daniel 13.11.: der Code darf Pläne verbessern (weniger S-Kurven, gleichmässiger Bahnhofsabstand, kürzere Bahnhöfe –
  Onnens-Bonvillars, Rothrist, Tecknau) → Vergleich neu mit Einordnung «besser» (REGELN 5).
- Offen in V0: Entscheide 7.1–7.6 holen; Messungen 5.3 (S-Kurve über Pläne), 5.5 (Bahnhofsabstand), 5.6 (Bahnhofslänge) bauen
  und in die Regression (alle_plaene_pruefen) mit Einordnung «besser»; Liste der Overrides (6); Herkunft je Plan auf der Seite.
- Fertig, wenn: REGELN.md vollständig, Widersprüche entschieden, Herkunft je Plan auf der Seite. Danach V2 (alle 15 Regeln
  Standard in allen Wegen, Konolfingen = S2 als erster Fall), dann N2 (NE aus dem Code), P2b (Bern/Basel), Referenzen.

### S1b – Sagliains-Bündel durchgehend (Daniel 16.11., REGELN 1.10/1.8)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt S1b: Sagliains-Bündel durchgehend»
- Zielplan **vereina__sagliains** + **region_vereina**: (1) Darstellungsfehler am Portal: Ausrundung und **ein Stummel je Gleis**
  (heute doppelt/falsch); (2) der Nebengleis-Abstand (0,55 Ebene) wird im Regionalplan und im Nachbarbahnhof (Sagliains
  Sasslatsch) gleich übernommen – kein Trichter, kein Versatz am Tunnelportal.
- Idee Daniel (prüfen, nicht sofort bauen): Sasslatsch–Sagliains als **ein grösserer Plan ohne Bahnhofstrennung** optimieren.
  Vorgeschichte: Knotenplan über Nebengleis am 3.11. getestet (`knoten_nebengleis`), verlor Tunneleinmündung und Schenkel
  (6 Topologie-Befunde) → Archiv «3.11.» lesen, Variante mit grösserem Plan als Vorher/Nachher an Daniel.

### G1 – Glion Gleise und Perrons (Daniel 17.11.: «ein Gleis im Bahnhofsteil zu wenig, ein Perron nicht neben dem Gleis»)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt G1: Glion Gleise und Perrons»
- Zielplan **mob__glion** (+ region_mob). Ortskenntnis Daniel 17.11.: **keine Spitzkehre** – die Strecke läuft durch den Bahnhof;
  zwei Perrongleise, ein Gleis ohne Perron und ein Stumpen, der nur von oben (Seite Rochers-de-Naye) erreichbar ist. Plan zeichnet
  heute im Bahnhofsteil ein Gleis zu wenig, der untere Perron liegt nicht entlang seines Gleises (seit v149, nicht S1b).
  Achtung: `ergebnisse/region_mob/roh.json.gz` ist um Glion lückenhaft (Ways mit 1–5 Knoten) – Geometrie aus vollständigen
  OSM-Daten (Release «daten») prüfen, nicht aus roh. Offene Hinweise wyu2, i06se, v2w8.
- Fertig, wenn: vier Gleise wie oben, jeder Perron entlang seines Gleises, Stumpen nur von oben angebunden, OSM-Abgleich ohne
  neue Befunde.

### S2 – Konolfingen Topologie richtig
- Einstieg: «Weiter mit UEBERGABE.md – Schritt S2: Konolfingen Topologie»
- Zielplan **konolfingen**: DKW 254420784, 1689231120, 1689231106 gezeichnet; Abstellgleise West nicht mehr über Strecke 430
  (VB2 bei 367/317 und 353/341), kein Gleis unter Gleis (VB2 584/270), Gleisfeld West richtig angebunden (VC1 402/293);
  DKW 1689230829 bleibt (am 12.11. mit Regionsregeln verloren).
- Weg: Regeln aus `region_lauf.py` (dkw_auto, kreuzung_schnitt, haupt_fortsetzung, …) auch für Repo-Bahnhöfe einschalten,
  einzeln, jede am OSM-Abgleich gemessen (V-Summe Konolfingen 12 → 0 Ziel), nicht an G-Zählern. Hinweise ttv8, z6f2, 33fs,
  3d6h, 8bce danach beantworten.
- Fertig, wenn: Konolfingen ohne VA1/VB2/VC1, keine neuen V-Befunde in anderen Plänen, Seite veröffentlicht.

### G0 – Grundprüfung als Sperre (Entscheid Daniel 18.11.: «so Dinge wie nicht überschneiden, paralleler Abstand etc. sollten funktionieren»)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt G0: Grundprüfung als Sperre»
- Anlass: S2 meldete «Gl.-6-Schräge kreuzt nichts», tatsächlich Schnitt bei 558/283 (v153). Der OSM-Abgleich zählt eine
  Kreuzung nur, wenn er sie keiner OSM-Weiche zuordnen kann – eine nahe Weiche (< 40 px) «erklärte» sie. Eine reine
  Geometrieprüfung (zwei gezeichnete Linien schneiden sich ausserhalb ihrer Endpunkte) fand sie sofort.
- Bauen: Prüfung nur auf das gezeichnete SVG, ohne OSM-Zuordnung, je Plan mit Ort: (1) Schnitt ohne DKW-Symbol, Kreuzungs-
  knoten oder Niveautrennung (REGELN 2.4/2.5); (2) Gleis auf Gleis (VD1 übernehmen); (3) Querabstand paralleler Gleise vor/nach
  einem gemeinsamen Knick ungleich (REGELN 1.15/2.7); (4) Pfeil zeigt nach innen / auf Nachbargleis (1.14); (5) Abgang
  oder Knick mit 90° (1.2); (6) Treppe (Wunsch 5). Alle 137 Pläne + Prüfstand; Ausgangsstand als Basis committen
  (`spurplan/grundpruefung_basis.json`), Workflow `seite` rot, wenn ein Plan einen **neuen** Befund bekommt; Spalte in
  `regression/tabelle.md`.
- Arbeitsweise ab G0: «sauber/kreuzt nichts» nur mit dieser Prüfung melden, nie nach Augenschein.
- Fertig, wenn: Prüfung läuft im Workflow, Basis gesetzt, der Fall 558/283 (Konolfingen v153) wird als Prüfstand-Baustein
  erkannt.

### T-SZU – Testregion SZU (Wunsch Daniel 18.11.)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt T-SZU: Testregion SZU»
- Perimeter: Zürich HB Gl. 21/22 (SZU), Selnau, Giesshübel, dann Sihltalast bis Saalsporthalle(-Sihlcity) und Uetlibergast
  Binz – Friesenberg – Schweighof – Triemli – Uitikon Waldegg – Ringlikon – Uetliberg. Daniel: ab Binz bis Uetliberg sollte
  erwartungsgemäss sehr einfach sein (Prüfstein: dort darf nichts von Hand nötig sein).
- Aufbau wie `regionen/vereina/`: `regionen/szu/region.json` (bbox, Linien-Refs aus OSM im ersten Lauf bestimmen, Betreiber
  SZU / Sihltal Zürich Uetliberg Bahn), `orte.json` (Richtungsorte z. B. Sihlwald/Langnau für S4), `region_lines.json`;
  Workflow `regionen` um «szu» ergänzen. Keine Overrides im ersten Lauf – was nicht stimmt, wird Regel oder Befund.
- Messen: G0-Sperre, OSM-Abgleich, Verkettung; Ergebnis als Liste «was die Grundregeln nicht halten» → Arbeitsliste.
- Fertig, wenn: Region SZU auf der Seite, G0 ohne Befund ab Binz–Uetliberg, übrige Befunde benannt.

### HT – Hauptgleis-Topologie als Sperre (Entscheid Daniel 18.11. 15:51, REGELN 0.1 und Kopf «HT»)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt HT: Hauptgleis-Topologie als Sperre»
- Anlass: Giesshübel (T-SZU) – der OSM-Abgleich meldete am Code-Plan 52 Befunde, gesperrt hat nur G0 (Geometrie); in der Skizze
  fielen Schere statt zweier Spurwechsel, fehlende Depot-Anschlüsse und Gl. 43 auf der falschen Seite niemandem ausser Daniel auf.
- Bauen: in `osm_abgleich.py` (Netzmodell <key>_netz.json + OSM) die Befunde mit Hauptgleis-Beteiligung als HT1–HT3 ausweisen
  (VB1/VB2/VC1); neu HT4 Seite (Abzweig im Plan links/rechts des Hauptgleises in dessen Fahrrichtung = OSM, Grundlage `r38_seite`)
  und HT5 Fahrwege (Graph aus dem gezeichneten Plan über das Netzmodell gegen OSM-Graph: Enden der Hauptgleise paarweise, Weg
  ohne Richtungswechsel an einer Weiche; Mengen vergleichen). Hauptgleis = grün nach 1.21/1.24. Ausgangsstand als Basis
  (`spurplan/hauptgleis_basis.json`), Workflow `seite` rot bei neuem Befund, Spalte HT in `regression/tabelle.md`; Prüfstand ebenso.
- Prüffälle (Selbsttest wie G0): Giesshübel aus Code (heute, HT > 0), ein Plan mit Schere statt zweier Spurwechsel, Abzweig zur
  falschen Seite, fehlender Spurwechsel (Fahrweg fehlt) – je in mindestens zwei Drehungen.
- Danach: Liste aller Pläne mit HT > 0 an Daniel (Ziel 0; die Liste bestimmt die Reihenfolge der Folgeschritte).
- Fertig, wenn: HT läuft im Workflow, Basis gesetzt, die Prüffälle werden erkannt, Bericht nennt G0 und HT je Plan.

### K0 – Sichtbar: Ins im Regionalplan und Zwischengeraden im Bahnhofplan (Wunsch Daniel 19.11.)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt K0: Ins und Zwischengeraden»
- Anlass (19.11., Daniel: «wann passieren mal wieder sichtbare Fortschritte … Zwischengeraden oder das nicht Aufeinandertreffen
  von Gleisen in Ins»): seit v155 nur Prüfungen gebaut (G0, T-SZU, HT), nichts Sichtbares. **Dieser Schritt muss auf der Seite
  sichtbar sein und am selben Tag veröffentlicht werden.** Keine neuen Prüfungen bauen; G0/HT nur als Leitplanke (Sperre grün).
- **Teil 1 – Ins im Regionalplan NE** (Hinweis `1470h7mj983zrabw11m1`, region_ne x 1498/y −874, im Plan Ins lx 551/ly 121):
  «Im Bahnhofplan scheinen die Gleise verbunden, im Regionalplan nicht». REGELN 4.x / Entscheid 18.11. (Rothrist): der Regionalplan
  zeigt den Bahnhof wie dessen Bahnhofplan. Vorgehen: Ausschnitt Ins aus `ergebnisse/seite/plaene/region_ne.svg` und `ins.svg`
  rendern (nur Ausschnitt), Stelle mit G0 (GS/GG/GP) und Verkettung (`verkettung.py`) benennen, Ursache in der Einbettung
  (`region_olten_lauf.py --konfig spurplan/werkstatt/ne/region_ne.json`, `region_geometrie.py`) suchen, im Code beheben (kein
  Override). Fertig: im Regionalplan treffen die Gleise wie im Bahnhofplan aufeinander, Differenzbild Ins.
- **Teil 2 – Zwischengeraden im Bahnhofplan** (REGELN 1.9; W8 wirkt heute nur im Regionalplan `region_geometrie.py` und im
  Bahnhofplan nur am Abgang `spurplan_schema.py` ~Z. 4828): Zielplan **aarau** (Hinweise `fmlk3ybhicj80yggwifb`,
  `vnyq1jtx6sv6gc2scn80`), mitprüfen Solothurn `xke0q8que3hufliwbag9`, Zweisimmen `jy8ro0t1s42ghqu25tyk`, Selnau
  `j9ouxkqumkzu5bwvwyqp`, Konolfingen `0fzpdkb9gtvz8ectd8iz` (sonst S2b). Zu Beginn: Zwischengeraden in allen Plänen zählen
  (W8-Messung aus `region_geometrie.py` auf die Bahnhofpläne anwenden) → Liste an Daniel; dann im Löser des Bahnhofplans: zwei
  Knicke mit kurzer Gerade (< 1,5 Ebenen) ohne Weiche/Perron/Nummer dazwischen zu einer 60°-Schräge zusammenlegen (eine Regel,
  alle Pläne, cfg-Schalter mit REGELN 1.9 in Spalte «Code»). Fertig: Zwischengeraden in Aarau weg, Zählung über alle Pläne
  gesunken, kein Plan mit neuem G0/HT-Befund.
- Ablauf wie Abschnitt 0 (Vorher-Ausschnitte + Zielbild an Daniel zu Beginn, Regression jede Zeile erklären, Differenzbilder,
  veröffentlichen, Hinweise beantworten). Wird Teil 2 zu gross: Teil 1 + Aarau veröffentlichen, Rest als K0b abspalten.
- Schritte S3 (Aarau Zwischengeraden) und R2 (Zwischengeraden-Teil) gehen in K0 auf; R2 behält nur die Gleissprünge.

### V3 – Bahnhofregister, OSM-Verdacht, Sperre «veraltet» (Entscheid Daniel 20.11.)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt V3: Bahnhofregister»
- Anlass (20.11.): Zugehörigkeit Bahnhof → Plan/Region steht an 4 Orten (bahnhoefe.json, werkstatt/olten/region_olten.json,
  werkstatt/ne/region_ne.json, regionen/*/region.json – dort erst zur Laufzeit aus OSM); `regionen` ohne Eingabe rechnet nur mob;
  Neuchâtel/Onnens-Bonvillars doppelt (Werkstatt Olten + NE). Veraltete Pläne sehen in der Regression «unverändert» aus.
- Bauen: `spurplan/netz/bahnhoefe.json` (jeder Bahnhof einmal; Schlüssel **SBB-Abkürzung**, dazu **BPUIC**, atlas-Koordinaten,
  OSM-Station, Linien, Regionen, Quelle/Workflow, Code-Commit und Fingerabdruck des letzten Baus) – vom Workflow `seite` geschrieben.
  Daten: Release «vorbereitung» (`dienststellen`, `betriebspunkte` – liegen schon vor).
- Prüfung «OSM-Verdacht» (neue Karte auf der Seite, nur Befund, keine Sperre): atlas ↔ OSM > ~150 m, Name/Abkürzung abweichend,
  Linie/km der Betriebspunkte ≠ OSM-Linie, Gleise mit Perron SBB ≠ OSM, Betriebspunkt im Perimeter ohne Plan. Daniel entscheidet:
  OSM korrigieren oder Ausnahme (REGELN Ebene 6).
- Sperre «veraltet»: Plan mit älterem Code-Commit als `spurplan/code/` auf main → `seite` rot. `regionen`: bei Push auf
  `spurplan/code/**` alle Regionen nacheinander (mob, szu, vereina).
- Fertig: Register vollständig (alle ~150 Pläne), Karte OSM-Verdacht auf der Seite, Sperre greift im Test (alter Plan → rot).

### V4 – Neuchâtel in den gemeinsamen Bauweg (Entscheid Daniel 20.11., REGELN 0.9)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt V4: NE aus dem Code»
- Anlass: `region_ne.json` baut nur Ins (+ Vauseyon) neu, ~55 NE-Bahnhöfe sind Werkstatt-Stand Oktober – Regeln seit Mitte
  Oktober (K0, K0b, G0, Perron-Modell …) kommen dort nicht an. Widerspricht REGELN Abschnitt 5 («Abnahme = Basis, kein Einfrieren»).
- Vorgehen: in Teilen (je Linie) aus dem Code bauen, Regression je Teil; abgenommene Pläne, die nach Ebene 5 besser werden →
  Liste «Vorschlag: einfacher als abgenommen» mit Differenzbild (REGELN 0.9: kürzere Nebengleise, gleichmässigere Abstände
  erwünscht; Topologie und Hauptfahrwege dürfen sich nicht ändern). Dabei Messung W59 «kurze Nebengleise» (REGELN 5.9) bauen.
- Fertig: alle NE-Pläne aus dem Code, G0/HT grün, Seite veröffentlicht, Liste «einfacher» an Daniel.

### V4b – NE: Sperre G0 grün und veröffentlichen (aus V4, 20.11.)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt V4b: NE veröffentlichen»
- (1) seite-Lauf 0c47dd1: G0 rot nur `region_ne GT 4→5` – neue Treppe Neuchâtel-Vauseyon ← Les Deurres (Regionalplan ~ -752/-557;
  v158 lief die Linie leicht schräg gerade ein). Lokal nicht nachstellbar (lokal GT 0, auch die alten zwei Concise/Cressier fehlen –
  Numerik der Lage-Ausgleichung). Verdacht: Typvorlage-ports.json tragen jetzt `knoten/aus/ll` (verkettung.py nutzt sie) → andere
  Verkettung. Prüfen im Workflow (Log `region_ne_log.txt`), REGELN 4.5 (Versatz nur wenn sonst Kreuzung, sonst kippen).
- (2) Regression: 19 × «schlechter?». 17 Typvorlagen = Messartefakt: veröffentlichte alte Fassung hat den orangen Prüfkreis «W» an der
  Weiche, T7 zählt ihn als Anschluss (Gümmenen, Ligerz: Geometrie gleich) → T7 soll Prüfkreise ignorieren. region_ne G2 35→32, W53 8→10 erklären.
- (3) Liste «einfacher als abgenommen» (REGELN 0.9): W59 (5.9) misst, kürzt noch nichts. Höchste Werte: Cornaux 12, Onnens 12, Travers 5,
  Colombier 3 – Kürzung als eigener Code-Schritt, Daniel zuerst die Liste zeigen.
- Fertig: seite grün, Seite veröffentlicht (NE-Karten «aus Code»), offene NE-Hinweise pjyb/vpkw/zlwn angesehen. **Erledigt 21.11. (v160).**

### V4c – NE: HT-Befunde abbauen (aus V4b, 21.11.)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt V4c: NE HT»
- Anlass: 53 NE-Pläne seit V4 erstmals von HT gemessen; Ausgangsstand steht in `hauptgleis_basis.json` (80 Befunde). Zwei Arten:
  (a) **Messartefakt Typvorlage**: `vorlage.py` zeichnet die Weiche an der Standardstelle, `<b>_netz.json` (spurplan_schema) hat
  noch die OSM-Lage → Paar HT1+HT2 (Gümmenen, Sugiez, Muntschemier, Galmiz, Pensier …). Lösung: vorlage.py schreibt das Netzmodell
  mit (Weichen/Abzweige an der gezeichneten Stelle, OSM-Knoten bleiben). (b) **echt oder unklar**: Le Landeron (HT2 6, HT5 5),
  Riedbach (HT2 7), Colombier (HT3 3), Cornaux/Gorgier/Bevaix HT5 – je Plan ansehen, Zielplan an Daniel.
- Fertig: Basis NE sinkt (Artefakte weg), echte Fehler als Hinweis-Liste bzw. behoben, Seite veröffentlicht. **Erledigt 21.11. (v161).**
- **Stand 21.11. (V4c):** Artefakte weg (vorlage.py legt das Netzmodell auf den Plan, REGELN Kopf «HT»); St-Blaise CFF und Serrières
  korrigiert; Gampelen = Frage F6. **Rest Typvorlagen (lokal, 51):** Spurwechsel/Weiche am Planrand fehlt in der Vorlage – Rosshäusern
  (HT1 2, HT5 3), Bern Brünnen (HT1 2, HT5 2), Grandson (HT1 2, HT5 4), Ligerz/St-Blaise Lac/Avenches (je HT1 1); Fahrwege zu Gleisen mit
  Streckennummer (Gl. 501/652/709 …) – Gorgier (7), Le Landeron (5), Bevaix (3) erst ansehen, ob Ziel-Zuordnung oder echt; künstlicher
  Schnitt am Planrand Riedbach/Tüscherz/Zihlbrücke. **Nicht-Vorlagen NE:** Colombier HT3 3, Cornaux HT5 5, Travers HT2 3, Bôle HT2 2/HT3 1,
  Neuchâtel HT5 17, Vauseyon HT5 5, Auvernier HT5 4 – nächster Schritt V4e.
  **Nachmittag 21.11. (Daniel: F6 = A, «die anderen wie St-Blaise»):** Gampelen, Rosshäusern, Bern Brünnen, Grandson, St-Blaise Lac nach OSM;
  Typvorlagen 51 → 22. Rest: Avenches HT1 (Abstellschlaufe statt Stumpen), Ligerz HT1 (Messung: Abbildung quer je Seite fehlt),
  Bevaix/Gorgier/Riedbach/Tüscherz/Zihlbrücke/Bern Brünnen HT5 (Gleisziele, Planrand), Courtepin HT2.
  Regionalplan: Concise – Onnens lagen die Gleise 14 px aufeinander (G0 GG, numerisches Kippen nach den Vorlagen) → netz_lage `_cross`
  zählt Überlagerung (REGELN 4.5); dort bleibt ein kleiner paralleler Versatz → V4d. Seite v162 (ergebnisse ae4ef51). Regression
  «schlechter?» G2 +1 je Schutzstumpen = Messartefakt (Stumpen beginnt unter der Ausrundung, Bild gleich) – G2 soll ihn nicht zählen (V4e).

### V4e – NE: HT-Rest (aus V4c, 21.11.)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt V4e: NE HT-Rest»
- **Avenches zuerst (Daniel 21.11. abends, REGELN 3.6):** ohne Typvorlage aus dem Code, Override `cfg.s_max_fix` 3680 (Industriegebiet
  ~700 m östlich mit 5–6 Weichen kommt mit). Lokal: HT 0, aber G0 GS 1 (Gleis der südlichen Abstellanlage kreuzt Stumpen ohne Weiche,
  x 613/y 198) und GG 1 (31 px aufeinander, x 775/y 220) → Abstellanlagen-Regel im allgemeinen Code (REGELN 2.10 «fehlt», wie Solothurn
  0bw9). Daniel 21.11. sah dieselben zwei Stellen: Stumpen nach rechts soll VOR dem Gleis enden, das ins Hauptgleis
  hochgeht (kreuzt die Schräge), und «Miniknubbel» vor dem Pfeil nach unten ganz rechts (= GG). Erst mit G0 grün veröffentlichen. Bern Brünnen ohne Bümpliz-Nebengleis erledigt (v163).
  **Avenches erledigt 21.11. spät (v164)** – Nachtrag V4e. Weiter mit dem Rest unten (nächster Chat, gleicher Einstieg).
- **Stand 22.11. früh (v165):** erledigt Ligerz, Tüscherz HT1/HT2, Bern Brünnen, Auvernier, Colombier-HT5, Typvorlagen-Spurwechselpaare.
  **Rest NE (Seite v165):** Typvorlagen – Bevaix HT5 1 (Abgang Neuchâtel = Spurwechselweiche, Messung: Gl. 662 zwischen Weiche und Abgang),
  Gorgier HT2 1/HT5 2 (Gleisring Anschluss, Linien 512/513), Riedbach HT2 1/HT5 2, Tüscherz/Grandson/Riedbach je HT5 «künstlicher Schnitt»
  am Planrand, Le Landeron HT5 1, Zihlbrücke HT5 2, **Courtepin HT2 erledigt** (Industriegleis 705109983 hat in OSM keinen
  gemeinsamen Knoten mit der Strecke; Daniel 22.11.: das westliche Gleis ist nicht mehr angeschlossen (OSM-Spur 705109982/362102323, nicht gezeichnet – stimmt), das nördliche rechts (Richtung Courtepin) schon → Plan richtig, OSM-Lücke 1 m am Südende; Daniel 22.11.: Ausnahme, genutzte Anlage laut Satellitenbild → REGELN 6 «HT-Ausnahmen»). Nicht-Vorlagen – Chambrelien HT1 1
  (OSM-DKW 393419061 im Plan als zwei Weichen), Onnens HT1 1 (Spurwechsel 184779526), Colombier HT3 3, Cornaux 7, Travers 5, Bôle 3,
  Neuchâtel 19, Vauseyon 4, Murten 2.
- **Stand 22.11. vormittags (v167):** Typvorlagen NE alle HT 0 (Le Landeron, Gorgier, Riedbach, Grandson, Tüscherz, Bevaix, Zihlbrücke;
  Courtepin = Ausnahme). **Rest = nur noch Pläne mit «zeichnen»-Override** (Hand-Linien, die das Netzmodell nicht kennt → HT misst die
  Lage des Laufs): Chambrelien HT1 1/HT5 1, Onnens HT1 1, Colombier HT3 3, Cornaux 7, Travers 5, Bôle 3, Murten 2; dazu Neuchâtel 19 und
  Vauseyon 4 (eigener Bau). Vorschlag nächster Schritt: wie `vorlage.netz_mitschreiben` ein Netzmodell auf die zeichnen-Linien legen
  (OSM-Weichen an die gezeichneten Abzweige, Zusatz `weichen` erlaubt), dann je Plan echte Fehler von Messartefakten trennen.
  **Stand 22.11. abends (v169):** auch die Hand-Linien-Pläne NE HT 0 (Chambrelien, Onnens, Colombier, Cornaux, Travers, Bôle, Murten).
  **Rest V4e: nur Neuchâtel (HT3 2, HT5 17) und Vauseyon (HT2 1)** – beide aus dem Workflow `plaene` (nicht region_ne-Kette; `vorlage
  --weichen` läuft dort nicht). Nächster Chat: Neuchâtel ansehen (Abgänge Biel/Ins/Yverdon ↔ Gl. 5–7 und A42–A72 «im Plan, nicht in OSM»).
  Riedbach Anschluss-T geklärt (Daniel 22.11.: von Seite Bern erreichbar, Zurücksetzen Richtung Bern = OSM) → Vorlage `gegen` (v168).
  Prüffall vorlage_riedbach_90: HT2 gedreht nicht geprüft (Zuordnung Doppelspurwechsel Ost kippt nur gedreht) – ansehen.
  Daniel 22.11.: Seite eines neuen Gleises (oben/unten, Zihlbrücke) ist kein harter Fehler – wichtig ist Weiche da und Topologie richtig.
- **Erledigt 22.11. spät (v170): Neuchâtel und Vauseyon HT 0 – V4e abgeschlossen** (Nachtrag V4e Teil 5).
- Liste oben unter V4c «Rest». F6 (Gampelen) erledigt; dann je Plan OSM ansehen, Vorlage/Override nach OSM (REGELN 0.1),
  Vorher/Nachher an Daniel wie St-Blaise CFF. Fertig: NE-Pläne HT 0 oder als OSM-Ausnahme begründet.

### V4d – NE ruhig und Nebengleise kürzen (aus V4b, 21.11.)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt V4d: NE ruhig»
- Zielplan Regionalplan NE: S-Kurve Riedbach–Bern Brünnen (Hinweis pjyb), Knick vor Muntelier (vpkw), leichte S-Kurve vor
  Tüscherz (zlwn) – REGELN 4.5. Dazu W59-Kürzung (REGELN 5.9): Daniel 21.11.: **Onnens-Bonvillars kürzen** («eher zu lang»),
  **Cornaux nicht** («wirkt gut gedrängt», W59 misst dort Überlänge, die keine ist → Messung prüfen). Rest der Liste (Travers 5,
  Colombier 3; Rothrist 21, Thun 16, Zofingen 10) noch offen.

### K0b – Zwischengeraden Rest (aus K0, 19.11.)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt K0b: Zwischengeraden Rest»
- Code: `_zg_zusammenlegen` in `spurplan_schema.py` (vor `_BRAUN`), Zählung `code/zwischengeraden.py` (ZG < 2 Ebenen, ZL länger, HK Höcker).
- (1) Zweisimmen `jy8r` (mob__zweisimmen 326/182): Kette bricht am Wechsel dünn→dick (Verkettung nur innerhalb einer Klasse) – Klassengrenze
  auf die neue Schräge legen. (2) Solothurn `xke0`: Weiche am Knick → doppelter Abstand Gl. 2/3, Anschluss direkt aus der Schräge.
  (3) Selnau `j9ou` (ZL 866/147): nur wenn Daniel es will (Antwort auf der Seite). Konolfingen `0fzp` bleibt in S2b.
- Fertig: Zielpläne ohne ZG, G0/HT-Sperre grün, Seite veröffentlicht.

### T-SZU1 – DKW aus 4-Arm-Weiche und Güterverkehr schwarz (Entscheid Daniel 18.11. 14:43, REGELN 2.4/1.21)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt T-SZU1: DKW aus 4-Arm-Weiche und Güterverkehr schwarz»
- Anlass: Depot Giesshübel – Weichen 1263316996 (Arme 47°/57° ↔ 227°/237°) und 1263338286 (34°/41° ↔ 213°/221°) sind DKW-Form in
  einem Knoten, ohne `railway:switch`; der Code zeichnet sie als Weiche (Teil der OSM-Abgleich-Befunde Giesshübel: VD1 37, VB2 8,
  VC1 5, VB1 2). 717 Giesshübel–Wiedikon hat `railway:traffic_mode=freight`, ist aber grün (Code schaut nur auf service).
- Zielplan: **szu__zurich_giesshubel** – zwei DKW-Symbole im Depot, 717 schwarz mit schwarzem Pfeil «717 Zürich Wiedikon»
  (Ziel in `regionen/szu/region_lines.json` von «Zürich HB» auf «Zürich Wiedikon» korrigieren, Ort in orte.json ergänzen).
- Bauen (alle Pläne, kein Override): 4-Arm-Erkennung dort, wo DKW_3ARME/`dkw_auto` die OSM-DKW lesen (`spurplan_schema.py`);
  Güterverkehr in der Grün/Schwarz-Zuordnung (pax/Fahrwege, `verbindungen_pruefen` / `spurplan_schema`), auch netz_lage-Pfeilfarbe.
- Prüfen: Prüfstand-Baustein «dkw_4arme» (X-Knoten in allen Drehungen); alle Pläne: wo greifen die zwei Regeln sonst noch (Liste +
  Differenzbilder an Daniel, E9); G0-Sperre; OSM-Abgleich Giesshübel vorher/nachher nennen (nicht nur G0, Nachtrag 18.11. 14:35).
- Fertig, wenn: beide DKW im Plan, 717 schwarz, Seite veröffentlicht.

### T-SZU2 – Achse knickt im Fenster (Entscheid Daniel 18.11. 14:06: «C», REGELN 2.15)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt T-SZU2: Achse knickt im Fenster»
- Anlass (gemessen 18.11., OSM): Achse Giesshübel = Linie 712. Sie kommt aus Selnau mit Kurs ~215° und knickt 250–350 m südlich des
  Bahnhofs auf ~150° (Saalsporthalle). Depot/Abstellgleise (~1,7 km, 60–300 m SW des Bahnhofs) laufen mit 220–250° geradeaus weiter,
  713 geht nach W, 717 mit ~190°. Der Knotenplan mit Saalsporthalle hat ±1 km Fenster (`sw_search_m` 1009), der Knick liegt ganz drin.
  Gerade gezogen entlang der 712 schwenkt das Depot weg und läuft als Schrägen übers Bündel: Plan GS 11, GG 33, GQ 5; im Regionalplan
  zeigt der Sihltal-Abgang nach W und liegt nördlich des Uetlibergasts (REGELN 0.2/4.3).
- Zielbild: `spurplan/vergleich/szu/zielbild_giesshuebel.svg` (Skizze 18.11., von Daniel durchgesehen; Depot vereinfacht, DKW fehlen).
- Zielplan: **szu__zurich_giesshubel** – Achse = Einfahrt Selnau + Depot (gerade, ruhig), Sihltal 712 als Abzweig nach REGELN 2.6 Richtung
  Saalsporthalle, 713 als Abzweig nach Uetliberg; im Regionalplan Sihltal südlich, Uetliberg westlich. Zu Beginn Vorher-Ausschnitt +
  Skizze «so soll es aussehen» an Daniel.
- Bauen (für alle Pläne, kein Override, kein Regionen-Schalter): (1) Kursprofil der Achse im Fenster (je 100 m gemittelt), Knick > 30°
  erkennen; (2) Bündel = Gleise mit Kurs ±15° zueinander, Gesamtlänge im Fenster, längstes Bündel wird Achse; (3) abbiegende Linie als
  Abzweig/Abgang; (4) Lage/Drehung im Regionalplan aus der neuen Achse. Ort im Code zuerst suchen: Achswahl `topologie_linien.py`
  (`_axis.json`, «achse_durchgehend» 1.27), Spurplan `spurplan_schema.py`/`spurplan_warp.py`, Knotenpläne `straenge.py --knoten`.
- Prüfen: Prüfstand-Baustein «achse_knick» (Gerade mit Knick 30/45/60/75°, Bündel geradeaus) in allen Drehungen; G0-Sperre; alle
  136 Pläne: wo greift 2.15 sonst noch (Liste an Daniel, jede Änderung mit Differenzbild – E9); Unruhe SZU/MOB/Vereina nicht schlechter.
- Weichenfolge aus OSM (18.11., je Hauptgleis von Selnau Richtung SW; oben = NW-Gleis Y, unten = Perrongleis X): Spurwechsel X→Y
  (s 418–487), Spurwechsel Y→X (668–735, keine Schere), 717 mündet in Y Richtung NE (845), 713 ab Y nach SW (863), Depot ab Y (899),
  Spurwechsel X→Y (887–963), Depot ab Y (970), Depot zusätzlich ab 713; Saalsporthalle: Spurwechsel Y→X davor (1259–1326) und
  dahinter (1613–1725), Abstellgleis ab X (1733). Anschlussgleise an der 717: 41 westlich, 43 östlich (zwischen 717 und Hauptgleisen).
  Zielbilder nur aus dieser Liste zeichnen und die Liste mitgeben (Fehler der ersten Skizze 18.11.: Schere, Depot-Anschlüsse, Gl. 43).
- Danach aus der T-SZU-Arbeitsliste (Abschnitt 6) nur, was 2.15 nicht schon löst: 3 gegen 2 Gleise Selnau (V1/S1), S3 Adliswil↔Selnau,
  T5 Verbindungsgleis ohne Pfeil, Uetliberg 90° gedreht, Label Binz.
- Fertig, wenn: Giesshübel ohne Depot-Schrägen über dem Bündel (GS/GG im Plan deutlich unter 11/33, Ziel 0), Sihltal im Regionalplan
  südlich, 2.15 in REGELN «heute aktiv in» nachgeführt, Seite veröffentlicht.

### S2b – Konolfingen Gleisfeld West (Ebenen-Löser)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt S2b: Konolfingen Gleisfeld West»
- Zielplan **konolfingen**, Westkopf: Abstellgleise 53/54 + Stumpen 1689230917 liegen in OSM *über* der 430 von Steffisburg
  (d −24…−36 gegen −37…−55) und hängen über 1689230955 → Weiche 223385024 am Gleis zu Gl. 4 (nicht an 4694358196 Gl. 5/6).
  Heute VB2 bei 361/307 und 348/331, VC1 397/283, VD1 409/259 (Hinweis 3d6h; tnvp «Knubbel kurz gerade» gleiche Stelle).
- Befund S2: Die Weichenstrasse 33390862 + 606745360 (Gruppe, `home[n] = la + (lb-la)·f`) zieht den Trennknoten 1689230957
  (lane_guess −2,8) auf Ebene 2 (Gl. 5); die Abstellgleise bekommen lane_guess 0/1 → darunter, der Abgang Steffisburg kreuzt
  sie. Ansatz: Seitenabgang-Knoten nicht über Nebengleise legen, die nach d darüber liegen (Reihenfolge REGELN 0/Geografie),
  bzw. Ebene < 0 für den Trennknoten zulassen; 223385024 rechts von 1689230955 halten.
- **Zielbild Daniel 18.11. (Hinweis gnmh):** eine Diagonale 4→5, aus ihr geht waagrecht etwas weg, dann trennen sich 2×2
  Abstellgleise ab; die Diagonale liegt so, dass 4/5 nur eine Ebene auseinander sind und die Abstellgleise links ausserhalb
  des Gleises nach Steffisburg liegen. Dazu 2nht «alles weiter nach vorne Richtung Bern, 4/5 nur noch ein Gleisabstand»,
  8tp8 «Gleis von 4 und von 3 zu nah beieinander» (West bei 1689230812), 0fzp «Zwischengerade» bei 4694402472 (Gl. 6 → 76
  steigt zweimal), wvq1 «Prellböcke auch im Abstellbereich Ost (77/86/87) – Konsistenz über den ganzen Bahnhof» (Fenster
  Ost so weit, dass die Gleise mit Prellbock enden, REGELN 3.2).
- Mitnehmen: VD1 auf Gl. 3 bei 595/211 (Verbindung 156705005 läuft 49 px auf Gl. 3 bis Weiche 254421673 – Weiche an den Fuss
  der Schräge legen); VB1 1689230852 (Gruppe oben links). Hinweise 3d6h, tnvp, gojth (Gl. 1 keine Nummer, nicht grün), ezxj.
- Fertig, wenn: Konolfingen OSM-Abgleich ohne VB2/VC1, keine neuen V-Befunde anderswo, Seite veröffentlicht.

### R4 – Rothrist im Regionalplan aus dem Bahnhofplan (Wunsch Daniel 18.11.)
- Einstieg: «Weiter mit UEBERGABE.md – Schritt R4: Rothrist im Regionalplan»
- Daniel: «Bahnhofplan Rothrist ist sauber, wieso ist der Regionalplan anders (90 Grad, nicht angeschlossene Gleise, weniger
  gezeichnet) – wenn schon so detailliert Nebengleise drin sind, dann lass doch grad alle, so wie im Bahnhofplan» (Hinweis 1u2n).
- Befund 18.11.: Der Regionalplan nimmt `rothrist_regional_*` aus `werkstatt/olten/regional_rothrist/` (Variante 15.10., eigenes
  Fenster sw_search_m 1600, ohne Detail-Overrides, alle 8 Abgänge am Rand). Versuch Variante weg (region_olten.json
  «varianten» ohne regional_rothrist): Bahnhofplan erscheint mit allen Nebengleisen, aber die Linie 400 (Bern) verlässt ihn
  seitlich bei x≈510 – netz_lage schliesst diese seitlichen Ports nicht an, im Westen beginnen 2 Gleise lose. Darum
  zurückgenommen. Weg: seitliche Ports in netz_lage anschliessen (Lage «Abzweig #31 / Abgang 400 #40 / 450 #41» anpassen)
  oder im Bahnhofplan die 400 bis an den Rand führen; danach Variante löschen (eine Fassung je Bahnhof, REGELN 4).
- Fertig, wenn: Regionalplan zeigt Rothrist wie den Bahnhofplan, alle Gleise angeschlossen, Verkettung 0.

### S3 – Aarau Zwischengeraden
- Einstieg: «Weiter mit UEBERGABE.md – Schritt S3: Aarau Zwischengeraden»
- Zielplan **aarau** (Hinweise fmlk, vnyq; Messung MZ), mitprüfen Solothurn (xke0) und Zweisimmen (jy8r). W8 wirkt heute nur im
  Regionalplan zwischen den Plänen – in den Löser des Bahnhofplans bringen (Knicke mit kurzer Gerade zusammenlegen).
- Fertig, wenn: die Zwischengeraden in Aarau weg, Solothurn/Zweisimmen nicht schlechter, Seite veröffentlicht.

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

### 12.11.2026 ~22:20 – Schritt V1 abgeschlossen (Commit d5f52c5, Seite-Lauf 21:17 UTC)
- Neu `code/osm_abgleich.py` (Regeln VA1/VA2 DKW, VB1/VB2 Weiche↔Abzweig, VC1 falsch angebunden, VD1/VD2 Gleis/Perron auf Gleis,
  REGELN.md) im Workflow `seite` auf allen 63 Plänen mit Netzmodell → `ergebnisse/seite/osm_abgleich/`; Netzmodelle gepackt in
  `ergebnisse/seite/netz.tgz` (MOB/Vereina exportiert jetzt `region_lauf`). V-Regeln zählen in der Regression zur Topologie.
- Stand: VA1 10, VA2 6, VB1 54, VB2 76, VC1 11, VD1 50, VD2 1. Konolfingen trifft genau Daniels Stellen (DKW 254420784/1689231120/
  1689231106 fehlen, Abstellgleise über 430, Gleis unter Gleis). Linke Weichenstrasse Olten: VB2 = flache Kreuzungen → Schritt K.
- **Hinweis-Abdeckung 34/57** (vorher 17/57 gleiche Messung nur Regelprüfung; 26/61 alte Zählung): `code/hinweis_abdeckung.py`,
  Ergebnis `ergebnisse/seite/abdeckung.md`. Eingabe `spurplan/hinweise_offen.json` = offene Hinweise mit Anker – **jede Runde aus
  der Sammlung `feedback` neu schreiben**. Ungedeckt sind v. a. Perron-/Darstellungsfragen (P2a) und Zweisimmen/Montreux-Feinheiten.
- Lücken: Vereina (regionen nur mit `-f region=vereina`, nachgestartet), NE-Werkstatt (fest seit 21.10.) und Referenzen ohne
  Netzmodell → kein Abgleich bis N2. **Olten: 18 % der Netzmodell-Knoten liegen 1 Ebene neben dem gezeichneten Gleis** (Export in
  `spurplan_schema` folgt einer späteren Ebenenverschiebung nicht; betrifft auch Pin-Anker) → in V2 klären; Abgleich fängt es ab.
- Regression nach Vereina-Lauf 2/136 gleichwertig: region_vereina + vereina__sagliains = R1a-Stummel am Planrand (Vereina lief
  seit 7.11. nicht). Seite **nicht** veröffentlicht (live v146 zeigt sonst dasselbe) – beim nächsten Veröffentlichen mitnehmen.
- Für V2: jede Regel an `osm_abgleich` (Summe je Plan) und Abdeckung messen, nicht an G-Zählern. Antworten: ttv8, z6f2, 33fs, 3d6h, b3j5.

### 12.11.2026 ~23:35 – Fahrplan umgestellt auf «sichtbar zuerst»
- Daniel: in R1a–V1 hat sich sichtbar wenig verändert; Konolfingen-Überschneidungen, Sagliains-Unparallelität, Aarau-Zwischen-
  geraden «haben schon funktioniert». Grund: Regeln nur im Weg MOB/Vereina, W8 nur im Regionalplan, R1a-Stummel zielt auf 24 px.
- Neu S1 (Sagliains), S2 (Konolfingen), S3 (Aarau) vor V2/K; jeder Schritt mit Zielplan und Vorher/Nachher (Abschnitt 0).

### 13.11.2026 ~00:20 – Schritt S1 abgeschlossen, Seite v147 (Commit 08022dd, ergebnisse a473f9c)
- `_stub_buendel`: Soll-Querabstand der Schrägen = Abstand der Gleise vor dem Knick (|Δy| der Wurzeln, cfg `stub_buendel_davor`)
  statt fest `lane_px`. Sagliains-Portal: oberer Knick 7,6 px (= 13,2·tan 30°) statt 20 px versetzt, parallel 13,2 px.
- Neue Messung **QK** (`pruefstand_messen`): zwei Gleise knicken gemeinsam → Querabstand danach = davor; schliesst Spurwechsel-
  Treppen, Fächer und Zusammenführungen aus. F akzeptiert Pfeilpaare eines QK-Bündels. Auf allen MOB/Vereina-Plänen vorher nur
  Sagliains (Ziel), Klosters Selfranga (S-Kurve jxpf → R3a) und Montreux (Pfeilstelle → R3b).
- Bausteine `buendel_knick` (60°, 1 Ebene) / `buendel_knick_eng` (30°, 0,55 Ebene): vorher QK 2, jetzt nur Q 4 je Fall (= der
  0,55-Abstand selbst, offene Frage Abschnitt 4 – der Code zeichnet auch 4,5 m real so eng). Basis neu gesetzt (248 Fälle).
- Regression 2/136, beide gewollt: vereina__sagliains, region_vereina (Bündel Sasslatsch–Autoverlad parallel statt Trichter;
  dafür kleiner Bündel-Versatz am Tunnelportal = R1b-Verhalten → Kandidat für R3a). Nicht gemacht: Bündel-Knick im Löser/
  Regionalplan allgemein (gilt laut Daniel für jedes Bündel) – QK misst es überall, Code nur für Stummel.
- Lokal gerechnet zeigt Klosters Platz rechts «Landquart» statt «Davos» – auch ohne Änderung, im Workflow korrekt (lokales Artefakt).

### 13.11.2026 ~08:10 – Review nach S1, Entscheid «alle Bahnhöfe gleich»
- Prüfungen über alle 137 Pläne (v147): neu gezeichnet werden nur MOB/Vereina 57, Olten 14, Repo 4; NE 53 + Referenzen/fest 8
  ohne Code-Lauf und ohne V/G-Prüfung. QK echt: Olten, Region Olten 2, Vereina 2, Selfranga, Konolfingen, Montreux.
- Unruhigster Plan Region Olten (E+Z+QK+K 53, X 21, G 45) – in keinem Schritt Zielplan → bei K/R2 als Zielplan nehmen.
- Selbstkritik S1: Stummel mit 0,55 Ebene am Planrand widerspricht E5 (Randzone) – in V0 entscheiden lassen.
- Daniel: Regeln überall, alle Bahnhöfe gleich erstellen → neuer Schritt V0 vor S2; V2/N2/P2b danach in dieser Reihenfolge.

### 13.11.2026 ~22:40 – Entscheide Daniel, Karte «Fragen an Dani»
- Aufgehoben: P3/B18, Einfrieren, R8, E8-Stummel, Perron 110 px → REGELN 6, 5, 3.4, 2.12, 1.18. Bestätigt: 1.5 (Nebengleise enger), 2.5.
- Neu: Karte «Fragen an Dani» im Werkzeugkasten (`code/fragen_bauen.py`, `spurplan/fragen/`), Fragen F1–F4 = REGELN 7.2–7.5, F5 Konolfingen Ost.
- Seite v148 (ergebnisse 4eb30e2): Regression 0/137 geändert, Prüfstand = Basis.
- 16.11. v149: Karte «Fragen an Dani» war unlesbar (bauen.py `strip()` traf das erste eingebettete `<svg>`); Ausschnitte jetzt
  als Gruppe mit Beschnitt, `strip()` nur am äusseren `<svg>`. Regression: nur `fragen` geändert.

### 16.11.2026 ~06:00 – Fragen an Dani beantwortet
- F1–F5 je A → REGELN 1.3, 1.8, 1.10, 4.4, 4.5; Abschnitt 7 leer. F5: Konolfingen Ost richtig. Zusätze Daniel → Schritt S1b.

### 16.11.2026 ~06:50 – Schritt S1b abgeschlossen, Seite v150 (ergebnisse 453a3a6)
- Knubbel an Pfeil-Stummeln (REGELN 1.6): waagrechte «M…L…»-Stücke vor dem Kürzen als «M…H…» schreiben, sonst fand G6 sie nicht;
  G6 lässt einen Rest, der ganz auf einem anderen geraden Gleis liegt, weg (sonst Spitzkehre, Prüfstand sagliains K 0→2).
- Nebengleis-Abstand (REGELN 1.5, cfg `ebene_eng_laengs`, `build_ly`): voller Abstand nur, wo ein Personen-/berührtes Gleis längs
  neben der Nachbarebene liegt. Sasslatsch jetzt 0,55 wie Sagliains → Regionalplan gerade durchs Portal, kein Trichter.
- Regression 11/137, alle erklärt: Ziel vereina__sagliains (VB2 Portal weg; VB1 257/123 war vorher falsch dem Knubbel zugeordnet,
  Ast läuft 10 px auf dem Nebengleis = VD1, Kandidat R3a), sasslatsch, region_vereina; Nebengleise enger: Selfranga, Vauseyon
  (abgenommen, E9: gleiche Zählung), Konolfingen, Solothurn, Glion; region_ne G2 +4 = Prüfartefakt (Maske am Planrand Bôle–Auvernier,
  Bogen 16°→26° nach Verschiebung, optisch ausgerundet); region_mob T7 +1 = bestehende Glion-Treppe jetzt mitgezählt; fragen (vorher).
- Offen: kurze Verbindungen zwischen 0,55-Ebenen werden flacher (Selfranga ~52° statt 60°, REGELN 1.3) → zu R3b. Variante «ein Plan
  Sasslatsch–Sagliains» lokal: falscher Knoten, 6 T + 6 Verkettung → mit N1 (Fenster automatisch) neu prüfen.
- Lokal ≠ Workflow im Prüfstand: `/tmp/pruefstand_repo/spurplan/code` ist ein Symlink des ersten Laufs – vor Vergleichen löschen.

### 17.11.2026 ~05:35 – S1b-Korrektur, Seite v151 (Commit 49f4dfa, ergebnisse e60e301)
- Daniel: Vauseyon-Abstellgleis kam nicht mehr bis zum Prellbock (Fächer gestaucht). `ebene_eng_laengs` enger gefasst: über Weiche
  berührtes Nebengleis zählt wieder wie Personengleis (REGELN 1.5) – Vauseyon wieder = Abnahme, region_ne G2 39→35, Selfranga
  oben wieder voller Abstand; Sasslatsch/Sagliains/Portal bleiben wie S1b. Konolfingen-Überlappungen = S2 (seit v149),
  Glion = neuer Schritt G1 (seit v149; keine Spitzkehre, Korrektur Daniel).

### 17.11.2026 ~15:30 – Schritt B1: V0-Rest + G1 fertig, S2/S3 abgespalten (Commits 83c613b, 118f171, ab0586e, 9182f24)
- V0-Rest: `wuensche.py` W53/W55/W56 (REGELN 5) in `alle_plaene_pruefen` (Wunsch-Summe entscheidet «besser/schlechter»,
  Übersicht `regression/wuensche.md`); `overrides_liste.py` → `seite/overrides.md` (REGELN 6); Label «aus Code <Commit> <Datum>».
- G1 Glion: REGELN 1.27 (`topologie_linien` Achse läuft über Linienende ohne Umkehr weiter) + 1.26 (`ebenen_zum_stamm`:
  Nebengleis mit Weichenanschluss nur nach oben rückt unter das nächste überlappende Gleis). Erste Fassung ohne die zwei
  Bedingungen verschlechterte Solothurn (VB2/VD1) und Rothrist (G6) – Fallstrick: Ketten ohne Schräg-Anschluss nie bewegen.
- S2 Konolfingen: keine der LR-Regeln (dkw_auto, kreuzung_schnitt, haupt_fortsetzung, hauptgleis_funktion, spurgruppe_seite,
  randzone, r28e/f, r36b) ändert den Plan; r49 kostet DKW 1689230829 (VA1 +1). Ursache der drei fehlenden DKW: am Knoten zeichnet
  der Plan nur 2–3 Arme (`--dbg`: «DKW? 254420784 3», «DKW? 1689231120 2») – Arme der Diagonale 143221510/475716119 liegen an
  LATCUT/xs_over-Positionen statt am DKW-Knoten. Ansatz: Diagonalkette durch die DKW (R45) auch für OSM-getaggte DKW erzwingen.
- S3 Aarau: die Zwischengeraden (fmlk, vnyq) tragen in OSM eine Weiche (1799639073 auf Gl. 3 / Stumpen ab der Verbindung;
  390523657, 1799626775). r49 für alle (cfg-Versuch `zwischengerade_schraeg`) löscht diese Weichen (VB1 +3, VD1 +4) – verworfen.
  Ziel: eine durchgehende 60°-Schräge mit Abzweig aus der Schräge (wie Solothurn xke0), nicht Weiche weglassen.

### 17.11.2026 ~23:30 – Schritt S2 Konolfingen Ostkopf, Seite v153 (Commits a29a470, 8e0439c, 5750a22)
- OSM-Abgleich Konolfingen 12 → 6 (VA1 3→0, VB1 2→1, VB2 4→2); Prüfstand = Basis; Regression nur Konolfingen/Region besser.
- REGELN 2.4: R45-Kette endet an DKW mit Streckenabgang → Abgang setzt die Gerade fort (`r45_ende_abgang`, W8 lässt ihn aus);
  OSM-DKW mit < 4 Armen = Weiche (Daniel: 1689231106 «einfache Weiche»; Schema + osm_abgleich `dkw_osm_unvollstaendig`).
- REGELN 1.28 neu (`rand_flucht`): Nebengleis läuft an Verzweigung ohne Personengleis längs hinaus → nur Flucht-Gleis mit
  Pfeil, Knoten bleibt an Ort, r15 läuft nicht über DKW zurück, kein Fächer an der DKW (DKW 1689231120, Hinweise z6f2/8bce).
- REGELN 1.3 `r49_eng`: echter S-Bogen → volle 60°-Schräge, nicht an DKW (Hinweis 33fs). Erste Fassung (+2 px Toleranz)
  verschob Werkstatt-Pläne um 1–2 px, zweite ohne Personengleis-Bedingung änderte Rothrist/Zofingen – beides korrigiert.
- Regression (Seite ergebnisse a5284a5): nur Konolfingen besser und Region Olten (Rothrist-Regionalvariante West: Pfeile
  zurück → nach aussen, REGELN 1.28); Zofingen/Rothrist standen schon vor S2 in der Tabelle. Hinweise ttv8, z6f2, 8bce, 33fs
  behoben-Kandidaten; 3d6h beantwortet (→ S2b). Offen → S2b (Befund im Abschnitt S2b).

### 18.11.2026 ~07:30 – S2 Nachbesserung, Seite v154 (Commit e3f66cb, ergebnisse aa7f1b6)
- Daniel: Gl.-6-Schräge kreuzte die Schräge von Gl. 5 noch (yz3m) – mein Bericht «kreuzt nichts» war falsch (Pfad endete an
  223385037 links vom Knick). Neu REGELN 2.3 `r45_anschluss_gerade`; osm_abgleich 3. Zuordnung (Weichenstrasse). V-Summe 6.
- Rothrist-Regionalvariante → eigener Schritt R4 (Befund dort); neue Konolfingen-Hinweise → S2b.

### 18.11.2026 ~11:20 – Schritt G0 abgeschlossen (Commit 404ca61, ergebnisse 95b263b; Seite nicht neu veröffentlicht)
- Neu `code/grundpruefung.py` (REGELN «Grundprüfung als Sperre» im Kopf; Codes GS/GG/GQ/GP/GW/GT bei 0.1–0.6, 1.2, 1.14, 1.15,
  2.5, 2.7) – nur SVG; X/QK aus `pruefstand_messen`, T7-Treppe aus `ruhe`. Ausnahmen: DKW-Bögen, `railway_crossing` aus dem Netzmodell
  (≤ 9 px), weisse Lücke/Flügel, Gleis unter Gleisnummer-Schild, Einmündung mit Überstand, Einlauf ≤ 3 Ebenen (bleibt VD1).
- Workflow `seite`: Selbsttest + alle 136 Pläne → `ergebnisse/seite/grundpruefung/`, Spalte G0 in `regression/tabelle.md`, Schluss-
  schritt «Sperre G0» rot bei Zunahme gegen `spurplan/grundpruefung_basis.json` [plaene]. Workflow `pruefstand`: 456 Pläne [pruefstand].
- Basis: Pläne GS 124, GG 136, GQ 36, GP 52, GW 5, GT 54; Prüfstand GS 26, GG 2, GW 60, GT 149 (zwischengerade d90, Vorlage ±60°/a60
  = bekannte R2/R3-Befunde). Prüffälle `spurplan/grundpruefung_faelle/`: Konolfingen v153 GS 558/283 erkannt, v154 nicht.
- Fallstrick: Ausrundung als Ecke gibt Schein-Schnitte (Konolfingen 567/307) – Schnitt/Auflage auf der echten Kurve rechnen.
  Basel/Bern (fest) haben kaputtes Markup `</text<circle` – wird beim Einlesen repariert. Basis neu nur mit `--basis-aus`/`--basis-setzen`.

### 18.11.2026 ~12:20 – Schritt T-SZU abgeschlossen, Seite v155 (Commits 114156c, 1d587e8; ergebnisse 644a346)
- Neu `regionen/szu/` (Linien 727/712/713/717, keine Overrides). Code: Normalspur-Linien in `region_vorbereiten` (Spur aus den Linien,
  MOB/Vereina byte-gleich); Kreuzungsstelle aus zwei Streckengleisen → BP in der Mitte (REGELN 3.5, Borrweg); echtes Gleisende am
  bbox-Rand kein Abgang (REGELN 1.13, Uetliberg «Linie 713 ↑»). Abgangsziel Richtung Stadt = Zürich HB (Giesshübel < 0,004° von Binz).
- **Binz–Uetliberg: G0 0, Verkettung 0, nichts von Hand.** G0-Basis um szu__*/region_szu ergänzt (Ausgangsstand).
- Arbeitsliste T-SZU2 (alles im Knoten Giesshübel·Saalsporthalle bzw. HB–Selnau): (1) Depot-/Abstellgleise Giesshübel kreuzen
  das Bündel – Plan GS 11, GG 33, GQ 5; (2) 3 Gleise Giesshübel→Selnau gegen 2 in Selnau (V1, S1, T1/T3/T4); (3) Fahrbeziehung
  Adliswil↔Selnau nicht durchgehend (S3); (4) Verbindungsgleis nach unten ohne Pfeil (T5); (5) Lage: Sihltal-Abgang Adliswil
  liegt im Regionalplan nördlich des Uetlibergasts (Drehung Giesshübel 0°, REGELN 0.2/4.3), Uetliberg 90° gedreht (Stumpen
  senkrecht), Label Binz im Bündel; (6) Selnau·HB SZU Süd GQ 1, Plantitel «HB SZU Süd» aus Haltepunktname.

### 18.11.2026 ~14:10 – Entscheid Daniel zu Giesshübel: Variante C (REGELN 2.15)
- «Giesshübel ganz schief»: Ursache Achsknick 65° im Fenster, Depot geradeaus (Messung im Schritt T-SZU2). Daniel wählt C = allgemeine
  Regel statt Schnitt/Override → neu REGELN 2.15; Schritt T-SZU2 ausgeschrieben (Abschnitt 5). Noch kein Code.

### 18.11.2026 ~14:45 – Entscheide Daniel: 4-Arm-Weiche = DKW, Güterverkehr schwarz (REGELN 2.4, 1.21)
- Anlass Skizze Giesshübel: Hauptgleisfehler (Schere statt zwei Spurwechsel, Depot-Anschlüsse, Gl. 43 falsche Seite) – Skizze war
  ungeprüft; der OSM-Abgleich hatte am Code-Plan 52 Befunde, berichtet wurde nur G0. Neu Schritt T-SZU1 vor T-SZU2.
- 15:51 entschieden: Hauptgleis-Topologie immer korrekt (Seite, Fahrwege) → REGELN 0.1 + Kopf «HT», Schritt HT vor T-SZU1.

### 18.11.2026 ~23:55 – Schritt HT abgeschlossen (REGELN 0.1 / Kopf «HT»; Seite nicht neu veröffentlicht)
- Neu `code/hauptgleis.py`: HT1–HT3 = VB1/VB2/VC1 mit Hauptgleis (osm_abgleich gibt bei VB2 jetzt `farben` mit); HT4 Seite an
  OSM-Weichen (Äste auf ~35 m in OSM vs. Netzmodell-Lage); HT5 Fahrwege im gezeichneten Plan vs. OSM (Enden ↔ Linienenden im Plan
  per Zuordnung, Perrongleise über Nummernschild) + künstliche Schnitte am Planrand. OSM-Graph = ganze Ways zwischen den gezeichneten
  Knoten (Netzmodell-Stücke lassen Anschlussknoten aus), geteilte Ways (ID+2 Ziffern) auf den OSM-Way zurückgeführt, Stück zwischen
  zwei Abgängen = ausserhalb (Tecknau). Fallstrick: DKW-Klammern unterbrechen im SVG das durchgehende Gleis (Aarburg Gl. 2 647–657).
- Prüffälle `hauptgleis_faelle/` (Builder `code/hauptgleis_faelle.py`): Giesshübel aus Code, Wangen unverändert/ohne Spurwechsel/
  mit Schere/falsche Seite, je 0°/90° – Selbsttest bestanden; läuft in `seite` (Sperre) und `pruefstand`. Spalte HT in der Regression.
- Basis `hauptgleis_basis.json` (82 Pläne mit Netzmodell): HT1 44, HT2 64, HT3 10, HT4 5, HT5 267; 28 Pläne mit HT > 0 – Liste
  `ergebnisse/seite/hauptgleis/hauptgleis.md`, an Daniel zur Reihenfolge der Folgeschritte. Olten (HT5 176) nur stichprobenweise geprüft.

### 19.11.2026 ~14:35 – Neuer Schritt K0 (sichtbar) vor T-SZU1
- Daniel 19.11. (REGELN 1.9): zu lange nichts Sichtbares (seit v155 nur G0/T-SZU/HT). K0 = Ins im Regionalplan (Hinweis 1470, bisher
  unbeantwortet und in keinem Schritt) + Zwischengeraden im Bahnhofplan (REGELN 1.9; S3 und R2-Zwischengeraden gehen in K0 auf).

### 19.11.2026 ~15:55 – Schritt K0 abgeschlossen, Seite v156 (Commits 83a0dc2, 64a3fa4; ergebnisse 148d254)
- Ins (Hinweis 1470): Meterspur setzte am gemeinsamen Knoten (override knoten_x 559,9) 2,5 px neben dem Ende der Rollbock-Schräge an;
  neu fängt der Code das Ende der gezeichneten Normalspur (REGELN 2.12, cfg `ms_anschluss_fang`). G0-Basis region_ne GQ 0→1 bewusst
  (Schräge jetzt durchgehend → derselbe GQ wie im Bahnhofplan ins; GQ in Ins selbst offen).
- Zwischengeraden (REGELN 1.9): `_zg_zusammenlegen` verkettet Teilpfade zu Gleisen, legt Schräge–Gerade(< 2 Ebenen)–Schräge gleicher
  Richtung ohne Weiche/Gleisende/Nummer zu einer mittigen 60°-Schräge zusammen; Enden auf dem Durchgangsgleis nur bis zur Ausrundung
  (sonst G0 GG). Neu `code/zwischengeraden.py`, Bericht `ergebnisse/seite/zwischengeraden.md` im Workflow seite. ZG 14 → 10
  (Aarau 4 → 0; Rest: Bern/Basel fest, Prüfstand 4, Zweisimmen 1 → K0b). Aarau G0 GT 5→1, Region Olten GT 10→6.
- Regression v156: 4 Pläne geändert – aarau/region (gewollt, nur Aarau-Stellen im Differenzbild); zofingen/rothrist unverändert
  seit 17.11. (Abstand zur Abnahme, nicht K0). Lokal geprüft: in Region Olten ändert die Regel ausser Aarau keinen Plan.

### 20.11.2026 ~17:35 – Schritt K0b gerechnet (Commits 5fe545e, f5763a3, 0d1deb2; Seite noch nicht veröffentlicht)
- REGELN 1.9 erweitert (cfg `zg_klassen`, `zg_cbogen`, `zg_abzweig`): Verkettung über dünn↔dick (Grenze in die Mitte der neuen Schräge,
  Zweisimmen jy8r), steiler S-Bogen (C) zählt als Schräge, Weiche am Knick → Abzweig direkt aus der Schräge (Solothurn xke0).
- Kettenende, wo der dicke Fahrweg über ein dünnes Gleis weiterläuft: nicht kürzen und Schräge an dieses Ende rücken (sonst Lücke
  bzw. G0 GG Solothurn); nur dann, sonst mittig (erste Fassung verschob Aarau – behoben).
- Regression 0d1deb2: 5 geändert – solothurn (gewollt; G2 3→4 = Abzweig ohne Ausrundung aus der Schräge, so gewünscht),
  mob__zweisimmen/region_mob besser (W53 −1, Wunsch −14), zofingen/rothrist alt (17.11.). G0-Sperre grün. ZG 10 → 9.
- Offen: Veröffentlichen (Daniel fragen), Hinweise jy8r/xke0 danach beantworten. Selnau j9ou (ZL ~4 Ebenen): Frage an Daniel
  mit Skizze im Chat 20.11. – bei «Ja» `zg_max_ebenen` nur für Gleiswechsel ohne Perron/Nummer auf 4,5 anheben (beide ZL Selnau).

### 20.11.2026 ~19:15 – Seite v157 veröffentlicht (ergebnisse be95332); Selnau → neuer Schritt K0c
- v157 = K0b (Live war = v156). Hinweise jy8r/xke0 beantwortet. Die drei roten seite-Mails 16:43–17:00 = G0-Sperre auf 5fe545e (behoben).
- Daniel 20.11. zu Selnau j9ou: «ja – der Fehler ist aber, die zwei Gleise dort sollten parallel sein». Ursache: OSM teilt beide
  Gleiswechsel in zwei Ways ohne Weiche dazwischen; die Mittelstücke wurden ein eigenes Gleis (eigene Ebene) und drückten Gl. 1/2
  auseinander. Neu REGELN 2.2 / cfg `r34_kette` (nur zwischen Streckengleisen mit Personenverkehr; Konolfingen sonst GQ +1).
  Lokal: Selnau parallel, direkte Schrägen, G0 GQ 1→0, ZL Selnau 2→0.
- **K0c (offen, Schalter vorerst aus):** seite-Sperre rot mit `r34_kette` an (Lauf 17:54 UTC): (1) Selnau HT5 0→1 «Abgang 712
  Adliswil ↔ Gl. 1 fehlt» – vermutlich Messfehler: Nummernschild «1» rückt neben den Perron links der Gleiswechsel, HT sucht den
  Plan-Weg nur zur Kante am Schild (OSM: alle Kanten des Gl.-1-Stücks) → in `hauptgleis._fahrwege` Plan-Ziel = alle grünen Kanten
  des Nummerngleises, oder Schild rechts der Wechsel; (2) Giesshübel GS 11→12 (R34k-Kette 110676791/302538635 im Depotknoten) –
  prüfen, ggf. Kette dort ausnehmen. Dann Schalter an, `regionen` für **szu und vereina** von Hand (Standard nur mob!).
- Hinweis: `regionen` ohne Eingabe rechnet nur **mob** – nach Code-Änderung szu/vereina einzeln starten (`-f inputs[region]=szu`).

### 20.11.2026 ~20:15 – Entscheide Daniel: Register, OSM-Prüfung, kartographische Freiheit
- Neue Schritte V3 (Register mit SBB-Abkürzung/BPUIC/Koordinaten, OSM-Verdacht, Sperre «veraltet») und V4 (NE aus dem Code) vor
  K0c; V5/V6 (ein Lauf, Netz West) danach. «Einfacher darf Ziel sein» → REGELN 0.9 und 5.9.

### 20.11.2026 ~20:50 – Schritt V3 abgeschlossen, Seite v158 (Commits 5e32a01, ce5b16c; ergebnisse bb5df3c)
- Neu `code/bahnhofregister.py` (REGELN Kopf «VR», 6): Register `netz/bahnhoefe.json` (180 Abk., 144 Pläne; Commit/Fingerabdruck in
  `ergebnisse/seite/register/register.json`), vom Lauf `seite` nur bei Änderung auf main geschrieben. Daten: Release «vorbereitung».
- Karte «OSM-Verdacht und Herkunft» (Werkzeugkasten): 26 Befunde – OG 5 (Neuchâtel 3–7, Ins 3/4, Aarau 10, Konolfingen 2, Binz 2),
  OU Ligerz, OR Aarau Torfeld, OL Solothurn, OK 2 (RhB-Autoverlad), OB 16 (u. a. Trimbach, Triemli, HB SZU); MF 4 (Neuchâtel,
  Onnens, Kerzers, Vauseyon mehrfach). Daniel: je Befund A/B → `netz/osm_ausnahmen.json`.
- Sperre VR: `seite` rot, wenn Plan aus Code älter als `spurplan/code/`; `netz/veraltet_basis.json` = 58 feste Pläne (fällt mit V4/N2/P2b).
  Live bewiesen: zwei Läufe auf 5e32a01 rot, weil sie Repo-/Regionspläne vor dem Push von plaene/regionen sahen → «wartet», solange
  ein weiterer seite-Lauf ansteht (ce5b16c). `regionen` rechnet bei Push auf `spurplan/code/**` alle Regionen (Standard jetzt alle).
- Befund: Thun/Ins/Murten/Kerzers sind Dateien vom 26./27.10. (`werkstatt/olten/reg`), standen als «aus Code» → Label «fest seit».

### 20.11.2026 ~23:15 – Schritt V4 Teil 1: NE-Bauweg (Commits d979b78, 0c47dd1; Seite nicht veröffentlicht, G0 rot)
- `region_ne.json` baut alle 54 NE-Bahnhöfe (vorher nur Ins); Kette = run.sh inkl. Typvorlage und `viewbox_text` (Travers-Text war abgeschnitten).
- REGELN 4.11: px-Ausnahmen wandern mit dem Warp (`PXW`, `<b>_warp_bezug.json` = Oktober-Warp, 19 Orte; nicht Ins/Kerzers, die seit Okt. gebaut
  werden). Anlass Auvernier: Linie 219 endete 82 px vor Gl. 3. Fallstrick: `spurplan_check` überschreibt Plan **und ports.json** → Kette sichert sie.
- bauen.py: NE-Karten aus dem Bau («aus Code · NE-Bauweg»), Gruppe/Status aus zusatz_plaene.json. `veraltet_basis` ohne NE (bleiben Basel, Bern, Referenzen).
- 13 Pläne geändert (Auvernier, Bevaix, Bôle, Chambrelien, Colombier, Cornaux, Marin, Onnens, Riedbach, Travers, Twann, Murten, Ins) – alle Topologie
  gleich, Differenzbilder angesehen; Typvorlagen byte-gleich. W59 (REGELN 5.9) gemessen, Gewicht 0. Rest → V4b.

### 21.11.2026 ~11:55 – Schritt V4b abgeschlossen, Seite v160 (Commit 16ca65c, ergebnisse 476a7bc)
- Treppe Les Deurres → Vauseyon: Auslöser war Murten (Abgang Fribourg 19 px verschoben → Netz 4 px verschoben → Vauseyon-Port
  auf der anderen Seite der Portgeraden, Kandidat «Knick am Schnittpunkt» fiel weg). Neu REGELN 4.5 `schraeg_port`: Ende ≤ 8°
  neben der Portgeraden → schräge Gerade, Knick am Port. Lokal nachstellbar (lokal = Workflow). Wirkung: NE nur Vauseyon, Olten
  gleich, Vereina 1 Stelle ruhiger (Sasslatsch-Abzweig eine Gerade bis zum Portal). Bisektion: `netz_lage.py` direkt in /tmp/region_ne (5 s).
- T7 (ruhe.py) zählt den orangen Prüfkreis nicht mehr als Anschluss → Regression 18 → 1 «schlechter?» (Bôle W56 6→7, aus V4 bekannt).
- Sperre HT wäre ebenfalls rot gewesen: 53 NE-Pläne erstmals gemessen → Ausgangsstand in die Basis (wie HT-Einführung 18.11.) → V4c.
- Hinweise pjyb/vpkw/zlwn beantwortet (Stellen noch da) → V4d. Abnahmen unverändert (69).

### 21.11.2026 ~13:20 – Schritt V4c abgeschlossen, Seite v161 (Commits b440c7a … c0aa2bb, ergebnisse dab114d)
- Ursache Paar HT1+HT2 in Typvorlagen: Netzmodell aus dem allgemeinen Lauf, Vorlage zeichnet anders. Neu `vorlage.netz_mitschreiben`
  (REGELN Kopf «HT»): Weichen reihenfolgetreu an die Abzweige (Abgänge + Perronmitte als Stützpunkte), OSM-Spurwechsel zwischen zwei
  Weichen ergänzt (fehlten im Netzmodell → falsche HT5), Lauf-Fassung `<b>_netz_lauf.json`. Fallstrick: `spurplan_check` in
  region_olten_lauf überschrieb das Netzmodell wieder → wird jetzt mit gesichert (wie ports.json).
- 42 Typvorlagen HT 159 → 51 (lokal; HT5 findet jetzt fast alle Ziele, darum in 6 Plänen HT5 höher – erstmals gemessen, kein Rückschritt).
- Sichtbar: St-Blaise CFF beide Spurwechsel Seite Biel, Serrières Spurwechsel Seite Neuchâtel (je HT → 0, abgenommene Pläne, Differenzbild an
  Daniel). Gampelen → Frage F6. Prüffälle `hauptgleis_faelle/vorlage_*`. G0 unverändert.

### 21.11.2026 ~22:45 – Schritt V4e Teil 1: Avenches, Seite v164 (Commits f3871dc, e240519, dad7a31; ergebnisse 930d990)
- Avenches ohne Typvorlage: `s_max_fix` 3680 (Industriegebiet Ost), `d_lim_neben` 110 (Abstellanlage Süd ~100 m neben der Strecke ganz mit
  Prellböcken – vorher zwei gleiche Pfeile aufeinander = GG/«Miniknubbel»), Gleisnummern 1/2 per `gleise`/`nummern` (REGELN 3.6). G0 0, HT 0.
- Neu REGELN 2.10 `_stumpf_vor_schnitt`: Stumpfgleis endet 8 px vor einem Schnitt ohne Weiche (GS weg); nicht an Weichen-/Kreuzungsknoten,
  R45-DKW, `dkw_px`, höchstens 3 Ebenen kürzen. Erste Fassung kürzte Rothrist (durch das DKW-Feld, ~600 px), Zofingen (EKW) und Montreux –
  korrigiert; im Endstand ändert die Regel nur Avenches. Regionalplan NE: Avenches länger, Linie Murten–Payerne gestreckt (Domdidier rückt).
- osm_abgleich Avenches VB1 1 (Weichen 1975565327/…332 im Plan an einem Punkt; vorher fälschlich dem Schnitt zugeordnet) – keine Sperre.
- Rest V4e unverändert (Liste unter V4c «Rest» / Nicht-Vorlagen). Abnahmen unverändert (69).

### 22.11.2026 ~07:00 – Schritt V4e Teil 2, Seite v165 (Commit b38a85c, ergebnisse 713dd2b)
- Doppelter Spurwechsel der Typvorlage: zweite Weiche begann 8 px VOR dem Ende der ersten (Reihenfolge am gemeinsamen Gleis vertauscht)
  → `vorlage.SW_GAP` 28 px, kurze Gerade dazwischen (REGELN 2.2). Sichtbar: Bevaix (dazu `richtung` steigend wie OSM), Bern Brünnen, Riedbach,
  Tüscherz, St-Blaise CFF. Fallstrick: links verschob es auch einfache Spurwechsel – nur bei «anzahl 2».
- Ligerz: Doppelspurbeginn `seite` oben (OSM: durchgehend ist das südliche Gleis) + Abstellgleis als `linie`; dabei Fehler in vorlage.py
  (doppelspurbeginn oben: `ys.insert(0)` verschob die Indizes, Schräge fehlte) behoben.
- vorlage.netz_mitschreiben: Weichen je Gleis reihenfolgetreu (Tüscherz HT1+HT2 weg). hauptgleis HT5: mehrteilige Perrongleise (OSM track_ref
  über mehrere Ways, z. B. 652/662) im Plan über alle ihre Kanten auf derselben Geraden (REGELN Kopf HT) – nur Abnahmen von Befunden, alle Pläne.
  Prüffälle `vorlage_bern_brunnen`, `vorlage_tuscherz`. HT gesamt HT1 48→46, HT2 74→73, HT5 296→271, Basis gesenkt (17 Pläne). G0 unverändert, Abnahmen 69.
- Regression: geänderte Zeilen alle erklärt (SW_GAP, Ligerz-Override, Messung); region_ne G2 43→36, Ligerz und Riedbach im Regionalplan.
- Lokal ≠ Workflow: Ins HT5 2 nur lokal (Lage-Numerik), Workflow 0. Werkzeuge: OSM-Skizze längs Fensterachse war hilfreich (nicht im Repo).

### 22.11.2026 ~10:20 – Schritt V4e Teil 3, Seite v167 (Commits 0037b08, 4cf5457; ergebnisse 9fb85fd)
- NE-Typvorlagen HT 0 (Basis gesenkt: bevaix, gorgier, grandson, le_landeron, riedbach, tuscherz, zihlbruecke). HT gesamt 40 → 33 Pläne > 0.
- Messung (REGELN Kopf HT): Abgang ohne `aus_ll` bekommt die Richtung vom Plan-Schwerpunkt weg (Le Landeron/Gorgier/Riedbach: Spurwechsel
  am Rand galt als Fahrweg). vorlage.netz_mitschreiben: Knotenfolge je Gleis (Gorgier 512, Bevaix 662), künstliche Schnitte des Laufs auflösen
  (Grandson/Riedbach/Tüscherz), Zusätze `weichen` (Gorgier Ring, Tüscherz, Zihlbrücke) und `abgaenge_knoten` (Zihlbrücke). Pläne byte-gleich.
- Sichtbar: Zihlbrücke Doppelspurbeginn Ins nach OSM oben (Gl. 234 nach Norden). Regionalplan zeigte eine veraltete Oktober-Datei
  «zihlbrucke» (Umlaut-Slug) → netz_lage sucht ae/oe/ue zuerst (REGELN 4.11); Treppe Zihlbrücke–Gampelen weg.
- Prüffälle vorlage_le_landeron/gorgier/riedbach (0/90°), vorlage_zihlbruecke_0 (90° scheitert am Testaufbau: Gleis-«y» wird nicht gedreht).
- Regression: keine neue Zeile «schlechter?» (die 6 sind älter, bekannt); G0 unverändert. Abnahmen nicht neu exportiert (keine neuen seit V4e Teil 2).
- Fallstrick: lokaler Lauf (region_olten_lauf) schreibt in werkstatt/ne – vor dem Commit zurücksetzen (Numerik lokal ≠ Workflow).
- Nachtrag 12:15 (v168, ergebnisse 15c82c8): Riedbach Anschluss-T nach OSM (Daniel), Vorlage `gegen` (REGELN Kopf HT). Prüfstand-Lauf 738d349 rot (Prüffall riedbach_90), mit 6947437 behoben.

### 22.11.2026 ~17:20 – Schritt V4e Teil 4, Seite v169 (Commits cb6414d, 42ddfe6; ergebnisse 66b75bc)
- Sichtbar: Chambrelien – Gl. 2 mündet vor dem Abzweig 224 ein (vorher am selben Punkt = V, im Plan nicht befahrbar), Gl. 3 mündet in die
  Weiche 393419063 (endete 12 px davor). Übrige Hand-Linien-Pläne waren richtig gezeichnet, nur falsch gemessen.
- REGELN Kopf HT «Hand-Linien»: `vorlage.py --weichen` (zeichnen.weichen, zeichnen.netz_ergaenzen) in region_olten_lauf.kette; Messung:
  Abzweig mit geradem Vorstück, DKW als Weichenpaar, Teilungspunkte aus allen Berührpunkten, Gleisziel = Mitte.
- Fallstrick: erste Fassung ergänzte OSM-Verbindungen in allen zeichnen-Plänen -> Olten HT1/3/4 neu (seite rot, cb6414d); jetzt nur auf Wunsch.
  Messänderungen über alle 135 Pläne alt/neu verglichen (`hauptgleis.py --alle` auf ergebnisse/seite/plaene + netz.tgz): nur Abnahmen,
  ausser Giesshübel HT3 -> HT2 an derselben Kreuzung (Basis bewusst). HT gesamt 46/70/15/5/261 -> 33/55/9/5/233, Basis gesenkt (17 Pläne).
- Prüffälle zeichnen_chambrelien/murten/cornaux/onnens_bonvillars (0/90°). G0 unverändert.

### 22.11.2026 ~20:55 – Schritt V4e Teil 5 (Abschluss), Seite v170 (Commits f3b6319, d42f0b0; ergebnisse 33d9692)
- Sichtbar (nur Bahnhofplan Neuchâtel, Ostkopf): 35567630 (Biel unteres Gleis) kreuzt die Linie nach Ins an der EKW 109 gerade und läuft
  als Abstellgleis weiter (Pfeil) – vorher mündete die Schräge ins Gleis nach Ins (Fahrweg Biel -> Ins, den OSM nicht hat). Hand-Linie im
  Override (`zeichnen`), Kreuzung auf OSM-Knoten 416784002 (G0 GS). Regionalpläne unverändert (Region NE nutzt das kürzere Werkstatt-Neuchâtel).
- Übrige 19+1 Befunde = Messung (REGELN Kopf HT, Nachtrag 22.11. abends): `vorlage --weichen` jetzt auch in `lauf.py` (Neuchâtel `netz_ergaenzen`),
  Kette endet an Kreuzung (OSM-DKW 58/63 = Kreuzung + 4 Weichen), Kreuzung geradeaus = OSM-Fortsetzung (flache EKW), Perrongleis-Kante auf
  seiner Geraden, DKW-Bogenweiche unter DKW-Symbol kein HT1, Regel-39b-Stummel (Vauseyon, Netzmodell `angedeutet`) kein HT2.
- Alle 135 Pläne alt/neu gemessen: nur Neuchâtel, Vauseyon (-> 0) und Solothurn HT5 15 -> 14; Basis HT und G0 (Neuchâtel GG 3 -> 1) gesenkt.
  Prüffälle `zeichnen_neuchatel` (HT1 nur 0°, Testaufbau), `neuchatel_vauseyon`. Fallstrick: erster seite-Lauf nach Push lief vor `plaene` -> rot, später grün.
- Offen fürs Auge: Neuchâtel im Regionalplan NE ist noch die Werkstatt-Fassung (Fenster ohne Ostkopf) – REGELN 4.x «Regionalplan wie Bahnhofplan».

### 22.11.2026 ~21:30 – Nachtrag V4e: EKW 109 mit Symbol, Seite v171 (Commit e1446b5, ergebnisse d457c93)
- Daniel: «bräuchte ein EKW-Symbol, man sieht nicht, dass von Ins abgebogen werden kann» → `dkw_px` mit einer Klammer (Ins Ost ↔ Abstellgleis).
  Messung: Symbol mit einer Klammer = EKW, nur geradeaus + diese Bogenfahrt (REGELN Kopf HT / 2.4); OSM-Bogenweiche mit 3 Armen zählt für VA2.
  Alle 135 Pläne gemessen: nur Neuchâtel ändert (VA2 4 -> 0). HT 0, G0 grün.
- Daniel: «der Teil fehlt im Regionalplan völlig» – stimmt: Region NE nutzt `werkstatt/ne/neuchatel_*` (Fenster ohne Ostkopf, eigener
  Override), nicht den Bahnhofplan aus `plaene`. → neuer Schritt **V4f** (Fahrplan): Neuchâtel im Regionalplan aus dem Bahnhofplan
  (wie Vauseyon als `repo_bahnhoefe`), Nachbarfenster Saint-Blaise/Serrières prüfen (T13), Zielbild Ostkopf mit EKW im Regionalplan.

### 23.11.2026 ~09:45 – Schritt V4f abgeschlossen, Seite v172 (Commit 43a3919)
- Sichtbar: Regionalplan NE zeigt Neuchâtel wie den Bahnhofplan – Ostkopf mit Spurwechsel, EKW 109 (Symbol) und Abstellgleis-Pfeil.
- Umsetzung: `region_ne.json` `repo_bahnhoefe` + «neuchatel» (wie Vauseyon), REGELN 4.11 ergänzt. Ports gleich aufgebaut (2 West, 3 Ost), nur
  weiter östlich → keine Lage-Anpassung nötig. Werkstatt-Dateien `werkstatt/ne/neuchatel_*` (spurplan, warp, override …) sind jetzt unbenutzt;
  `neuchatel_fenster.json` bleibt für T13 der Nachbarn (Fenster West unverändert, Ost 3 km vor St-Blaise CFF → kein Konflikt).
- Regression: nur region_ne (G2 30→32 = G2 des Bahnhofplans Neuchâtel, bestätigt 8.11.); Nachbarn verschieben sich als Block (Plan länger),
  Gampelen ohne die zwei Knicke (ruhiger), Biel-Linie um 0.1° gedreht. G0/HT grün, Topologie T1–T6 0. netz_lage meldet neu eine
  Überlappung der Rahmen St-Blaise Lac/CFF (nur Rechtecke, im Bild getrennt). Abnahmen unverändert.

### 23.11.2026 ~10:40 – Schritt V4d Teil 1, Seite v173 (Commit 6f56298, ergebnisse 8eb3e4d)
- Sichtbar (Regionalplan NE): S-Kurve Riedbach – Bern Brünnen (pjyb) und Twann – Tüscherz (zlwn) weg – Ursache je ein Gleisabstand Versatz,
  weil Doppelspur-Bahnhöfe das Achsgleis zufällig wählten (Gl. 1 oder 2). Neu `kette_paarung` in lage_auto.py (REGELN 4.5): Achsgleis passend
  zum Nachbarn der Kette. Regionalplan NE G0 GT 4 → 0. Olten/MOB/Vereina/SZU unverändert.
- Onnens-Bonvillars kürzer (Daniels Wahl): cfg `leer_max` 150 in spurplan_warp.py (REGELN 5.9), Plan 1820 → 1446 px; Kette Yverdon rückt nach.
  W59 misst jetzt nur leere Länge (Cornaux 12 → 0, Onnens 6 → 2); NE-Rest: Avenches/Colombier/Galmiz/Travers je 1.
- vpkw Muntelier: Knick vor der 60°-Weiche (Linie Sugiez kommt ~80°) – Rückfrage an Daniel: (A) Knick nach Sugiez, (B) Abzweig flacher.
  Versuch A über `seiten_richtung` (Gewicht 10) verzog Galmiz (V-Form), Versuch «Einmündung gerade» in place() verschob Sugiez – beide verworfen.
- Regression: geändert durch V4d nur onnens_bonvillars (G2 1→2, W56 5→2, W59 6→2) und region_ne (Block-Verschiebungen um ~5 px); G0/HT ohne Zunahme.
  Die übrigen «schlechter?» (Grandson, Chambrelien, Avenches, Gorgier, Bôle, Le Landeron, St-Blaise Lac) sind ältere Stände vs. Archiv-Abnahme.

