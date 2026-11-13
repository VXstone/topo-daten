# Regeln für die Spurpläne

**Einzige Quelle seit 13.11.2026.** Das Doc «Regelwerk Spurpläne» (Stand 25.10., mit Regelkatalog-Entwurf 24.10.), die
chronologische Fassung `REGELN_ARCHIV_bis_2026-11-13.md` und die Übergabe-Archive sind nur noch Geschichte: Anlass und
verworfene Ansätze stehen dort, gelten tut, was hier steht. Neue Entscheide von D. Eckenstein kommen **hier** an die passende
Stelle der Hierarchie (nicht unten anhängen), Datum ins Feld «seit».

## Wie dieses Regelwerk funktioniert

**Hierarchie (Ebenen).** Ein Plan entsteht aus der Grundform (Ebene 1) und den Mustern, die der Code im Ort findet (Ebene 2).
Was nur von der Grösse abhängt, regelt Ebene 3, das Zusammensetzen zur Region Ebene 4. Es gibt **keine Bahnhofstypen mit
eigenen Regeln** und **keine Regeln je Workflow**: jeder Plan wird mit demselben Code und denselben Regeln erzeugt
(Entscheid 13.11.). Ein Knoten ist ein Ort mit vielen Mustern plus der Grössen-Schwelle aus Ebene 3.

**Regel oder Wunsch.**
- **Regel** = hart. Hat eine Prüfung; ein Befund ist ein Fehler. Eine Code-Änderung darf eine Regel nie verletzen, auch nicht
  in abgenommenen Plänen.
- **Wunsch** = Gütemass (Ebene 5). Hat eine Messzahl, kleiner ist besser. Der Code **darf** Pläne verändern, um Wünsche zu
  verbessern – auch abgenommene –, solange keine Regel verletzt wird (siehe «Vergleich», Ebene 5).
- **Ohne Prüfung** steht «Sicht» (nur Sichtkontrolle durch Daniel) oder «fehlt» (Prüfung noch zu bauen).

**Rangfolge bei Konflikten:** Grundsätze 0.1 → 0.8; innerhalb einer Ebene gilt die speziellere Regel nur, wo sie ausdrücklich
«Ausnahme zu …» sagt. Widersprüche, die noch nicht entschieden sind, stehen in Abschnitt 7 – bis zum Entscheid gilt der
höhere Grundsatz.

**Felder je Regel:** Nr (Ebene.Nr) · Regel · Auslöser (wann sie greift; leer = immer) · alt (frühere Nummern) · Code (Datei/cfg)
· Prüfung · heute aktiv in. «heute aktiv in» zeigt die Lücke zum Entscheid 13.11.: **alle** = in allen Wegen, die neu rechnen
(Linien-Regionen MOB/Vereina, Olten-Werkstatt, Repo-Bahnhöfe); **LR** = nur Linien-Regionen (`region_lauf.py`); **O** = nur
Olten-Werkstatt; **Reg** = nur Regionalplan. Ziel (Schritt V2): überall «alle». Nicht neu gerechnet werden heute die
NE-Bahnhöfe (fest seit 21.10., Schritt N2), Basel/Bern (P2b), Thun/Ins/Murten/Kerzers (Referenzen) und die Blaupausen.

---

## 0. Grundsätze in Rangfolge

