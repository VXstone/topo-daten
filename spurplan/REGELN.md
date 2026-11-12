# Regeln für die Spurpläne

Massgeblich ist das Doc **«Regelwerk Spurpläne»** (D. Eckenstein / Claude):
https://claude.ai/code/artifact/4e313295-38e5-4eac-968a-5649cbac5ff9 – dort werden Regeln ergänzt und kommentiert.
Diese Datei ist die Kurzfassung für den Code; Nummern wie im Doc (B = Bahnhof, N = Region, E = Entscheide 20.10., R = seit 17.10.).
Stand 21.10.2026.

## Grundsätze in Rangfolge (gelten vor allen Einzelregeln)
1. Topologie stimmt (jedes Gleis hängt an, wo es real anhängt) – hart
2. Lage stimmt mit der Karte (N/S, O/W, Querreihenfolge) – hart
3. Jede Weiche ab Hauptgleis sichtbar, mindestens als Pfeil – hart
4. Keine 90° (nur 60° mit Ausrundung)
5. Abstand: nie näher als ein Gleisabstand
6. Gerade so lange wie möglich
7. Detailgrad: kleine Bahnhöfe ganze Anlage, grosse Knoten Hauptgleise + Abgänge
8. Darstellung

## Topologie und Reihenfolge
| Nr | Regel | Prüfung im Code |
|---|---|---|
| R2 | Jede Weiche zweigt so vom Gleis ab, wie sie real liegt (Seite und Richtung); Pfeile in weggelassene Anlagen nur drehen, wenn es topologisch stimmt (E2) | noch keine automatische; Override `r38_seite` |
| R3 | Weichen, Spurwechsel und Abzweige von Nebengleisen liegen entlang eines Gleises in der realen Reihenfolge (Ligerz, Schafis) | im Aufbau |
| E3 | Mehrere OSM-Elemente < 20 m (Weichen + Kreuzung), die zusammen ein Gleis kreuzen, sind eine DKW mit Symbol; Klammern verbinden je einen linken mit einem rechten Ast | `dkw_px` von Hand, Automatik offen |
| E4 | Zwei Verbindungen zwischen denselben Gleisen = zwei Achsen, auseinander zeichnen | G8 |
| R14 | Abzweig mit Weichen: eigener Plan (Betriebspunkt) oder im nächsten Bahnhof integriert, nie nur ein Knick | O2 |
| R8 | Jeder SBB-Betriebspunkt hat einen eigenen Plan | O2 |

## Farbe
| Nr | Regel | Prüfung |
|---|---|---|
| B3 | Gleise ohne service grün, Abstell-/Industrie-/Dienstgleise schwarz | – |
| E1 | Jedes Perrongleis über Weichen grün erreichbar; übrige Spurwechsel schwarz | `verbindungen_pruefen.py` |
| R1 | Schwarz hinter grün | Zeichenreihenfolge |

## Geometrie
| Nr | Regel | Prüfung |
|---|---|---|
| B1 | Gleise waagrecht, Verbindungen 60° mit Ausrundung, Figur zwischen ihren Weichenpunkten | – |
| B2 | Gleisabstand 24 px; Nebengleise 55 %, voller Abstand bei Berührung eines Hauptgleises | – |
| R4 | Kein Gleis unter 90°; Ausnahme Tunnelportale, Brückenflügel | G4, `region_winkel.py` |
| R5 | Weichenrundungen überall, auch Pfeilstummel und Einmündungen | G2, G3 |
| E7 | Stoss oder Gleisende > 1 px neben dem Nachbargleis ist ein Befund | G6, G7 |
| E5 | Planrand im Doppelspurabstand, verschiedene Linien im doppelten Abstand | `planrand_pruefung.py` |
| R10 | Knicke nur am Bahnhof | – |
| R11, R12 | Spurwechsel auf freier Strecke nur im geraden, parallelen Stück; Nebengleise nie im Spurwechsel | G5 |

## Inhalt
| Nr | Regel | Prüfung |
|---|---|---|
| R6, E10 | Gleisnummern: SBB-Perronkanten > SBB-Perronflächen > OSM; nur Gleise mit Perron; Halt mit einem Gleis ohne; fehlend «?» | G1, G1? |
| R7 | Stillgelegtes (OSM disused) nicht zeichnen | – |
| R9 | Nebengleise auf freier Strecke bleiben | Regionalplan Prüfung 4 |
| E6 | Anschlussgleise jede Weiche nach OSM, zusammengedrängt | – |
| E8 | Meterspur bis ~40 m neben Normalspur als Stummel mit Ziel | `meterspur_cfg.d_max` |

## Arbeitsweise
- E9: Abgenommene Pläne dürfen sich ohne Topologieänderung ändern; jede Änderung im Differenzbild (R13: jede Runde gegen `vergleich/`).
- Zuerst Override je Bahnhof, neue Regel im Code nur bei Mehrfachnutzen; Overrides über OSM-Nummern statt Pixel.
- Nie selbst abnehmen; Abnahme macht D. Eckenstein.

## Regionen (Workflow «regionen», seit 21.10.2026)
- `spurplan/regionen/<region>/region.json` beschreibt eine Linien-Region (Linien, Äste, Normalspur-Umkreise, Optionen je Bahnhof, Lage). `region_lauf.py <region>` baut daraus alle Bahnhofspläne und den Regionalplan.
- Schmal- und 800-mm-Spur: braun wie die Meterspur in Ins (dick = Streckengleis, dünn = Nebengleis); Normalspur in gemischten Bahnhöfen (Montreux, Zweisimmen) grün/schwarz wie immer.
- Betriebspunkte ohne Weiche erscheinen im Regionalplan als Halt, Betriebspunkte mit Weichen als Spurplan.

