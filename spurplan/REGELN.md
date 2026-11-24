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

**Grundprüfung als Sperre (G0, seit 18.11., Entscheid D. Eckenstein «nicht überschneiden, paralleler Abstand etc. sollten
funktionieren»).** `code/grundpruefung.py` prüft jeden Plan der Seite und den Prüfstand **nur auf dem gezeichneten SVG**
(ohne OSM-Zuordnung): **GS** Schnitt ohne DKW-Symbol, OSM-Kreuzungsknoten oder Niveautrennung (2.4/2.5) · **GG** Gleis auf
Gleis, das ein Gleis verdeckt (0.1) · **GQ** Querabstand nach gemeinsamem Knick ≠ davor (1.15/2.7) · **GP** Pfeil nach innen
oder auf ein Nachbargleis (1.14) · **GW** Knick oder Abgang ≥ 80°/75° (0.4/1.2) · **GT** Treppe (5.1). Stand der Pläne in
`grundpruefung_basis.json`; bekommt ein Plan einen **neuen** Befund (Zahl je Regel steigt), wird der Workflow `seite` rot.
«Sauber / kreuzt nichts» wird nur mit dieser Prüfung gemeldet, nie nach Augenschein.

**Hauptgleis-Topologie als Sperre (HT, seit 18.11., Entscheid D. Eckenstein «Hauptgleise Weichen die weg gehen, Hauptgleise
Topologie immer korrekt, sprich korrekte Seite weg und korrekte Fahrwege»).** Prüft jeden Plan aus Code über sein Netzmodell
gegen OSM, nur wo ein Hauptgleis (grün, 1.21/1.24) beteiligt ist: **HT1** OSM-Weiche am Hauptgleis ohne Abzweig im Plan (= VB1)
· **HT2** Abzweig am Hauptgleis im Plan ohne OSM-Weiche, z. B. Schere statt zweier Spurwechsel (= VB2) · **HT3** Gleis an
der falschen Weiche angebunden (= VC1) · **HT4** Abzweig zur falschen Seite (links/rechts in Fahrrichtung des Hauptgleises,
2.1) · **HT5** Fahrweg falsch: die Menge der Fahrwege zwischen den Enden der Hauptgleise (Abgänge, Perrongleise, Gleisenden;
ohne Richtungswechsel an einer Weiche) im Plan ≠ OSM; dazu ein Gleis, das im Plan am Planrand endet, obwohl es in OSM im Plan
weiterläuft (künstlicher Schnitt, z. B. Achsknick Giesshübel). Code `code/hauptgleis.py` (seit 18.11.): Fahrweg-Regel an jedem
Knoten in Plan und OSM gleich – Äste nach der Hauptrichtung in zwei Seiten, Wechsel nur auf die andere Seite; Kreuzung ohne
Weiche nur geradeaus; DKW-Symbol = ein Knoten. Prüffälle `hauptgleis_faelle/` (Giesshübel, Spurwechsel fehlt, Schere, falsche
Seite; je 0°/90°), Selbsttest in `seite` und `pruefstand`. Ziel ist **0** in jedem Plan; bis dahin Ausgangsstand als Basis
(`hauptgleis_basis.json`), jeder **neue** Befund macht `seite` rot (wie G0). Berichte nennen G0 **und** HT. Zielbilder von Hand (ohne Netzmodell) nur aus der
Weichenfolge je Hauptgleis aus OSM, die Liste wird mitgegeben. **Netzmodell = gezeichneter Plan (seit 21.11., V4c):** zeichnet
die Typvorlage den Bahnhof neu (`vorlage.py`), legt sie auch `<key>_netz.json` auf ihre Zeichnung – OSM-Weichen eins zu eins an
den Abzweig der Vorlage (Reihenfolge längs bleibt), übrige Knoten über Abgänge/Gleisnummern abgebildet, OSM-Verbindungen
zwischen zwei Weichen, die der allgemeine Lauf nicht zeichnete (Spurwechsel), ergänzt; Lauf-Fassung bleibt `<key>_netz_lauf.json`.
Sonst misst HT die alte Lage (Paar HT1+HT2 = Messartefakt). Liegt der Planrand genau auf einer Weiche, die die Vorlage zeichnet
(Netzmodell `vorlage.gezeichnet`), zählt das Stück zwischen zwei Abgängen zum Plan (sonst ausserhalb, Tecknau). Prüffälle `vorlage_gummenen`, `vorlage_saint_blaise_cff`. **Seit 22.11. (V4e):** Weichen werden der Vorlage **je Gleis** reihenfolgetreu zugeordnet (Ebene der Weiche ↔ Ebene des Abzweigs), nicht über alle Gleise zusammen – Weichen auf verschiedenen Gleisen dürfen längs anders liegen als in OSM (Tüscherz); ein Perrongleis aus mehreren OSM-Stücken ist im Plan über jede grüne Kante erreichbar, auf der die Mitte zweier seiner Knoten liegt (gleiche Gerade wie das Ziel; Bevaix Gl. 652, Auvernier, Däniken). Prüffälle `vorlage_bern_brunnen`, `vorlage_tuscherz`.
**Seit 22.11. (V4e Teil 3):** Abgang ohne Richtung nach aussen (`aus_ll` fehlt, Planrand genau auf einer Spurwechselweiche):
aussen = vom Schwerpunkt der Plan-Knoten weg – sonst galt der Spurwechsel selbst als Fahrweg Abgang ↔ Abgang (Le Landeron,
Gorgier, Riedbach). Im Netzmodell der Vorlage bleibt die Knotenfolge je Gleis wie im Lauf (Knoten hinter einer Weiche nicht
vor ihr; Gorgier Gl. 512, Bevaix Gl. 662); ein künstlicher Knoten, an dem der Lauf ein totes Nebengleis aufs Streckengleis
führte, wird aufgelöst (OSM ohne Verbindung; Grandson, Riedbach, Tüscherz). Wo die Ebene des Laufs nicht zur Vorlage passt,
legt der Zusatz `weichen: [[osm, x, y]]` die OSM-Weiche an den gezeichneten Abzweig (Gorgier Anschlussring, Tüscherz,
Zihlbrücke), `abgaenge_knoten` die OSM-Knoten der Abgänge je Seite (Zihlbrücke: Lauf kannte nur einen Abgang Ins). Anschluss `gegen` (innen, läuft aber nach aussen; T-Stumpen zum Bahnhof = Zurücksetzen): Riedbach, Daniel 22.11.
Prüffälle `vorlage_le_landeron`, `vorlage_gorgier_saint_aubin`, `vorlage_riedbach`, `vorlage_zihlbruecke_0`. **Hand-Linien (`zeichnen`, seit 22.11.):** `vorlage.py --weichen` legt auch dort das Netzmodell auf die Zeichnung
(`zeichnen.weichen: [[osm, x, y]]`) und ergänzt OSM-Verbindungen zwischen zwei Weichen, deren Ways die Hand-Linie ersetzt
(`weglassen`/`zeichnen.weg`; Cornaux, Travers). Messung: ein Ast mit geradem Vorstück auf dem Gleis ist ein Abzweig (Richtung
auf 30 px, Onnens); Abzweige < 7,5 px zusammen; Teilungspunkte der Plan-Linien aus allen Berührpunkten, kurze Verbindungsstücke
sind kein Doppel (Murten); Gleisziel = Gleismitte; OSM-DKW als Weichenpaar gezeichnet ist kein VB2 (Chambrelien, HT5 prüft die
Fahrwege). Prüffälle `zeichnen_chambrelien`, `zeichnen_murten`, `zeichnen_cornaux`, `zeichnen_onnens_bonvillars`.
**Seit 22.11. abends (V4e Neuchâtel/Vauseyon):** `vorlage.py --weichen` läuft auch im Workflow `plaene` (`lauf.py`, Pläne mit
`zeichnen.weichen`/`netz_ergaenzen`); eine Kette endet auch an einer Kreuzung (OSM-DKW = Kreuzung + 4 Weichen, DKW 58).
Messung: an einer Kreuzung heisst geradeaus der Way, der in OSM die Fortsetzung ist (alle Ways am Knoten paarweise, am geradesten
zuerst; flache EKW 109 ≈ 6°); mehrteiliges Perrongleis zählt die nächste Kante **auf seiner Geraden** (Neuchâtel A15); eine
Bogenweiche einer OSM-DKW (≤ 30 m neben der Kreuzung) unter einem DKW-Symbol ist gezeichnet (kein HT1); ein nach Regel 1.16 (R39b)
angedeuteter Stummel ist kein Abzweig (Netzmodell `angedeutet`, Vauseyon). Prüffälle `zeichnen_neuchatel`, `neuchatel_vauseyon`. EKW (Symbol mit **einer** Klammer, REGELN 2.4): im Plan nur geradeaus und die eine Bogenfahrt zwischen den Ästen des Klammerwinkels
(Neuchâtel EKW 109, Hinweis Daniel 22.11.: «EKW-Symbol, sonst sieht man nicht, dass von Ins abgebogen werden kann»); OSM-Bogenweiche mit 3 Armen zählt für VA2 als EKW.