| Nr | Grundsatz | Art | alt | Prüfung |
|---|---|---|---|---|
| 0.1 | **Topologie stimmt:** jedes Gleis hängt dort an, wo es real anhängt; keine Schein- oder fehlenden Verbindungen, keine Gleissprünge, kein Gleis endet im Leeren. Farbe gehört dazu (grün = im Personenverkehr befahrbar). | Regel | G1, T1, E1 | T1–T8, V/S, VA–VD, G7, PS «T» |
| 0.2 | **Reihenfolge wie die Karte:** was klar nördlich (östlich) liegt, liegt im Plan nicht südlich (westlich); Querreihenfolge der Gleise wie real. Abstand, Winkel und Drehung sind frei. | Regel | G2, N1, L1 | L2, L3 |
| 0.3 | **Jede Weiche ab Hauptgleis sichtbar**, mindestens als Pfeil – auch in grossen Knoten, einzeln. | Regel | G3, B9, S1 | VB1, W |
| 0.4 | **Keine 90°:** Verbindungen 60° mit Ausrundung; Ausnahme Tunnelportal, Brückenflügel. | Regel | G4, R4, R5 | G2, G3, G4 |
| 0.5 | **Abstand:** parallele Gleise im Ebenenabstand; parallel bleibt parallel im gleichen Querabstand, in jeder Drehung, jedem Abgangswinkel und durch jeden gemeinsamen Knick. | Regel | G5, B2, 6.11., 12.11. | Q, P, QK, E, F (siehe 7.1) |
| 0.6 | **Ruhe:** gerade so lange wie möglich; keine Treppen, keine unmotivierten Ecken, keine S-Kurven. | Wunsch (Ebene 5) | G6, R10, 4.11. | T7, Z, E, QK, Ebene 5 |
| 0.7 | **Detailgrad:** kleine Bahnhöfe ganze Anlage, grosse Knoten Hauptgleise + jede Weiche als Abgang. | Regel | G7, B16, B17 | Sicht |
| 0.8 | **Darstellung:** Symbole, Beschriftung, Kompaktheit. | Regel/Wunsch | G8 | Ebene 1.F, 5 |

---

## 1. Grundform – gilt für jeden Plan

### 1.A Gitter und Geometrie
| Nr | Regel | Auslöser | alt | Code | Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 1.1 | Gleise waagrecht auf Ebenen (24 px); Verbindungen 60°, eine Figur bleibt zwischen ihren Weichenpunkten. | | B1, W2 | spurplan_schema | PS «D» (Drehung) | alle |
| 1.2 | Ausrundung überall: Weichen, Pfeilstummel, Einmündungen, Gleisenden (7 px, DKW-Ketten 10 %). | | R5, W3, B8 | spurplan_schema `_rund_stub` | G2, G3 | alle |
| 1.3 | Einheitlicher Winkel: alle Diagonalen einer Anlage gleich (60°), nicht variieren, um Platz zu gewinnen. | | V1 | dkw_auto | fehlt | LR |
| 1.4 | Gleisabstand: Hauptgleise 1 Ebene; Gleise zweier Doppelspuren je 1 Ebene, zueinander 1 oder höchstens 2 Ebenen. | | B2, A1, R1c | `buendel_kompakt` | Q | alle |
| 1.5 | **Ausnahme zu 0.5:** Nebengleise zueinander enger (55 %, bei Platzmangel bis 40 %); voller Abstand, sobald ein Hauptgleis über eine Weiche berührt. Grund: Pfeile in Anlagen werden später durch die richtigen Anlagen ersetzt (bestätigt 13.11.). Lange parallele Nebengleise wie Sagliains (Autoverladgleis) sind selten, dort eher OSM-Unschärfe. | Nebengleis neben Nebengleis | B2, A2, 7.1 | spurplan_schema | Q – **anpassen**: gegen die erlaubte Ebene prüfen | alle |
| 1.6 | Stoss oder Gleisende > 1 px neben dem Nachbargleis ist ein Fehler; kein Knubbel (gerades Stück über den Anfang einer Ausrundung hinaus). | | E7, A3, W9 | | G6, G7 | alle |
| 1.7 | Kein Gleis deckt ein anderes (> 12 px deckungsgleich); kein Perron auf einem Gleis. | | E4, A5 | | VD1, VD2, G8 | alle |
| 1.8 | Kein Gleis wechselt die Ebene ohne Weiche oder Werfung; keine Badewanne (Mulde ohne Weiche bleibt oben, wenn frei). | | F11, F10 | `f10` | E, PS «E» | alle |
| 1.9 | Zwischengeraden zwischen zwei Spurwechseln entfallen (Gleise rücken zusammen), ausser dazwischen liegt ein Gleis mit Perron oder Nummer. | | B7, F7 | spurplan_schema | Z, F7 | alle |