## Entscheide 25.10.2026 (D. Eckenstein)
- B14: Perron 110 px, Gleisnummer in der Perronmitte – für alle Pläne, auch Olten, Bern, Basel.
- B13: Perrons aus SBB Open Data für jeden Bahnhof, auch Region Neuchâtel.
- N2: Lage eines Bahnhofs zuerst nach geradestem Streckenanschluss, dann nach Kartenachse; Kreuzungsbahnhof (Kerzers) als X mit zwei Schenkeln.
- B7: Spurwechsel mit Zwischengerade immer zusammenrücken, ausser es liegt wirklich ein langes Gleis dazwischen.
- Galmiz (Einzelentscheid): Perron unten/südlich, nicht zwischen den Gleisen; Kreuzungsgleis darf grün sein (Güter-Kreuzungsgleis).
- Regelkatalog-Entwurf (Stufen T/L/S/W/A/F/D/Z) im Doc, Tab «Regelkatalog (Entwurf 24.10.)»; noch nicht bestätigt.
- Lage geteilt (Grundsatz 2): hart = Reihenfolge der Äste an jedem Knoten und zwischen benachbarten Betriebspunkten (Tecknau nicht südlich von Dulliken); weich = globale Lage weiter entfernter Punkte (nur Hinweis) und Drehung eines Bahnhofs (geht der Linienführung nach).
- Farbe gehört zur Topologie (Stufe 1): grün = im Personenverkehr befahrbar, aus den Fahrwegen berechnet. Durchfahrgleis (beidseitig über Weichen am Streckengleis, parallel) grün, auch als siding; Ausnahme service=yard. Signale in OSM zu lückenhaft.
- B7 «langes Gleis» = Gleis mit Perron oder Gleisnummer.
- B17 grosser Knoten = grosse Nebengleisanlage (Olten, Bern, Basel, Däniken RB, RB Limmattal, Buchs SG, Bern Weyermannshaus; nicht Olten Hammer). Schwelle aus OSM, daran geeicht.
- Grundsatz 3 auch in grossen Knoten: jede Weiche einzeln als Pfeil.
- B2: Fehlt Platz, Nebengleise enger statt Plan länger, Untergrenze 40 % (~10 px).

## Verkettung (D. Eckenstein 29./30.10.2026)
- Jede Hauptgleisweiche gehört zu einem Betriebspunkt und steht in dessen Plan (im Code, nicht per Override).
- Ein- und Zweispurwechsel erkennt der Code selbst (Gleiszahl je Strecke aus OSM bzw. aus den verketteten Plänen).
- Pfeile und Abgänge kommen beim nächsten Bahnhof an: im Regionalplan werden Pfeilpaare als Gleis verbunden; Prüfung V1 (Gleiszahl beidseits), V2 (Pfeil gegen Abgang), V3 (Gleis kommt nicht zurück) in `verkettung.json` / `bericht.json`.
- Parallele Linien auf einer Doppelspur (Klosters Platz – Klosters Dorf) sind eine Strecke mit beiden Liniennummern.

## Strangbild (D. Eckenstein 3.11.2026)
- Aus OSM allein: Betriebspunkte mit ihren Weichen (und Perrons/Halten) sind Knoten, durchgehende Streckengleise zwischen zwei Knoten sind Stränge. Ein Gleis berührt einen Betriebspunkt nur an einer Weiche, einem Perron oder als Halt; eine Kreuzung ohne Weiche zählt nicht.
- Ein Strang gehört nur den beiden Betriebspunkten an seinen Enden; er wird nie im Plan eines dritten gezeichnet.
- Fahrbeziehungen je Betriebspunkt (über Weichen fahrbar, keine Spitzkehre) und Dreiecke kommen aus dem Strangbild (Vereina: Sagliains Sasslatsch – Sasslatsch – Autoverlad).
- Die Regionaltopologie kommt aus dem Strangbild. Prüfung S1 (Streckengleise je Nachbar = Gleiszahl), S2 (Abgang je Fahrbeziehung vorhanden), S3 (Fahrbeziehung im Plan durchgehend gezeichnet).
- R33b: Streckengleis nach der letzten Weiche ohne weitere Abzweigung läuft auf seiner Ebene gerade aus dem Plan (Klosters → Selfranga).
  Seit 6.11. nicht im parallelen Bündel: liegt im Doppelspurabstand (< 8 m) ein Gleis daneben, das schräg bleibt, oder auf
  beiden Seiten ein Gleis, bleibt das Gleis schräg (Regression Olten 3.11.–6.11.: unterbrochene Gleise).

## Knotenpläne (3.11.)
- Pläne werden nur an ruhigen Stellen geschnitten: Strang ohne Weiche ≥ `knoten_ruhig_m` (500 m). Liegen zwei Betriebspunkte mit eigenen Weichen näher beieinander, entsteht ein gemeinsamer Plan (Titel nennt alle, Hauptpunkt = Personenbahnhof bzw. meiste Weichen). Halte ohne Weiche schneiden nie. Ausdehnung höchstens `knoten_max_m` (2500 m). `knotenplaene: false` = ein Plan je Betriebspunkt.
- Ablauf: region_vorbereiten → straenge --knoten (knoten.json) → region_vorbereiten mit knoten.json → wie bisher.
- Nur Mehrgleiszonen werden zusammengelegt (Strecke mit ≥ 2 Gleisen); ein kurzer einspuriger Schenkel bleibt Schnittstelle/Abgang (`knoten_einspur: true` legt auch diese zusammen). Dreiecke bleiben so im Regionalplan Dreiecke: Achse (Susch – Sagliains), Schenkel der Zulaufstrecke je unter 90° (D. Eckenstein 3.11.: «die Lösung, die am meisten Ruhe bringt, je nach Ort»).
- Ergibt Vereina: Sagliains · Autoverlad; MOB: keine Änderung.
- 3.11. abends (Sagliains – Susch): Rest eines fremden Strangs aus lauter künstlichen Punkten fällt aus dem Ausschnitt (straenge --bereiche; 960-Stück im Plan Sagliains Sasslatsch). Regionen: `haupt_fortsetzung` 0.15 (Hauptgleis läuft an der Weiche im Hauptgleis weiter, nicht im Nebengleis), Regel `r28e` (Personengleis am Randpunkt läuft längs an den Planrand statt 60°-Stummel), `r49` (zu eng für 60°: volle Schräge statt 90°). Bahnhöfe aus «plaene» unverändert (abgenommen).

