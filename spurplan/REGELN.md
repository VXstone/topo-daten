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