### 1.B Planrand und Abgänge
| Nr | Regel | Auslöser | alt | Code | Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 1.10 | Streckengleise verlassen den Plan im Standardabstand: gleiche Linie oder Gleis ohne Liniennummer 1 Ebene, verschiedene Linien 2 Ebenen. | Streckengleis am Rand | E5, A4, Randzone | `randzone`, a4_rand | planrand_pruefung | **LR** (Randzone), alle (a4) – Widerspruch 7.2/7.3 |
| 1.11 | Streckengleis nach der letzten Weiche läuft auf seiner Ebene gerade aus dem Plan; nicht im parallelen Bündel, wenn ein Nachbar schräg bleibt. | | R33b, F4 | spurplan_schema | E | alle |
| 1.12 | Abgang mit Liniennummer und Richtungsort (näherer Ort; hat ein anderer Abgang schon den Ort, der andere Ort der Linie). | | B10, Z2 | exit_town, linienenden.json | T | alle |
| 1.13 | Abgang mit Pfeil nur, wenn das Gleis ≥ 300 m weitergeht oder zu Bahnhof/Anschluss führt; echtes Gleisende → Stumpen mit Prellbock. | | T12, «echte Gleisenden» | `gleisenden` | T5 | LR (Gleisenden), alle (T12) |
| 1.14 | Pfeile zeigen nur nach aussen, nie auf ein Nachbargleis (< 1,5 Ebenen); sonst kurzer Stumpen richtig gezeichnet, nie ersatzlos löschen. Pfeilspitze ≥ ½ Ebene neben jedem Gleis. | | 4.11., A6 | `pfeil_aussen` | fehlt | **LR** |
| 1.15 | Schräg den Plan verlassende Gleise, die nebeneinander knicken, behalten quer den Abstand von davor (Knickversatz d·tan(θ/2)). | Bündel knickt | 12.11. (S1) | `stub_buendel_davor` (nur Stummel am Rand) | QK | alle (nur Stummel) |
| 1.16 | Weichen bis 150 m hinter einem seitlichen Abgang als kurzer Stummel auf der Abgangsschräge. | | T15, R39b | spurplan_schema | – | alle |

### 1.C Perrons und Nummern
| Nr | Regel | Auslöser | alt | Code | Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 1.17 | Jeder Perron aus OSM/SBB wird gezeichnet (≥ 3 m), mindestens 40 px, nie über Gleise oder Weichenbögen; Lage dort, wo seine Gleise liegen; an mehreren Gleispaaren je Paar ein Balken; beidseitige Perrons bleiben. | | B13, P1, 4./5./6.11. | `perron_frei`, `perron_abschnitt`, `perron_teile`, `perron_beidseitig` | P1, PF | **LR** (ausser beidseitig) |
| 1.18 | Perronlänge **80 px** für alle Pläne, Gleisnummer in der Perronmitte (13.11.: 110 px aufgehoben). | | B14, Z1, 5.11., 7.6 | `perron_standard_px` | fehlt | LR 80 / sonst noch 110 (V2) |
| 1.19 | Perronformen: Querperron an Kopfgleisen als U oder L um die Gleisenden. | Kopfgleise mit Querperron | 8.11. | – (P2a) | PF | fehlt |
| 1.20 | Gleisnummern: SBB-Perronkanten > SBB-Perronflächen > OSM; nur Gleise mit Perron; Halt mit einem Gleis ohne Nummer; fehlt sie überall «?». `ref` in Gleisnummernform ist ein Gleis, keine Linie. | | R6, E10, D11, 6.11. | gleisnummern_sbb, `gleisnummer_aus_ref` | G1 | alle (MOB: aus_ref aus) |

### 1.D Farbe und Inhalt
| Nr | Regel | Auslöser | alt | Code | Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 1.21 | Grün = im Personenverkehr befahrbar (aus den Fahrwegen): Gleise ohne service, Perrongleise, Durchfahrgleise beidseitig am Streckengleis (auch siding, nicht yard); sonst schwarz; schwarz unter grün. | | B3, E1, D3, R1 | verbindungen_pruefen | E1-Prüfung | alle |
| 1.22 | Meterspur/Schmalspur braun (dick Strecke/Perrongleis, dünn Nebengleis), auch Perrons, Prellböcke, Pfeile, Nummern; Dreischienengleis grün mit braun gestrichelt. | | Z4, 4./6.11. | spurplan_schema | Sicht | alle |
| 1.23 | Stillgelegtes (disused) nicht zeichnen; Bushalte sind keine Perrons. | | R7, D6, 5.11. | | fehlt | alle |
| 1.24 | Hauptgleis aus Funktion: Perrongleis, Fortsetzung eines endenden Streckengleises bis zum Perrongleis, oder Kette usage=main/branch zwischen zwei Streckengleisen ist Hauptgleis; an der Weiche läuft das Hauptgleis weiter (Perrongleis vor Nebengleis). | | 3.11., `haupt_fortsetzung` | `hauptgleis_funktion`, `haupt_fortsetzung` 0.15 | fehlt | **LR** |
| 1.25 | Gleis bleibt Gleis: gerades Gleis mit Ebenenwechsel an den Enden behält ≥ 40 px bzw. 35 % seiner Länge. | | 3.11. | `gleis_mindestlaenge` | fehlt | **LR** |