## Topologie über die Region (3.11. abends, oberste Regel)
- Regionalplan verbindet Gleise zwischen zwei Plänen nach Strang (Strang-Nummer der Anschlüsse aus verkettung.py), nicht oberstes mit oberstem. Anschlüsse ohne Liniennummer, deren Gleis im Plan am anderen Ende ankommt, gehören ins Bündel (Selfranga).
- Gerade Strecke mit kleinem Seitenversatz zwischen gegenüberliegenden Anschlüssen: ein Versatz ≤ 30° in der Mitte statt Zickzack (Lage-Option `ein_versatz`, Standard an bei automatischer Lage).
- Prüfung `netz_lage --pruefen` → topologie_region.json, Bericht «topologie_region»: T1 Gleis endet im Leeren, T2 Gleissprung (nach Strang verbunden und gekreuzt), T3 Streckengleis laut Strangbild nicht angeschlossen, T4 Strecke nach Lage statt nach Strang verbunden (nur direkte Strecken ohne Halt dazwischen).
- Drehung der Knotenbahnhöfe (lage_auto): je Planseite eine Stimme statt je Anschluss (`seiten_stimme`, Standard an). Sagliains Sasslatsch: zwei Tunnelgleise überstimmten den Schenkel zum Autoverlad (V-Form) → jetzt 0°; Montbovon 150° → 120°. `peilung_ziel` (Peilung zum Zielbahnhof) ausprobiert, verschlechterte Zweisimmen/Rochers de Naye → Standard aus.
- Planfenster aus dem Strangbild (3.11. abends): jede Weiche, an der ein Strang des Betriebspunkts beginnt, liegt im Plan (straenge anker_m → sw_search_m). Montbovon: Zusammenlauf nach La Tine 399 m (Suche 350 m) → sah aus wie Doppelspur.
- Ast-Gleise, die in ein Streckengleis der Region münden, werden ganz übernommen (`aeste_muendung`); Montbovon Gl. 3 Süd (TPF) war am 300-m-Kreis abgeschnitten und erschien als «247 Bulle».
- Perron frei (`perron_frei`, Regionen): Perronbalken auf den freien Abschnitt gekürzt, unter 24 px weg (Flendruz: Perron fällt weg – offen).
- Knotenplan über Nebengleis (`knoten_nebengleis`, nur bis 600 m Abstand der Betriebspunkte). Sagliains + Sagliains Sasslatsch (1,2 km) getestet: Plan verlor Tunneleinmündung und Schenkel, 6 Topologie-Befunde → nicht zusammengelegt.
- Hauptgleis aus Funktion (`hauptgleis_funktion`, Regionen): Nebengleis gilt als Hauptgleis, wenn es Perrongleis ist (≤12 m neben einem Perron ohne anderes Hauptgleis, Lenk), wenn es ein endendes Streckengleis bis zum Perrongleis fortsetzt, oder wenn eine Kette von Verbindungen mit usage=main/branch zwei Streckengleise verbindet (Zweisimmen Zufahrt Gl. 3/5).
- R28f (Regionen): Streckengleis im Bogen nahe am Planende läuft an den Planrand statt als Stummel (Gruben, La Tine).
- Perronfarbe nach Spur der anliegenden Gleise (Schmalspur braun), Halte im Regionalplan in Linienfarbe.
- Feedbackkarte: Label der Regionalpläne automatisch aus bericht.json (Stand, Topologie, Verkettung) + «notiz» (regionalplaene.json).