**Bahnhofregister und Sperre «veraltet» (VR, seit 20.11., Entscheid D. Eckenstein «Regionen harmonisieren, OSM-Fehler
erkennen»).** Jeder Bahnhof steht **einmal** im Register `spurplan/netz/bahnhoefe.json` (Schlüssel **SBB-Abkürzung**, dazu
BPUIC, atlas-Koordinaten, OSM-Station, Linien, Regionen, Pläne mit Quelle/Workflow); Code-Commit und Fingerabdruck je Plan
stehen in `ergebnisse/seite/register/register.json`. Erzeugt `code/bahnhofregister.py` in jedem Lauf `seite` aus der Seite,
den Dienststellen (atlas) und den Betriebspunkten (Release «vorbereitung»). Teile desselben Orts (Abzweig, cul-de-sac, ≤ 1 km)
zählen zum Plan. **Sperre VR:** ein Plan aus Code, dessen Bau-Commit den letzten Commit unter `spurplan/code/` nicht
enthält, macht `seite` rot (Linien-Regionen: `regionen` rechnet bei Code-Push alle Regionen; solange `plaene`/`regionen`
noch laufen, nur «wartet»). Bewusst feste Pläne (NE fest seit 21.10., Basel/Bern, Referenzen) stehen in
`netz/veraltet_basis.json` und fallen mit V4/N2/P2b weg. Selbsttest (alter Commit → rot) im selben Schritt. **OSM-Verdacht**
(nur Befund, Karte «OSM-Verdacht und Herkunft» im Werkzeugkasten): **OA** OSM-Station > 150 m vom atlas-Punkt · **ON** Name
weicht ab (ohne Kantonskürzel/St./Ortsvorsatz) · **OR** Abkürzung ≠ `railway:ref` · **OU** BPUIC ≠ `uic_ref` · **OL** Linie
der SBB-Betriebspunkte nicht unter den OSM-Linien im Plan · **OG** SBB-Gleis mit Perron ohne Perron-`ref` in OSM (SBB gilt,
1.C) · **OK** keine OSM-Station · **OB** Betriebspunkt im Perimeter (Vieleck, 4.10) ohne Plan · **MF** Bahnhof an mehreren
Orten geführt. Daniel entscheidet je Befund: OSM korrigieren oder Ausnahme (Ebene 6, `netz/osm_ausnahmen.json`).

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
| 0.1 | **Topologie stimmt:** jedes Gleis hängt dort an, wo es real anhängt; keine Schein- oder fehlenden Verbindungen, keine Gleissprünge, kein Gleis endet im Leeren. Farbe gehört dazu (grün = im Personenverkehr befahrbar). **An Hauptgleisen immer und ohne Ausnahme** (seit 18.11., Entscheid Daniel nach Giesshübel): jede Weiche, die von einem Hauptgleis weggeht, ist da; sie zweigt zur **richtigen Seite** ab (wie real, in Fahrrichtung); die **Fahrwege** stimmen (welches Gleis über welche Weiche in welcher Richtung mit welchem verbunden ist, keine zusätzlichen, keine fehlenden). Gesperrt mit HT (siehe Kopf). | Regel | G1, T1, E1 | T1–T8, V/S, VA–VD, G7, PS «T», GS, GG, **HT** (`hauptgleis.py`, Basis `hauptgleis_basis.json`) |
| 0.2 | **Reihenfolge wie die Karte:** was klar nördlich (östlich) liegt, liegt im Plan nicht südlich (westlich); Querreihenfolge der Gleise wie real. Abstand, Winkel und Drehung sind frei. | Regel | G2, N1, L1 | L2, L3 |
| 0.3 | **Jede Weiche ab Hauptgleis sichtbar**, mindestens als Pfeil – auch in grossen Knoten, einzeln. | Regel | G3, B9, S1 | VB1, W |
| 0.4 | **Keine 90°:** Verbindungen 60° mit Ausrundung; Ausnahme Tunnelportal, Brückenflügel. | Regel | G4, R4, R5 | G2, G3, G4, GW |
| 0.5 | **Abstand:** parallele Gleise im Ebenenabstand; parallel bleibt parallel im gleichen Querabstand, in jeder Drehung, jedem Abgangswinkel und durch jeden gemeinsamen Knick. | Regel | G5, B2, 6.11., 12.11. | Q, P, QK, E, F (siehe 7.1), GQ |
| 0.6 | **Ruhe:** gerade so lange wie möglich; keine Treppen, keine unmotivierten Ecken, keine S-Kurven. | Wunsch (Ebene 5) | G6, R10, 4.11. | T7, Z, E, QK, Ebene 5, GT |
| 0.7 | **Detailgrad:** kleine Bahnhöfe ganze Anlage, grosse Knoten Hauptgleise + jede Weiche als Abgang. | Regel | G7, B16, B17 | Sicht |
| 0.8 | **Darstellung:** Symbole, Beschriftung, Kompaktheit. | Regel/Wunsch | G8 | Ebene 1.F, 5 |
| 0.9 | **Kartographische Freiheit** (seit 20.11., Daniel): alles, was die Karte lesbarer und nicht falscher macht, ist erwünscht – einfacher darf Ziel sein (kürzere Nebengleise, gleichmässigere Bahnhofsabstände, weniger Knicke), auch an abgenommenen Plänen. Grenze: 0.1 Topologie stimmt, und die **Hauptfahrwege sind intuitiv erkennbar** (durchgehende Hauptgleise gerade und dick, Abzweige als Abzweige). | Grundsatz | 20.11. | Ebene 5, Regression «Vorschlag: einfacher» |
| 0.10 | **Hinweise nach Priorität** (seit 21.11., Daniel): Hinweise mit Topologie- oder Überschneidungsfehler (Gleis über Gleis, Schnitt, falsch/nicht angebunden, fehlende Weiche/Gleis/Doppelspur, Weiche falsch herum) sind **prio** (Pin-Nummer rot), alle übrigen **nice** (orange). Claude schlägt die Einstufung vor, Daniel schaltet um (Knopf am Hinweis). Der Fahrplan nimmt prio zuerst. | Grundsatz | 21.11. | Feld `prio` in Sammlung `feedback`, seite.html |