---

## 2. Muster – greifen, wo der Code sie im Ort findet

Jedes Muster hat einen Prüfstand-Baustein (`pruefstand_bausteine.py`) und ein Soll-Bild; auf der Seite soll je Plan stehen,
welche Muster erkannt wurden (V0).

| Nr | Muster | Regel | alt | Code | Baustein / Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 2.1 | Weiche | zweigt ab wie real (Seite, Richtung, stumpf/spitz); Reihenfolge entlang des Gleises wie real | R2, R3, V6, T2, T3 | spurplan_check «F», `r38_seite` | VC1, fehlt (Reihenfolge) | alle |
| 2.2 | Spurwechsel | eine 60°-Diagonale; auf freier Strecke nur im geraden parallelen Stück, einzeln, nicht ineinander; Nebengleise zweigen nie im Spurwechsel ab; crossover zwischen zwei Streckengleisen ist immer Schräge | R11, R12, N7, F6, T7, Randzone | `verbindung_schraeg` | G5, r5_halt | alle |
| 2.3 | Weichenstrasse | Diagonale läuft zum entferntesten Gleis durch, die näheren zweigen ab | B6, F5 | spurplan_schema | fehlt | alle |
| 2.4 | DKW / EKW / Schere | OSM-Elemente < 20 m, die ein Gleis kreuzen = DKW mit Symbol an Ort, liegend, Klammern in den stumpfen Winkeln; Kette durch DKW eine gerade 60°-Linie; Durchschneidung mittig zwischen zwei Diagonalen | E3, B8, V2–V4, T5, W4 | `dkw_auto` | VA1, VA2, Montreux-Westende | **LR** |
| 2.5 | Kreuzung ohne Verbindung | Lücke im unteren Gleis nur bei Niveautrennung (bridge/tunnel/layer), Brücke mit Flügeln, Tunnel nur Lücke; gleiche Ebene beide durchgezogen; Werfung = Ebenenwechsel unter/über der Kreuzung (bestätigt 13.11.) | B19, T4, 6.11. | `kreuzung_schnitt`, netz_lage `_kreuzungen` | X, unterwerfung (Schritt K) | LR (Bahnhof), Reg |
| 2.6 | Abzweig / seitlicher Abgang | ausgerundet unter 60°; ein Abzweig läuft höchstens eine Achse parallel und geht dann weg; parallele Abgänge bleiben parallel | B11, W5 | spurplan_schema | ab30, ab60 (Schritt A2) | alle |
| 2.7 | Bündel knickt | parallele Gleise knicken gemeinsam, Querabstand danach = davor (Ausfahrten, Spurwechselpaare, Abgänge, Stummel) | 12.11., IDEEN «Bündel als Einheit» | nur Stummel: `stub_buendel_davor` | buendel_knick, QK | alle (nur Stummel) |
| 2.8 | Gleisdreieck | kein fester Standard: Darstellung mit der meisten Ruhe nahe der Geografie (eine Achse, Zulaufstrecke teilt sich auf zwei Schenkel ≤ 90°, ausgerundet) | 3.11. | knoten.json | Sicht | alle |
| 2.9 | Kreuzungsbahnhof zweier Linien | im Regionalplan X: je Linie eine gerade Achse, Kreuzung unter 60° in der Mitte | N2, W7 | Override «seitlich» | W1 | O (Kerzers) |
| 2.10 | Anschluss-/Abstellgleise | jede Weiche nach OSM, zusammengedrängt, ohne Längenmassstab | E6, D2, (B16 widerspricht – entschieden: E6) | | fehlt | alle |
| 2.11 | Kopfgleise / Stumpfgleise | endet daneben (< 30 m) ein weiteres Gleis: Kopfbahnhof, keine fehlende Weiche; nie bei Gleis mit Nummer oder auf anderer Ebene | R27b | spurplan_schema | – | alle |
| 2.12 | Meterspur neben Normalspur | Meterspur wird gezeichnet wie Normalspur (eigene Pläne, Regionen); bis ~40 m neben Normalspur in deren Plan mitgenommen. «Im Regionalplan nur als Stummel mit Ziel» aufgehoben 13.11. | E8, D9 | `meterspur_cfg.d_max` | – | alle |
| 2.13 | Schiebebühne | Depotgleise mit gemeinsamem Anfang ≥ 40 px, Bühne gestrichelt | 4.11. | `schiebebuehne` | – | **LR** |
| 2.14 | Tunnelportal | Klammer nur, wo alle Gleise gerade und parallel (±18 px); ausnahmsweise 90° | 4.11., R4 | netz_lage | – | alle |