## Ruhe und Topologie (3.11. spät)
- Kette: durchgehendes Gleis der inneren Bahnhöfe auf der Kettenachse (Anschlusspaar mit kleinstem Querversatz, `gerade_kette`).
- Regel 16 (Abgang am Datenrand) nur an echten Way-Enden – Saanen: Weichenknoten mitten im Streckengleis galt als Datenrand, Hauptgleis-Stück fehlte (betrifft alle Pläne, im Workflow plaene geprüft).
- T5 (gleisenden.py, je Bahnhofsplan): Streckengleis endet im Leeren (nicht an Gleis, Anschluss, Pfeil, Prellbock, Planrand oder seitlichem Abgang).
- T6 (netz_lage --pruefen): Haken – Strecke kehrt um > 120° oder läuft gegen die Anschlussrichtung in den Plan.
- T5/T6 stehen im Bericht unter «topologie_region» und damit auf der Feedbackkarte.
- R36b (Regionen): Weiche direkt vor dem Planrand mit Haupt- und Nebengleis – das Streckengleis läuft weiter (Sendy-Sollard: Kreuzungsgleis lief als «Montreux» weiter, Streckengleis fehlte).
- Gleis bleibt Gleis (`gleis_mindestlaenge`, Regionen): gerades Gleis mit Ebenenwechsel an den Enden behält ≥ 40 px bzw. 35 % seiner Länge (Sendy-Sollard: 190-m-Kreuzungsgleis auf 32 px gestaucht; Flendruz: Perron wieder da).
- Halt bleibt Halt (netz_lage `halt_ohne_schlaufe`): Halte ohne Weiche nie als Schlaufe.
- Offen: Château-d'Oex – durchgehendes Gleis wechselt im Plan zwei Ebenen (links Gl. unten, rechts oben) → Versatz auf den Nachbarstrecken (La Chaudanne, Les Granges). Lösung: Punkt 4 (durchgehendes Hauptgleis im Plan gerade).
- 4.11.: R27b ergänzt keine Weiche über ein drittes Gleis hinweg (La Tine: Stumpen, nur Seite Zweisimmen angeschlossen). Prellböcke an Meterspur braun.
- Punkt 4 «Einspur gerade durch»: im Bahnhofsplan (`einspur_gerade`) zerlegt es die Weichenstrasse (Château-d'Oex) → aus. Stattdessen im Regionalplan «Kippen statt Versatz» (lage_auto `kipp_max` 8°): liegen Ein- und Ausfahrt eines Kettenbahnhofs quer versetzt, wird er so gedreht, dass beide auf der Kettenachse liegen. La Tine – Flendruz jetzt eine Gerade.

## Ruhe (4.11.)
- Definition (D. Eckenstein): Ruhe = keine Treppen und keine unmotiviert erscheinenden Ecken – unmotiviert, weil auf kurzem Stück und ohne sonstige Änderung (keine Weiche, keine Gleiszahländerung, kein Abzweig).
- Prüfung T7 (ruhe.py): je Bahnhofsplan (Streckengleise) und im Regionalplan (Strecken und Nebengleis-Verbindungen ausserhalb der Spurpläne). Treppe = innerhalb 100 px > 12° hin und zurück (Netto < 6°) ohne Anschluss dazwischen; Ecke = Knick > 8° mit beiden Schenkeln < 40 px, unbegründet. Bericht «ruhe» {treppen, ecken}, Feedbackkarte «Ruhe: …».
- Pfeilpaare (verkettete Nebengleise) in Querreihenfolge gepaart und mit dem Strecken-Connector gezeichnet (Sagliains Sasslatsch – Autoverlad: keine Kreuzung, keine Treppe).
- Kleiner Versatz zwischen gegenüberliegenden Anschlüssen (≤ 8°, `schraeg_max`): leicht schräge Gerade statt Treppe.
- Dreischienengleis (OSM gauge «1000;1435»): grün mit braun gestricheltem Strich darüber (alle Pläne; Zweisimmen Gl. 6/7, Chur–Ems, Worblaufen–Zollikofen).
- Pfeile nur nach aussen (`pfeil_aussen`, Regionen): zeigt ein R38-Pfeil auf ein Nachbargleis (innerhalb 1,5 Ebenen), wird stattdessen ein Stumpen gezeichnet (Schräge bis knapp vor die Mitte, kurzes Gleis in Richtung der Anlage, Prellbock, ausgerundet) – nicht ersatzlos löschen (D. Eckenstein 4.11.).
- Perronlage dort, wo seine Gleise liegen (`perron_abschnitt`, Regionen): Zweisimmen 7/8 (OSM 845 m, Gl. 8 endet vorher) sass auf Gl. 8.
- Offen Zweisimmen: Einfahrt wirkt einspurig/DKW (Gstaad- und Lenk-Linie laufen über Verbindungen zusammen); Perron an Gl. 12 fehlt in OSM.

## Randzone (4.11., D. Eckenstein: Streckengleise am Planrand im Standardabstand)
- Streckengleise treten am Planrand im Standardabstand aus: gleiche Linie **oder ein Gleis ohne Liniennummer** eine Ebene (24 px), zwei verschiedene Linien zwei Ebenen (E5). Gilt in Regionen (`randzone`, via region_lauf an); SBB-Bahnhöfe aus «plaene» unverändert (Prüflauf offen, Punkt 2).
- Ablauf im Schema (nach A4): zuerst die ganze Kette auf die Nachbarebene, wenn Ziel- und Zwischenebenen frei sind. Sonst nur das Randstück: eine gerade Teilstrecke (≥ `randzone_m` 60 m) hinter der letzten Belegung wird Schräge, das Stück bis zum Rand liegt im Standardabstand. Versetzt wird die Kette mit weniger Streckengleis – das durchgehende Hauptgleis bleibt liegen (Sagliains Sasslatsch).
- Lage der Schräge: am inneren Ende, gleich hinter dem Ende des Gleises auf der Zielebene (6 px Luft). Beginnt am selben Weichenknoten ein Gleiswechsel in dieselbe Richtung, liegt die Schräge auf ihm (Gleis biegt auf der Zielebene ab, der Gleiswechsel läuft weiter – Selfranga Gl. 2). regel_pruefung meldet das als G8 (gewollt).
- Beschriftung: Abgang ohne Liniennummer neben Abgang mit Nummer und gleichem Ziel (≤ 1,5 Ebenen) gehört ins Bündel – eine Beschriftung «Linie 910 / Sagliains».
- Gleiswechsel (service=crossover) zwischen zwei verschiedenen Streckengleisen ist immer Schräge, auch ohne Querversatz in OSM (Vernex: Streckengleise schwingen ±3,5 m auseinander, Wechsel liegen gerade in der Mitte).
- `hauptgleis_funktion` c) gilt nicht für Spurwechsel: Kette zwischen zwei parallel laufenden Streckengleisen derselben Linie (jedes Ende ≤ 6 m neben dem anderen Gleis) bleibt Gleiswechsel (Vernex Linie 100 lag im doppelten Abstand). Zweisimmen unverändert.
- planrand_pruefung: Gleis ohne Liniennummer neben einer Linie = Doppelspurabstand (vorher 48 px verlangt).