---

## 1. Grundform – gilt für jeden Plan

### 1.A Gitter und Geometrie
| Nr | Regel | Auslöser | alt | Code | Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 1.1 | Gleise waagrecht auf Ebenen (24 px); Verbindungen 60°, eine Figur bleibt zwischen ihren Weichenpunkten. | | B1, W2 | spurplan_schema | PS «D» (Drehung) | alle |
| 1.2 | Ausrundung überall: Weichen, Pfeilstummel, Einmündungen, Gleisenden (7 px, DKW-Ketten 10 %). | | R5, W3, B8 | spurplan_schema `_rund_stub` | G2, G3, GW | alle |
| 1.3 | Einheitlicher Winkel: alle Diagonalen einer Anlage gleich (60°), nicht variieren, um Platz zu gewinnen. Gilt strikt im Bahnhofplan; Kippen und leichte Schrägen nur im Regionalplan (16.11., F4). Reicht der Platz für eine einzelne Verbindung nicht: volle 60°-Schräge, die auf dem anschliessenden Gleis ausläuft, kein S-Bogen – auch im Bahnhofplan (seit 17.11., S2 Konolfingen 33fs «sehr steil»); nicht an einer DKW. | | V1, 7.5 | dkw_auto, `r49_eng` | fehlt | LR (Gitter), alle (`r49_eng`) |
| 1.4 | Gleisabstand: Hauptgleise 1 Ebene; Gleise zweier Doppelspuren je 1 Ebene, zueinander 1 oder höchstens 2 Ebenen. | | B2, A1, R1c | `buendel_kompakt` | Q | alle |
| 1.5 | **Ausnahme zu 0.5:** Nebengleise zueinander enger (55 %, bei Platzmangel bis 40 %); voller Abstand, sobald ein Hauptgleis über eine Weiche berührt – und nur dort, wo das Personen-/berührte Gleis längs tatsächlich neben dem Gleis der Nachbarebene liegt (16.11., S1b: Sasslatsch wie Sagliains). Grund: Pfeile in Anlagen werden später durch die richtigen Anlagen ersetzt (bestätigt 13.11.). Lange parallele Nebengleise wie Sagliains (Autoverladgleis) sind selten, dort eher OSM-Unschärfe. | Nebengleis neben Nebengleis | B2, A2, 7.1 | spurplan_schema `build_ly`, `ebene_eng_laengs` | Q – **anpassen**: gegen die erlaubte Ebene prüfen | alle |
| 1.6 | Stoss oder Gleisende > 1 px neben dem Nachbargleis ist ein Fehler; kein Knubbel (gerades Stück über den Anfang einer Ausrundung hinaus), auch an Pfeil-Stummeln (16.11., S1b Sagliains). | | E7, A3, W9 | spurplan_schema `_knubbel`, G6 | G6, G7 | alle |
| 1.7 | Kein Gleis deckt ein anderes (> 12 px deckungsgleich); kein Perron auf einem Gleis. | | E4, A5 | | VD1, VD2, G8 | alle |
| 1.8 | Kein Gleis wechselt die Ebene ohne Weiche oder Werfung; keine Badewanne (Mulde ohne Weiche bleibt oben, wenn frei). **Ausnahme:** Randzone (1.10) darf vor dem Planrand ohne Weiche die Ebene wechseln; derselbe Abstand gilt dann im Regionalplan und im Nachbarbahnhof weiter (16.11., F2). **Seit 24.11. (K0d, Selnau HB-Ende):** eine OSM-Weiche zählt nur, wenn ihr Abzweig gezeichnet wird (stillgelegter Abzweig zählt nicht); ein Gleis, das so ohne gezeichnete Weiche über einen Bogen in ein Stumpfgleis (Prellbock/Gleisende im Plan) weiterläuft, behält seine Ebene bis zum Ende. | 24.11. | F11, F10, 7.3 | `f10`, spurplan_schema `stumpf_fortsetzung` | E, PS «E», HT2 | alle |
| 1.9 | Zwischengeraden zwischen zwei Spurwechseln entfallen (Gleise rücken zusammen), ausser dazwischen liegt ein Gleis mit Perron oder Nummer. **Im Bahnhofplan (seit 19.11., K0):** wechselt ein Gleis zweimal in dieselbe Richtung die Ebene und liegt dazwischen ein waagrechtes Stück unter 2 Ebenen ohne Weiche, Gleisende oder Nummer, werden die beiden Schrägen zu **einer** 60°-Schräge in der Mitte zusammengelegt (Aarau, Zweisimmen). **Seit 20.11. (K0b):** auch über einen Wechsel dünn↔dick hinweg (Klassengrenze kommt in die Mitte der neuen Schräge, Zweisimmen), auch mit steilem S-Bogen als Schräge, und mit Weiche am Knick, wenn der Abzweig auf eine Ebene zwischen den beiden Enden führt: dann zweigt er **direkt aus der Schräge** ab (Solothurn, Hinweis xke0). Längeres Stück (Selnau, ZL) nur auf Daniels Entscheid – Zählung ZG/ZL. | 19.11. / 20.11. | B7, F7 | spurplan_schema `zg_zusammen`, `zg_max_ebenen`, `zg_klassen`, `zg_cbogen`, `zg_abzweig` | Z, F7, `zwischengeraden.py` (ZG) | alle |
| 1.26 | Nebengleise liegen so nah am Stammgleis wie möglich: eine Nebengleis-Kette unter dem Stammgleis rückt hoch bis direkt unter die nächste Kette, die sie längs überlappt (höchstens bis unter das Stammgleis) – nur wenn sie über Weichen ausschliesslich nach oben anschliesst und keine ihrer Schrägen dann über einem Gleis dazwischen läuft (Solothurn); Querreihenfolge bleibt (17.11., G1 Glion: Gleis ohne Perron lag sieben Ebenen tiefer, weil das Depot dahinter dieselben Ebenen brauchte). Perrongleise bleiben, wo die Schichtung sie hinlegt. | Nebengleis unter dem Stammgleis | – | spurplan_schema `ebenen_zum_stamm` | W56/Sicht | alle |