---

## 3. Knoten-Zusatz – nur was von der Grösse abhängt

| Nr | Regel | Auslöser | alt | Code | Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 3.1 | Grosser Knoten: nur Hauptgleise + jede Weiche in die Anlage einzeln als Abgang | grosse Nebengleisanlage (Olten, Bern, Basel, Däniken RB, RB Limmattal, Buchs SG, Weyermannshaus; nicht Olten Hammer) – **Schwelle aus OSM fehlt** | B17, D1 | `--hauptgleise` (von Hand) | Sicht | O, Basel/Bern fest |
| 3.2 | Planfenster: jede Weiche, an der ein Strang des Betriebspunkts beginnt, liegt im Plan; Fenster bis zum Abzweig, wenn Gleise sich ≤ 1 km hinter dem Rand trennen; endet, wo das Fenster des Nachbarn beginnt | | T11, T13, 3.11. | straenge `anker_m`, `fenster_streckenende` | V1–V3, S1–S3 | LR (vollständig), sonst `s_min_fix`/`s_max_fix` von Hand |
| 3.3 | Knotenpläne: Pläne nur an ruhigen Stellen schneiden (≥ 500 m ohne Weiche); nahe Betriebspunkte teilen einen Plan (≤ 2500 m); Halte ohne Weiche schneiden nie | | 3.11., T9 | straenge `--knoten` | – | **LR** |
| 3.4 | Jeder SBB-Betriebspunkt ist in einem Plan enthalten (eigener oder gemeinsamer Knotenplan, 13.11.: «eigener Plan je Betriebspunkt» aufgehoben); ein Abzweig mit Weichen ist nie nur ein Knick | | R8, R14, T8 | | O2 | alle |
| 3.5 | Kreuzungsgleis (beide Enden auf demselben Streckengleis, ≤ 600 m) gehört samt Weichen zum näheren Betriebspunkt | | 5.11. | `kreuzungsgleis_m` | V1/V2 | **LR** |

---

## 4. Region – Zusammensetzen der Pläne

