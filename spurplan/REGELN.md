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