### 1.B Planrand und Abgänge
| Nr | Regel | Auslöser | alt | Code | Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 1.10 | Streckengleise verlassen den Plan im Standardabstand: gleiche Linie oder Gleis ohne Liniennummer 1 Ebene, verschiedene Linien 2 Ebenen. Gilt nur für **Streckengleise**; Nebengleis-Bündel behalten ihren Abstand (1.5) bis an den Rand. Der Abstand am Rand wird im Regionalplan und im Nachbarbahnhof gleich übernommen (16.11., F1/F2). | Streckengleis am Rand | E5, A4, Randzone, 7.2 | `randzone`, a4_rand | planrand_pruefung | **LR** (Randzone), alle (a4) – Widerspruch 7.2/7.3 |
| 1.11 | Streckengleis nach der letzten Weiche läuft auf seiner Ebene gerade aus dem Plan; nicht im parallelen Bündel, wenn ein Nachbar schräg bleibt. | | R33b, F4 | spurplan_schema | E | alle |
| 1.12 | Abgang mit Liniennummer und Richtungsort (näherer Ort; hat ein anderer Abgang schon den Ort, der andere Ort der Linie). | | B10, Z2 | exit_town, linienenden.json | T | alle |
| 1.13 | Abgang mit Pfeil nur, wenn das Gleis ≥ 300 m weitergeht oder zu Bahnhof/Anschluss führt; echtes Gleisende → Stumpen mit Prellbock – auch nahe am Rand des Regionsausschnitts (seit 18.11., T-SZU Uetliberg: «Linie 713 ↑»). | | T12, «echte Gleisenden» | `gleisenden` (auch straenge `_am_rand`) | T5, S2 | LR (Gleisenden), alle (T12) |
| 1.14 | Pfeile zeigen nur nach aussen, nie auf ein Nachbargleis (< 1,5 Ebenen); sonst kurzer Stumpen richtig gezeichnet, nie ersatzlos löschen. Pfeilspitze ≥ ½ Ebene neben jedem Gleis. | | 4.11., A6 | `pfeil_aussen` | GP | **LR** |
| 1.15 | Schräg den Plan verlassende Gleise, die nebeneinander knicken, behalten quer den Abstand von davor (Knickversatz d·tan(θ/2)). | Bündel knickt | 12.11. (S1) | `stub_buendel_davor` (nur Stummel am Rand) | QK, GQ | alle (nur Stummel) |
| 1.16 | Weichen bis 150 m hinter einem seitlichen Abgang als kurzer Stummel auf der Abgangsschräge. | | T15, R39b | spurplan_schema | – | alle |
| 1.28 | Nebengleis läuft an einem inneren Knoten längs aus dem Plan, an dem weitere Nebengleise enden (z. B. direkt hinter einer DKW): nur das Gleis in seiner Flucht läuft weiter (kurzes Stück in der Flucht, Pfeil nach aussen); die anderen enden dort nicht, der Knoten bleibt an Ort und behält seine Ebene; ein Abgang wandert nie über eine DKW zurück (seit 17.11., S2 Konolfingen 8bce «Pfeile retour»). | Gleis verlässt den Plan an einer Verzweigung | – | `rand_flucht` | VA1, Sicht | alle |
| 1.27 | Bahnhofsachse läuft durch: liegt ein Bahnhof < 3 km vor dem Ende seiner Linie und setzt dort eine andere Linie ohne Richtungsumkehr fort (≤ 75°), läuft die Achse auf ihr weiter; mit Umkehr (Spitzkehre, z. B. Zweisimmen 120/321) endet sie (17.11., G1 Glion: 121/122, «keine Spitzkehre»). | Linienwechsel im Bahnhof | – | topologie_linien `achse_durchgehend` | Sicht | LR |

### 1.C Perrons und Nummern
| Nr | Regel | Auslöser | alt | Code | Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 1.17 | Jeder Perron aus OSM/SBB wird gezeichnet (≥ 3 m), mindestens 40 px, nie über Gleise oder Weichenbögen; Lage dort, wo seine Gleise liegen; an mehreren Gleispaaren je Paar ein Balken; beidseitige Perrons bleiben. | | B13, P1, 4./5./6.11. | `perron_frei`, `perron_abschnitt`, `perron_teile`, `perron_beidseitig` | P1, PF | **LR** (ausser beidseitig) |
| 1.18 | Perronlänge **80 px** für alle Pläne, Gleisnummer in der Perronmitte (13.11.: 110 px aufgehoben). | | B14, Z1, 5.11., 7.6 | `perron_standard_px` | fehlt | LR 80 / sonst noch 110 (V2) |
| 1.19 | Perronformen: Querperron an Kopfgleisen als U oder L um die Gleisenden. | Kopfgleise mit Querperron | 8.11. | – (P2a) | PF | fehlt |
| 1.20 | Gleisnummern: SBB-Perronkanten > SBB-Perronflächen > OSM; nur Gleise mit Perron; Halt mit einem Gleis ohne Nummer; fehlt sie überall «?». `ref` in Gleisnummernform ist ein Gleis, keine Linie. | | R6, E10, D11, 6.11. | gleisnummern_sbb, `gleisnummer_aus_ref` | G1 | alle (MOB: aus_ref aus) |
| 1.29 | Ein Gleis mit zwei Nummern (eine Kette, z. B. Selnau Gl. 1 → HB SZU Gl. 21): jede Nummer, neben deren Teil ein eigener Perron liegt, wird angeschrieben (Perron zur Hälfte neben diesem Teil und mehr als neben dem Teil der Hauptnummer); Teile ohne eigenen Perron bleiben ohne Nummer (Dulliken 12/13). | Kette mit mehreren Gleisnummern | K0e 24.11. | `nummer_je_perron` | Sicht | alle |

### 1.D Farbe und Inhalt
| Nr | Regel | Auslöser | alt | Code | Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 1.21 | Grün = im Personenverkehr befahrbar (aus den Fahrwegen): Gleise ohne service, Perrongleise, Durchfahrgleise beidseitig am Streckengleis (auch siding, nicht yard); sonst schwarz; schwarz unter grün. Ein Gleis nur für Güterverkehr (`railway:traffic_mode=freight`) ist schwarz, auch ohne service und mit Liniennummer; sein Abgang mit schwarzem Pfeil und schwarzer Beschriftung «Linie / Ziel»; nur die Farbe – Lage und Abgänge wie beim Streckengleis (sonst verlor Solothurn 415 seinen Streckenabgang) (seit 18.11., Entscheid Daniel, T-SZU 717 Giesshübel – Wiedikon; umgesetzt 24.11., T-SZU1). | | B3, E1, D3, R1 | verbindungen_pruefen; Güterverkehr spurplan_schema `gueter_schwarz` | E1-Prüfung | alle |
| 1.22 | Meterspur/Schmalspur braun (dick Strecke/Perrongleis, dünn Nebengleis), auch Perrons, Prellböcke, Pfeile, Nummern; Dreischienengleis grün mit braun gestrichelt. | | Z4, 4./6.11. | spurplan_schema | Sicht | alle |
| 1.23 | Stillgelegtes (disused) nicht zeichnen; Bushalte sind keine Perrons. **Seit 24.11. (K0d, Daniel: «das Tramperron von zwei Ebenen weiter oben»):** ein Perron, neben dem (bis 15 m) nur Gleise liegen, die mindestens zwei Ebenen (OSM `layer`) höher oder tiefer sind, gehört nicht zu ihnen (Tramhaltekanten über dem SZU-Tunnel in Selnau und am HB). Fehlt ein Perron in OSM, ergänzt ihn das Override `platforms_plus` als Ortswissen (Abschnitt 6; HB SZU zwischen Gl. 21/22). | 24.11. | R7, D6, 5.11. | spurplan_schema `perron_ebene`, Override `platforms_plus` | fehlt | alle |
| 1.24 | Hauptgleis aus Funktion: Perrongleis, Fortsetzung eines endenden Streckengleises bis zum Perrongleis, oder Kette usage=main/branch zwischen zwei Streckengleisen ist Hauptgleis; an der Weiche läuft das Hauptgleis weiter (Perrongleis vor Nebengleis). | | 3.11., `haupt_fortsetzung` | `hauptgleis_funktion`, `haupt_fortsetzung` 0.15 | fehlt | **LR** |
| 1.25 | Gleis bleibt Gleis: gerades Gleis mit Ebenenwechsel an den Enden behält ≥ 40 px bzw. 35 % seiner Länge. | | 3.11. | `gleis_mindestlaenge` | fehlt | **LR** |