| Nr | Regel | Art | alt | Code | Prüfung | aktiv |
|---|---|---|---|---|---|---|
| 4.1 | Verkettung: Pfeile/Abgänge kommen beim Nachbarplan an; Gleise zwischen zwei Plänen nach Strang verbunden, nie oberstes mit oberstem | Regel | 29./30.10., 3.11. | verkettung.py, netz_lage | V1–V3, S1–S3, T2–T4 | alle Regionen |
| 4.2 | Ein- und Zweispurwechsel erkennt der Code selbst; überzählige Gleise münden unter 60° ein | Regel | N5, W6, 29.10. | | V1 | alle Regionen |
| 4.3 | Reihenfolge wie die Karte (0.2): Paare ≥ 1,5 km auf der Karte, Umkehr ab 60 px ist Fehler; gleiche Höhe erlaubt; grob parallele Linien nur Seite quer zur gemeinsamen Richtung; Achse > 60° neben der Karte nur Hinweis | Regel | L2, L3a, 5.11. | lage_pruefung | L2, L3 | alle Regionen |
| 4.4 | Bahnhof liegt so, dass die Strecken am geradesten anschliessen, dann nach Kartenachse; Drehung frei (je Planseite eine Stimme), leicht gekippter Bahnhof ok | Wunsch | N2, L3, 3./4.11. | lage_auto, lage_suche | Unruhe | LR (Suche) |
| 4.5 | Zwischen zwei Bahnhöfen eine gerade Strecke ohne Treppen; durchgehende Gleise einer Reihe auf Gleishöhe | Wunsch | N3, N4, F2, F3 | `gerade_kette`, `kipp_max` | T7 | alle Regionen – Widerspruch 7.4 |
| 4.6 | Bündel zwischen zwei Plänen: parallele Pfeilpaare als Bündel verbunden, ein nötiger Versatz gilt fürs ganze Bündel | Regel | R1b | `buendel_andocken`, `pfeile_buendel` | QK, T7 | alle Regionen |
| 4.7 | Nebengleise und Spurwechsel auf freier Strecke bleiben im Regionalplan | Regel | R9, D7 | | Prüfung 4 | alle Regionen |
| 4.8 | Bündel so legen, dass möglichst wenige Gleise kreuzen; echte Über-/Unterwerfung darf kreuzen | Wunsch | N6, F8 | | X | alle Regionen |
| 4.9 | Streckenlänge gestaucht (c0 + c1·km^p), Halte ≥ 60 px und gleichmässig über die Strecke verteilt | Wunsch | N10, F9, 4.11. | lage_auto | T8 | alle (gleichmässig: LR) |
| 4.10 | Perimeter = Vieleck; alles darin wird gezeichnet | Regel | N11, D10 | | fehlt | alle Regionen |

---

## 5. Wünsche – Gütemasse, die der Code verbessern darf

Ein Wunsch ist kein Fehler, sondern eine Messzahl je Plan (kleiner = ruhiger). **Neu 13.11. (D. Eckenstein):** der Code darf
Pläne verändern, um diese Zahlen zu senken – auch abgenommene –, und der Vergleich wertet das als Verbesserung.

| Nr | Wunsch | Messung | Gewicht | Stand |
|---|---|---|---|---|
| 5.1 | Keine Treppen (hin und zurück ohne Anschluss dazwischen) | T7 Treppe (ruhe.py) | 8 | gemessen: Bahnhofspläne + Regionen |
| 5.2 | Keine unmotivierten Ecken (Knick > 8° mit kurzen Schenkeln, ohne Weiche/Gleiszahländerung) | T7 Ecke, Z | 4 | gemessen |
| 5.3 | **Weniger S-Kurven** (zwei Gegenknicke auf einem durchgehenden Gleis, auch über Planränder) | E, F3, neu: S-Kurve über Pläne | 6 | E gemessen; Regionalplan **fehlt** |
| 5.4 | Parallele Bündel durch Knicke (QK) | QK | 6 | gemessen (alle Pläne) |
| 5.5 | **Gleichmässiger Bahnhofsabstand** im Regionalplan: Abstand je Strecke proportional zur gestauchten Distanz, Streuung klein | neu: Varianz px/gestauchte km je Region | 3 | **fehlt** |
| 5.6 | **Kurze Bahnhöfe:** Planlänge je Inhalt (Weichenachsen, Perrons) nahe am Median vergleichbarer Pläne; Anlass Onnens-Bonvillars, Rothrist, Tecknau | neu: px je Weichenachse, Abweichung zum Median | 3 | **fehlt** |
| 5.7 | Wenige Kreuzungen ohne Bauwerk | X | 2 | gemessen |
| 5.8 | Lage nahe an der Karte (Drehung, Achse) | L3a | 0 (Hinweis) | gemessen |

**Vergleich (Regression) – neue Einordnung:** ein geänderter Plan ist
- **Fehler**, wenn eine Regel neu verletzt ist (Topologie, V-, T-, G-Befunde) – egal was sonst besser wird;
- **besser**, wenn keine Regel neu verletzt ist und die Wunsch-Summe sinkt → Differenzbild an Daniel als «Vorschlag: wurde
  besser», er bestätigt kurz (Vorgabe 6.11.); bei abgenommenen Plänen nimmt er neu ab;
