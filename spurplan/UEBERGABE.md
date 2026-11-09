# Übergabe Spurpläne – Stand 9.11.2026 abends

Kurz halten. Gelesen wird **nur diese Datei**, und zwar Abschnitt 0 + der eigene Schritt in Abschnitt 5. Verlauf und
Begründungen stehen in den Archiven – nur gezielt mit `grep` lesen, nie ganz:
- `UEBERGABE_ARCHIV_bis_2026-11-06.md` – Override-Schlüssel und ihr Anlass, Regeln bis 6.11.
- `UEBERGABE_ARCHIV_2026-11-06_bis_11-09.md` – Schritte A, 0, M, E, P1, 1, R1 Teil 1 im Detail (Montreux-Westende, DKW, Prüfstand-Befundliste).

Nachträge: am Ende eines Schritts **höchstens 10 Zeilen** in Abschnitt 6 und den Schritt in Abschnitt 5 abhaken.
Wird Abschnitt 6 länger als ~60 Zeilen, die ältesten Nachträge ins Archiv verschieben.

## 0. Arbeitsweise (gilt in jedem Schritt)
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

## 3. Stand (9.11.2026, Commit 1120d6a, Seite live v142)
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
- [ ] **R1a Regression R1 Teil 1 abschliessen** (klein)
- [ ] **R1b Bündel docken an** (mittel)
- [ ] **A2 Abzweigende Doppelspur** (mittel, Topologie)
- [ ] **K Kreuzungen und Werfungen** (mittel; nimmt R2-Teil Unterwerfung auf)
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