---

## 2. Muster – greifen, wo der Code sie im Ort findet

Jedes Muster hat einen Prüfstand-Baustein (`pruefstand_bausteine.py`) und ein Soll-Bild; auf der Seite soll je Plan stehen,
welche Muster erkannt wurden (V0).

| Nr | Muster | Regel | alt | Code | Baustein / Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 2.1 | Weiche | zweigt ab wie real (Seite, Richtung, stumpf/spitz); Reihenfolge entlang des Gleises wie real | R2, R3, V6, T2, T3 | spurplan_check «F», `r38_seite` | VC1, fehlt (Reihenfolge) | alle |
| 2.2 | Spurwechsel | eine 60°-Diagonale; **zwei Spurwechsel hintereinander (Typvorlage «anzahl 2», seit 22.11.):** Reihenfolge wie OSM (`richtung`), dazwischen ein kurzes gerades Stück (`SW_GAP` 28 px) – vorher begann die zweite Weiche vor dem Ende der ersten (Bevaix, Bern Brünnen, Riedbach, Tüscherz, St-Blaise CFF); auf freier Strecke nur im geraden parallelen Stück, einzeln, nicht ineinander; Nebengleise zweigen nie im Spurwechsel ab; crossover zwischen zwei Streckengleisen ist immer Schräge; **seit 20.11.:** ein Gleiswechsel, den OSM in mehrere Stücke ohne Weiche dazwischen teilt, ist als Ganzes Schräge (kein eigenes Mittelgleis, die Streckengleise bleiben parallel – Selnau j9ou; an seit 24.11., Schritt K0c; nur zwischen Streckengleisen mit Personenverkehr) | R11, R12, N7, F6, T7, Randzone | `verbindung_schraeg`, `r34_kette`, `r34k_max_m` | G5, r5_halt | alle |
| 2.3 | Weichenstrasse | Diagonale läuft zum entferntesten Gleis durch, die näheren zweigen ab. Mündet ein schräger Anschluss von der anderen Seite in einen Zwischenknoten einer geraden 60°-Kette, läuft er als deren Verlängerung ein; Gleise vom selben Fuss auf nähere Ebenen zweigen aus ihm ab (seit 18.11., S2 Konolfingen yz3m «Gleis von 6 und von 5 kreuzen») | B6, F5 | spurplan_schema, `r45_anschluss_gerade` | osm_abgleich 3. Zuordnung (Abzweig bis 60 px schräg neben der Weiche) | alle |
| 2.4 | DKW / EKW / Schere | OSM-Elemente < 20 m, die ein Gleis kreuzen = DKW mit Symbol an Ort, liegend, Klammern in den stumpfen Winkeln; Kette durch DKW eine gerade 60°-Linie; Durchschneidung mittig zwischen zwei Diagonalen. Endet die Kette an einer DKW und läuft dahinter ein Streckenabgang weiter, liegt die DKW auf der Geraden und der Abgang setzt sie fort (seit 17.11., S2 Konolfingen 430 nach Hasle). Eine OSM-DKW/EKW mit weniger als 4 Armen in OSM ist eine einfache Weiche (Tag unvollständig; Entscheid Daniel 17.11., Konolfingen 1689231106). Umgekehrt: eine OSM-Weiche mit 4 Armen in einem Knoten, je zwei auf jeder Seite (X-Form, Arme einer Seite ≤ 20° auseinander), ist eine DKW mit Symbol, auch ohne `railway:switch` (seit 18.11., Entscheid Daniel, T-SZU Depot Giesshübel 1263316996/1263338286; Dreiwegweiche = 3 Arme auf einer Seite, bleibt Weiche; enden alle vier Arme am Knoten, werden je zwei gegenüberliegende zu einer durchgehenden Linie zusammengesetzt; liegt im Plan eine Seite ganz auf der Ebene des Knotens, zeigt das Symbol die Gegenseite – umgesetzt 24.11., T-SZU1) | E3, B8, V2–V4, T5, W4 | `dkw_auto`, `r45_ende_abgang`, DKW_3ARME / osm_abgleich `dkw_osm_unvollstaendig`; 4-Arm-Knoten spurplan_schema `dkw_4arme` (`dkw_4arme_finden`, auch in osm_abgleich; `dkw_4arme_linien` = Ways zu Linien zusammensetzen, aus: verschob Aarau) | VA1, VA2, Montreux-Westende | **LR** (dkw_auto), alle (Rest) |
| 2.5 | Kreuzung ohne Verbindung | Lücke im unteren Gleis nur bei Niveautrennung (bridge/tunnel/layer), Brücke mit Flügeln, Tunnel nur Lücke; gleiche Ebene beide durchgezogen; Werfung = Ebenenwechsel unter/über der Kreuzung (bestätigt 13.11.) | B19, T4, 6.11. | `kreuzung_schnitt`, netz_lage `_kreuzungen` | X, unterwerfung (Schritt K), GS | LR (Bahnhof), Reg |
| 2.6 | Abzweig / seitlicher Abgang | ausgerundet unter 60°; ein Abzweig läuft höchstens eine Achse parallel und geht dann weg; parallele Abgänge bleiben parallel | B11, W5 | spurplan_schema | ab30, ab60 (Schritt A2) | alle |
| 2.7 | Bündel knickt | parallele Gleise knicken gemeinsam, Querabstand danach = davor (Ausfahrten, Spurwechselpaare, Abgänge, Stummel) | 12.11., IDEEN «Bündel als Einheit» | nur Stummel: `stub_buendel_davor` | buendel_knick, QK, GQ | alle (nur Stummel) |
| 2.8 | Gleisdreieck | kein fester Standard: Darstellung mit der meisten Ruhe nahe der Geografie (eine Achse, Zulaufstrecke teilt sich auf zwei Schenkel ≤ 90°, ausgerundet) | 3.11. | knoten.json | Sicht | alle |
| 2.9 | Kreuzungsbahnhof zweier Linien | im Regionalplan X: je Linie eine gerade Achse, Kreuzung unter 60° in der Mitte | N2, W7 | Override «seitlich» | W1 | O (Kerzers) |
| 2.10 | Anschluss-/Abstellgleise | jede Weiche nach OSM, zusammengedrängt, ohne Längenmassstab. **Seit 21.11. (Daniel, Avenches):** ein Stumpfgleis, dessen gerades Ende ein anderes Gleis ohne Weiche schneidet, endet kurz vor dem Schnitt (in OSM liegt das Ende davor, erst die Stauchung schiebt es darüber) | E6, D2, (B16 widerspricht – entschieden: E6) | `spurplan_schema` `_stumpf_vor_schnitt`, cfg `stumpf_vor_schnitt` (`stumpf_schnitt_px` 8, `stumpf_min_px` 6) | GS (G0) | alle |
| 2.11 | Kopfgleise / Stumpfgleise | endet daneben (< 30 m) ein weiteres Gleis: Kopfbahnhof, keine fehlende Weiche; nie bei Gleis mit Nummer oder auf anderer Ebene | R27b | spurplan_schema | – | alle |
| 2.12 | Meterspur neben Normalspur | Meterspur wird gezeichnet wie Normalspur (eigene Pläne, Regionen); bis ~40 m neben Normalspur in deren Plan mitgenommen. «Im Regionalplan nur als Stummel mit Ziel» aufgehoben 13.11. Am gemeinsamen Knoten (Rollbock Ins) setzt die Meterspur genau am Ende des gezeichneten Normalspurgleises an (0.1; seit 19.11., K0, Hinweis Ins 1470). | E8, D9 | `meterspur_cfg.d_max`, `ms_anschluss_fang` | – | alle |
| 2.13 | Schiebebühne | Depotgleise mit gemeinsamem Anfang ≥ 40 px, Bühne gestrichelt | 4.11. | `schiebebuehne` | – | **LR** |
| 2.14 | Tunnelportal | Klammer nur, wo alle Gleise gerade und parallel (±18 px); ausnahmsweise 90° | 4.11., R4 | netz_lage | – | alle |
| 2.15 | Achse knickt im Planfenster | Knickt das Gleis, dem die Bahnhofsachse folgt, innerhalb des Planfensters um mehr als 30° (Kurs über je 100 m gemittelt), folgt die Achse dem Bündel mit der grössten parallelen Gleislänge im Fenster (Strecken- und Nebengleise, Kurs ±15°). Das abbiegende Gleis verlässt den Plan als Abzweig nach 2.6 (ausgerundet, unter 60°), auch wenn es die Linie mit der Liniennummer ist. Gilt für alle Pläne (auch Knotenpläne); Lage und Drehung im Regionalplan folgen der neuen Achse. Abgrenzung: 1.27 (Achse läuft am Linienende auf einer anderen Linie weiter) bleibt; 2.15 entscheidet nur, wenn im Fenster ein Knick > 30° liegt (Entscheid Daniel 18.11., T-SZU Giesshübel: 712 knickt 250–350 m südlich des Bahnhofs von Kurs 215° auf 150°, das Depot läuft mit 220–250° geradeaus weiter und wurde als Schrägen über das Bündel gezogen, G0 GS 11 / GG 33) | 18.11. | `spurplan_schema` cfg `achse_knick` (Achse im Fenster, Ast verlässt den Plan seitlich), `straenge` Konfig `knoten_knick` (Knick zwischen zwei Betriebspunkten → kein gemeinsamer Knotenplan); beide **Standard aus** seit 24.11. (T-SZU2: Giesshübel GS 12→20 mit `achse_knick`, Regionalplan SZU 6 × 90° an der Sihltal-Verbindung mit `knoten_knick`) | GS, GG, GQ; Baustein «achse_knick» fehlt | teilweise (Code da, aus) |