- **gleichwertig**, wenn Regeln und Wünsche gleich bleiben → Differenzbild ansehen (Fallstrick: neu erfundene Weiche);
- **schlechter**, wenn die Wunsch-Summe steigt → nur mit Begründung im Nachtrag.

E9 (abgenommene Pläne dürfen sich nur ohne Topologieänderung ändern) bleibt und ist hier enthalten. **Abnahme = Vergleichsbasis, kein Einfrieren** (13.11.): auch abgenommene und bisher feste Pläne (NE, Basel, Bern, Referenzen) werden aus dem Code erzeugt; der Vergleich zeigt «besser» oder «Fehler».

---

## 6. Ausnahmen je Ort

**Entscheid 13.11.:** Overrides nur für Ortswissen, das nicht in OSM/SBB-Daten steht (z. B. Perronlage Galmiz) – nie für Geometrie oder Topologie; keine Handzeichnung (alt P3 «zuerst Override je Bahnhof», B18 «Handzeichnung, wo die Automatik scheitert» aufgehoben). Ausnahmen sind Daten, keine Regeln: `spurplan/bahnhoefe/*_override.json`, `regionen/*/region.json` (Optionen je Bahnhof),
Werkstatt-Overrides Olten/NE. Jede Ausnahme nennt Regel und Grund; Ziel ist, dass die Liste schrumpft (Hauptgleisweichen,
Topologie und Perronlage nie per Override, Vorgabe Daniel). Bekannte Einzelentscheide: Olten Ost 60° gedreht (E12),
Galmiz Perron südlich / Kreuzungsgleis grün, Rothrist Detailvariante (E11), Kerzers X.
**Fehlt (V0):** Liste aller Overrides mit Regel und Grund.

---

## 7. Offene Widersprüche – Entscheid Daniel

Entschieden 13.11. abends: 7.1 (→ 1.5) und 7.6 (→ 1.18). Offene Fragen stehen mit Bild auf der Karte «Fragen an Dani» (`spurplan/fragen/fragen.json`).

| Nr | Widerspruch | Vorschlag Claude | Entscheid |
|---|---|---|---|
| 7.2 | 1.10 Randzone (Gleis ohne Liniennummer am Rand 1 Ebene) gegen 1.15/S1 (Sagliains-Stummel verlassen den Plan mit 0,55 Ebene) | 1.10 gilt nur für Streckengleise; Nebengleis-Bündel behalten ihren Abstand | offen – Frage F1 auf der Karte «Fragen an Dani» |
| 7.3 | 1.10 Randzone erzeugt vor dem Rand absichtlich einen Ebenenwechsel ohne Weiche – 1.8 verbietet das (Prüfung E) | Randzone als ausdrückliche Ausnahme zu 1.8; E zählt sie nicht | offen – Frage F2 auf der Karte «Fragen an Dani» |
| 7.4 | 4.5/R10 «Knicke nur am Bahnhof» gegen Versatz auf der Strecke (R1b-Bündelversatz, «ein Versatz ≤ 30° in der Mitte», `schraeg_max` 8°) | Versatz auf der Strecke nur, wenn sonst Gleise kreuzen; sonst Bahnhof kippen (≤ 8°) | offen – Frage F3 auf der Karte «Fragen an Dani» |
| 7.5 | 1.3 einheitlicher 60°-Winkel gegen r49 «zu eng für 60°: volle Schräge», `kipp_max` und leicht schräge Strecken (P meldet sie) | 1.3 gilt im Bahnhofplan; Kippen und Schrägen nur im Regionalplan, P dort mit Toleranz | offen – Frage F4 auf der Karte «Fragen an Dani» |

---

## Anhang: alte Nummern

Alte Nummern (B, N, E, R, V, F11, Regelkatalog T/L/S/W/A/F/D/Z/P) stehen in der Spalte «alt»; Prüf-Kürzel (G1–G8, T1–T8,
V-, S-, L-Befunde, Prüfstand Q/P/QK/F/K/Z/E/X/T/PF/D) bleiben die Namen der Prüfungen. Vollständige Herleitung:
`REGELN_ARCHIV_bis_2026-11-13.md`, Doc «Regelwerk Spurpläne» (Tabs «Untitled» und «Regelkatalog (Entwurf 24.10.)»).