## Bestehende Regeln sauber (4.11. abends, D. Eckenstein: «zuerst die bestehenden Regeln dort, wo wir prüfen»)
- R28f nur, wenn das Gleis am Schnitt ≤ `r28f_d_max` (8 m) neben der Achse liegt. Sasslatsch: die abzweigende 960 nach Sagliains (54 m daneben) wurde an den Planrand gezogen – Haken an der Weiche, Strecke endete im Leeren (T5). Ebenso betroffen: Montbovon, Montreux, Chamby, Zweisimmen, Glion, Klosters Platz.
- T6 Haken neu: aufsummierte Richtungsänderung über ≤ `haken_px` (120 px) Strecke inkl. Anschlussrichtung beider Pläne, Grenze `haken_grad` (110°). Die alte Fassung drehte die Anker doppelt (Fehlalarme, z. B. Klosters Platz – Abgang 910) und sah Umkehr aus zwei Knicken nicht.
- T8 (neu): zwei Halte einer Strecke näher als 90 % von `halt_abstand_min` (60 px).
- Nur Linien-Regionen (`auto.linien_region`, setzt region_lauf; Olten/Neuchâtel byte-gleich):
  - Halte bekommen Platz: Zwischenraum einer Strecke mit h Halten mindestens (h + 1) × `halt_abstand_min`, Halte gleichmässig über die ganze Strecke (Château-d'Oex – Flendruz: La Palaz, Les Granges, Les Combes lagen 40 px auseinander).
  - Seitlicher Anschluss gibt in der Ausgleichsrechnung nach (`seite_nachgiebig` 0.6).
  - Zwischen zwei Plänen auch die direkte Gerade von Anschluss zu Anschluss (mit kurzen Stummeln zum Ausrunden), statt Absatz/Treppe (Sagliains Sasslatsch – Sasslatsch). Nicht für Abgänge.

## Haken (4.11. spät)
- Kurvenbahnhof (Linien-Regionen, `peilung_ziel_ab` 60°): weicht die Gleisrichtung am Planrand um mehr als 60° von der Richtung zum Nachbarplan ab, zählt für die Drehung die Richtung zum Nachbarplan (Klosters Platz: Gleis zeigt am Südende nach Westen, Selfranga liegt im Süden). Global (`peilung_ziel`) bleibt aus – es verdrehte Sasslatsch.
- Abgang gerade aus dem Plan (Linien-Regionen, `abgang_knick` 60°): liegt der Abgang mehr als 60° neben der Anschlussrichtung (Kehre gleich nach dem Plan, Klosters – Davos), kommt er in Anschlussrichtung.
- Abgangsziel: hat ein anderer Abgang desselben Bahnhofs schon dieses Ziel, gilt der andere Ort der Linie (915 Davos statt Landquart).
- Kein eigener Abgang (Strangbild): offenes Ende eines Gleises ohne Liniennummer, dessen Fortsetzung nach < 300 m endet oder dessen Fernpunkt ≤ 1 km neben dem Fernpunkt eines Abgangs mit Liniennummer liegt (Zweisimmen Gl. 86/87 Richtung Umspuranlage: Phantom «Linie None / Spiez» mit 2 Gleisen).

## Perrons, Portale, Schiebebühne (4.11. spät)
- Jeder Perron aus OSM wird gezeichnet (Regionen `perron_min_m` 3 m statt 20 m: Valmont, Toveyre, Paccot, Crêt-d'y-Bau, Le Tremblex hatten keinen Perron), mindestens `perron_min_px` 40 px. `perron_frei` löscht nie mehr: reicht der freie Abschnitt nicht (< 24 px), gilt die Mindestlänge; reicht er, bleibt er (Chamby: nicht in den Weichenbogen).
- Prüfung P1 (region_lauf, perrons.json): Perron aus OSM (≥ 10 m) nicht gezeichnet. Alter Stand hätte 10 Bahnhöfe gemeldet.
- Portale: Klammer nur, wo alle Gleise gerade und parallel laufen (±18 px, Linien-Regionen; sonst ±9 px wie bisher); Punkte der Nachbargleise quer zur Strecke statt gleicher Längenanteil. Ohne Platz mit vollem Fenster schrittweise kleiner (Selfranga – Selfranga Süd ist nur 61 px lang). Klosters Platz: Portal vom Knick aufs gerade Stück.
- Schiebebühne (Regionen `schiebebuehne`): Way mit railway=traverser oder note «shifting/traverser/Schiebebühne»; beidseits offene kurze Gleise daneben sind Depotgleise: gemeinsamer Anfang, mindestens 40 px, Bühne als gestrichelte Querlinie (Glion). regel_pruefung überspringt gestrichelte Symbole.

## Verkettung MOB, Sagliains (5.11.)
- Kreuzungsgleis (`kreuzungsgleis_m` 600 m): Nebengleis mit beiden Enden als Weichen auf demselben Streckengleis gehört mit beiden Weichen zum Betriebspunkt des näheren Endes – in region_vorbereiten (Bereichskerne) und straenge (Anker). Belmont – Châtelard: V1/V2 weg, Belmont zeigt das ganze Gleis.
- Streckenende ohne Weiche (Regionen `fenster_streckenende`): endet ein Streckengleis und läuft nur ein Nebengleis weiter (auch «Hauptgleis aus Funktion»), zählt der Punkt fürs Planfenster; straenge `anker_m` zählt ihn mit +60 m. Lenk: Abgang «Linie 321 ← Zweisimmen» statt Abstellgleis ohne Nummer (V3, S1 weg).
- Gezeichnete Knoten (ports.json `knoten`) enthalten auch Schrägen von Nebengleisen; S3 sah den Weg Blonay → Abstellgleis-Schräge → Hauptgleis in Chamby als unterbrochen.
- Pfeilverbindungen knicken nicht an der Pfeilspitze (Linien-Regionen): Sagliains Ladegleise ohne Knubbel (G6). Offen: V der Ladegleise – der Pfeilstummel zeigt nach aussen, die Ladegleise kommen von der anderen Seite; braucht im Bahnhofplan das Wissen, welche Pfeile verbunden werden (längs statt Pfeil).
- Bekannt: G8 «deckungsgleich» meldet den Randstummel (22 px über dem Gleisende, alle Pläne) – Prüffehler.
- Perron an mehreren Gleispaaren (5.11., D. Eckenstein Zweisimmen: «zuerst zwischen 7 und 12, dann zwischen 7 und 8, weil es sich zwischen 7 und 12 öffnet»; Regionen `perron_teile`): der Perronumriss wird je 10 m dem Gleispaar zugeordnet, zwischen dem er liegt (nächstes Gleis je Seite bis 14 m); jedes Paar über ≥ 50 m bzw. 12 % der Länge bekommt einen eigenen Balken genau zwischen seinen Gleisen. Zweisimmen: Balken 7/8 und 7/12.

## Messung (Stufe A, 5.11.)
- G8 «deckungsgleich» zählt keine Schindel mehr: endet eine der beiden Linien in der Überdeckung, ist es dasselbe Gleis doppelt gezeichnet (Weichenbogen läuft aufs Gleis aus, Ketten überlappen am Stoss). Gezählt werden nur Linien, die beidseits über die Überdeckung hinauslaufen. Vorher: Olten 27, Solothurn 13, MOB/Vereina je 8 Fehlalarme.
- T6 Haken berücksichtigt bei seitlichen Anschlüssen auch den Knick im Plan (60°-Stummel auf die Planachse): Les Sciernes – Montbovon wird jetzt erkannt.
- Unruhe-Wert (qualitaet.py `unruhe`, `GEWICHTE`): eine Zahl je Plan/Region, kleiner ist besser. Topologie 50 je Befund (T1–T8, V/S, A–F), P1 30, Treppe 8, Ecke 4, G4/G7 10, G6/G8 3, G2 2, Netzbefund 2, Planrand/Randabstand 5. Regionen: Bericht `kennzahlen`, `unruhe`, `unruhe_teile`, Vergleich mit `regionen/<r>/basis.json` (`region_lauf.py <r> --basis` schreibt sie neu); Feedbackkarte «Unruhe N (±Δ zur Basis)». Neue Kennzahlen gelten nicht als Verschlechterung.
- T7 (ruhe.py) läuft auch im Workflow `plaene` (Kennzahlen ruhe_treppen/ruhe_ecken je Bahnhof).
- Rechenumgebung in allen Workflows fixiert (OPENBLAS_CORETYPE=Haswell, 1 Thread, PYTHONHASHSEED=0); CPU-Info in `umgebung.txt`. Anlass: zwei Seiten-Builds je Commit ergaben abwechselnd zwei Fassungen von Olten/Neuchâtel.

## Lage gegen die Karte und Suche (Stufe C, 5.11.)
- Grundsatz 2 als Befund (netz_lage --pruefen → lage_pruefung.json, Bericht `lage`): L2 Paar Nord/Süd bzw. Ost/West vertauscht (ohne Abgänge), L3 Planachse > 60° neben der Karte, Abgänge seitenverkehrt, Streckenreihenfolge, L4 Abgangsrichtung > 100° neben der Richtung zum Zielort (orte.json; nicht zum Datenrand – die 915 fährt ab Klosters zuerst nach Nordwesten). Gewichte im Unruhe-Wert: L2 10 (paarweise), L3 20, L4 30.
- Suche für die Regionallage (`lage_suche.py`, in region_lauf vor der endgültigen Lage): je Knotenbahnhof (automatisch auf 30° gedreht) Drehung ±30/60/90° probieren, je Bahnhof die beste Variante übernehmen, wenn sie den Unruhe-Wert um mindestens `auto.suche_min` (6) senkt; bis keine Verbesserung mehr oder `auto.suche_max_sek` (1500 s). Gemessen wird, was von der Lage abhängt: Topologie Region, L2–L4, G2–G8, Ruhe Regionalplan. Protokoll lage_suche.json, Bericht `lage_suche`. Aus: Lage `auto.suche: false`.
- Ergebnis 5.11.: MOB Haken 3 → 0 (Montbovon 60°, Montreux 30°, Rochers de Naye 60°, Chamby −30°, Lenk 0°, Zweisimmen −60°), Unruhe 797 → 617; Vereina Sagliains −60°, Unruhe 79 → 59.
- **Geografie leitet die Reihenfolge, nicht die Lage** (D. Eckenstein 5.11.2026 21:20): Was auf der Karte klar nördlich (östlich) liegt, darf im Plan nicht südlich (westlich) liegen (Tecknau nicht unterhalb Dulliken) – auch nicht, weil am Nachbarknoten ein Abgang zu beiden Orten führt. Gleiche Höhe ist erlaubt, wenn nötig (Ins auf Höhe Lyss); Abstand und Winkel sind frei. Umsetzung: L2 bleibt (Paare ≥ 1,5 km auf der Karte, Umkehr erst ab 60 px im Plan – gleiche Höhe ist kein Befund). Achse > 60° neben der Karte ist kein Mangel mehr, nur Hinweis **L3a** (Gewicht 0, nie «schlechter»); L3 bleibt für seitenverkehrte Abgänge und Streckenreihenfolge. **Grob parallele Linien** (D. Eckenstein 5.11. 22:29, Rochers de Naye südlich der MOB 100, beide von Montreux nach Osten): bei Paaren auf verschiedenen Linien (keine gemeinsame Liniennummer, Hauptrichtungen < 60° auseinander) zählt nur die Seite quer zur gemeinsamen Richtung, nicht die Lage längs davon.

## Gleisenden, Bushalte, Perron-Standardlänge (5.11.2026, Rückmeldung MOB)
- **Echte Gleisenden** (Regionen): region_vorbereiten schreibt je Betriebspunkt `gleisenden` = Knoten, die auch in den Schweiz-Daten nur an einem Gleis hängen; region_lauf gibt sie als cfg `gleisenden` weiter. Sie gelten nie als Datenrand → Stumpen mit Prellbock statt Abgang mit Pfeil (Rochers de Naye).
- **R27b**: endet daneben (< 30 m) ein weiteres Gleis, ist es ein Kopfbahnhof mit Stumpfgleisen, keine fehlende Weiche.
- **R27b (6.11.)**: nie bei einem Gleis mit eigener OSM-Gleisnummer (`railway:track_ref`, Zofingen Gl. 40) und nie auf ein
  Gleis auf Brücke/im Tunnel/anderer Ebene (Aarburg-Oftringen, Aarebrücke). Regressionen seit 29.10., abgenommene Pläne.
- **Bushalte**: highway=platform ohne railway=platform, im Mittel > 6 m vom nächsten Gleis, ist kein Perron (Montbovon «Montbovon, gare», Lenk A/B/C). Bahnperron nur als highway=platform (St. Stephan, 1,8 m) bleibt.
- **Perron-Standardlänge** (Regionen, cfg `perron_standard_px` 80): jeder Perron gleich lang um seine Mitte, perron_frei kürzt auf den freien Abschnitt; Perronteile (Zweisimmen) bleiben.

## Antworten D. Eckenstein 6.11.2026 (Gleisnummer aus ref, Perrons beidseitig, Pfeile, Kreuzungen)
- **Parallel bleibt parallel:** parallele Gleise behalten denselben Abstand quer zum Gleis, in jeder Drehung und jedem Abgangswinkel (Plan in `IDEEN_REVIEW.md` «Standards / Blaupausen-Prüfstand»). Standardisiert wird der Abstand, nicht der Winkel.
- **Caux:** 4 Weichen, Plan stimmt (auch Satellitenbild). Der Stumpen aus Gl. 2 Richtung Rochers-de-Naye ist ein Nebengleis → dünn zeichnen, nicht fett.
- **Gleisnummer aus `ref`:** Gleise mit `ref` in Gleisnummernform sind Gleise, keine Linien (Susch Gl. 1, Montreux Gl. 4). Montreux Gl. 4 hat Zugsverkehr → gehört in den Plan; MOB-Schalter `gleisnummer_aus_ref` wieder einschalten, sobald der Plan damit stimmt.
- **Perron beidseitig / Spezialperrons:** ein Gleis kann auf beiden Seiten einen Perron haben. Montreux: Mittelperron 3/5 öffnet sich, Gl. 4 liegt dazwischen mit Perron auf beiden Seiten (bedient von 3 her); Gl. 7 hat beidseitig Perron (bedient von 6 her, der andere ist einfach vorhanden). Ebenso Zweisimmen. Echte Zwillingsperrons (beide Seiten bedient): Le Noirmont, Renens m1. Kein Perron darf deswegen wegfallen (P1).
- **Perron-Standardlänge 80 px** (Linien-Regionen): bestätigt.
- **Nebengleise:** Strichstärke bleibt wie sie ist (keine weitere Hierarchie). **Pfeile an Meterspur braun** (sind noch schwarz).
- **Kreuzung ohne Verbindung:** Lücke im untergeordneten Gleis nur bei echter Niveautrennung (Brücke, Über-/Unterführung, Tunnel). Gleisdurchschneidung (Kreuzung auf gleicher Ebene, z. B. Kerzers) → beide Gleise durchgezogen. Details folgen (D. Eckenstein).

## Antworten D. Eckenstein 6.11.2026 abends (nach Schritt A)
- **Wangen bei Olten:** neuer Stand passt (nur Perron).
- **Kerzers:** Gl. 2 und 5 bleiben ohne Nummer – Nummern nur an Perrongleisen (R6/E10 bestätigt).
- **Verbundene Perrons / Spezialperrons** brauchen eine eigene Lösung im Code: Thun Gl. 16/18 hängen an Perron 1,
  Montreux (verbundene Perrons), Zweisimmen, Bern Gl. 49/50, Basel um Gl. 3 und um Gl. 35. Deshalb kommt die Perronfrage
  (kürzere 110-px-Perrons in abgenommenen Plänen) nach diesem Schritt nochmals; bis dahin nichts zurückstellen.

## Regression über alle Pläne (6.11.2026, Befund Olten)
- Jede Runde vergleicht `code/alle_plaene_pruefen.py` alle Pläne der Feedback-Seite mit ihrer Abnahme-Fassung (sonst erste bzw. zuletzt veröffentlichte Fassung). Geänderte Pläne brauchen eine Erklärung (Regel nach E9 oder Fehler) und ein Differenzbild für Daniel. «Byte-gleich» nur noch behaupten, wenn dieser Lauf es zeigt.

## Verschachtelte Weichenanlagen – Referenz Montreux Westende Gl. 5/6 (D. Eckenstein 7.11.2026, bestätigt 23:00)
Referenzbild (Soll): `vergleich/montreux_westende_skizze.png` (Fassung 3). Gilt für Schritt E (DKW-Automatik) und als
Baustein im Prüfstand (Schritt 1).

**Aufbau (Topologie, stimmt 1:1 mit OSM):**
1. Ab Prellbock je eine **spitze Weiche gegen das andere Gleis**: auf 6 (W 1126121816 → Way 97211358/8290-Ast), auf 5
   (W 1126121501 → Way 97211375).
2. Die beiden Schrägen kreuzen sich im **Mittelstück** (X 2793859963, OSM `railway_crossing`) – zusammen eine Schere.
3. Jede Schräge endet auf dem anderen Gleis in einer **DKW in Fortsetzung des Gleises**: auf 6 DKW 1126121469, auf 5
   DKW 207308647. In OSM je eine Kreuzung mit vier Weichen ≤ 20 m und zwei kurzen Bogen-Ways (E3).
4. Die Stränge nach aussen kreuzen je ein Gleis als **Durchschneidung** (keine Verbindung): der Ast aus der DKW auf 6 den
   Ast von Gl. 7 (X 1126121838), der Ast aus der DKW auf 5 die Zufahrt von Gl. 4 (X 8914106524).
5. Gl. 7 läuft ohne Weiche in den **Ast von 7**; dieser bildet mit dem Gleis von 6 die **DKW 1126121977** und geht stumpf in
   das Streckengleis (W 1126122400). Gl. 6 läuft nach der DKW 1977 in einen Stumpen.
6. **Gl. 4 geht nur in Gl. 5** (W 2793859953, stumpf).
7. Der Ast aus der DKW auf 6 hat nach der Durchschneidung die **Verbindung zur Rochers-de-Naye** (W 1126121532, einzige
   Verbindung MOB–MGN), **stumpf von links**, und endet im Stumpen. Der Ast aus der DKW auf 5 öffnet nach der Durchschneidung
   mit W 1126122358 ins **Abstellfeld**.

**Zeichenregeln (allgemein, nicht nur Montreux):**
- **V1 Einheitlicher Winkel:** alle Diagonalen einer Anlage unter demselben Winkel (60°); nicht variieren, um Platz zu
  gewinnen.
- **V2 Durchschneidung mittig:** jede Kreuzung ohne Verbindung (Mittelstück einer Schere, Durchschneidung) liegt in der
  Mitte zwischen zwei Diagonalen – nicht auf einer Gleisebene. Gleise, die dort enden und weiterlaufen (Gl. 7 → Ast von 7,
  Gl. 4 → Zufahrt in 5), werden dafür selbst zur Diagonale.
- **V3 Eine Schräge, eine Linie:** eine Schräge läuft gerade durch Mittelstück, DKW und Durchschneidung (R45), keine
  Hilfsebenen dazwischen.
- **V4 DKW an Ort:** eine DKW bleibt auf ihrem Gleis, mit Symbol; die Bogen-Ways und ihre Weichen zeigt das Symbol. Die
  durchgehenden Gleise (hier 5 und 6) laufen gerade weiter.
- **V5 Fett** nur die Perrongleise und die Fahrwege von den Perrongleisen ins Streckengleis (Montreux: von 6 und 7 über
  DKW 1977, von 4 über W 9953). Schere, Äste zum Abstellfeld und zum Stumpen dünn.
- **V6 Abzweigrichtung wie real:** stumpf/spitz und links/rechts einer Weiche wie in OSM (Rochers-de-Naye stumpf von links).

**Backlog (Idee D. Eckenstein):** Topologie in zwei Durchgängen – einfache Lösung, Plausibilitätsprüfung («ach nee»),
dann nur die auffällige Stelle mit feinerem Suchradius und Mustern (Schere, DKW, EKW, Durchschneidung). Siehe
`IDEEN_REVIEW.md`.

## Abgleich Plan gegen OSM (V1, 12.11.2026, D. Eckenstein «wir übersehen was»)
Gemessen auf der gezeichneten Geometrie gegen OSM über das Netzmodell (`code/osm_abgleich.py`, Workflow «seite», je Plan
`ergebnisse/seite/osm_abgleich/<key>.json`; Zähler messen die Topologie nicht). Alle V-Regeln zählen in der Regression zur Topologie.
- VA1 OSM-DKW/EKW ist im Plan als DKW gezeichnet · VA2 keine DKW-Bögen ohne OSM-DKW/EKW
- VB1 jede OSM-Weiche auf gezeichneten Gleisen hat einen Abzweig im Plan · VB2 jeder Abzweig im Plan (≥ 3 Richtungen) hat in OSM
  eine Weiche, DKW oder Kreuzung (auch «Gleis über Gleis»; Niveautrennung = weisse Lücke, zählt nicht)
- VC1 die am Abzweig angeschlossenen Gleise gehören in OSM zu dieser Weiche (z. B. Gleisfeld an Gl. 5 statt Gl. 4)
- VD1 Gleis auf Gleis (> 12 px deckungsgleich) · VD2 Perron auf Gleis
- Zuordnung eins zu eins: längs bis 40 px frei (gestauchte Weichenstrassen über die Ways bis 150 px), quer gleiche Ebene.
- Kennzahl Hinweis-Abdeckung (`code/hinweis_abdeckung.py`, `ergebnisse/seite/abdeckung.md`): offene Hinweise mit Befund < 40 px.