---

## 3. Knoten-Zusatz – nur was von der Grösse abhängt

| Nr | Regel | Auslöser | alt | Code | Prüfung | heute aktiv in |
|---|---|---|---|---|---|---|
| 3.1 | Grosser Knoten: nur Hauptgleise + jede Weiche in die Anlage einzeln als Abgang | grosse Nebengleisanlage (Olten, Bern, Basel, Däniken RB, RB Limmattal, Buchs SG, Weyermannshaus; nicht Olten Hammer) – **Schwelle aus OSM fehlt** | B17, D1 | `--hauptgleise` (von Hand) | Sicht | O, Basel/Bern fest |
| 3.2 | Planfenster: jede Weiche, an der ein Strang des Betriebspunkts beginnt, liegt im Plan; Fenster bis zum Abzweig, wenn Gleise sich ≤ 1 km hinter dem Rand trennen; endet, wo das Fenster des Nachbarn beginnt | | T11, T13, 3.11. | straenge `anker_m`, `fenster_streckenende` | V1–V3, S1–S3 | LR (vollständig), sonst `s_min_fix`/`s_max_fix` von Hand |
| 3.3 | Knotenpläne: Pläne nur an ruhigen Stellen schneiden (≥ 500 m ohne Weiche); nahe Betriebspunkte teilen einen Plan (≤ 2500 m); Halte ohne Weiche schneiden nie | | 3.11., T9 | straenge `--knoten` | – | **LR** |
| 3.4 | Jeder SBB-Betriebspunkt ist in einem Plan enthalten (eigener oder gemeinsamer Knotenplan, 13.11.: «eigener Plan je Betriebspunkt» aufgehoben); ein Abzweig mit Weichen ist nie nur ein Knick | | R8, R14, T8 | | O2 | alle |
| 3.5 | Kreuzungsgleis (beide Enden auf demselben Streckengleis, ≤ 600 m) gehört samt Weichen zum näheren Betriebspunkt. Kreuzungsstelle aus zwei Streckengleisen (zwei getrennte Wege zwischen denselben zwei Verzweigungen, je ≤ 600 m) gehört samt beiden Weichen zum Betriebspunkt, der ihrer Mitte am nächsten liegt (seit 18.11., T-SZU Borrweg: Weichen gingen an Binz und Friesenberg) | | 5.11. | `kreuzungsgleis_m`; region_vorbereiten/straenge «Kreuzungsstelle» | V1/V2, S1, GG | **LR** |
| 3.6 | Anschluss- und Industrieanlagen bis etwa 4–5 Gleise (Mass Cornaux), die an der Strecke eines Bahnhofs hängen, kommen ganz in dessen Bahnhofplan (auch ~700 m vom Bahnhof weg, Avenches), besonders wenn sie einfach sind; grössere Anlagen nach 3.1. Ein Neben-/Anschlussgleis gehört zum Betriebspunkt, dem seine Weiche am nächsten liegt (Bern Brünnen: Abstellgleis 240 m vor Bümpliz Nord gehört zu Bümpliz Nord) – seit 21.11. (Daniel, V4c) | Avenches, Bern Brünnen | | Typvorlage (`vorlage`) bzw. Planfenster `s_min_fix`/`s_max_fix`, seitlich `d_lim_neben` (Avenches: Abstellanlage Süd ~100 m neben der Strecke ganz mit Prellböcken) | HT1 | NE |

---

## 4. Region – Zusammensetzen der Pläne

| Nr | Regel | Art | alt | Code | Prüfung | aktiv |
|---|---|---|---|---|---|---|
| 4.1 | Verkettung: Pfeile/Abgänge kommen beim Nachbarplan an; Gleise zwischen zwei Plänen nach Strang verbunden, nie oberstes mit oberstem | Regel | 29./30.10., 3.11. | verkettung.py, netz_lage | V1–V3, S1–S3, T2–T4 | alle Regionen |
| 4.2 | Ein- und Zweispurwechsel erkennt der Code selbst; überzählige Gleise münden unter 60° ein | Regel | N5, W6, 29.10. | | V1 | alle Regionen |
| 4.3 | Reihenfolge wie die Karte (0.2): Paare ≥ 1,5 km auf der Karte, Umkehr ab 60 px ist Fehler; gleiche Höhe erlaubt; grob parallele Linien nur Seite quer zur gemeinsamen Richtung; Achse > 60° neben der Karte nur Hinweis | Regel | L2, L3a, 5.11. | lage_pruefung | L2, L3 | alle Regionen |
| 4.4 | Bahnhof liegt so, dass die Strecken am geradesten anschliessen, dann nach Kartenachse; Drehung frei (je Planseite eine Stimme), leicht gekippter Bahnhof ok; Kippen (≤ 8°) und leichte Schrägen nur im Regionalplan (16.11., F4) | Wunsch | N2, L3, 3./4.11. | lage_auto, lage_suche | Unruhe | LR (Suche) |
| 4.5 | Zwischen zwei Bahnhöfen eine gerade Strecke ohne Treppen; durchgehende Gleise einer Reihe auf Gleishöhe. Versatz auf der Strecke nur, wenn sonst Gleise kreuzen; sonst den Bahnhof leicht kippen (16.11., F3) | Wunsch | N3, N4, F2, F3, 7.4, R1b | `gerade_kette`, `kipp_max`, `schraeg_port` (21.11.: Ende fast auf der Portgeraden ≤ `schraeg_max` → schräge Gerade, Knick am Port; Paarung der Gleise zählt aufeinanderliegende Gleise wie eine Kreuzung, V4c Concise – Onnens; Seite egal; `kette_paarung` (23.11., V4d Riedbach – Bern Brünnen, Twann – Tüscherz): bei Doppelspur wählt der Bahnhof das Achsgleis, dessen Gleise an die des Nachbarn in der Kette anschliessen – kein Gleisabstand-Versatz auf der Strecke) | T7 | alle Regionen – Widerspruch 7.4 |
| 4.6 | Bündel zwischen zwei Plänen: parallele Pfeilpaare als Bündel verbunden, ein nötiger Versatz gilt fürs ganze Bündel | Regel | R1b | `buendel_andocken`, `pfeile_buendel` | QK, T7 | alle Regionen |
| 4.7 | Nebengleise und Spurwechsel auf freier Strecke bleiben im Regionalplan. **Ausnahme seit 24.11. (Daniel, Ortskenntnis Olten):** OSM-Stücke von Haupt-/Verbindungsgleisen, die als siding/yard getaggt sind, sind keine Nebengleise und werden nicht als Stumpen gezeichnet – südlich Olten zwischen Knick und Bornlinie (Ways 57016117/137216908, 137216810, 137216805/137713015) | Regel | R9, D7 | Lage-Datei `nebengleis_hand` (Wege, leere `pts` = weglassen) | Prüfung 4 | alle Regionen |
| 4.8 | Bündel so legen, dass möglichst wenige Gleise kreuzen; echte Über-/Unterwerfung darf kreuzen | Wunsch | N6, F8 | | X | alle Regionen |
| 4.9 | Streckenlänge gestaucht (c0 + c1·km^p), Halte ≥ 60 px und gleichmässig über die Strecke verteilt | Wunsch | N10, F9, 4.11. | lage_auto | T8 | alle (gleichmässig: LR) |
| 4.10 | Perimeter = Vieleck; alles darin wird gezeichnet | Regel | N11, D10 | | fehlt | alle Regionen |
| 4.11 | **Ein Bauweg für alle Bahnhofspläne** (V4, 20.11., Folge von 0.9 und «alle Bahnhöfe gleich»): auch die NE-Bahnhöfe werden jeden Lauf aus dem Code gebaut (Kette wie run.sh inkl. Typvorlage, danach Beschriftungsrand); Pixelwerte in Ausnahmen (`x:`, `perrons_px`, `nummern_px`, `dkw_px`) gelten für den Warp ihres Baus (`<b>_warp_bezug.json`) und wandern mit der Streckenposition mit, wenn der Code den Plan streckt oder staucht. Der Regionalplan nimmt genau diesen Bahnhofplan (Schlüssel mit Umlaut als ae/oe/ue zuerst – seit 22.11., Zihlbrücke zeigte eine veraltete Fassung «zihlbrucke»). Bahnhöfe aus dem Workflow `plaene` (Neuchâtel, Vauseyon) nimmt der Regionalplan als `repo_bahnhoefe` mit allen Nebengleisen wie im Bahnhofplan, keine eigene Werkstatt-Fassung – seit 23.11. (V4f, Neuchâtel Ostkopf mit EKW 109 fehlte) | Regel | V4, V4f | region_olten_lauf `kette`, `repo_bahnhoefe`, spurplan_schema `PXW`, `px_mitfuehren` | Regression, G0, VR | alle Bahnhofspläne |
| 4.12 | **Weniger Knicke vor festem Winkel** (seit 23.11., Daniel, V4d Muntelier vpkw): kommt eine Strecke schräg an einen Abzweig, wird im Regionalplan der Abgangswinkel dieser einen Weiche an die Strecke angepasst (z. B. ~40° statt 60°, ausgerundet, unter 90°), statt die Strecke knicken zu lassen oder den Knick an den Nachbarbahnhof zu schieben – in «einfachen Situationen» (nur diese eine Weiche ändert den Winkel). Kein starres Winkelraster im Regionalplan; 1.3 (einheitliche 60°-Diagonalen) gilt weiter für Weichenverbindungen im Bahnhofplan. | Wunsch | V4d | netz_lage `_stummel`/`_abgang_winkel`, lage_auto `place` (Kette ab der Weiche statt ab dem Stummelende, sonst wandert der Knick zum Nachbarbahnhof; Knoten-Ausgleich unverändert), Lage `abgang_winkel` (Standard an; `abgang_winkel_min` 20°, `_max` 75°, `_dmax` 40°): ein Gleis, Stummel = eine Weiche ab geradem Gleis, Kette mit inneren Bahnhöfen, kein Gleis des Plans im neuen Weg → Stummel entfällt, Strecke beginnt ausgerundet an der Weiche (seit 23.11. abends, Muntelier 60° → 42°, Sugiez auf der Geraden) | T7, W53 | Regionalpläne |

---

## 5. Wünsche – Gütemasse, die der Code verbessern darf

Ein Wunsch ist kein Fehler, sondern eine Messzahl je Plan (kleiner = ruhiger). **Neu 13.11. (D. Eckenstein):** der Code darf
Pläne verändern, um diese Zahlen zu senken – auch abgenommene –, und der Vergleich wertet das als Verbesserung.

| Nr | Wunsch | Messung | Gewicht | Stand |
|---|---|---|---|---|
| 5.1 | Keine Treppen (hin und zurück ohne Anschluss dazwischen) | T7 Treppe (ruhe.py) | 8 | gemessen: Bahnhofspläne + Regionen |
| 5.2 | Keine unmotivierten Ecken (Knick > 8° mit kurzen Schenkeln, ohne Weiche/Gleiszahländerung) | T7 Ecke, Z | 4 | gemessen |
| 5.3 | **Weniger S-Kurven** (zwei Gegenknicke auf einem durchgehenden Gleis, auch über Planränder) | W53 (`wuensche.py`; Gleise über Planränder verkettet), E, F3 | 6 | gemessen alle Pläne (17.11.) |
| 5.4 | Parallele Bündel durch Knicke (QK) | QK | 6 | gemessen (alle Pläne) |
| 5.5 | **Gleichmässiger Bahnhofsabstand** im Regionalplan: Abstand je Strecke proportional zur gestauchten Distanz, Streuung klein | W55 (`wuensche.py`): Variationskoeffizient px / km^0,75 benachbarter Bahnhöfe, /10 | 3 | gemessen Regionalpläne (17.11.) |
| 5.6 | **Kurze Bahnhöfe:** Planlänge je Inhalt (Weichenachsen, Perrons) nahe am Median vergleichbarer Pläne; Anlass Onnens-Bonvillars, Rothrist, Tecknau | W56 (`wuensche.py`): Leerlänge (ohne Weiche/Perron/Gleisende ± 40 px, Ausfahrt 2 × 120 px frei) / 100 px | 3 | gemessen Bahnhofspläne (17.11.; Onnens 5, Rothrist 4, Tecknau 1) |
| 5.7 | Wenige Kreuzungen ohne Bauwerk | X | 2 | gemessen |
| 5.8 | Lage nahe an der Karte (Drehung, Achse) | L3a | 0 (Hinweis) | gemessen |
| 5.9 | **Kurze Nebengleise** (20.11.): Neben-, Abstell- und Anschlussgleise ohne Perron/Nummer so kurz wie nötig, Reihenfolge der Weichen bleibt | W59 (`wuensche.py`): seit 23.11. nur **leere** Länge – gerades Stück eines dünnen Gleises zwischen zwei Ereignissen des Plans (Weiche/Knick/Ende irgendeines Gleises) über 80 px, Summe / 100 px (Daniel 21.11.: Cornaux «gut gedrängt» = 0, Onnens «eher zu lang»); seit 23.11. abends zählt ein Perron ≤ 40 px quer daneben als Inhalt (Gleis längs Perron nicht leer, Perronenden = Ereignisse; Travers/Galmiz/Avenches). Kürzen: cfg `leer_max` (px, `spurplan_warp.py`: leerer Abschnitt zwischen zwei Segmentgrenzen – Weiche, Gleisende, Abgang – höchstens so breit, Mindestbreiten bleiben, übrige Abschnitte nicht stärker gestaucht als ohne; seit 23.11. spät); Hand-Linien mit `x:` wandern nicht mit → relativ zu einem Knoten (`n:<id>±px`) schreiben | 0 (nur Messung, Gewicht entscheidet Daniel) | gemessen Bahnhofspläne (V4, 20.11.); `leer_max`: Onnens-Bonvillars 120 (Daniels Wahl 21.11.), Rothrist 150, Tecknau 90, Olten Hammer 150 (Daniel 23.11.: «die drei sollten auch gekürzt werden»; Olten Hammer seit 24.11., V4g: im Regionalplan bleibt das Ende Seite Olten, wo es war – Mitte in `olten_region_lage.json` verschoben –, sonst wird die freie Strecke länger und das Nebengleis südlich Olten schlauft über Gl. 3, G0 GS); Hand-Linien-Pläne kürzen im Override: Colombier Abstellgleis 706 (23.11., 232 → 120 px leer) |

**Vergleich (Regression) – neue Einordnung:** ein geänderter Plan ist
- **Fehler**, wenn eine Regel neu verletzt ist (Topologie, V-, T-, G-Befunde) – egal was sonst besser wird;
- **besser**, wenn keine Regel neu verletzt ist und die Wunsch-Summe sinkt → Differenzbild an Daniel als «Vorschlag: wurde
  besser», er bestätigt kurz (Vorgabe 6.11.); bei abgenommenen Plänen nimmt er neu ab;
- **gleichwertig**, wenn Regeln und Wünsche gleich bleiben → Differenzbild ansehen (Fallstrick: neu erfundene Weiche);
- **schlechter**, wenn die Wunsch-Summe steigt → nur mit Begründung im Nachtrag.
- **egal (nicht melden)**: Verschiebung als Block – ein ganzer Abschnitt oder Bahnhof parallel um wenige px versetzt, Form und Topologie gleich (seit 23.11., Daniel: «für Leser:innen nicht wahrnehmbar»). Im Bericht nicht aufführen; gemeldet werden nur Formänderungen (Knick, Versatz, Länge, Gleis/Weiche).

E9 (abgenommene Pläne dürfen sich nur ohne Topologieänderung ändern) bleibt und ist hier enthalten. **Abnahme = Vergleichsbasis, kein Einfrieren** (13.11.): auch abgenommene und bisher feste Pläne (NE, Basel, Bern, Referenzen) werden aus dem Code erzeugt; der Vergleich zeigt «besser» oder «Fehler».

---

## 6. Ausnahmen je Ort

**Entscheid 13.11.:** Overrides nur für Ortswissen, das nicht in OSM/SBB-Daten steht (z. B. Perronlage Galmiz) – nie für Geometrie oder Topologie; keine Handzeichnung (alt P3 «zuerst Override je Bahnhof», B18 «Handzeichnung, wo die Automatik scheitert» aufgehoben). Ausnahmen sind Daten, keine Regeln: `spurplan/bahnhoefe/*_override.json`, `regionen/*/region.json` (Optionen je Bahnhof),
Werkstatt-Overrides Olten/NE. Jede Ausnahme nennt Regel und Grund; Ziel ist, dass die Liste schrumpft (Hauptgleisweichen,
Topologie und Perronlage nie per Override, Vorgabe Daniel). Bekannte Einzelentscheide: Olten Ost 60° gedreht (E12),
Galmiz Perron südlich / Kreuzungsgleis grün, Rothrist Detailvariante (E11), Kerzers X.
**Liste (17.11.):** `spurplan/code/overrides_liste.py` → `ergebnisse/seite/overrides.md` (jeder Lauf `seite`), je Eintrag Art
(Ortswissen / Schalter / Typvorlage / Geometrie) und Grund. Stand 17.11.: 910 Einträge an 125 Orten – 245 Ortswissen,
351 Schalter, 126 Typvorlage (NE, fällt mit N2), 188 Geometrie (abbauen in V2/N1/N2). Herkunft je Plan steht im Kartenlabel
(«aus Code <Commit> <Datum>» / «fest seit <Datum>»; Referenzen Thun/Ins/Murten/Kerzers seit 20.11. ehrlich «fest seit», sie sind
Dateien). **OSM-Ausnahmen** (seit 20.11., VR): ein Befund der Karte «OSM-Verdacht», den Daniel als richtig bestätigt
(«B Ausnahme»), steht als `"<Code>:<Abk>": "<Entscheid, Datum>"` in `spurplan/netz/osm_ausnahmen.json` und wird nicht mehr
gemeldet; «A OSM korrigieren» heisst: in OSM beheben, nicht im Code umgehen. **HT-Ausnahmen** (seit 22.11., Courtepin): ein HT-Befund, den
Daniel als richtig bestätigt (Anlage real so, OSM unvollständig – z. B. Satellitenbild), steht in `spurplan/hauptgleis_ausnahmen.json`
(Plan, Regel, Lage, Grund); `hauptgleis.py` zählt ihn nicht mehr, zeigt ihn aber im Bericht als «Ausnahme». Eintrag nur auf Daniels Entscheid.

---

## 7. Offene Widersprüche – Entscheid Daniel

Keine offenen. Entschieden 13.11. abends: 7.1 (→ 1.5), 7.6 (→ 1.18); 16.11. (Karte «Fragen an Dani», je A): 7.2 (→ 1.10),
7.3 (→ 1.8), 7.4 (→ 4.5), 7.5 (→ 1.3, 4.4). Neue Widersprüche hier als Zeile 7.x eintragen und als Frage auf die Karte
(`spurplan/fragen/fragen.json`).

---

## Anhang: alte Nummern

Alte Nummern (B, N, E, R, V, F11, Regelkatalog T/L/S/W/A/F/D/Z/P) stehen in der Spalte «alt»; Prüf-Kürzel (G1–G8, T1–T8,
V-, S-, L-Befunde, Prüfstand Q/P/QK/F/K/Z/E/X/T/PF/D) bleiben die Namen der Prüfungen. Vollständige Herleitung:
`REGELN_ARCHIV_bis_2026-11-13.md`, Doc «Regelwerk Spurpläne» (Tabs «Untitled» und «Regelkatalog (Entwurf 24.10.)»).
