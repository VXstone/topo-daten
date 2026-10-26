# Schematische Spurpläne aus OSM – Übergabe

Stand: 1. Oktober 2026 · Pilot: Bahnhof Thun · Test: Kerzers / Ins / Murten (Ins, Murten fertig; Kerzers Entwurf)

## Ziel

Schematische Spurpläne im Stil der Uppsala-Vorlage, automatisch aus echten Gleisdaten (OpenStreetMap) erzeugt:

- horizontale Gleise, 60°-Verbindungen mit Ausrundung, Stumpfgleise mit Punkt
- Gleise ohne `service`-Tag grün, Abstell-, Industrie- und Dienstgleise schwarz
- Gleisnummern in Lücken der Linie, Streckenabgänge mit Liniennummer und Richtung
- Topologie und Reihenfolge stimmen mit der Realität überein, Längen sind bewusst nicht massstäblich

## Dateien

| Datei | Zweck |
|---|---|
| `spurplan_schema.py` | Generator: OSM-JSON → SVG, schreibt zusätzlich `req.json` (Platzbedarf der Verbindungen) |
| `spurplan_warp.py` | x-Entzerrung (lineares Programm), schreibt `warp.json` |
| `spurplan_check.py` | Prüfalgorithmus: vergleicht die gezeichneten Linien mit der OSM-Topologie, schreibt `check_overlay.svg` |
| `thun_spurplan.svg` | Ergebnis Thun, Entwurf 6 (Prüfung: 0 Befunde) |

## Ablauf

```
./run.sh <bahnhof>          # z.B. ./run.sh murten  (Datei: kim.json mit {"kerzers":…, "ins":…, "murten":…})
```

Das Skript führt aus: `spurplan_schema.py --station <b> --nowarp` → `spurplan_warp.py <b>` → `spurplan_schema.py --station <b>` (zweimal) → `spurplan_check.py --station <b>`. Optionen: `--src`, `--axis-ref <Streckennummer>` (Achse erzwingen), `--out`.

Die Schritte 2 und 3 können bei Bedarf wiederholt werden. Benötigt werden `numpy`, `scipy` und `svgpathtools`, für die PNG-Vorschau zusätzlich `cairosvg`.

## Daten holen (Colab)

Die Sandbox erreicht weder Overpass noch OSM; die Daten kommen über Colab. Wichtig sind ein eigener User-Agent, `out geom;` und kleine Ausschnitte pro Bahnhof. Mehrere Server mit Wartezeit durchprobieren, denn grosse Ausschnitte enden in HTTP 504 oder einem Timeout.

```python
import requests, json, time

stations = {   # grosszügige Ausschnitte inkl. Weichenköpfe (Koordinaten prüfen!)
    "kerzers": "46.966,7.180,46.986,7.212",
    "ins":     "46.997,7.090,47.015,7.122",
    "murten":  "46.918,7.110,46.936,7.138",
}
servers = ["https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter",
           "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
headers = {"User-Agent": "Gleisplan-Schema/0.1 (Colab; d.eckenstein)"}

def query(bbox):
    return f"""
[out:json][timeout:60];
(
  way({bbox})[railway~"^(rail|platform)$"];
  way({bbox})[public_transport=platform][train=yes];
  node({bbox})[railway~"^(switch|buffer_stop|railway_crossing|station|halt)$"];
);
out geom;
"""

result = {}
for name, bbox in stations.items():
    for attempt in range(6):
        url = servers[attempt % len(servers)]
        try:
            r = requests.post(url, data={"data": query(bbox)}, headers=headers, timeout=90)
            if r.ok and r.text.lstrip().startswith("{"):
                result[name] = r.json()
                print(f"{name}: {len(r.json()['elements'])} Elemente ({url})")
                break
            print(f"{name}: HTTP {r.status_code} bei {url}, neuer Versuch …")
        except requests.RequestException as e:
            print(f"{name}: {type(e).__name__} bei {url}, neuer Versuch …")
        time.sleep(10 * (attempt + 1))
    time.sleep(5)

json.dump(result, open("kerzers_ins_murten.json", "w"))
from google.colab import files
files.download("kerzers_ins_murten.json")
```

Thun-Ausschnitt zum Vergleich: `46.748,7.612,46.762,7.648`, 248 Elemente. Liefert ein Bahnhof weniger als etwa 30 Elemente, liegt der Ausschnitt daneben.

## Verfahren

1. **Referenzachse:** Kürzester Weg über die Stammlinie (Hauptgleise bevorzugt), geglättet. Alle Gleisknoten werden in eine Längskoordinate `s` und einen Seitenversatz `d` umgerechnet. Das gleicht Bahnhofsbögen aus.
2. **Segmente:** Die Gleise werden an Weichen und gemeinsamen Knoten geteilt und auf den Bereich `s_min…s_max` / `|d| ≤ d_lim` zugeschnitten.
3. **Gleis oder Verbindung:** Flache Segmente mit `|Δd/Δs| < flat_slope` sind Gleise. Steile Segmente sind Verbindungen. Stumpfgleise sind immer Gleise.
4. **Ketten und Ebenen:** Durchgehende Gleise werden an Knoten zu Ketten verbunden. Die Kompaktierung legt die Ketten auf möglichst wenige Ebenen, ohne die echte Reihenfolge zu verändern. Gleise auf derselben Ebene brauchen mindestens `lane_gap_m` Längsabstand.
5. **Weichen platzieren:** Siehe Regeln unten.
6. **x-Entzerrung:** Ein lineares Programm minimiert die Gesamtbreite und die Abweichung vom Massstab, unter der Bedingung, dass jede Verbindung mindestens die Breite der Standardfigur bekommt.
7. **Zeichnen:** SVG mit Standardfiguren, Gleisnummern, Prellböcken, Streckenabgängen und Pfeilen.
8. **Prüfen:** Siehe Prüfalgorithmus unten.

## Weichen-Standard

Einstellbar in `CFG`:

- `sw_angle = 60`: Neigung jeder Diagonale
- `sw_radius = 7` px: Ausrundung zwischen Gleis und Diagonale
- `sw_min_run`: kürzeste Diagonale
- **Grundfigur:** Gerade – Ausrundung – Diagonale – Ausrundung – Gerade. Die Figur bleibt immer zwischen den beiden Weichenpunkten und ragt nie darüber hinaus.

## Regeln (aus der Thun-Iteration)

| # | Regel | Anlass |
|---|---|---|
| 1 | Die Figur bleibt immer innerhalb ihrer Weichenpunkte; bei Platzmangel wird zuerst der Radius, dann der Winkel reduziert | Stummel ragte über den Weichenpunkt hinaus |
| 2 | Weichenstrasse: Die Diagonale läuft zum am weitesten entfernten Gleis durch, die näheren Gleise zweigen davon ab | Ecke-dann-Rundung, V-Formen |
| 3 | Abzweige aus einer Diagonale verlassen die Weiche in Richtung der Diagonale | «Knubbel» an der Weiche |
| 4 | Eine Weichenstrasse verkettet nur Segmente derselben Gleisklasse; ein Personengleis folgt seinem eigenen OSM-Way | Gleis 18 lief aufs Abstellgleis |
| 5 | Über Kreuzungen (Knoten auf einem anderen Gleis) läuft eine Diagonale nur auf demselben OSM-Way weiter | Schräggleis zerfiel in Stücke |
| 6 | Mindestabstand `lane_gap_m` zwischen Gleisen auf derselben Ebene | Gleise schienen durchzulaufen |
| 7 | Vorrang an einer Weiche: durchgehendes Gleis vor der Way-Regel; ein durchlaufendes Personengleis schlägt ein durchgehendes Nebengleis | Gleis 4 tauchte ab; Abstellgleis wurde angehoben |
| 8 | Kreuzt eine Diagonale ein Hauptgleis an einer Weiche, verläuft sie als Polygonzug durch die echten Weichenpunkte | Verbindung 4 → 2 erreichte Gleis 2 zu früh |
| 9 | Einzelne Verbindungen liegen dort, wo das echte Gleis die Seite wechselt; eine Diagonale wird an der Weiche auf dem Hauptgleis verankert | Überlagerung mit Nachbargleisen |
| 10 | Abgeschnittene Enden bleiben auf der Ebene ihres inneren Endes; seitlich auslaufende Gleise erhalten einen schrägen Pfeil in die echte Richtung; isolierte Reststücke entfallen | Gleise landeten auf fremden Ebenen |
| 11 | Lagen auf Diagonalen werden in Pixeln gerechnet, weil die Entzerrung nicht linear ist | Versatz an Zwischenweichen |

## Verallgemeinerung (seit Kerzers/Ins/Murten)

- Projektionsursprung = OSM-Stationsknoten (nächster am Normalspurnetz); nur Normalspur (`gauge=1435`).
- Achse: von allen äusseren Gleisenden das Paar, dessen Weg am meisten Perronlänge abdeckt (Option `--axis-ref`).
- Ausschnitt: Weichen und Perrons im Umkreis `sw_search_m` um den Bahnhof, plus `s_pad`.
- Streckenabgänge: Liniennummer aus `ref`, Richtung als nächster Ort in Fortsetzung der Strecke (Peilung, Ortstabelle `CFG["towns"]`).
- Perrons als Balken zwischen den beiden Gleisen, an denen sie real liegen; Perronlänge bleibt in der Entzerrung erhalten (mind. 60 %).

| # | Neue Regel | Anlass |
|---|---|---|
| 12 | Nummerierte Gleise (`railway:track_ref` < 30, > 60 m) sind immer Gleise | Murten Gleis 4 wurde als Verbindung gezeichnet |
| 13 | `service=crossover` und lange flache Seitenwechsel ohne geraden Abschnitt (Schnellfahrweichen) sind Verbindungen | Ins: Verbindungen über leere Zwischenebene |
| 14 | Kurze gerade Mittelstücke zwischen zwei Verbindungsstücken gehören zur Verbindung; sehr kurze gerade Stücke (< 15 m, Δd < 1 m) sind Gleisfortsetzungen | Ins: Gleis 4 wechselte die Ebene |
| 15 | Seitlich auslaufende Strecken beginnen dort, wo sie das erste Gleis erreichen | Murten: Linie 255 lief auf fremdem Gleis |

## Zusammengeführter Regelsatz (1.10.2026, abends)

Ein Skript `spurplan_schema.py` für alle Bahnhöfe; Thun, Ins, Murten, Kerzers bestehen die Prüfung mit 0 Befunden. Bahnhofsspezifisches steht nur noch in `<bahnhof>_override.json` (`pax`, `platforms`, `cfg`).

Aufruf: `./run.sh <bahnhof>` mit `<bahnhof>.json` im selben Ordner. Regeln 12–16 sind über `cfg.rules` einzeln abschaltbar (Ausschlussverfahren).

| # | Regel (neu oder geschärft) | Anlass |
|---|---|---|
| 13 | geschärft: `service=crossover` nur bei echtem Seitenwechsel (> 2,5 m); sanfter Seitenwechsel ohne Gerade nur bei ≥ 120 m Länge und < 15 m Geraden | Thun: Fortsetzung Gleis 3 → 233 ist als crossover getaggt; kurze Fächerbögen wurden zu Verbindungen |
| 16 | Offenes Gleisende ohne Prellbock am Rand der Daten = Streckenabgang; ebenso Gleise, deren Folgeway beim Zuschneiden am Längsende wegfällt | Thun: Abgänge Richtung Spiez fehlten; Stumpfgleise 16/18 wurden fälschlich Abgang |
| 17 | Abgeschnittene Enden flacher Gleise behalten zuletzt fest ihre Ebene | Thun: Streckengleis lief am Ostende aufs Nachbargleis |
| 18 | Weichenstrassen-Diagonalen werden ganz am Schluss mit den endgültigen Ebenen in Pixeln bemessen, Verankerung an der Hauptgleis-Weiche bleibt; Weichen auf Start-/Zielebene liegen vor bzw. nach der Ausrundung | weicher Bogen statt 60°, Versatz an Weichen |
| 19 | Achse: Anteil `usage=main` vor Perronabdeckung (falls Stammlinie erfasst); Option `axis_mode: main_extremes`, `axis_refs` | Thun: Perron Schwäbis zog die Achse auf Linie 430 |
| – | Abgänge gleicher Linie/Seite teilen den Ort; Ortswahl nur bis ca. 25 km | doppelte bzw. falsche Beschriftung (Fribourg bei Thun) |
| – | Mittelperron nur im Abschnitt, in dem zwischen den beiden Gleisen nichts liegt | Perron 16/18 über Stumpfgleis |

Prüfer: Weichen, die real < 12 m auseinander liegen, gelten als gemeinsamer Knoten (sonst Fehlalarme bei dicht folgenden Weichen). Thun-spezifisch: `d_lim: 48` (Abstellfächer im Südwesten).

## Prüfalgorithmus (`spurplan_check.py`)

- **A** – Verbindung nicht geschlossen: Am OSM-Knoten gehen nicht alle beteiligten Linien durch denselben Punkt.
- **B** – Scheinverbindung oder Überlagerung: Zwei Gleise ohne gemeinsamen OSM-Knoten berühren oder überlagern sich.
- **C** – Kreuzung ohne OSM-Knoten: nur ein Hinweis, es kann eine Überwerfung sein.
- **D** – Die Reihenfolge der Gleise quer zur Achse ist vertauscht.

Der Prüfer kontrolliert nur die Topologie, nicht die Ästhetik. Thun-Verlauf: Beim ersten Lauf gab es 25 Befunde, jetzt sind es 0.

## Offene Punkte

- **Perrons fehlen:** Im Thun-Export gab es keine `railway=platform`-Elemente. Der neue Query enthält Perrons; die Zeichnung der Perronkanten ist noch zu bauen.
- **Gleisnummern:** Sie stammen nur aus `railway:track_ref`. Eine Override-Tabelle (Ebene, Farbe, Gleisnummer pro OSM-Way) für Einzelfälle fehlt noch.
- **Ästhetik:** Die Verbindung 4 → 3 im Osten von Thun ist flacher als 60°, und einige Abstellgleise zweigen mit einem kleinen Haken ab.
- **Thun-spezifisch, vor Kerzers/Ins/Murten zu verallgemeinern:**
  - Projektionsursprung in `xy` (`lat0 = 46.755`, Längengrad 7.625) → aus den Daten ableiten
  - `CFG["names"]` (Linie 290/310/430) und `CFG["ref_fix"]` → aus `ref`-Tags und `station`-Knoten ableiten
  - `s_min`/`s_max`/`d_lim` → automatisch aus Bahnhofsposition und Weichenköpfen
  - Input: die neue Datei enthält mehrere Bahnhöfe in einem Dictionary
- **Kerzers:** Die Perrongruppen (1/3 und 4/6) liegen entlang der Achse hintereinander, die Linie 220 erscheint nur als schwarze Stummel. Eine einzelne Achse bildet den Bahnhof nicht sauber ab → zweite Achse oder Netzschema nötig; Abgleich mit Ortskenntnis nötig.
- **Datenqualität:** In Ins und Murten sind einzelne Perrongleise in OSM als `service=siding` erfasst und erscheinen deshalb schwarz; Ins hat nur einen Perron erfasst.
- **Override-Tabelle (umgesetzt):** `<bahnhof>_override.json` mit `pax` (Gleisnummern als Personengleis) und `platforms` (`{"between": ["2","3"]}` = Mittelperron, `{"outer": "4"}` = Aussenperron). Ersetzt die OSM-Perrons. Erster Einsatz Ins (Ortskenntnis): Mittelperron 2/3, Aussenperron 4. Lehre: OSM erfasst Perronkanten pro Gleis; daraus lässt sich Mittel- vs. Aussenperron nicht zuverlässig ableiten.
- **Netzplan Dreieck (`spurplan_netz.py` → `dreieck_netzplan.svg`):** Ins und Murten als eingebettete Spurpläne (`spurplan_schema.py --bare`, Anschlüsse aus `<bahnhof>_ports.json`). Kerzers von Hand nach OSM und Ortskenntnis: senkrecht, Gleise 6/5/4 (220) im Westen, 3/2/1 (251) im Osten, Aussenperrons an 6, 4, 3 und 1, Gleise 5 und 2 ohne Perron, niveaugleiche Kreuzung am Südkopf. Müntschemier, Sugiez und Münchenwiler-Courgevaux mit je zwei Aussenperrons. Strecken aus `dreieck_strecken.json`: Gleiszahl per Querschnitt, alles einspurig ausser westlich Ins; Kreuzungsstellen Müntschemier, Sugiez, Münchenwiler-Courgevaux. Die Linie 256 mündet zwischen Muntelier-Löwenberg und Galmiz Richtung Murten in die 251. Einschränkung: Der Query holte nur Gleise mit Linien-`ref`; Kreuzungsgleise ohne `ref` (z.B. Galmiz) fehlen möglicherweise.
- **Nächste Schritte:** Kerzers, Ins und Murten einzeln zeichnen und die Regeln am Prüfer messen. Danach ein Netzschema für das Dreieck mit den Bahnhöfen als Knoten.


## Netzplan grosser Perimeter (automatisch, seit 1.10.2026 abends)

Ziel: plotbare Karte eines grossen Perimeters im Stil des Dreiecks. Pilot: Region Olten (Rothrist/Zofingen – Wangen b. O. – Tecknau – Däniken/Schönenwerd).

Ablauf: `./run_netz.sh region.json olten_region "Region Olten" S,W,N,E Ausgabe.svg`

1. `netz_topologie.py`: Streckengleise (ohne `service`) je Linie (`ref`, fehlende Nummern von Nachbargleisen übernommen) zu Achsen; parallel laufende Achsen derselben Linie abgezogen (Vierspur = eine Achse); Achsen werden abgeschritten (Schleifen wie Olten–Däniken–Schönenwerd/Eppenberg werden korrekt erfasst). Knoten: Bahnhöfe, Halte, Abzweige, Abgänge am Perimeterrand (Zielort aus `region_lines.json` + `orte.json` per Peilung, Orte im Perimeter ausgeschlossen). Gleiszahl je Kante per Querschnitt.
2. `netz_stationen.py`: Perrongleise je Bahnhof (Override `pax` oder nummerierte Gleise ≤ 12 im Umkreis 220 m), Querreihenfolge (Hauptachse per PCA), Perrons (Override = Ortskenntnis, sonst Annahme, hellgrün markiert), Neben-/Abstell-/Güteranlagen (Anzahl Gleise im Umkreis 600 m, Seite).
3. `netz_layout.py`: Bereinigung (Abzweige im Bahnhofskopf < 560 m → Bahnhof, Abzweige mit 2 Anschlüssen auflösen, lose Enden weg); Kanten auf 0°/60°/90°/120° (+ Gegenrichtungen), keine zwei Kanten in dieselbe Richtung an einem Knoten; Bahnhöfe als zwei Köpfe mit fester Länge in Bahnhofsrichtung (Ein-/Ausfahrten nie zurück in den Bahnhof); Knotenlagen per gewichteter Ausgleichsrechnung (Richtung exakt, Länge ~ L_geo^0.75, schwacher Zug zur Geografie). Prüfgrösse: max. Richtungsabweichung (Pilot 0,2°).
4. `netz_render.py`: Streckengleise grün, je Gleis eine Linie; Bahnhöfe als Gleisharfe mit Nummern und Perrons; Halte als Perronbalken; Anlagen als feine graue Kontur mit Gleiszahl; Abgänge mit Linie und Zielort; Legende.

Darstellungshierarchie (Hinweis D. Eckenstein): Neben-, Abstell-, Güter- und Anschlussgleise feiner und enger – im Netzplan als Kontur, im Spurplan dünnere Linie (1,6 px) und Ebenenabstand 55 % (Regel 24, `side_lane_factor`). Detailkarten („Zoom“) für grosse Anlagen sind der nächste Schritt.

### Neue Spurplan-Regeln aus dem Härtetest Region Olten

| # | Regel | Anlass |
|---|---|---|
| 20 | Seitenausschnitt im Perronbereich so breit, dass alle Personengleise (Override `pax`) hineinpassen; ausserhalb Standard | Olten: Gleise 1–8 lagen > 60 m neben der Achse |
| 21 | Doppelt belegte Ebenen (bei Überwerfungen) auflösen: Ebene einfügen | Überwerfungen Olten Nord |
| 22 | Lage-Schätzung ausserhalb der äussersten Gleise mit Gleisabstand weiterzählen | Abstellgleise klebten auf dem Randgleis |
| 23 | Abstellgleise, die seitlich aus dem Ausschnitt laufen, weglassen | Fragmente am Rand |
| 24 | Ebenenabstand Neben-/Abstellgleise 55 %, dünnere Linie; Weichenlagen auf Diagonalen pixel-linear | Lesbarkeit, Plotbarkeit |
| – | `region_lines.json`: Zielorte je Linie; Peilung wählt nur unter diesen | falsche Orte (Fribourg bei Thun, Olten statt Bern) |

Stand Prüfung Spurpläne: Thun, Ins, Murten, Kerzers, Schönenwerd, Safenwil, Dulliken, Hägendorf 0 Befunde (Dulliken/Hägendorf trotzdem unbrauchbar: Prüfer erkennt fehlende Bahnhofsgleise nicht); Zofingen 2, Tecknau 3, Aarburg-Oftringen 3, Däniken 11, Olten 53, Olten Hammer 13.

### Offen (Netzplan)
- Perronlage ausser Olten/Zofingen nur angenommen (hellgrün) → Overrides.
- Tunnel (Hauenstein-Basis, Eppenberg) noch nicht gekennzeichnet.
- Detailkarten für Anlagen Olten, Däniken, Rothrist, Olten Hammer.
- Dreieck Kerzers–Ins–Murten mit dem automatischen Verfahren neu erzeugen (Vergleich zur Handanordnung).
- Grossen Perimeter: Daten kachelweise (Colab-Zelle in diesem Dokument) – Laufzeit Layout/Rendering vernachlässigbar.

## Netzplan mit eingebetteten Spurplänen (`netz_lage.py`, seit 3.10.2026)

Das vollautomatische Layout (`netz_layout.py`, Bahnhöfe als Harfen) zeigte keine Fahrwege. Deshalb neu: **jeder Bahnhof ist sein eigener Spurplan**, im Netzplan als Ausschnitt eingebettet; die Strecken verbinden die Abgänge der Spurpläne (Detailgrad wie das Dreieck Kerzers–Ins–Murten).

Ablauf:
1. Je Bahnhof `./run.sh <bahnhof>` → Spurplan, Prüfung und `--bare`-Fassung (`<bahnhof>_bare.svg` ohne Titel und Abgangstexte) plus `<bahnhof>_ports.json` (Abgänge mit Lage, Richtung, Linie, Peilung).
2. `python3 netz_topologie.py region.json olten_region S,W,N,E` → Topologie + Achsen je Bahnhof (Regel 25).
3. `python3 netz_lage.py olten_region "Region Olten" plan.svg [--info]`.

Die Lage ist **halbautomatisch**: `<name>_lage.json` (beim ersten Lauf geografisch erzeugt, danach von Hand verfeinert):
- `"Bahnhof": [x, y]` Mitte des Spurplan-Kastens; `"Abzweig #id"`, `"Abgang 500 #id"` für Abzweige/Abgänge (`--info` listet alle Strecken mit Anschlussseite).
- `"drehung": {"Bahnhof": 0|90|-90|180}` (Schrift bleibt aufrecht).
- `"als_halt": ["Hägendorf"]` Bahnhof nur als Haltesymbol (z. B. am Datenrand abgeschnitten).
- `"richtung": {"#22": {"#24": 240}}` Abgangsrichtung einer Strecke am Abzweig (für Dreiecke/Verbindungskurven).

Regeln des Netzplans:
- Strecken als 1–3 Schenkel in 0°/60°/90°/120°…, je Gleis eine Linie mit Gleisabstand = Ebenenabstand im Spurplan, Ecken gerundet.
- Anschluss an Spurplan-Abgänge: Peilung + Liniennummer; Abgänge im Innern des Ausschnitts werden bis an den Kastenrand verlängert.
- An Abzweigen liegen alle Strecken auf einem gemeinsamen Spurraster (die oberste Strecke nimmt die oberen Spuren), damit Gleise durchlaufen statt zu fächern.
- Halte auf dem längsten geraden Stück, in geografischer Reihenfolge, Beschriftung abwechselnd oben/unten; Kreuzungshalt auf Einspur mit 2 Gleisen.

Weitere Spurplan-Ergänzungen:
- **Regel 25**: Achse aus der Netztopologie (`<bahnhof>_axis.json`), Schleifen abgeschnitten, beidseitig 1,5 km verlängert; Mindestausschnitt ±350 m um den Bahnhof.
- **DKW-Symbol**: OSM `railway:switch=double_slip` → die zwei Bögen der Doppelkreuzungsweiche (Thun: 10 DKW – die „Überschneidungen“ waren DKW).
- Abgangsbeschriftungen suchen eine freie Lage (kein Text auf Linien).

Stand Region Olten (3.10.2026): Netzplan zusammenhängend mit allen 11 Spurplänen, Dreieck Olten Nord (Verbindung Dulliken ↔ Hauenstein) als Sehne. Schwach sind weiterhin die Spurpläne Olten (Vorbahnhof Nord abgeschnitten), Däniken (Güteranlage), Rothrist (NBS-Gleise mitten im Ausschnitt), Hägendorf (Datenrand).

## Nachtrag 9.10.2026 – Rothrist und Schleife Rothrist–Zofingen

Anlass (D. Eckenstein): In Rothrist begannen Gleise mitten im Bahnhof, die Schleife Rothrist–Zofingen fehlte.

Spurplan-Regeln:
- **Regel 26**: Die Topologie-Achse wird an das Gleisbündel angeschmiegt (Median-Querversatz der Streckengleise je 80 m, geglättet, 3 Durchgänge). Die grobe Achse lag in Kurven bis 50 m neben den Gleisen; deshalb fiel der Westkopf von Rothrist aus dem Ausschnitt. Pro Bahnhof abschaltbar mit `cfg.axis_snap=false` (Olten, Aarburg-Oftringen, Zofingen, Däniken, Olten Hammer: dort war die bisherige Achse besser).
- **Regel 27**: OSM-Lücken schliessen. Ein offenes Gleisende ohne Prellbock, das in Verlängerung des Gleises < 6 m vor einem Knoten eines anderen Gleises liegt, wird angeschlossen (Rothrist Gl. 1 endete 4,6 m vor der Weiche). Nur in Gleisrichtung, sonst werden Stumpfgleise an Nachbargleise gehängt (Thun).
- **Regel 28**: Läuft ein Gleis längs aus dem Ausschnitt (nächster Punkt jenseits s_min/s_max), wird es bis an den Planrand gezogen statt als seitlicher Abgang behandelt (vorher kollabierte Gl. 1 Rothrist auf einen Punkt).
- `rothrist_override.json`: `cfg.sw_search_m=1600` → Westkopf (Spurwechsel bis s≈1100) im Ausschnitt.

Netzplan:
- Lose Enden < 150 m neben einer anderen Strecke werden dort als Abzweig angeschlossen (die Schleife ging beim Abziehen paralleler Achsen verloren). Rothrist–Zofingen: Abzweig #43 auf der 451 (520 m vor Aarburg) → Abzweig #25 auf der 500 (1 km südlich Aarburg).
- `merge_radius` je Bahnhof in der Lagedatei (Aarburg-Oftringen 450 m), damit Abzweige ausserhalb des Spurplans eigene Knoten bleiben.
- Geometrie beim Zusammenfassen von Kanten nach Endpunkten ausgerichtet (Topologie-Geometrien sind nicht einheitlich orientiert).
- Halte-Beschriftung: Seite mit den wenigsten Überlagerungen.
- Die 453 (Rothrist Gl. 4 → Unterwerfung → Richtung Aarburg/Zofingen) kreuzt im Netzplan die 450-Gleise nach Olten ohne Verbindung = Unterwerfung.

Prüfstand (9.10.): Regressionssatz Thun/Ins/Murten/Kerzers 0 Befunde; Rothrist A1 (vorher A1 B4); Wangen 0 (vorher D14); Tecknau B4 (vorher B3 D13).

## Nachtrag 9.10.2026 (abends) – Prüfungen, Norden oben, Rothrist 4 Gleise, Aarburg

Anlass (D. Eckenstein): Tecknau lag südlich von Däniken; von Rothrist nach Bern nur 3 statt 4 Gleise (die mittleren auf die NBS); bei Aarburg wechselte die durchgehende Doppelspur Rothrist–Aarburg scheinbar die Fahrrichtungsseite.

Prüfungen im Netzplan: `python3 netz_lage.py <name> "<Titel>" plan.svg --pruefen`
1. **Gleise entlang der Strecken**: gezeichnete Gleise je Strecke gegen den OSM-Querschnitt; Anzahl Abgänge des Spurplans je Strecke; Spurplan-Abgänge ohne Strecke; Spuren, die an einem Abzweig nur auf einer Seite liegen; Gleise einer Strecke, die sich kreuzen (= Fahrrichtungsseite wechselt). Liniennummer-Wechsel an Abzweigen als Hinweis.
2. **Lage Nord/Süd, Ost/West**: alle Paare von Spurplänen, Abzweigen und Abgängen mit > 1,5 km Abstand; Befund, wenn die Reihenfolge im Plan der Geografie widerspricht (Achsanteil > 50 % und > 1,5 km, Plan > 60 px).

Stand Region Olten _04: Prüfung 2 = 0 Befunde (vorher 85). Prüfung 1 = 5 Befunde, alle aus den Spurplänen (Olten: 1 Abgang für die zweigleisige 410, 2 statt 3 Gleise Richtung Olten Nord, 5 freie 540-Seitenabgänge; Zofingen 3 statt 2 Gleise Richtung Luzern).

Netzplan neu **Norden oben**: Olten senkrecht (`drehung -90`), Hauenstein nach Norden (Tecknau, Läufelfingen senkrecht), Aarau nach Osten, Aarburg/Zofingen nach Süden, Rothrist/Wangen nach Westen. Die 540 kreuzt nördlich Olten die 500 ohne Verbindung (Überwerfung Olten Nord).
- `senkrecht: ["#24", "#25", "#31"]` in der Lagedatei: Abzweig mit senkrechter Achse (Spuren quer = x).
- **Spurfolge**: Hat ein Abzweig auf einer Seite eine einzige Strecke mit bekannten Liniennummern je Gleis (aus dem Spurplan), werden die Spuren nach Liniennummer auf die Äste verteilt. Rothrist West: 450 | 400 | 400 | 450 → 450 nimmt die äusseren Spuren und kreuzt die NBS (Überwerfung), 400 die mittleren.
- Weniger Spurplan-Abgänge als Streckengleise: Anschlusspunkte quer auffächern statt zusammenlegen.
- Gleisreihenfolge je Strecke: die Zuordnung mit den wenigsten Kreuzungen wird gewählt.
- Mehrere Halte auf einer Strecke werden gleichmässig verteilt.

Spurplan-Regeln:
- **Regel 16b**: Datenrand bei kreisförmigem Ausschnitt (`cut.py`, Radius um den Bahnhof) erkennen – vorher nur am Rechteck-Rand.
- `cut.py`: Radius je Bahnhof (`R_ST`, Rothrist 2400 m, damit die NBS-Einmündung und die vierte Spur drin sind); Aufruf `python3 cut.py rothrist`.
- **Regel 29**: Zweigen zwei Gleise derselben Richtung seitlich ab (Doppelspur 451 in Aarburg: Gl. 1 und Gl. 3 über Überwerfung), darf der innere Abgang nicht auf der Linie des äusseren liegen – er wird stromabwärts verschoben, so dass die Doppelspur parallel bleibt.
- `region_lines.json`: 453 → Zofingen (vorher fälschlich Olten).

## Nachtrag 12.10.2026 – Achslage, Bündel, Wangen, Aarburg

Ausgabe künftig nur noch **ein konsolidierter Regionalplan** (`<Datum>_Region Olten Netzplan_NN.svg`), Prüfbericht unten links im Plan eingebettet. Einzelne Spurpläne nur noch auf Wunsch.

- **Prüfung 3 – Achsen und Seiten gegen die Karte** (`--pruefen`): (a) zeigt die Achse jedes Spurplans im Plan in dieselbe Himmelsrichtung wie auf der Karte (Abweichung > 60° = Befund); (b) liegen Abgänge auf gleicher Höhe (< 40 m längs) im Plan auf derselben Seite der Achse wie auf der Karte; (c) liegen seitliche Abgänge auf der richtigen Seite; (d) ist die Reihenfolge der Strecken an einer Spurplanseite dieselbe wie auf der Karte (Richtung 1,5 km weg). Stand: Olten Nord meldet 540/500 vertauscht = reale Überwerfung; Dulliken Ost zwei 540-Abgänge vertauscht (offen).
- **Bündel stapeln**: Verlassen mehrere Strecken eine Spurplanseite verschränkt (Rothrist Ost: Olten = Gl. 3+2, Aarburg = Gl. 4+1), werden die Bündel in der Reihenfolge ihrer Ziele nebeneinandergelegt; Gl. 4 kreuzt am Kastenrand (Unterwerfung 453) statt zwischen 3 und 2 einzufädeln.
- **Regel 30**: Gleisstücke, die nahtlos (< 15 m, Querversatz < 1,6 m) aneinander anschliessen, liegen auf derselben Ebene; Querordnung erst ab 2,5 m Abstand verbindlich. Wangen: das Nordgleis springt nicht mehr an jeder Weiche.
- **Regel 29 (geändert)**: Bei zwei parallel seitlich abzweigenden Gleisen wird der äussere Abgang stromaufwärts gelegt (nicht der innere stromabwärts). Aarburg: der Stummel liegt wieder südlich der 451 nach Rothrist.

### Gleisführung im Netzplan: so lange wie möglich gerade (12.10.2026)
- Jedes Gleis bleibt auf seiner Spur und wechselt nur, wo es nötig ist: an einem Knick der Strecke (der Seitenversatz geht im Knick auf) oder – wenn der Knick weiter als 250 px weg ist, der Versatz grösser als 1,5 Gleisabstände ist oder die Seite gestapelt ist – gleich am Spurplan-Rand mit einem 60°-Versatz (`track_line`).
- Rothrist Ost: Gl. 4 taucht am Rand unter 3 und 2 durch und läuft dann gerade bis vor Aarburg; dort ein einziger Knick in den seitlichen Abgang (Lage Rothrist/Abzweig #43 auf die Höhe des Aarburger Abgangs + 40 px abgestimmt, Schleife #43→#25 auf dem 60°-Strahl).
- Abzweig #31 (NBS): das linke 450-Gleis läuft gerade weiter und schwenkt erst im Knick nach links weg.

### Olten neu (12.10.2026, abends)
- Olten-Spurplan mit angeschmiegter Achse aus den Hauptgleisen: `cfg = {axis_snap: true, snap_win_m: 200, snap_smooth_m: 500, snap_main_only: true, d_lim: 90, s_min_fix: 4000}`. Neue Schalter: `snap_win_m` (Fenster Median), `snap_smooth_m` (Glättung), `snap_main_only` (nur usage=main), `s_min_fix`/`s_max_fix` (Ausschnitt von Hand). Ergebnis: Gleise 1–12 in richtiger Reihenfolge, Güterbahnhof Olten Nord im Plan, 410 Solothurn als zwei Gleise am Südkopf statt seitlicher Stummel, 500 Basel zweigleisig. Restbefunde fast nur im Güterbahnhof.
- Netzplan: Abgänge ohne Liniennummer (`ref` fehlt) gelten als Kandidat mit kleinem Abzug, aber nur zum Auffüllen direkt neben passenden Abgängen (≤ 30 px); Abgänge mit passender Linie haben Vorrang. Wangen–Olten jetzt zweigleisig angeschlossen.
- Überdeckung Bahnhöfe (Olten / Olten Hammer): der grössere Spurplan (Fläche) gewinnt.
- `track_line`: Mini-Schenkel < 3 px und Knicke < 4° werden vorher entfernt (sonst Haken), Versatz in kurzen Schenkeln begrenzt.

### Regionalplan nur mit Hauptgleisen (12.10.2026, spät)
- Spurpläne für den Regionalplan mit `./run.sh <bahnhof> --hauptgleise`: ohne `service=yard` und `service=spur` (Güter-/Abstellanlagen gehören in eigene Detailpläne). Strecken-, Perron-, Überhol- und Verbindungsgleise bleiben. Effekt: Olten 61 → 12 Befunde, Däniken 18 → 0.
- Weiterlauf an Weichen: `service=crossover` wird nur als Fortsetzung gewählt, wenn es nichts anderes gibt (Schönenwerd: Gl. 1 und 2 spreizten, weil eine lange, flache Verbindung als Weiterlauf galt).
- Regel 30 erweitert: Lücke bis 40 m (`r30_gap_m`), Querversatz bis 3 m (`r30_dd_m`).
- Abgänge an den Längsrändern werden im Spurplan bis an die Abgangsposition gezogen (vorher Lücken zwischen Spurplan und Strecke).
- `als_halt`-Bahnhöfe überdecken keine anderen mehr (Olten wurde von Olten Hammer verdrängt).
- Offen: Nordkopf Olten (Treppen über mehrere Ebenen bei den Spurwechseln Richtung 540/500) braucht eine eigene Iteration wie Thun; Zofingen ebenso.

### Prüfung 4 und Regel „Weichen auf Hauptgleisen sichtbar“ (12.10.2026, spät)
- **Prüfung 4** (`abstand.py plan.svg [--min px] [--liste] [--png]`): wertet das fertige SVG aus (inkl. eingebetteter, gedrehter Spurpläne). Befund, wenn zwei Linien über ≥ 2,5 × Mindestabstand parallel näher als der Mindestabstand (Regionalplan 4,5 px, Spurplan 10,7 px) nebeneinander laufen, ohne zusammenzulaufen ("zu nah"), oder wenn ein abzweigendes Gleis eng am Stammgleis klebt ("Weiche verdeckt"). Fortsetzungen (Spurplan → Strecke), DKW-Bögen und Stummel sind ausgenommen. Kalibriert an Thun/Ins/Murten/Kerzers (0–2 Befunde). Im Regionalplan als Prüfung 4 im Bericht.
- **Regel 31**: Ebenen, die ein Hauptgleis über eine Weichenverbindung berührt, bekommen vollen Gleisabstand (nicht 55 %).
- **Regel 32**: parallele Weichenverbindungen mit überlappender Höhe bekommen in der x-Entzerrung mindestens einen Gleisabstand Längsabstand.
- Doppelte Abgänge (zwei Ways enden im selben Randpunkt) werden zusammengefasst – Zofingen zeigte deshalb drei statt zwei Gleise nach Luzern.
- Stand: Prüfung 4 meldet noch 5 Stellen, alle im Nordkopf Olten (lange Verbindung auf Zwischenhöhe neben Gl. 6; zwei aufeinanderfolgende Diagonalen 10→9→6 leicht versetzt).

## Prüfstand und Kontaktbogen (12.10.2026, Schritt 1 des neuen Vorgehens)
`python3 pruefstand.py` zeichnet alle Bahnhöfe mit dem aktuellen Regelsatz neu (Referenz Thun/Ins/Murten/Kerzers voll, Region Olten mit `--hauptgleise`), lässt die Prüfungen A–D, E (zu nah) und W (Weiche verdeckt) laufen, vergleicht mit `pruefstand_basis.json` und schreibt den Kontaktbogen `<Datum>_Kontaktbogen Spurplaene.png`.
- Abgenommene Bahnhöfe dürfen in keiner Prüfung schlechter werden; sonst meldet der Prüfstand einen Rückschritt (Rückgabewert 1) und die Änderung wird nicht übernommen.
- Abnahme: `python3 pruefstand.py --abnehmen <bahnhof> …` (nach Freigabe durch D. Eckenstein). Abgenommen 12.10.2026: Thun, Ins, Murten, Kerzers.
- Stand 12.10.2026: sauber (0 Befunde) Safenwil, Wangen b. O., Dulliken, Däniken, Schönenwerd, Läufelfingen; offen Olten (B11 C1 E3 W2), Aarburg-Oftringen (B4), Rothrist (D1), Zofingen (A1 B2), Tecknau (B4), Olten Hammer (A1 B4 W2).

## Feedback-Seite (13.10.2026)
Artefakt «Spurplan-Feedback»: https://claude.ai/artifact/CKejJqUWnbF6D6EXgA5Nvv (privat, Datenbank `db`).
- Bau: `python3 feedback/bauen.py "<Netzplan-Label>" <regionalplan.svg>` → `feedback/index.html`, dann gleiche Datei neu veröffentlichen (gleiche URL). Vorlage `feedback/seite.html`. Der Regionalplan braucht die `data-st`/`data-name`-Kennungen an den Spurplan-Gruppen (netz_lage.py schreibt sie seit 13.10.).
- Sammlung `feedback`: je Klick ein Dokument {plan, plan_stand, x, y (Plankoordinaten), bahnhof, lx, ly (Koordinaten im Spurplan des Bahnhofs, auch bei Klick im Regionalplan), art, text, status, antwort, version, erstellt}.
- Status: offen → behoben (Claude schreibt `antwort` + `version`) oder rueckfrage → erledigt (D. Eckenstein bestätigt).
- Sammlung `abnahme`: Dokument je abgenommenem Bahnhof → danach `pruefstand.py --abnehmen <key>` ausführen.

## Nachtrag 13.10.2026: erste Feedback-Runde (18 Hinweise, Netzplan_10)
Neue Regeln in spurplan_schema.py:
- Verkettung: Fortsetzung auf demselben OSM-Way klar bevorzugt (`way_pen` 0.06 statt 0.01) – Wangen Gl. 4 lief über einen Spurwechsel weiter.
- Regel 33: Abgang (Kette mit abgeschnittenem Ende) übernimmt die Ebene des Bahnhofsgleises, in das er ohne Weiche übergeht (auch direkt aneinanderstossende Ketten) – keine S-Kurven am Planrand.
- Regel 34: kurzes Stück zwischen zwei durchgehenden Gleisen (Versatz 1,5–5 m, < 120 m, kein langes Parallelstück) = Spurwechsel. Personengleise nur < 90 m und abschaltbar (`r34p`, in Olten aus). Ausserdem `service=crossover` mit Versatz > 1 m und 100–300 m Länge = Spurwechsel (Rothrist-Treppen).
- Regel 35 (nur --hauptgleise): Nebengleise mit seitlichem Schnitt weglassen (Rothrist West: Pfeile ins Nichts). In Olten aus (`r35`), sonst kippt der Ostkopf.
- Regel 28b: Längsschnitt auch erkennen, wenn das Gleis in einem anderen Way weiterläuft (Aarburg Gl. 3 Richtung Olten). In Olten aus (`r28b`). Nur das auslaufende Gleis wird an den Rand gezogen (LAT_OWN), Spurwechsel am selben Knoten bleiben (Zofingen 90°-Strich).
- Regel 36: verlässt ein Personengleis den Plan an einer Weiche mit weniger Fortsetzungen als Stücken, läuft nur das fluchtende weiter (Zofingen Süd Gl. 3).
- Regel 29: Verschiebung stromaufwärts nicht hinter den vorherigen Knoten; Rest wird mit dem anderen Abgang stromabwärts ausgeglichen (Aarburg Stummel Gl. 1; kostet 6 B-Befunde durch Überlagerung auf Gl. 2, optisch unauffällig).
- Beschriftung Abgänge: Gruppen nur zusammenhängend, bei Platzmangel einzeilig.
- Prüfung R (abstand.py --winkel, Prüfstand): Gleisstücke steiler als 75° = 90-Grad-Stück. Basis R ergänzt (Kerzers 1).
- netzplan_bauen.py NN: Regionalplan mit Prüfbericht und Zeichenerklärung (feedback/legende.py).
Offen: Olten (Knick/Pfeil West, Nordkopf) → Schritt 2; Rothrist Ost Kreuzung 4 über 3/2 (Netzplan-Ebene); Abzweige auf freier Strecke als kleine Spurpläne (Spurwechsel bei #43 und #25); DKW-Klammern im Plan.

## Nachtrag 13.10.2026 (2. Feedback-Runde, Netzplan_11)
Entscheide D. Eckenstein: kleine Bahnhöfe mit ganzer Anlage; grosse Güteranlagen (Olten, Däniken, Olten Hammer) Hauptgleise + jede Weiche in die Anlage als Abgang; Spurwechsel auf freier Strecke zeichnen; DKW-Symbol (helle Klammern in den stumpfen Winkeln); Rothrist Ost: 3/2 biegen ab über 4, 4 senkt sich später zu 1.
- pruefstand.py: `GROSS = {olten, daniken, olten_hammer}` → `--hauptgleise`, alle anderen ohne.
- Regel 15b: flaches Hauptgleis mit seitlichem Schnitt bleibt bis zu seinem Ende gezeichnet (+ Abgangsstummel), Däniken Gl. 4.
- Regel 37: Richtung seitlicher Abgänge relativ zum nächsten Streckengleis (Strecke im Bogen), Suche über alle Ways bis 400 m.
- Regel 38 (--hauptgleise): Weichen in weggelassene yard/spur-Ways als Abgang (22 px, 60°, Pfeil).
- Regel 39: seitlicher Streckenabgang mit Ausrundung (Port verschoben auf Ende der Ausrundung).
- DKW: Arme in 26 px gemessen (hinter Ausrundung); Symbol nur bei echter Kreuzung (2 Gegenpaare), sonst alte Bögen.
- `<key>_ports.json` enthält `ways` (gezeichnete Way-IDs).
- netz_lage.py: Spurwechsel auf freier Strecke aus region.json (nicht in Spurplänen, 20–300 m, verbindet zwei Streckengleise), auf Doppelspur als 60°-Diagonale; `stack_aus` (Lage-JSON) und `late`-Spurwechsel in track_line; Abzweig #43 auf Rothrist-Mitte + 1 Spur.
- Feedback-Seite: Antworten auf Rückfragen (`rueckmeldungen` [{text, am}], Status → offen).
Offen (Runde 3, 15 neue Hinweise): S-Kurven Dulliken/Däniken-Strecke, Hauenstein-Basistunnel Platz + Spurwechsel, Über-/Unterwerfung Symbol nördlich Olten, Verbindungsgleise Olten 4/7 → Hauenstein, Tecknau (Mittelperron 3/4, Gleis 1, Stumpen, Spurwechsel statt Zwischengerade, kürzer), Wangen Pfeil Gl. 1, Murten Gleis 1 Nummer, Kerzers Achsen (Ins–Bern Gl. 6, Murten–Lyss Gl. 1, Neuchâtel/Ins–Bern fehlt) – Kerzers/Murten sind Referenz, Änderung nur mit Neu-Abnahme.

## Grundsätze in Rangfolge (D. Eckenstein, 13.10.2026) – gilt vor allen Einzelregeln
Bei einem Konflikt gewinnt immer der höhere Grundsatz. Der Prüfstand vergleicht lexikografisch (erster unterschiedlicher Grundsatz entscheidet).
1. **Topologie stimmt** – jedes Gleis hängt an, wo es real anhängt, keine Scheinverbindungen (Prüfung A, B, C; Regeln 27, 34, 36)
2. **Lage stimmt mit der Karte** – N/S, O/W, Querreihenfolge (Prüfung D, Netzplan 2/3; Regeln 21, 30, 37, Spurfolge)
3. **Jede Weiche ab Hauptgleis sichtbar**, mindestens als Abgang (Prüfung W; Regeln 15b, 31, 32, 38)
4. **Keine 90°-Winkel** – nur 60° mit Ausrundung (Prüfung R; Regel 39)
5. **Abstand** – nie näher als ein Gleisabstand (Prüfung E)
6. **Gerade so lange wie möglich**, Spurwechsel spät und als ein Versatz (Regeln 26, 28, 28b, 29, 33, `late`)
7. **Detailgrad** – kleine Bahnhöfe ganze Anlage, grosse Knoten Hauptgleise + Abgänge + Detailblatt (Regeln 23, 35, GROSS)
8. **Darstellung** – Symbole, Beschriftung, Kompaktheit
Für Schritt 2 (Gleisverteilung als Optimierung): 1–3 harte Bedingungen, 4–6 gewichtet minimiert.

## Nachtrag 13.10.: Vorbilder für Olten (vorbild/)
- handzeichnung_region.png (Daniel): Topologie der Region. Olten kompakter Knoten; Zuläufe: Hauenstein-Scheitel (Läufelfingen–Trimbach, NW), Basistunnel (N, gestrichelt = Tunnel), Aarau 4-gleisig über Dulliken/Däniken (O), Jurasüdfuss über Wangen/Hägendorf (W), Süd zweifach: Borntunnel→Rothrist (NBS) und Aarburg-Oftringen→Zofingen.
- designvorbild_rothrist_rupperswil.png: Zielbild. Olten senkrecht, Gleise 1–12 nebeneinander; Zuläufe als parallele Bündel, so sortiert, dass Kreuzungen minimal sind (Kreuzungspunkte = Sterne); Weichen als feine Striche zwischen Parallelen; Nebengleise nur als graue Stummel mit Pfeil; Rothrist/Aarburg auf einem gemeinsamen waagrechten Band.
- Folgerung: Kern von Olten ist die Reihenfolge der Bündel (welches Streckengleis auf welcher Spur) mit Kreuzungen als Zielgrösse. Das ist Schritt 2 (Spur- und Weichenlage als MILP, Grundsätze 1–3 hart, Kreuzungen + Knicke + Abstand als Ziel).
- Vorgehen: Optimierung erst an Übungsstationen (Olten Hammer, Aarburg-Oftringen, Tecknau, Zofingen), Referenzen Thun/Ins/Murten/Kerzers als Regressionsschutz, dann Olten.
- Versuch Regel 40 (13.10.): Ebenen aller Ketten gemeinsam als MILP (scipy milp; Reihenfolge quer, Weichenrichtung, Fortsetzungen, Höhe). Schaltbar mit SPUR_OPT=1 oder rules.r40, Standard aus. Ergebnis am Prüfstand: ohne Bindung an den bisherigen Stand (34,1,12,13,0), mit Bindung (SPUR_WU=3) (29,1,7,14,2) gegenüber heute (29,0,7,12,3). Also kein Gewinn: die Überlagerungen (B) entstehen nicht bei der Ebenenwahl, sondern bei der Längslage der Weichen-Diagonalen (parallele Diagonalen mit gleichem Versatz fallen auf dieselbe Strecke). Nächster Schritt: Ebenen und Weichen-x gemeinsam optimieren (Diagonalen als Intervalle mit Mindestabstand, keine Überlagerung als harte Bedingung). Üben an Olten Hammer (Mini-Olten, B4/R4/W2), Aarburg-Oftringen (B5), Zofingen, Tecknau.
- Übung Olten Hammer (13.10.): Ausschnitt endet neu vor der Südeinfahrt Olten (olten_hammer_override s_max_fix 5240). Vorher reichte er bis dort, wo 450/500 quer zur Achse 410 laufen (Ursache von B4/R4/W2). Jetzt sauber. Olten Hammer ist im Regionalplan kein eigenes Feld, also keine Wirkung auf den Netzplan. Prüfstand gesamt (24,0,5,8,3) statt (29,0,7,12,3).
- Übung Aarburg-Oftringen Süd: B5 sitzen alle an einem Knoten (DKW Gl. 2, 451-Abgänge ab Gl. 2 und Gl. 1, Abstellstummel). Mehrere Weichen über 40 m fallen auf ein x zusammen, weil Seitenabgang (Regel 15/LAT_CUT), Regel 29 und Weichenstrassen-Gruppen die x-Lage nacheinander überschreiben. Ein weiterer Patch (Regel 41) wirkte nicht und ist wieder entfernt. Folgerung: eine einheitliche Geometrieschicht (jede Weiche = Knoten mit x/y, jede Verbindung gerade oder 60°, alle x in einem LP mit Reihenfolge und Mindestabstand) statt Einzelregeln.
- Olten Hammer Runde 2 (Hinweise Daniel 13.10.): (1) Gl. 4 rechts endete mit Prellbock, obwohl die Anlage weiterläuft: Gleisende mit Abgang in weggelassene Anlage (Regel 38) bekommt keinen Prellbock mehr; läuft die Anlage geradeaus weiter, gibt es einen Pfeil (CONT38). (2) Doppelter Spurwechsel West: der zweite Wechsel (crossover 196578220) fiel weg, weil sein Ende auf einem Randknoten des Streckengleises lag und als seitlicher Schnitt galt -> Regel 42 (Weichenverbindung an Randknoten ist nicht abgeschnitten). Der erste Wechsel mit Zwischengerade (zwei Ways in Serie) wird mit rules.r34n (nur Olten Hammer, global brach es Thun/Olten/Wangen) zur Diagonale. (3) Mittelperron zwischen 2 (Nord) und 3 (Süd): neue Override-Schlüssel "gleise" (Gleisnummer -> Ways) und platforms[].s (Längsbereich). Perronlage geschätzt (OSM ohne Perron).
- Arbeitsweise ab 13.10.: Bahnhof für Bahnhof über die Feedback-Seite (feedback/arbeit.json: reihenfolge, aktuell, stand[key].status "kontrolle" + "neu"). Nach jeder Fassung: Hinweise in der DB beantworten (behoben/rueckfrage), arbeit.json nachführen, bauen.py, Seite neu veröffentlichen.
- Tecknau (13.10.): tecknau_override.json mit r34n, nummern ["1","2"] (neuer Override-Schlüssel: auch Nebengleise beschriften), Mittelperron 3/4 (s 4330-4610, geschätzt), px_per_m 0.7 (kürzer). r34n gilt jetzt auch für kurze crossover-Ways in Serie (dd>0.8, L<100). Rückfrage an Daniel offen: was mit «Gleis 1 fehlt» gemeint ist.
- Runde 4 (13.10., Feedback-Seite): neue Override-Schlüssel "schraeg" (Ways als Diagonale erzwingen) und "pfeile" ({way, seite, laenge}: Gleis läuft mit Pfeil weiter, z. B. Wangen Gl. 1 links). Regel 28d (opt-in, Tecknau): an einer Weiche am Wayende zählt der Nachbar ausserhalb des Ausschnitts -> Hauptgleis läuft längs an den Rand statt seitlich (global eingeschaltet verschlechterte es Rothrist). Tecknau: s_max_fix 5170, side_lane_factor 1.0, schraeg [1315701709, 1315701703].
- Runde 5 (13.10.): Olten Hammer abgenommen. Override "gerade" (Way oder [way, s_bis]) erzwingt Gleis statt Diagonale; "pfeile" unterdrückt jetzt den Prellbock am Pfeilende. Wangen: Gl. 1 = 145634094/263977260/145634086 (auf einer Höhe, Pfeil links); Gl. 2 = 145634087 (links nur Entgleisungsvorrichtung). Tecknau ohne Befunde. Daniel: bei kleinen Nebengleisanlagen sind steile Harfenstränge (R) zweitrangig.
- Referenzen wieder geöffnet (13.10., Wunsch Daniel): Kerzers, Murten, Thun in feedback/arbeit.json; bauen.py zeigt Referenzen in der Arbeitsliste nicht mehr als abgenommen (pruefstand_basis bleibt Regressionsschutz).
- Murten: Achse neu durch Gleis 1 (achse_aus_ways.py -> reg/murten_axis.json, axis_snap false), pax 1-4, px_per_m 1.5.
- Kerzers (Keilbahnhof mit Kreuzung): Override "kreuzung" {a: 220 ab Gl. 6 -> Bern, b: 251 von Murten -> Gl. 1} zeichnet die Kreuzung schematisch als X mit unterem Band; Nebengleise an den kreuzenden Ways fallen weg, "weglassen" für U1 u. a.; pax 1-6; r28d. Neue Override-Schlüssel: "kreuzung", "weglassen".
- Runde 6 (13.10. abends): Feedback-Seite: weisses Planblatt deckt jetzt den ganzen Zoombereich (rect width="100%" hing am viewBox), Planfläche auch im Dunkelmodus hell. Abgenommen: Olten Hammer, Tecknau, Wangen, Murten.
- Kerzers: "kreuzung" um c/d erweitert (c = 258 Murten -> Weichenkopf Gl. 6, d = 259 Weichenkopf Gl. 1/3 -> Bern); Nebengleise an den kreuzenden Ways bleiben (ohne_nebengleise false), damit 4/5 über 380966231 angebunden sind; Override "platz" [[569100123, 1283055801, 130]] gibt der Kreuzung Breite (Warp-Mindestbreite); spurplan_check überspringt A/B zwischen den schematisch gezeichneten Kreuzungs-Ways (KX_WAYS). Läufelfingen: pax ["2"].
- Runde 7 (13.10. abends, alle Hinweise): Kerzers neu mit Süd-Nord-Achse (kerzers_axis.json) wie eine grosse DKW, Overrides x_kreuzung, schraeg, gerade, ebene_wie, pax_ways, platz, weglassen. Ins wieder offen: DKW-Symbol kleiner (alle Pläne), platz für Abzweig 256. Dulliken/Däniken Perrons; Däniken s_min_fix 3360 (Gl. 4 + Weiche Abstellgruppe). Schönenwerd/Zofingen: "zusatz_spurwechsel" (Gegenwechsel nach Ortskenntnis, fehlt in OSM). Zofingen Westkopf: "knoten" (Weichenknoten auf Gl.-4-Ebene), "direkt" (Gleis 195100348 als gerade Schräge), "knoten_versatz_m", platz. Aarburg: "stummel_versatz", Ausrundung kürzt jetzt alle Geraden am Abgang (keine Doppelung), Nulllängen-Stücke entfernt. Pfeile auf Hauptgleis-Enden entfallen. Gleisnummer im Perronbereich hat Vorrang. Regionalplan: Tecknau/Abgang 500 nördlicher (Platz Basistunnel), "xo_manuell" (Spurwechsel Abzweig–Zofingen). Offen: S-Kurven Region, Olten 4/7 Hauenstein, Überwerfungssymbol, Olten Hammer als Feld, Ins Meterspur (Daten fehlen), Ins Gl. 2 Rückfrage.
- Runde 8 (13.10. spät): Olten Hammer als eigenes Feld im Regionalplan (lage: eigenes_feld, drehung 0, Lage [-310,345]; Wangen [-940,318], Abgang 410 [-1580,343]) -> Linie 410 gerade. Olten-Versuch: s_max_fix 6000 / d_lim 110 zeigt die Trennung Hauenstein (Tecknau, 503 Sissach, Basel) vs. Aarau im Olten-Plan, aber noch B13/A1 und neue Abgänge für den Regionalplan -> als olten_override_versuch_nord.json abgelegt, nicht aktiv. Nächste Runde: Olten Nordkopf.
- Runde 9 (13.10. Nacht): neue Overrides "abzweig_diagonale" (Gleis zweigt aus Schräge ab, Kerzers 2/3), "dkw_symbol" [[knoten, richtung]], "kuerzen" {way: x_px} (Safenwil), "direkt" legt die Schräge durch DKW-Knoten und zeichnet DKW-Symbole, zusatz_spurwechsel mit "pax". Schematische Wege (_rund) ausgerundet. Ausrundung an Abgängen kürzt keine durchgehenden Gleise mehr (Ins-Lücke). Abgenommen: Dulliken, Schönenwerd. Offen: Olten-Runde; Ins Meterspur (GitHub-Benutzer für topo-daten fehlt).

## Nachtrag 14.10.2026 (abends) – Basel SBB und Bern, Entwurf 1
Anlass (D. Eckenstein): Basel und Bern werden für Projekte gebraucht; erste Knoten ausserhalb der Region Olten.
- Daten direkt aus GitHub (VXstone/topo-daten, OSM-Stand 12.10.): `ausschnitt.py` Rechteck (Basel 47.525,7.545,47.565,7.645; Bern 46.930,7.385,46.975,7.480), dann **neues `cut.py <bahnhof> <radius> <roh.json>`** (Kreis um den Stationsknoten, Ways an der Kreisgrenze geteilt; Basel 2600 m, Bern 2300 m). Ohne Kreis lagen alle äusseren Gleisenden auf einer Seite (Ways reichen weit über das Rechteck) und die Achse fand den Bahnhof nicht.
- Stationsknoten: im Ausschnitt nur «Basel SBB» bzw. «Bern» als railway=station lassen (sonst nimmt der Generator Bern Europaplatz).
- **Neues `achse_hauptgleise.py <bahnhof> lat,lon lat,lon`**: Achse (Regel 25) als kürzester Weg über Hauptgleise zwischen zwei Randpunkten, danach mit axis_snap ans Bündel angeschmiegt. Bern: 46.9515,7.4205 → 46.9630,7.4535 (Bahnhof liegt im ~100°-Bogen); Basel: 47.5453,7.5763 → 47.5417,7.6229.
- `spurplan_schema.py`: (1) findet die Achswahl kein Endpaar < 150 m am Bahnhof, wird die Grenze gelockert (450/1350 m) statt abzubrechen; (2) SVG-Höhe nimmt auch Linien oberhalb des Blattrands mit (Bern Westkopf lief oben hinaus).
- `run.sh <bahnhof> [--hauptgleise]` (neu abgelegt): schema --nowarp → warp → schema → warp → schema → check.
- Overrides: `bern_override.json` pax 1–13 (OSM: nur 2/4/8/12/13 ohne service, Rest siding), d_lim 140, sw_search_m 1500, Orte Wankdorf/Bümpliz…; `basel_override.json` pax 1–17 + SNCF 30/31/33/35 (alle siding in OSM), d_lim 120, sw_search_m 1600. Beide wie grosse Knoten mit `--hauptgleise`. Perrons noch aus OSM (keine Ortskenntnis eingetragen).
- Stand Entwurf 1 (Feedback-Seite, Gruppe «Grosse Knoten (Entwurf 1)»): Bern A2 B59 C1 D1 E2 W9 R10; Basel A1 B130 E7 W18 R10. Gleisreihenfolge im Perronbereich stimmt bei beiden.
- Offen Bern: Westkopf mit den 220er-Gleisen (laufen von 12/13 hoch über alle Gleise und wieder hinunter, vermutlich Überwerfung), nur 4 Gleise Richtung Lorraine/Wylerfeld, Perrons, Abgangsorte (Fribourg/Neuchâtel/Schwarzenburg West, Olten/Thun/Biel Ost – Abzweige liegen ausserhalb des Ausschnitts).
- Offen Basel: Ostkopf (Gellert/Wolf/Verbindungsbahn) mit vielen Überlagerungen, Verbindungsbahn nach Basel Bad Bf als lange Schräge aus dem Blatt, Gleise 17/20 fehlen, SNCF-Gleise ohne Nummer (Nummern > 30 werden nicht beschriftet), Perrons.

## Nachtrag 14.10.2026 (spät) – Region Neuchâtel, Entwurf 1
Anlass (D. Eckenstein): weitere Bahnhöfe auf Ins–Neuchâtel–Chambrelien, Twann–Neuchâtel–Boudry, Neuchâtel–Travers (22 Bahnhöfe; Ins bleibt Referenz).
- `claude/ne_vorbereiten.py`: Ausschnitt aus der GitHub-Schweizdatei (Rechteck 46.85–47.15 / 6.6–7.2 → `ne_region.json`), je Bahnhof nur der eigene Stationsknoten als railway=station (Halte wie Cressier, La Neuveville, Zihlbrücke umgetaggt), Kreis mit `cut.py` (1300–1600 m, Neuchâtel 2300 m), Override-Grundgerüst mit Ortstabelle Region Neuchâtel, margin_x 330, lt_dist_w 2.
- `claude/region_lines_neuchatel.json` (als `region_lines.json` in den Arbeitsordner): 210 Biel/Neuchâtel/Yverdon, 220 Ins/Neuchâtel, 219 Neuchâtel/Travers/Fleurier, 221 Pontarlier, 223/224 Neuchâtel/La Chaux-de-Fonds.
- `spurplan_schema.py`: (1) ohne Gleisnummern (Halte) Titel unter den Perrons statt x=nan; (2) `cfg.lt_dist_w`: bei der Linientabelle näherer Zielort bevorzugt (sonst «Yverdon» schon ab Cressier).
- `claude/viewbox_text.py`: viewBox seitlich so erweitern, dass Abgangstexte nicht abgeschnitten werden.
- Achsen: Neuchâtel `achse_hauptgleise.py neuchatel 46.9905,6.9150 47.0040,6.9560`; Marin-Epagnier `achse_hauptgleise.py marin_epagnier 47.0115,6.9960 47.0090,7.0260` + s_min_fix 2000 (Way 45581982 hat nur Knoten bei s 2300 und 2020 → lag sonst ganz ausserhalb, Hauptgleis zerfiel); Chambrelien `axis_refs ["223"]` (sonst Achse auf der 219 unterhalb).
- `claude/ne_feedback.py`: hängt die Pläne als Gruppe «Region Neuchâtel (Entwurf 1)» an die Feedback-Seite (liest die live Seite, ersetzt nur diese Gruppe).
- Stand: 18 Pläne ohne Befund; Le Landeron D1 R2, Cornaux B2 (Raffinerie-Anschluss), Bôle B3 W1, Neuchâtel A1 B12 E1 W8 R5.
- Offen: Perronlagen überall nur aus OSM; Personengleise in OSM oft siding (Marin 2/4); Neuchâtel (223 Richtung Vauseyon nur als Pfeil, Abstellanlagen, Perrons 1/5); Chambrelien (Spitzkehre, Orte geraten); Ligerz nach OSM-Stand.

## Nachtrag 14.10.2026 (Nacht) – Olten, Thun, Rothrist: Feedback-Runden 1–5
Neue Regeln/Schalter in `spurplan_schema.py`:
- **R45** DKW-Standard (Blaupause E9): Ketten von Schrägen durch DKW = eine gerade 60°-Linie; Klammern + 10 %-Ausrundung (grün auf Hauptgleis). Abzweige an Zwischenknoten werden auf die Gerade gelegt; nahe am Endgleis als Gabel. Kreuzungen teilen den Schnittpunkt. Overrides: `r45_weiter` (Kette durch diese Weichen/Kreuzungen weiterziehen), `r45_gabel` (Ast als Gerade vom Endgleis), `als_dkw` (Knoten wie DKW zeichnen, Ortskenntnis), `dkw_gerade` {knoten: [sa, sb]}.
- **R46** Weichen mit Mini-Radius bekommen vollen Radius; Teilpfade der Länge 0 entfallen (sonst Punkte).
- **R47** Weggelassener Way zwischen zwei gezeichneten Gleisen = Spurwechsel statt zwei Pfeile.
- Mindestabstand Abzweig ↔ DKW 0,4 Ebenen; Gleis, das in einer Schrägen endet, mündet ausgerundet; zwei Äste aus derselben Gabel parallel versetzt.
- Pfeil-Ausrundung kürzt kein Gleis, an dem noch ein Abzweig beginnt.
- `zeichnen` erweitert: Punkte `["n:<knoten>[+-px][@+-py]", …]`, `"y:<px>"`, `"c60:<knoten>[+-px]"` / `"c60-:"` (auf der 60°-Linie durch einen Knoten), `port_am_anfang`, `ueber` (Über-/Unterführung nach E6: Lücke im unteren Gleis, Brückenflügel aussen am Bündel), `punkt_anfang`. Weggenommene Ways verlieren auch ihre Pfeile.
- Neue Overrides: `portale` [{s, y:[n:…], dir}] (Tunnelportal E7, dir −1 = öffnet nach links), `seitlich` [ways] (Abgang erzwingen), `weglassen_ohne_pfeil`, `ebene_tausch`, `enge_ebenen` [ebenen] (Abstellebenen zwischen Hauptgleisen schmal → Hauptachsen enger), `perron_einheitlich` (gleiche Länge/Mitte), `abgang` {way: {ref, ort}} für Beschriftungsgruppen.
- Seitlicher Schnitt direkt am Knoten (Olten Ost, Linie 531): Nachbar-Hauptgleis wird Abgang (LAT_CUT).
Olten: `olten.json` um Ways aus `region.json` ergänzt (bis Hauenstein-Portal; Original in /tmp gesichert, nicht im Projekt), s 4000–7060, Doppelspuren am Westrand gepaart (zeichnen), Aarau-Bündel mit Unterführung, 531 eng, Doppelspur + Spurwechsel vor dem Portal. Offen: dichter Knoten Ost (Schrägen von 3/4 hinunter, B-Befunde), Doppelspur-Paare im Nordosten (500 zusammen, 503 separat).
Thun: Dreispur 290+Gürbetal am Westrand (zeichnen mit Knotenbezug), enge_ebenen [11,10,9,7,6,5,4], Gabel Ost. Rothrist: zweite DKW per `als_dkw`.

### Ablauf einer Feedback-Runde (für alle Sitzungen gleich)
1. Hinweise holen: `ArtifactData query feedback` (neu seit letzter Fassung: `erstellt` oder `rueckmeldungen[].am`).
2. Je Hinweis Stelle im SVG suchen (Plankoordinaten = SVG-Koordinaten), Segmente mit `SEGDUMP=1 python3 spurplan_schema.py --src <b>.json [--hauptgleise]` (Zeile: id way pax a b xa ya xb yb s0 s1 lane) und `spurplan_check.py` lesen; zuerst Override, erst bei Mehrfachnutzen neue Regel.
3. `sh run.sh <b> [--hauptgleise]`, PNG-Ausschnitt ansehen (cairosvg). Referenzen (reg/) brauchen 0 Topologie-Befunde.
4. `python3 pruefstand.py` (timeout 600 s); keine neuen Rückschritte bei abgenommenen Bahnhöfen.
5. Regionalplan: Rothrist-Variante (`regional_rothrist/`, Schema kopieren, run.sh, ports/bare als `rothrist_regional_*`), `netz_lage.py olten_region "Region Olten" feedback/region.svg`.
6. `feedback/arbeit.json` (stand[key].neu) nachführen, `python3 feedback/bauen.py "Region Olten" feedback/region.svg`.
7. Veröffentlichen. Wird die Veröffentlichung wegen einer neueren Fassung (andere Sitzung) abgelehnt: `python3 feedback/merge_live.py <gespeicherte live.html>` (übernimmt fremde Pläne nach `zusatz_plaene.json` und den Untertitel), neu bauen, Diff nur PLANS/ARBEIT prüfen, erneut veröffentlichen.
8. Hinweise beantworten: Status «behoben» + `antwort` + `version`; nur teilweise erledigt = Status lassen, Antwort mit Stand; Unklares = «rueckfrage». Nie «erledigt» setzen und nie selbst abnehmen (Abnahme macht D. Eckenstein).
9. Projekt nachführen: spurplan_schema.py, geänderte Overrides, feedback/bauen.py, seite.html, merge_live.py.
- Achtung, mehrere Sitzungen gleichzeitig: Diese Sitzung hatte `spurplan_schema.py` im Projekt mit ihrer Fassung überschrieben; die vier Änderungen der Basel/Bern/Neuchâtel-Sitzung (Achswahl-Grenze 150/450/1350 m, viewBox mit Linien oberhalb des Blatts, Titel bei Halten ohne Gleisnummern, `cfg.lt_dist_w`) sind am 14.10. nachts wieder eingebaut. Vor jedem `project_write` von `spurplan_schema.py` deshalb zuerst die Projektfassung lesen und fremde Änderungen übernehmen (Regel: nie blind überschreiben).

### Runde 6 Olten (15.10.2026) – Knoten Ost von Hand
- `zeichnen`-Linien mit `tag: "ostknoten"` (7 Linien, Knotenbezug `n:`) plus `knoten_x` für die Enden; parallele 60°-Schrägen mindestens 28 px (ein Gleisabstand) auseinander. Zusammenführungen (378517710 + 197523816 in 2077484616): zuerst auf das Gleis, dann vereinigen.
- `spurplan_schema.py`: `knoten_x` gilt jetzt auch für die Enden einer Weichenstrasse (vorher wurde das Ende aus s gerechnet und überging den Override).
- Prüfstand Olten: B6 E4 W9 R1 (vorher B8 C1 E6 W9 R1). Offen: Westkopf Treppe 7–10 (xtwx), Doppelspuren NE (zt9q).
- Der Ablauf ist zusätzlich als Skill «spurplan-feedback-runde» gespeichert.

## Nachtrag 15.10.2026 – Perrons aus SBB Open Data (Basel, Bern Entwurf 2)
- GitHub-Workflow lädt zusätzlich SBB-Datensätze von data.sbb.ch ins Release `daten`: `perronoberflache.geojson.gz` (Perronfläche: bps_name, p_nr z. B. «5/6», perrontyp Mittel-/Aussen-/Dienstperron, p_lange, Punktgeometrie) und `perron.geojson.gz` (Perronlänge). `perronkante` lieferte 404 (Datensatz existiert laut Schema mit kundengleisnummer/Kantengeometrie, Export-ID noch klären). Quelle angeben: SBB AG, Open Data.
- Push-Konflikt im Workflow behoben: `git pull --rebase origin main && git push`. Während eines Laufs nicht committen.
- Daraus Override `platforms`: p_nr «a/b» = between [a, b], einzelne Nummer + Aussenperron = outer.
  - Bern: 1/2, 3/4, 5/6, 7/8, 9/10, 12/13, 49/50 (westl. Verlängerung 9/10); Gleis 11 ohne Perron. pax + 49, 50.
  - Basel SBB: 1/2, 3/4, 5/6, 7/8, 9/10, 11/12, 14/15, 16/17, 18 (Aussen), 19/20, SNCF 30/31, 33/35; Gleis 13 ohne Perron. pax + 18, 19, 20.
- Stand Entwurf 2: Bern A2 B66 D1 E1 W14 R10; Basel A1 B130 E7 W17 R10 (Topologie-Befunde unverändert, Perrons neu).
- Vorschlag: Perronanordnung künftig für jeden neuen Bahnhof automatisch aus perronoberflache übernehmen (statt Ortskenntnis/OSM).

### 15.10.2026 – Regionalplan Neuchâtel Entwurf 1, Regionalplan Olten
- Arbeitsordner `ne/`: Daten aus GitHub (`ausschnitt.py … ne=46.85,6.6,47.15,7.2 --flach`), `ne_vorbereiten.py`, Achsen Neuchâtel/Marin mit `achse_hauptgleise.py`, Ins aus `reg/`.
- Topologie in `ne/topo/` (damit keine Achsdateien die Spurpläne ändern): Daten gefiltert (Jura nördlich 47.025 / westlich 6.93 weg, Ost unterhalb 47.03 östlich 7.125 weg, Haltepunkte ohne Normalspur weg), Perimeter als Vieleck `ne_region_rand.json` (neu in netz_topologie.py: Abgänge auch an dessen Rand), `topo_ergaenzen.py` für die fehlende Kante Chambrelien–Les Geneveys (Spitzkehre).
- Lage: `ne_lage_bauen.py` reiht die Kästen nach ihrer Breite (Reihen 210 West, 219, 223, 210 Ost als Treppe, 220). Chambrelien ohne Drehung, 224 nach oben (Spitzkehre). Prüfung 2 = 0.
- netz_lage.py: weisse Blatt-Rechtecke in eingebetteten Spurplänen (`<rect … width="100%">` mit x/y) werden entfernt (verdeckten Nachbarpläne); neue Knoten ohne Lage geografisch; Stichstrecken ohne Endknoten weggelassen.
- Regionalplan Olten: Rothrist-Variante hat ein eigenes Override (nicht das des Detailplans, sonst falscher Ausschnitt); 410/Olten Hammer/Wangen 100 tiefer, keine Schlaufe am Südkopf.
- Feedback-Seite: mehrere Regionalpläne (`feedback/regionalplaene.json`, Seite erkennt Gruppe «Region»).
- Offen Neuchâtel: Ligerz fehlt (kein Stationsknoten in OSM), Halte mit Spurplan (Cressier, La Neuveville, Zihlbrücke) nur als Haltesymbol, Abgang 210 Yverdon mit senkrechtem Stück.
- 15.10. später: Olten `zeichnen` tag «basel_paar» (318/319 als parallele Doppelspur von Gl. 11/12 auf die Basler Gleise, 531 mündet von unten ins zweite Gleis, Spurwechsel danach). Neuchâtel: Cressier, La Neuveville, Zihlbrücke als Spurpläne (Topologie kind station), Ligerz kein Bahnhof mehr, La Neuveville–Twann Einspur (`gleise_strecke` in der Lagedatei, überzählige Gleise laufen mit 60° ein).
- 15.10. Runde Blaupause/Thun/Olten/Region: Blaupause B6 Halt an Doppelspur. Thun `zeichnen` «schlaufe_239» (172115483+172031152 sind ausserhalb dasselbe Gleis) und «ast_520460292», knoten_x 1829806191/1829799236. Olten: «west_bern» (Bern 7/8 gerade), Luzern A gerade auf 10, `perron_einheitlich` als {mitte_px, laenge_px}, «vierspur» (paralleler Versatz 7/8/9), 531 links als Kreuzung K134 bis Gleis 1, Gleis 480 als Pfeil (`zeichnen`-Option `pfeil`). Region Olten: Topologie-Kante #22–#24 (531) entfernt, neue Kanten Olten–#99–#22 mit `_eigen` (netz_lage legt eigene Strecken nicht mehr mit parallelen zusammen), Spurwechsel auf freier Strecke ausgerundet.
- 15.10. (später): Olten Spurwechsel Ost (aar) geradeaus in die Schräge (c60), Brückenflügel E6 aussen und nach aussen (Vorzeichenfehler behoben). Region: netz_lage `JMERGE` (mehr Gleise als Gegenseite: Bündel nebeneinander, überzählige münden ein), `buendel_zusatz` (Lagedatei: freie Anschlüsse weiterer Linien ins selbe Bündel, Olten|Dulliken mit 531), `gleise_strecke` Olten|Dulliken 4, Topologie Kante #19–#22 als 540+531 (6 Gleise). Rothrist Ost: `frueh` [Rothrist|Olten] (3/2 steigen sofort über 4), `spaet_anteil` 0.9, Abzweig #43 nach rechts (-60) – keine überlagerten Achsen mehr. merge_live.py: region_ne zählt zu den eigenen Plänen.

### 15.10.2026 (Mittag) – Olten bereit zur Abnahme, Verbindungsprüfung
- Olten Knoten Ost von Hand (`zeichnen`, Tags «ostknoten3/5/6», Lane-Bezüge Y158=n:635801600, Y182=n:635801598, Y206=n:635801508, Y230=n:635801190, Y254=n:251694977, Y278=n:635801317):
  - nach Daniels Skizze: 1/2 gehen direkt zwei Ebenen hinunter auf die Höhe von 4, 3 mündet in diese Schräge (c60 auf derselben Linie), 4 geht gleich nach den Perrons eine Ebene hinunter in die weisse Fläche; beide laufen gerade, die Linie von 1/2/3 mündet vor der Aarau-Schräge in 4 ein.
  - OSM-Topologie: 3 und 4 erreichen nur Aarau 1, 7/8/9 alle vier → 4 → Aarau 1, 7 → 2, 8 → 3, 9 → 4 je gerade; Spurwechsel doppelt 7/8, einfach 8 → 9, doppelt 206/230; Richtung Hauenstein ein Spurwechsel 206 → 182.
  - Gleis 10 → Basistunnel (Way-Kette 378516511/902335242/173173290/50062884) von Hand: bleibt auf 302, bis Gleis 11 die Ebene 326 verlassen hat (vorher 40 px Überlagerung = 4 B-Befunde).
  - Doppelter Spurwechsel Hauenstein im Tunnel (laut Daniel liegt er erst im Tunnel; OSM stimmt), Abstellgleis 480 West als ein Ast aus der Mitte der Schräge (Schräge ist in OSM `service=siding` und mündet knapp ausserhalb ins Solothurner Gleis).
- `spurplan_schema.py`: Über-/Unterführung erkennt auch waagrechte `zeichnen`-Linien (M…L… auf gleicher Höhe) als untere Gleise; `zeichnen`-Option `pfeil`; `perron_einheitlich` als {mitte_px, laenge_px}; Brückenflügel-Seite korrigiert.
- **Neu `verbindungen_pruefen.py <bahnhof> [--hauptgleise] [--pfad Gleis,W|O,Abgang]`**: für jedes Perrongleis (beide Richtungen) und jeden Abgang die ohne Richtungswechsel erreichbaren Abgänge, einmal im OSM-Netz (Hauptgleise; zusätzlich mit `service=siding` als «Hinweis»), einmal in den grünen Linien des SVG (Teilpfade, Übergang nur bei < 35° bzw. an Linienenden < 62°, Kreuzungen verbinden nicht). Abgänge mit einem geradeaus-Stück ausserhalb (250 m), damit Spurwechsel knapp jenseits des Planrands zählen. Meldet zusätzlich Weichen ohne Ausrundung (Linienende trifft ein Gleis unter > 35°).
- Stand Olten: alle 10 Perrongleise und 13 von 15 Abgängen stimmen; die 2 Restmeldungen betreffen die Hauenstein-Abgänge (Spurwechselpaar im Tunnel, Planrand). Prüfstand Olten (2, 0, 7, 1, 4): B2 = zwei Nebengleise, die 4 px neben dem Gleisanfang abzweigen (Topologie stimmt), W/E/R fast nur Brückenlücken/-flügel, Tunnelportal, Einmündung 4.
- 15.10. (später): Olten nach Daniels Hinweisen auf Fassung 47: Gleis 1 als eine gerade Schräge zwei Ebenen hinunter (2 und 3 münden ein, 3 gerade als Nebengleis = OSM siding 196578217), Spurwechsel 3 → 4 (OSM 230265798) vor der Einmündung, 4 senkt sich danach; 11 → Ast von 10 (siding 50062939), 366 vom Ast hinauf zu 9 (siding 718445981) mit Pfeil in die Abstellgruppe, Pfeil von 9 in die Abstellgruppe 61 (R38 zeichnet keinen Pfeil, wenn die Anlage parallel weiterläuft – hier von Hand). Tag «ostknoten7».
- Verbindungsprüfung aller Bahnhöfe (Gleisnummern-Lage wird jetzt aus dem Plan gelesen): Aarburg, Safenwil, Wangen, Dulliken, Däniken, Schönenwerd, Tecknau, Läufelfingen, Olten Hammer, Thun, Ins, Murten 0 Abweichungen. Rothrist 2 (Spurwechsel 453/451 knapp ausserhalb des Plans), Zofingen 2 (Gegenspurwechsel nach Ortskenntnis, nicht in OSM; Gleis 11 = Suhrer Abgangsgleis), Kerzers 1 (Gleis 16 am Rand = Abgangsgleis Gümmenen). Die Prüfung meldet Gleise, die zugleich Abgangsgleis sind, und Spurwechsel jenseits des Planrands als Abweichung.
- **Regel 48** (opt-in `cfg.rules.r48`, aktiv in Rothrist, Zofingen, regional_rothrist): Spurwechsel, die an der Weiche spitz beginnen («M x,y L … Q»), bekommen am Anfang dieselbe Ausrundung wie am Ende; `zusatz_spurwechsel` als Standardfigur mit Ausrundung. Global noch aus, damit abgenommene Bahnhöfe unverändert bleiben (Thun/Ins melden nur 36°-Treffer an DKW-Klammern).

### Nachtrag 15.10. Nachmittag (2): Olten-Ostkopf nach OSM, Kerzers 16
- Override `nummern_weg` (neu, Schema): Gleisnummern weglassen (Kerzers: 16 = Ausfahrgleis Gümmenen).
- Olten Ostkopf Gleise 7/8/9 Weiche für Weiche nach OSM neu gezeichnet (`zeichnen`, tag ostknoten8, Feld `_osm` je Linie mit Way-Nummer). Die alten Linien ostknoten2/3/4 für 7/8 sind ersetzt (V zwischen 7 und 8 gab es in OSM nicht).
  OSM-Reihenfolge: 196578221 (8→7), 196578224 (7→4er-Linie), 679251563 (7→313), 679251562 (8→9, nach 366), 7 wechselt auf die Lage von 8 (→314; 8 mündet über 679251567 ein), 679251565 (Nebengleis 9→314), 679251541 (314→313).
- Abstellgruppe 41–48 liegt zwischen 9 und 11, im Westen nur über 366 erreichbar; 46/47/48/41/44 enden im Osten stumpf, 42+45 → Gleis 52 nach Süden (ohne Verbindung zu 315/318/319). Rückfrage an D. Eckenstein, ob 45 in 315 mündet.
- Hilfsmittel: `SPUR_SD=<datei> python3 spurplan_schema.py --src olten.json --station olten --out /tmp/x.svg` (ohne --hauptgleise) liefert s/d aller Knoten inkl. Abstellgleise. Achtung: Schema-Aufrufe ohne `--out` überschreiben `olten_spurplan.svg` → danach `sh run.sh olten --hauptgleise`.

### Nachtrag 15.10. Nachmittag (3–5): Olten bereit zur Abnahme
- Ostkopf nach Skizze D. Eckenstein: Basel-Linie (350/330/559) eine Ebene über 182 (y158), 1/2 als Aarauer Linie (361/351/331) auf 182, taucht bei x1144 auf 206 ab; Spurwechselpaar 197523816/679251553 zwischen 182 und 206; Nebengleis 679258585 von 158 quer über 182 auf 206. 7 auf 230 durchgehend bis 313 (Lesbarkeit). Tags ostknoten8/9/10.
- Luzern Doppelspur auf 302/326 (Tag luzern), Abgänge West bei x124 (vorher 229) mit den drei Spurwechseln knapp ausserhalb des Ausschnitts (Tag west_rand: 137216805/137713015, 137216812, 137216810).
- 410 West: 976727148/50062909 von Hand ab x418, 50062913 schwarz (Scheinverbindung 410→3 weg). Zufahrt Abstellgruppe 564–566 (692444531/532) weggelassen.
- verbindungen_pruefen.py: `--rand_m N` (Abgangskette weiter hinaus, Olten 450), Abgangskette bleibt auf dem Streckengleis (keine siding/crossover), Regel 43 auch ausserhalb des Plans (Verbindungen zwischen Hauptgleisen). Olten: alle Perrongleise ok; 4 Meldungen = Spurwechsel zwischen zwei Abgängen am Planrand (Basel im Tunnel, Luzern/Bern West).
- Kerzers: Prüfung meldet Gleis 1 Ost → Lyss (OSM 3 / Plan 2) – bestand schon vorher, nicht angefasst (abgenommen).
- Prüfstand Olten (0, 0, 6, 1, 4): keine Topologie-Befunde mehr; W/E/R an Brücken, Portalen und der Weichenhäufung West.
- 15.10. spät: Olten nach Hinweisen 55–62 fertig zur Abnahme. 531 ist laut D. Eckenstein eine Durchschneidung (OSM bridge=yes trifft nicht zu) – keine Brücke zeichnen. Schema: Brückenflügel/Lücken jetzt je Bündel (Kreuzungen < 80 px, gleiche Richtung).

### 15.10.2026 abends – Region Olten fertig zur Abnahme, Bahnhöfe, Region Neuchâtel Entwurf 3
- Region Olten: Hinweise 19pu, 9ti3, 2016, 70ce, am5t, 51ta behoben (v62). netz_lage.py (Tunnelportale, XO nur auf geraden parallelen Stücken, spaet_anteil_strecke) im Projekt.
- spurplan_check.py: Prüfung B wertet zwei Gleise auch dann als verbunden, wenn ein kurzes Zwischenstück (< 80 m, z. B. Brücken-Way) ihre Enden verbindet (Aarburg Gl. 1 -> 451).
- spurplan_schema.py: "zeichnen.weg" nimmt auch die Prellbock-Punkte der weggenommenen Ways weg (wenn kein anderes Gleis dort endet). Olten unverändert (Byte-Vergleich).
- Aarburg: DKW 261001938 als gerade 60°-Linie (zeichnen). Rothrist: Industriegleis Nord aus Gleis 5 an der richtigen Weiche + Stumpengleis (zeichnen). Wangen: beide Abstellfächer mit 60°-Schrägen. Prüfstand: Topologie überall 0.
- Kerzers zeigt im Prüfstand W2 statt R1 (Rückschritt nach Regel): Befund an tangentialen Einmündungen, Bild unverändert; offen.
- Region Neuchâtel: netz_lage.py aus Olten übernommen (neu: Lage-Schlüssel "einmuenden_bei_wenig_abgaengen"). ne_lage_bauen.py: R = 200, Kastenbreite aus Gleisanlage + Abgängen, "ausrichten" je Reihe (Gleishöhe), Abgänge 219 oben/221 unten, Corcelles stack_aus + spaet_anteil 0.97 (223 mündet bei Abzweig #24). Plan nach olten/feedback/region_ne.svg kopieren, dann bauen.py.

### 15.10.2026 Abend – Regionalpläne gedrängter, Neuchâtel-Bahnhöfe nach Hinweisen
- Region Olten gedrängter: y-Werte jenseits ±520 bzw. +950 (Süden) um 30 % gestaucht, Abgänge 410/540/650/504/450 näher. Olten Süd: Zeile Hammer/Wangen/410 tiefer (keine U-Kurve), Spalte Aarburg/Zofingen auf die Olten-Abgänge (keine Stufe). Backups der Lagedatei in /tmp nur sitzungsweise.
- netz_lage.py: Lage-Schlüssel "einmuenden_versatz" (Olten 8 wie abgenommen, Neuchâtel 0 = genau 60°), "einmuenden_bei_wenig_abgaengen".
- ne_lage_bauen.py: R = 150, G = 80, ausrichten() mit REF-Filter je Bahnhof (Chambrelien 223, Auvernier 210), Abgang 224 rechts oben (Spitzkehre), frueh Bôle|Auvernier.
- spurplan_schema.py neue Override-Schlüssel: "perrons_px" [[x0,x1,y]], "nummern_px" [[text,x,y]], "kein_pax" [ways]. spurplan_check.py: Prüfung D überspringt Ketten, deren Ways alle in zeichnen.weg liegen.
- Konvention für die überarbeiteten Neuenburger Bahnhöfe: Perron 110 px, Gleisnummern in der Perronmitte, OSM-Perrons aus ("platforms": []).
- Chambrelien: neue Achse (achse_hauptgleise.py chambrelien 46.965591,6.809211 46.973505,6.828947), alles von Hand gezeichnet (zeichnen), "abgang" 27838827 = 223 Neuchâtel.
- Stationsweise: Colombier/Le Landeron/Cornaux/Saint-Blaise CFF/Travers per "weglassen" der Spurwechsel mit Zwischengerade (Gleise rücken eine Achse zusammen) + Neuzeichnen mit n:-Knoten; Bôle Anschlussfächer neu; Ligerz Doppelspur ohne Abstellgleis; Twann kein_pax + längerer Stumpen; Auvernier 219 schräg links oben.
- ne/ne_zusatz_update.py erneuert die NE-Pläne in olten/feedback/zusatz_plaene.json (Gruppe bleibt, Label «Entwurf 2 · Stand 15.10.2026»).

### 15.10.2026 spät – Region Neuchâtel mit Kerzers–Murten
Anlass (D. Eckenstein): «die Bahnhöfe um Kerzers-Murten fehlen im Regionalplan Neuchâtel».
- Topologie neu in `ne/topo2/`: `poly_clip.py` schneidet die Daten auf das Vieleck `ne_region_rand.json` zu (Ways am Rand auf den Rand gekürzt; Knoten nur innen). Vieleck neu bis 46.918 S / 7.205 O (Kerzers, Murten innen; Papiliorama, Fräschels herausgenommen). Aufruf `python3 netz_topologie.py ne_region_data.json ne_region 46.918,6.655,47.105,7.205`, danach `topo_ergaenzen.py ne_region ne_region_data.json 7 8 224` und von Hand: La Neuveville/Cressier/Zihlbrücke/Muntelier kind station, Ligerz-Kanten 1 Gleis. Knotennummern haben sich verschoben (#24→#29, Abgänge #38/#40/#43/#44/#45).
- region_lines: 220 bis Bern, 251 Lyss/Kerzers/Murten/Payerne, 255 Murten/Fribourg, 256 Murten/Ins.
- Neue Spurpläne: Müntschemier (Anschlussgleise vereinfacht, Gl. 2 Ost von Hand gegen falschen Pfeil), Sugiez (Perron 1 Kreuzungsgleis, 2 Streckengleis nach OSM), Muntelier-Löwenberg (Anschlussgleise als zwei Stumpen), Galmiz (Kreuzungsgleis von Hand, knoten_lane/knoten_x gegen Achsfehler). Kerzers und Murten unverändert aus `olten/reg` (abgenommen).
- Lage wie im Dreieck-Netzplan vom 1.10.: Kerzers senkrecht (drehung 90: Ins links oben, Lyss rechts oben, Murten links unten, Bern rechts unten), untere Reihe Murten – Muntelier – Galmiz, Sugiez senkrecht zwischen Ins und Muntelier. ne_lage_bauen.py: `pr(k, rot)` für gedrehte Kästen, alte Abzweig-/Abgang-Schlüssel werden aus der Lagedatei gelöscht.
- Prüfung 2 (Lage) 0, Prüfung 1 nur noch La Neuveville/Zihlbrücke. Plan 9008 × 1755.
- Offen: Müntschemier ohne Perrons (OSM hat keine), Galmiz Perron zwischen Streckengleis und Kreuzungsgleis (OSM), keine Gleisnummern in Galmiz/Muntelier.
- Regelwerk (Entwurf zum Korrigieren durch D. Eckenstein) als Doc «Regelwerk Spurpläne»: https://claude.ai/code/artifact/4e313295-38e5-4eac-968a-5649cbac5ff9 – Grundsätze, Regeln B1–B19 (Bahnhof) und N1–N11 (Region) mit Verweis auf die Blaupausen-Felder, Zusammenarbeit, offene Fragen.

### 16.10.2026 – Typvorlagen (Standardisieren statt Manufaktur), schräge Bahnhöfe im Regionalplan
Anlass (D. Eckenstein): «Standardisieren statt jedes Mal Manufaktur und Zeichnen. Irgendwann kommen dann Optionen zur Veränderung dazu.» und «Bahnhöfe müssen nicht streng horizontal oder vertikal sein, auch 60 Grad darf genutzt werden auf dem Regionalplan.»
- `claude/typ_vorschlag.py <b>`: liest OSM-Ausschnitt + Abgänge des allgemeinen Laufs und schlägt eine Beschreibung vor: typ (halt | halt2 | kreuzung | ueberholung | manufaktur), Querschnitt in der Perronmitte (ohne yard/spur/industrial), Hauptweg zwischen den Abgängen (usage=main bevorzugt) → Kreuzungsgleis oben/unten, Perronlage (oben/unten/zwischen), Anschlüsse (Weiche ±600 m, Seite, innen/aussen, Stumpen 1–2), seitliche Abzweige. `mit_ortskenntnis()` übernimmt Gleisnummern und Perronlage aus den geprüften Overrides (nummern_px, perrons_px).
- `claude/vorlage.py <b>`: zeichnet nach Override-Schlüssel "vorlage" immer gleich (Ebenen 24 px, 60°, Zulauf 110 px, Kreuzungsgleis 240 px, Perron 110 px mit Nummer in der Mitte, Anschlussstumpen, seitlicher Abzweig, doppelter Spurwechsel). Sichert die OSM-Abgänge als `<b>_osm_ports.json`, ordnet sie den Vorlage-Enden zu (Liniennummer, Ort, Peilung bleiben) und schreibt Abweichungen (Anzahl Abgänge je Seite, seitliche Abzweige) nach `<b>_vorlage_befund.json` (Feedback-Seite: Spalte A). Ausgabe im selben Format wie der allgemeine Lauf.
- `ne/run.sh`: ruft am Ende vorlage.py, wenn das Override "vorlage" enthält. `ne_zusatz_update.py`: Vorlagen-Befunde statt spurplan_check, Label «… · Typvorlage <typ>».
- Neuchâtel: 14 Bahnhöfe nach Vorlage (Sugiez, Galmiz, Müntschemier, Champ du Moulin, Noiraigue, Saint Blaise-Lac = kreuzung; Gampelen, Cressier, La Neuveville, Boudry, Serrières, Saint-Blaise CFF = halt2; Zihlbrücke, Muntelier-Löwenberg = halt). Manufaktur bleiben Neuchâtel, Auvernier, Colombier, Bôle, Chambrelien, Corcelles, Cornaux, Le Landeron, Marin, Travers, Twann, Ligerz, Kerzers, Murten, Ins. Rückweg: Schlüssel "vorlage" aus dem Override löschen, run.sh.
- `netz_lage.py`: Drehung auch ±60/±120 (rotv allgemein, Kastengrösse gedreht, Name rechts neben der Mitte); 0/90/180 unverändert (Region Olten byte-gleich).
- `ne_lage_bauen.py`: Sugiez unter 60° auf der Geraden ab Abzweig #35, Lage so, dass die 60°-Schräge nach links unten genau in den Abzweig von Muntelier trifft (oberes Ende mindestens 60 unter der Reihe Ins). Plan 8139 × 1755.
- Regelwerk-Doc: N2 (schräge Lage erlaubt), Abschnitt «Ausbau».

### 16.10.2026 abends – Reinform + Zusätze, Blaupause 2, gerade Regionalpläne, Region Neuchâtel erweitert
Anlass (D. Eckenstein): Schafis/Zihlbrücke Gleiszahlen prüfen; Regionalpläne gestaucht, «keine Treppe, ungefähr gerade Strecke zwischen zwei Bahnhöfen, leicht proportional zur Distanz»; Bahnhofstypen in die Blaupause; «Reinform + Addons» statt Typenvielfalt (Drehung/Spiegelung als Eigenschaft); Region erweitern bis vor Payerne, Fribourg, Bümpliz Nord, Biel, La Chaux-de-Fonds, Yverdon.
- OSM: La Neuveville–Ligerz Doppelspur (43797446/49), Einspur Ligerz–Twann; Ligerz als Bahnhof (Abzweig-Knoten umbenannt, Plan ligerz). Zihlbrücke: Doppelspur beginnt 200 m östlich (Weiche 632385979). Travers: 219 = Pontarlier, 221 = Fleurier (waren vertauscht).
- `vorlage.py` neu: {"strecke": einspur|doppelspur, "form": halt|kreuzung|ueberholung, "ueberholgleise", "perrons", "spiegeln", "gleise", "pax", "orte", "zusaetze": [spurwechsel (ende, anzahl 1|2, richtung), anschluss (ende, lage, seite, stumpen, pfeil), abzweig (ende, seite), doppelspurbeginn (ende, seite)]}. Seiten wie gezeichnet. Alte Beschreibungen werden umgesetzt (normalisiere). Masse: Zulauf 70, Kreuzungsgleis 200. OSM-Abgleich: Streckengleise je Seite = max(Abgänge allgemeiner Lauf, Gleiszahl der Nachbarstrecke aus der Topologie).
- `python3 vorlage.py --blaupause2 datei.svg`: Blaupause 2 (R1–R8 Reinformen, L1–L3 Lage, Z1–Z8 Zusätze) aus demselben Code; feedback/bauen.py hängt sie unter «Werkzeugkasten» an.
- `typ_vorschlag.py`: liefert die neue Beschreibung (Spurwechsel aus kurzen Querways, Doppelspurbeginn aus der Topologie).
- Regionalplan automatisch: Lagedatei {"auto": {c0, c1, p, gap, wg, abzweig_gap, knoten_gap}} → `lage_auto.ketten`: Bahnhöfe mit genau einer Strecke links und rechts liegen auf Ketten (gerade Linie zwischen zwei Knoten, Kästen in Kettenrichtung gedreht, beliebiger Winkel); Knoten (Abzweige, Abgänge, Bahnhöfe mit mehr Strecken) per Ausgleichsrechnung (Soll-Vektor je Kette: Richtung Geografie, Länge max(Platzbedarf, c0 + c1·km^p)), Ketten an einem Knoten ≥ 28° gespreizt, Überlappungen (gedrehte Rechtecke, Trennachsen-Test) durch Abstandsbedingungen gelöst. netz_lage: Verbinder darf in AUTO gerade in beliebiger Richtung laufen, Abzweige/Abgänge zeigen auf das andere Ende. Ohne "auto" unverändert (Region Olten byte-gleich).
- Erweiterung (`ne/topo3/`): Daten 46.78–47.16 / 6.57–7.42 (ausschnitt.py), Halte ohne Normalspur und Standseilbahnen weg, Vieleck `ne_region_rand.json` (vor Yverdon, Payerne, Fribourg/Pensier, Bümpliz Nord, Biel, La Chaux-de-Fonds, Fleurier, Aarberg; Niederwangen und Yverdon–Payerne ausgeschlossen). 26 neue Bahnhöfe (alle nach Vorlage; Avenches Ausschnitt 2200 m, Münchenwiler "orte"). Plan 7916 × 5330, Prüfung 1 = 0, 3 = 0, 2 = 7.
- Offen: Prüfung 2 (Uferlinien liegen enger als auf der Karte; Chambrelien rechts von Bôle), kleine Haken an zwei Abzweigen (Les Deurres), Ketten-Winkel frei statt 60°-Raster (bei Bedarf auf 15° runden).

### 17.10.2026 – Hinweisrunde Region Olten + Neuchâtel, Gruppierung, Skizze (Seite v71)
- Region Olten: Abzweig #24 (Trimbach/Tecknau) in der Topologie aufgelöst – Kanten #19–#13 (500, 2 Gl.) und #19–#15 (503, 1 Gl., `_eigen`) → der Trimbach-Ast nutzt den 503-Seitenabgang von Olten (vor dem Portal). Olten `portale` s 6890 → 6650 (Daniel; OSM-Tunnelbeginn 6890). Abgang 503 #37 auf y −1285 (Halte Sommerau/Rümlingen/Buckten auseinander, bleibt unter Abgang 500), Abgang 504 #38 auf y 1000.
- netz_lage.py: (1) überzählige Port-Gleise münden in die tatsächlich gezeichnete Linie mit ≤30° (vorher quer zur Portrichtung, "90 Grad ins äusserste"; alt: Lage `einmuenden_alt`). (2) `_kreuzungen()`: Kreuzung zweier Strecken ohne Knoten → oben/unten aus OSM (kreuzende Ways ohne gemeinsamen Knoten, bridge/tunnel/layer), unteres Gleis Lücke, oberes neu + Brückenflügel; aus mit Lage `ohne_kreuzungen` oder Env OHNE_KREUZUNG. (3) Tunnelportale auf der Strecke entfallen, wenn der Tunnel-Way zum Spurplan des Bahnhofs gehört (dort gezeichnet, `ST_WAYS`). (4) Abgänge mit Versatz < 25 zum Anschluss werden auf dessen Linie gelegt (keine S-Kurve).
- spurplan_schema.py: `portale` und Über-/Unterführungen (`ueber`) auch im `--bare`-Plan (Regionalplan). Olten bare mit `--hauptgleise` erzeugen. Env XINV=x1,x2 druckt s zu x-Pixeln.
- lage_auto.ketten: Zwischenräume einer Kette nie unter `gap` (Haken Corcelles/Les Deurres), innere Bahnhöfe quer so verschoben, dass die Anschlüsse auf der Kettenachse liegen; zu kurze Ketten → zusätzliche LSQ-Zeile.
- Feedback-Seite: NE-Bahnhöfe nach Strecken gruppiert (zusatz_plaene.json `gruppe` "NE n · von – bis", `region: "ne"`; ne_zusatz_update.py filtert auf `region`). Skizzen-Werkzeug ✎: Ziehen zeichnet Striche (Douglas-Peucker, optional 30°-Raster), gespeichert im Hinweis als `skizze: ["x,y x,y …", …]` (Plan-Koordinaten, Strings, weil die Datenbank keine verschachtelten Listen nimmt).
- Alle 18 offenen Hinweise beantwortet (behoben, v71).

### 17.10.2026 abends – freie Strecke gegen OSM, Neuchâtel mit SBB-Perrons (Seite v72)
- Daniel: «Zwischen Regionalplan und Bahnhöfen können Dinge zwischen Stuhl und Bank fallen» (Olten–Dulliken, Schafis, Serrières–Neuchâtel). Neu:
  - `spurplan_schema.py` mit Env `SPUR_FENSTER=1`: schreibt nur `<bahnhof>_fenster.json` (Achse lat/lon im Planfenster, d_lim, s) und beendet sich – keine anderen Dateien. Für alle Bahnhöfe einer Region einmal laufen lassen (Rothrist aus `regional_rothrist/` kopieren; Zihlbrücke-Slug kopieren).
  - `netz_lage.py`: OSM-Datei der Region aus Lage `osm` (Olten `region.json`, NE `ne_region.json`), Bezugspunkt-Versatz `osm_versatz` (NE −996/−851: Topologie aus anderem Ausschnitt). `_nebengleise()`: Komponenten aus service-Gleisen, die ausserhalb der Planfenster an Hauptgleise einer Strecke anschliessen, werden gezeichnet – zwei Hauptgleise = Spurwechsel (Gleisrang aus OSM-Querlage, auch 4 Gleise), sonst Neben-/Anschlussgleis parallel aussen mit 60°-Ästen, Stumpen mit Prellbock. Spurwechsel-Zeichnung (XO und neu) über Projektion statt Längenanteil (Linien sind verschieden lang).
  - `--pruefen` Prüfung 4 «freie Strecke gegen OSM»: Gleiszahl entlang der Strecke (Abschnitte ≥ 75 m) und nicht gezeichnete Spurwechsel/Nebengleise, Liste in `<name>_pruef4.json`. Stand: Olten 5 Befunde, NE 1.
  - Mehrere überzählige Port-Gleise münden je in ein eigenes Gleis (Dreieck Olten Nord: 531 an beide 540-Gleise, laut OSM).
  - Lage `auto_knick` (NE 76°): gerader Verbinder im Auto-Modus auch bei bis 76° zur Portrichtung (Chambrelien–Corcelles ohne Sprung). Olten Schönenwerd x 1830 (eine Schräge ab Däniken).
- Neuchâtel: `sbb_perrons.py <bahnhof> "<bps_name>" --schreiben` → Override `platforms` aus SBB perronoberflache (p_nr a/b = between, sonst outer), Lage aus OSM-Perron neben diesen Gleisen, sonst SBB-Länge um die Bahnhofsmitte (Median aller SBB-Punkte) innerhalb der Gleislänge. Neuchâtel: 1 Haus, 2/3, 4/5, 6/7; pax 1–7; Lauf mit `--hauptgleise`; Regeln r40 (MILP-Ebenen), r43, r48; neue cfg `r14a_m` (Länge kurzer Mittelstücke, Standard 50). Gittersuche r40-Gewichte: ww=6 spart Knicke, erzeugt aber Bögen statt 60° – Standard behalten. Offen: R 11 (meist Bögen im Abstellbereich Ost), Λ am Westkopf 3→5→4.
- Bern Brünnen Westside: Vorlage rechts doppelter, links einfacher Spurwechsel (OSM). Chambrelien: 224 grün erst ab Weiche.
- Kerzers als zwei 60°-Achsen im Regionalplan: Vorschlag (Regionalvariante wie Rothrist), Rückfrage offen.

### 18.10.2026 – Knicke nur am Bahnhof (Regionalplan Neuchâtel, Seite v73)
- Daniel: «Wenn Du mit den Ästen aus einem Bahnhof raus auf 60° gehen kannst, braucht es den Knick nicht – alles was Du vermeiden kannst vermeiden» (Chambrelien, Auvernier, Murten).
- netz_lage.py (nur Auto-Lage): Edge-Ports liegen am Gleisende statt am Kastenrand (`port_am_gleisende`, Standard an); Verbinder-Kandidat [A, B] mit Knick direkt am Port, wenn das andere Ende auf der Linie liegt (≤ 8°), und Knick am Schnittpunkt der Portgeraden; Lage `port_richtung` {"Bahnhof|Linie": Grad} und `auto.kette_winkel` {Bahnhof: Grad} (Murten 255 → 240°, Kette Münchenwiler 255°).
- spurplan_schema.py: `zeichnen`-Linien mit `nur_plan` / `nur_regional` (Auvernier: 219 im Spurplan schräg nach oben, im Regionalplan gerade aus Gleis 3).
- Chambrelien: Planende rechts x 640 statt 835.

### 19.10.2026 – Neuchâtel Entwurf 6, Sichtprüfung Regionalpläne (Seite v74)
- Daniel: «mach bei Neuchâtel und dann den Regionalplänen eine Iteration mit den entsprechenden Bahnhöfen zuerst»; 15 Hinweise (Neuchâtel 11, Region Olten 2, Region NE 2).
- Neuchâtel: cfg `rules.r49` (Zwischengerade → eine 60°-Schräge; zu knapp → Verlängerung aufs Zielgleis statt Bezier), `drop_service` [siding, yard, spur] (pax-Gleise und `behalten`-Ways bleiben), `perron_nur_gerade`, `perron_einheitlich`; Perron-Bereiche alle s 2999–3418 («Perronlängen Standard», 6/7 durch Gleis 7 begrenzt, 1 durch den Abzweig). Prüfung 0 Befunde, 0 × 90°. Abgang 220 Ins per `abgang`.
- netz_lage.py, Spurwechsel auf freier Strecke (XO): nur im geraden, parallelen Stück zwischen Nachbargleisen (Querabstand ≤ 1,6 Gleisabstände), ≥ 22 px + Gleisabstand von Abzweigen und Enden anderer Strecken, Mitten ≥ 24 px auseinander (sonst Bild wie DKW). Kein Platz → weglassen und melden («Spurwechsel ohne Platz weggelassen», Rothrist–Abzweig #43). Statt senkrecht über die Nebengleis-Funktion nachgezeichnet zu werden, gilt er als erledigt.
- netz_lage.py: «Schwarz hinter Grün» (schwarze Pfade 1,3 px vor dem ersten grünen; Lage `schwarz_oben` schaltet ab). Nebengleise: kurze Stumpen knicken nicht zurück (Mindestlänge 2 × Ast + 10 px), Nebengleise näher als 5,5 px an einer anderen Strecke entfallen (Aarburg, Vauseyon).
- netz_lage.py (Auto-Lage, Lage `port_bogen` Standard an): Knick am Gleisende 8–80° als Bogen – Linie beginnt 9 px im Bahnhof, Gleisende darunter weiss abgedeckt (Murten–Faoug).
- Neu `region_winkel.py plan.svg`: Sichtprüfung auf den obersten Pfaden des Regionalplans (eingebettete Spurpläne ausgenommen): schwarze Stücke ≥ 75° quer zu einer Strecke (Portale/Brückenflügel über ≥ 2 Gleise ausgenommen) und sich kreuzende schwarze Spurwechsel. Stand Olten 0, NE 0.
- Debug: PDBG=x,y (Stack, wenn path() den Punkt zeichnet), REFDBG=<Bahnhof> (Anker/refs), NBDBG (NBSEQ-Zeilen).
- 19.10. Mittag, Neuchâtel Entwurf 7 (Hinweis Daniel: «verletzt jetzt die Regel Weichen ab Hauptgleis – gewisse Gleise gar nicht mehr angebunden»): `drop_service` hatte die Verbindungsgleise von 5 (West), 6 und 7 entfernt (OSM siding). Override `behalten` mit den Verbindungen der Perrongleise zu Hauptgleisen und untereinander (≤ 150 m, gesucht mit kürzestem Weg über weggelassene Ways). Neu im Schema: Regel `r38m` (opt-in) – Abgang/Pfeil auch für Weichen mitten in einem gezeichneten Stück und Seite über Folge-Ways bis 300 m (kurze Weichen-Ways); Override `r47_pax` [ways] – Regel-47-Spurwechsel grün (befahrene Verbindung zwischen Hauptgleisen, in OSM siding; Neuchâtel 4↔3 Ost). Verbindungsprüfung Neuchâtel 0 Abweichungen, Prüfung 0. Lehre: nach `drop_service` immer `verbindungen_pruefen.py` laufen lassen.

### 19.10.2026 abends – Regelprüfung Regionalpläne, Onnens-Bonvillars, Gleisnummern (Seite v76)
- Daniel: Nebengleise auf freier Strecke bleiben (sonst fehlen Onnens-Bonvillars, Schafis). Arbeitsweise: Runden mit Prüfungen durch Claude, Regionalplan nach grosser Iteration gegen OSM prüfen, Daniel gibt Regeln, die über die Regionalpläne laufen.
- Neu `regel_pruefung.py <plan.svg> --osm <region.json> [--rand <vieleck.json>]` (liest die eingebetteten Spurpläne mit ihren Transformationen): G1 Spurplan ohne Gleisnummern, G2 Weiche ohne Ausrundung (Linienende trifft Gleis > 12°), G3 Knick ohne Ausrundung in einer Linie, G4 90° (Portale/Brückenflügel ausgenommen), G5 sich kreuzende Spurwechsel, O1 OSM-Bahnhof/Halt (Normalspur, keine Standseilbahn/Tram) fehlt im Plan bzw. Perron ohne Bahnhof, O2 Weichenhäufung (≥ 3 in 500 m) ausserhalb aller Planfenster (`<bahnhof>_fenster.json`) – Liste zum Durchsehen. Nach jeder grossen Iteration laufen lassen (beide Regionen).
- Stand NE: G1 29 → 6 (Môtiers, Couvet ohne Daten; Bôle, Ligerz, Zihlbrücke Manufaktur offen; Fräschels), G2 121 → 47, G5 4, O2 4 (Vauseyon, Gouttes-d'Or/Neuchâtel Ost, Concise Ost, Avenches Ost). Olten: G2 41, G3 2, O2 9.
- Onnens-Bonvillars: OSM hat keinen Stationsknoten (Perron disused) → `onnens_bonvillars_roh.json` aus schweiz_bahn.json.gz (Kreis 2,5 km), synthetischer Stationsknoten auf dem Hauptgleis bei der Perronmitte (Knoten 10123561533), `cut.py onnens_bonvillars 1500`, Topologie: Kante Grandson–Concise am nächsten Punkt geteilt (Sicherung /tmp/claude-0/ne_topo_vor_onnens.json), Lage `eigenes_feld`. Gleisnummern per `nummern_px` (SBB: 1 Hausperron = oberes Gleis, 3 Zwischenperron).
- Neu `gleisnummern_sbb.py <bahnhof> [bps] --schreiben`: Vorlage-Gleisnummern aus SBB perronoberflache (Flächen je Perron gemittelt, Aussenperrons zuerst, a/b: kleinere Nummer auf der Seite der kleineren bekannten Nummern), Ersatz OSM-Perron `ref`. Namensabgleich (Cressier NE, St-Blaise CFF, Gorgier-St-Aubin, Bole, …). Geschrieben für 24 Vorlage-Bahnhöfe.
- `vorlage.py`: Schräge, die auf einem Gleis beginnt/endet, bekommt ein Stück Gleis davor → Weiche ausgerundet (G2).

### 20.10.2026 – Regelentscheide D. Eckenstein, Differenzbild, GitHub-Vorbereitung (Seite v77)
Regeln (verbindlich, gelten für alle Spur- und Regionalpläne):
- Gleisnummern: **SBB vor OSM**. Nur Gleise mit Perron bekommen eine Nummer (Überhol-/Kreuzungsgleis ohne Perron: keine). Halt mit einem Gleis: keine Nummer. Perron vorhanden, aber keine Nummer in allen Quellen → **Fragezeichen-Symbol** (orange Kreis mit «?», Daniel trägt von Hand ein).
- Weichenrundungen gelten überall, auch für Abgangsstummel mit Pfeil und für Einmündungen der Strecke in den Spurplan.
- 90°: kein Gleis darf 90° abgehen. Einzige Ausnahmen: Tunnelportale und Brückenflügel (keine Gleise). Prellbock ist ein Punkt.
- Eigener Spurplan für jeden SBB-Betriebspunkt (Bahnhof, Haltestelle, Kreuzungs-/Dienststation, Abzweigstelle); reine Anschlussgleise bleiben Nebengleise auf der freien Strecke.
- Stillgelegtes (OSM disused / disused:public_transport) nicht zeichnen.
- Regressionsschutz: Vergleichsbasis eines Regionalplans ist der **abgenommene** Stand; bis dahin die letzte veröffentlichte Fassung. **Jede Runde ein Differenzbild** an Daniel.
Umsetzung:
- `vorlage.py`: Nummer nur an Gleisen mit Perron, keine bei Einzelgleis-Halt, «?»-Symbol bei fehlender Nummer. `spurplan_schema.py`: stillgelegte Perrons fallen weg (PLAT-Filter). `typ_vorschlag.py`: stillgelegte Perrons zählen nicht. Onnens-Bonvillars ohne Perron und ohne Nummern.
- `regel_pruefung.py` G1 nach den neuen Regeln (Gleise mit Perron ≥ 2 → Nummer nötig; «?» als G1? gelistet). Stand NE: G1? Môtiers, Couvet; G2 54, G5 4, O2 4. Olten: G2 51, G3 2, O2 9.
- Neu `diff_bild.py <alt.svg> <neu.svg> <out.png> [--hinweise h.json] [--liste out.json]`: Differenzbild (rot = Änderung ausserhalb Hinweisstellen, blau = an Hinweisstelle), Vergleichsstände in `feedback/vergleich/` (v76 abgelegt).
- GitHub-Vorbereitung (Paket `topo-daten_vorbereitung.zip`, Repo-Zugriff in der Sitzung nicht verknüpft): Workflow `vorbereitung` nach `bahndaten` → Release `vorbereitung` mit `betriebspunkte.json` (SBB-Betriebspunkte + SBB-Perrons + OSM-Stationen, Ersatzknoten bei fehlendem OSM-Stationsknoten), `gleisnummern.json` (Regeln oben; grosse Knoten > 5 Nummern von Hand), `region_<key>.json.gz` und `bahnhoefe_<key>.zip` (Kreis-Ausschnitte), `aenderungen.json` (gegen Vormonat). Getestet in der Sandbox: 1087 Betriebspunkte, NE 61 / Olten 24 Ausschnitte; ohne OSM-Stationsknoten u. a. Onnens-Bonvillars, Ligerz, Neuchâtel-Vauseyon, Vaumarcus, Montmollin-Montezillon, Boveresse.

### 20.10.2026 Mittag – Regionalpläne fertigstellen (Seite v78/v79)
Daniel: «Regionalpläne fertig machen»; Rothrist viel gedrängter als die Olten-Verbindungslinie, obwohl es real umgekehrt ist; in Neuchâtel wenige Details.
- Region Olten: Rothrist breiter. Neu cfg `warp_min` (Mindestanteil des Massstabs in der x-Entzerrung, Standard 0.15; `spurplan_schema.py` gibt ihn in `<b>_req.json` weiter, `spurplan_warp.py` liest ihn). `regional_rothrist/rothrist_override.json` (im Projekt als `claude/rothrist_regional_override.json`) mit `warp_min 0.65`. Lage: Rothrist x −669, Abzweig #31 / Abgang 400 #40 / Abgang 450 #41 je −238.
- Olten Ost: Lage-Schlüssel `nebengleis_hand` [{weg: [ways], pts: [[x,y]…], punkt}] – Nebengleis auf freier Strecke von Hand (Anschluss am Gleis Richtung Hauenstein, Ways 50063046/47, 137216150, 313267372/74). Offen: fehlende Weichen dort → eigener Betriebspunkt-Plan (Name bei SBB unbekannt, Rückfrage).
- `netz_lage.py` (NE und Olten jetzt gleich):
  - Spurwechsel auf freier Strecke: Gegenstück per Projektion, Ausrichtung je Linie (`_sgj`), Winkelprüfung 40–75° (nie quer). Ligerz: kein Z mehr.
  - Nebengleise: geometrische Wahl des äussersten Gleises (j_out), Normale je Linie; stört ein Nebengleis, wird es entlang der Strecke verschoben statt weggelassen; **neu: Nebengleise zweigen nie im Spurwechsel ab** (Abstand Gleisabstand + 4 px zu jeder Spurwechselmitte; Ligerz «nach dem Spurwechsel raus»).
  - Linien werden nach der Streckenschleife gezeichnet (DEFER); `_stoesse()` führt Enden verschiedener Strecken (< 0,7 Gleisabstand, ≤ 35°) zu einer Linie zusammen; Douglas-Peucker 1,6 px (Lage `ohne_glaettung`). Vauseyon: kein Versatz mehr am Stoss.
  - Debug: XODBG2, NBDBG2, NBDBG3 (Verschiebungsversuche), BOGDBG.
- `vorlage.py`:
  - Spurwechsel schwarz (Riedbach/Rosshäusern «Spurwechsel alle schwarz»), wie im Regionalplan.
  - Anschluss aussen am selben Ende wie ein Spurwechsel rückt um 2 Diagonalen + 40 px nach aussen (Grandson: wirkte wie Kreuzung).
  - Neu `"stumpf": "rechts"|"links"`: Überhol-/Kreuzungsgleis als Stumpengleis (Grandson Gl. 1 am Hausperron).
  - Neu Perronteil `zwischen_unten` (Mittelperron zwischen den unteren zwei Gleisen, Grandson 2/3).
  - Anschluss-Option `gleich_lang` (+ `verlaengern`): innen liegende Stumpen enden gleich weit, bis gegen das andere Perronende; Weiche dann 28 px weiter innen (nicht in der Kreuzungsweiche). Les Hauts-Geneveys.
- Bahnhöfe nach Hinweisen: Les Hauts-Geneveys Aussenperron 1; Münchenwiler 2 Aussenperrons (OSM 1/2); Môtiers Mittelperron, Nummern «?»; Cressier FR Anschluss auf der Perronseite; Courtepin Industrieanschluss (OSM 705109983) mit Pfeil; Grandson nach SBB (Hausperron 1 am Stumpengleis, Mittelperron 2/3). `typ_vorschlag.py`: Verbindungen zwischen Hauptgleisen (> 2,5 m quer) und weit entfernte Komponenten sind keine Anschlüsse (Bevaix, Kallnach, Gorgier, Le Landeron, Les Deurres u. a. neu).
- Neuchâtel: Plan war am 20.10. früh ohne `--hauptgleise` überschrieben worden (v77 ohne R38-Pfeile) → `sh ne_run.sh neuchatel --hauptgleise`. Achtung: Neuchâtel immer mit `--hauptgleise`.
- Prüfungen: NE Regelprüfung G1? 2 (Môtiers, Couvet), G2 57, G5 3, O2 8; Prüfung 4: 1 (Noiraigue–Champ du Moulin 780–855 m: OSM 2, Plan 1). Olten G2 52, G3 2, O2 9; Prüfung 4: 5 (Rothrist-Fensterränder, Aarburg, Dulliken 5/4). region_winkel: NE 1 (Vauseyon-Stummel), Olten 1 (Aarburg-Anschluss, parallel geführt). Differenzbilder gegen `feedback/vergleich/*_v76.svg`.
- 44 Hinweise beantwortet (v79): 29 behoben, 15 Rückfragen (Stummel horizontal Bevaix/Gorgier/Grandson/Riedbach, Le Landeron Spurwechsel/Ministummel, OSM-Gleise Bevaix/Riedbach/Gorgier, Neuchâtel 3, Olten Ost).

### 20.10.2026 Mittag (2) – Olten Ost, Rothrist/Borntunnel, Tunnelportale (Seite v80)
- **Olten Ost** (Name D. Eckenstein) als eigener Betriebspunkt-Spurplan: Ordner `olten/olten_ost/` (Daten aus region.json, Kreis 650 m, synthetischer Stationsknoten auf Way 1134009350, `run.sh olten_ost --hauptgleise`, Override `abgang` 531 → Olten). Topologie: Abzweig #22 → Station «Olten Ost» (`olten_region_topologie.json`), Lage «Olten Ost» [227, −380], `merge_radius` Olten Ost 150 (sonst schluckt er #19), `buendel_zusatz` «Olten|Olten Ost» (531 + 540 = 6 Gleise). `nebengleis_hand` entfällt (liegt jetzt im Spurplan; alter Eintrag als `_nebengleis_hand_vor_olten_ost`). Sicherungen der Topologie/Lage vorher in /tmp (sitzungsweise). Offen: die 531-Gleise aus Olten machen vor dem Bündel einen engen Bogen (war als V schon in v78).
- Rothrist Ost: Lage `kreuzung_tausch` [[x, y]] tauscht oben/unten einer Streckenkreuzung (OSM führt den Born-Tunnel-Way schon an der Kreuzung → 3/2 lagen fälschlich unten, weisse Lücken). Kreuzungslücke nur noch an Gleisen, die die obere Strecke wirklich kreuzen; Neuzeichnung der oberen Strecke nimmt Knicke in der Nähe ganz mit (keine Knubbel/Kerben).
- Tunnelportale: zweites Portal fehlte, wenn der Tunnel-Way in den OSM-Daten eines Bahnhofs liegt, dessen Spurplan keine Portale zeichnet (Gümmenen–Rosshäusern). Jetzt nur noch übersprungen, wenn das Override des Bahnhofs `portale` hat. Kurze Tunnel: Portale ≥ 18 px auseinander und nicht im Bogen (beide gemeinsam ins nächste gerade Stück).
- Riedbach: ein Parallelgleis mit Weichenverbindung (stumpen 1). `vorlage.py`: Anschluss am selben Ende wie ein Spurwechsel 2 Diagonalen + 75 px weiter aussen.
- Feedback-Seite: Auswahlliste (schmale Ansicht < 900 px) mit denselben Gruppen wie die Seitenleiste (optgroup).
- Rothrist-Regionalvariante mit `--hauptgleise` als Vorschlag gezeichnet (/tmp, nicht aktiv): Westkopf ohne Nebengleis-Knäuel; Entscheid D. Eckenstein offen.

### 20.10.2026 Nachmittag – GitHub-Vorbereitung eingespielt (VXstone/topo-daten)
- Workflow `vorbereitung` (läuft nach «Bahndaten Schweiz» und von Hand), Skripte in `skripte/vorbereitung/`, `konfig/regionen.json`. Lauf 39420108122: alle Schritte OK.
- Status je Datensatz und Schritt steht in `stand.json` → Schlüssel `vorbereitung` (Logs sind für Claude nicht lesbar). Release `vorbereitung`: betriebspunkte.json, gleisnummern.json, perronkanten.json, Ausschnitte je Region/Bahnhof, SBB-Rohdaten.
- SBB-Datensätze: Perronkanten = `21196_behig-haltekantepunkt` (kundengleisnr je Kante, 2799 Kanten, 978 Betriebspunkte); Betriebspunkte = `linie-mit-betriebspunkten`, Name aus `bezeichnung_offiziell` (Olten Ost (Abzw) = OLO, Olten Nord (Abzw) = OLN, Neuchâtel-Vauseyon (bif) = NEBI). Die alten IDs `perronkante…` liefern 404.
- Ergebnis: 1597 Betriebspunkte (596 ohne OSM-Stationsknoten → Ersatzknoten), Gleisnummern für 1333 (924 SBB, 409 OSM, 134 mit «?»). BLS-Halte (Gümmenen, Riedbach) nur aus OSM.
- Offen: `gleisnummern.py` nutzt noch die Perronflächen; auf `perronkanten.json` umstellen (genaue Kante je Gleis). Alte Release-Datei `sbb_perronkante.geojson.gz` (17 MB) von Hand löschen (Sitzung darf Releases nicht ändern).

### 20.10.2026 Nachmittag (2) – Hinweise Region Neuchâtel (Seite v81)
- `vorlage.py`: neuer Zusatz `{"art": "schutzstumpen", "ende": "links|rechts", "laenge": 26, "prellbock": true}` – kurzer gerader Stumpen in Verlängerung des Überhol-/Kreuzungsgleises über dessen Weiche hinaus («Ministummel horizontal», Schutzweiche). Le Landeron (4 Weichen zwischen den Hauptgleisen: links 1→2 steigend, rechts zurück fallend; Gleis 3 links Prellbock, rechts nichts), Gorgier (Abstellgleise links aus dem Überholgleis, Schutzstumpen beidseits), Grandson (Gleis 1 links, Anschlüsse weg), Bevaix und Riedbach (Anschluss innen, waagrecht Richtung Perron, 2 Stumpen), Môtiers (Gleise 3/2).
- `spurplan_schema.py`: Randstück eines `zeichnen`-Abgangs (port_way) beginnt nie vor dem Linienanfang (Chambrelien 224: grüner Stummel). Chambrelien: Gleis 2 grün von rechts (Fahrten von/nach Neuchâtel), links vom Perron schwarz. Bôle: oberstes Abstellgleis mündet unterhalb der Ausrundung. Onnens-Bonvillars: Schutzweiche Ost als kurzer gerader Stumpen (`zeichnen`), r44 an; DKW (OSM 1953027582) noch ohne Symbol.
- Neuchâtel: `pax_ways` 184331533/380141987 (Gleis 1 durchgehend grün), `perron_einheitlich` {mitte_px 680, laenge_px 100}. **Fehler gefunden:** `ne_zusatz_update.py` liess `spurplan_check.py` laufen, das `spurplan_schema.py` ohne `--hauptgleise` ausführt und den Plan überschreibt (v79/v80 ohne R38-Pfeile). Jetzt mit `--out /tmp/_check_<b>.svg` und `--hauptgleise` für `GROSS_NE = {"neuchatel"}`.
- `netz_lage.py`: Spurwechsel auf freier Strecke behalten die OSM-Reihenfolge (`_XO_ORD`; Ligerz: der zweite rutschte vor den ersten); Lage `xo_versatz` {way: px} verschiebt einen Spurwechsel (Ligerz 1411239688: −28); Lage `xo_umkehren` [[x, y]] (Radius 6) kehrt die Richtung um; Debug XOBASIS. `nebengleis_hand` mit leeren `pts` = Nebengleis bewusst weglassen. Vauseyon: Anschluss von Hand (Seite Neuchâtel aus der 223, teilt sich in 2; Ways 37214725/27, 580054999, 1104427571; Stumpen 49801712 weggelassen).
- Prüfungen NE: G1? 1 (Môtiers erledigt, Couvet offen), G2 55, G5 3, O2 4, region_winkel 0. Region Olten unverändert (Differenzbild leer).

### 20.10.2026 Abend – Neuchâtel-Hinweise, Anbindungen Regionalplan, Prüfregeln G6–G8 (Seite v82)
- **Fehler Anschlusspunkte:** `spurplan_schema.py` schrieb `<b>_ports.json` bei jedem Lauf, auch beim Prüflauf aus `ne_zusatz_update.py` (ohne `--bare`) → der Regionalplan bekam die Anschlüsse des Bahnhofsplans (Auvernier 219 lag 24 px zu hoch, «nicht mehr verbunden»). Jetzt nur noch im `--bare`-Lauf oder ohne `--out` (Standardlauf, danach überschreibt run.sh mit bare).
- `netz_lage.py` (Olten und NE gleich): Port-Bogen bei **seitlichen** Abgängen ohne weisse Maske – die Linie läuft 10 px in Stummelrichtung weiter und biegt dann ab (Ins 256, Murten 255 hingen in der Luft). Anker haben neu `side`.
- `regel_pruefung.py` neue Regeln: **G6** Knubbel (zwei Linien stossen mit Knick zusammen, ohne Fortsetzung oder tangentialen Abzweig), **G7** Gleis nicht angebunden (Linienende frei, anderes nicht paralleles Gleis 1,5–20 px daneben), **G8** Gleise deckungsgleich (> 10 px; Randstücke der Abgänge ausgenommen). DKW-Klammern (stroke-opacity) werden ignoriert. Stand NE: G6 1, G7 2 (Stösse 1,5–2 px Murten/Muntelier), G8 5 (Kerzers, Auvernier – unsichtbar). Olten: G6 7, G7 2, G8 26 (vor allem Rothrist/Olten, noch nicht angeschaut).
- `spurplan_schema.py`: Override `dkw_px` [{x, y, pax, rund_pax, arme: [[[ax,ay],[bx,by]], …]}] (DKW-Symbol an Pixelstelle, für von Hand gezeichnete Kreuzungen), Override `r38_seite` {way: oben|unten} (Seite eines R38-Pfeils), Meterspur auch im `--bare`-Plan (`meterspur_cfg.regional`, Standard an; Ins asm Richtung Biel im Regionalplan).
- `vorlage.py`: Anschluss-Option `t_form` (+ `t_laenge`): umgekehrtes T, am Fuss der Weichenverbindung ein zweiter Stumpen in Gegenrichtung (Riedbach, Bevaix). Neuer Zusatz `{"art": "linie", "pts": [[x,y],…], "punkt_ende"}` für Ergänzungen in Pixeln (Gorgier: Ring der Anschlussgleise nach OSM 524/525/505/684645119).
- Bahnhöfe: Couvet Gleise unten 1 / oben 2. Chambrelien: Gleis 3 eine gerade Schräge ab Gleis 1, Gleis 2 zweigt daraus ab. Onnens-Bonvillars: DKW 1953027582 als X zwischen den Ebenen mit Klammern, Schutzstumpen ohne Überlappung.
- Neuchâtel: Doppelspur Yverdon mit Standardabstand (`zeichnen`, unteres Gleis y182, senkt sich vor der Weiche), Spurwechsel 35567923 grün; DKW 11296350767/11296350764 + Kreuzung 631631020 als eine gerade Schräge vom Gleis-5-Streckengleis über das untere Streckengleis in die Abstellgruppe A (grün bis zur DKW, `dkw_px`); `pax_ways` + 32113632; `weglassen` 1222936432 (zweite Verbindung 2→1, «doppelt aufeinander»); `r38_seite` Abstellgruppe B nach oben. Verbindungsprüfung 0 Abweichungen.
- Differenzbild gegen v76; neue Vergleichsbasis `feedback/vergleich/region_ne_v82.svg`.
- Offen: Kerzers als zwei 60°-Achsen im Regionalplan (Ja von D. Eckenstein), G6/G8-Befunde Region Olten durchsehen, Gleisnummern aus perronkanten.json.

### 20.10.2026 Nacht – Regelentscheide E1–E12, Olten Ost 60°, Borntunnel, Gleisnummern aus Perronkanten (Seite v83)
- Regelentscheide D. Eckenstein (im Doc «Regelwerk Spurpläne», Abschnitt «Regelentscheide 20.10.2026»): E1 jedes Perrongleis grün erreichbar, übrige Spurwechsel schwarz · E2 Pfeil nur topologisch drehen (`r38_seite` oben|unten|gerade; gerade = Pfeil «läuft weiter») · E3 DKW aus mehreren OSM-Elementen < 20 m = eine DKW (von Hand `dkw_px`) · E4 doppelte Verbindungen = zwei Achsen, auseinander zeichnen (Neuchâtel 2→1) · E5 Planrand im Doppelspurabstand, verschiedene Linien doppelt (`planrand_pruefung.py`, neu) · E6 Anschlüsse jede Weiche nach OSM · E7 Stoss > 1 px = Befund (G7 Toleranz 1 px; Enden unter weisser Port-Maske ausgenommen) · E8 Meterspur Stummel mit Ziel, `meterspur_cfg.d_max` Standard 40 m · E9 abgenommene Pläne dürfen sich ohne Topologieänderung ändern (Differenzbild) · Rothrist bleibt Detailvariante.
- `spurplan_schema.py`: Ausrundung eines seitlichen Abgangs (R39) nimmt eine Verbindung, die genau im Eckpunkt beginnt, mit (Murten Gl. 4→3, 2 px Stoss); Override `als_rand` [ways] = Abgang am Längsrand statt seitlich; `r38_seite` "gerade".
- **Olten Ost 60°**: Regionalvariante `regional_olten_ost/` → `olten_ost_regional_{ports,bare,override}` (531 als zwei Gleise am linken Rand über den 540-Gleisen, fädeln mit 60° ein; Aarau Gl. 1 am rechten Rand auf 134 = Doppelspurabstand, auch im Spurplan Olten Ost). Lage: `drehung` Olten Ost −60, Lage [205.5, −302.6] = auf der Geraden der 540 aus Olten (sonst Zickzack, weil die Bündel am Port ohne parallelen Versatz knicken). Prüfung 3 meldet die Drehung (gewollt).
- `netz_lage.py`: Lage `tunnel_hand` {"A|B": [[ta, tb]]} – Tunnel als Anteile der gezeichneten Linie (Borntunnel: Rothrist|Olten [0.47, 0.66]; der geografische Anteil setzte das Südportal verkehrt).
- Gleisnummern im Repo: `gleisnummern.py` nimmt zuerst die SBB-Perronkanten (`aus/perronkanten.json`: jede Kante → nächstes Gleis ≤ 6 m), dann Perronflächen, dann OSM. Lauf 39495108807: 1360 Betriebspunkte, 915 aus Perronkanten, 171 Perronflächen, 274 OSM, «?» 107 (vorher 134). Stichprobe Grandson 1/2/3, Gorgier 3/2/1, Bevaix 2/1, Les Hauts-Geneveys 2/1 = wie von Hand.
- Offen: Kerzers als zwei 60°-Achsen; Regel E1 als automatische Färbung (heute Prüfung + Hand); E3 automatisch; NE-Bahnhöfe auf gleisnummern.json aus dem Release umstellen (Release-Dateien sind aus der Sitzung nicht ladbar → Datei anhängen oder Ausschnitt-Workflow).

### Geplant (20.10. spät, Wunsch D. Eckenstein): Skripte laufen im Repo, Claude prüft nur noch
- Ziel: VXstone/topo-daten = einzige Fassung aller Skripte, Overrides, Lage- und Topologiedateien; Workflow «plaene» baut nach jedem Commit und nach dem Monatsabzug alle Bahnhöfe, Regionalvarianten und beide Regionalpläne, lässt alle Prüfungen laufen (spurplan_check, verbindungen_pruefen, regel_pruefung G1–G8, planrand_pruefung, netz_lage --pruefen, region_winkel) und schreibt SVG, PNG-Ausschnitte, Prüfbericht (JSON) und Differenzbilder auf einen Branch `ergebnisse` (Repo-Dateien sind für Claude lesbar, Release-Dateien nicht).
- Claude: Hinweise lesen → Override/Lage/Skript committen → Lauf abwarten → Bericht und Bilder prüfen → Feedback-Seite veröffentlichen, Hinweise beantworten.
- Reihenfolge: 1. Region Neuchâtel (Ordner ne/, Typvorlagen), 2. Region Olten (olten/, regional_rothrist/, regional_olten_ost/, olten_ost/). Abnahmekriterium: erster Lauf im Repo liefert byte-gleiche SVGs wie die lokalen Fassungen v83 (feedback/vergleich/*_v83.svg).
- Actions-Minuten: öffentliches Repo unbegrenzt, privat 2000 min/Monat (Lauf ca. 5–10 min).

### 21.10.2026 – Repo-Lauf Neuchâtel, Reihenfolge-Regel R3, Murten, Onnens (Seite v85)
- Repo VXstone/topo-daten, Ordner `spurplan/`: `code/lauf.py` baut und prüft jeden Bahnhof aus `bahnhoefe.json` (Neuchâtel mit `--hauptgleise`); Workflow `plaene` schreibt nach Branch `ergebnisse`. Erster Lauf 39574334576 byte-gleich mit v83; Lauf 39577064931 mit den drei DKW (Gleis 2/1, A36/A44, A43/A44) ist die Fassung auf der Seite (Label «Repo-Lauf …»). `REGELN.md` = Kurzfassung, Master bleibt das Regelwerk-Doc. Lokal: `repo_holen.py` holt bericht/svg/bare/ports.
- Neuchâtel: «zwei Achsen» (E4) war ein Missverständnis – OSM zeigt dort eine DKW-Gruppe (double slips 11296350712/14/15/17 + Kreuzung 360421652) → als DKW gezeichnet (`dkw_px`, Arme frei). `spurplan_schema.py`: `R47_P` merkt sich den Way; R47-Spurwechsel fallen jetzt auch mit `zeichnen.weg` des Ways weg.
- **R3 Reihenfolge (netz_lage.py `_nebengleise`)**: Ein Nebengleis auf freier Strecke darf nur dort liegen, wo es gegenüber den Spurwechseln derselben Strecke auf der gleichen Seite liegt wie in OSM (`_ordnung_ok`, geografischer Anteil der Spurwechsel aus `xo["mid"]`). Passt keine Verschiebung, werden kürzere Längen versucht (0.6/0.4/0.25). Debug ORDDBG. Schafis: Lage `xo_versatz` 1411239688 −50, 1411239690 −30 (beide Spurwechsel Richtung La Neuveville), Anschluss jetzt auf der Seite Ligerz/Biel. Region Olten byte-gleich.
- Murten: Strecke Fribourg kommt waagrecht in Gleis 4 (`zeichnen` port_way 31798505, Abgang bei x 445/231 unter 60°), Weiche 359125844 zu Gleis 3 liegt rechts davon (vorher Weiche und Knick im selben Punkt, Hinweis «darstellung»). Auch `olten/reg/` nachgeführt (abgenommen, Topologie gleich, E9).
- Onnens-Bonvillars: DKW-Klammern oben/unten (je linker mit rechtem Ast).
- Prüfungen NE: G2 55, G3 1, G5 3, G6 1, G8 5 (wie v84); Differenzbild nur Schafis, Murten–Fribourg, Onnens.
- Neue Regel D. Eckenstein (21.10., R14 im Doc): Abzweig mit Weichen wird eigener Betriebspunkt-Plan oder in den nächsten Bahnhof integriert (wie Olten Ost). Umsetzung offen (Kandidat Vauseyon).

### 23.10.2026 – Repo ist die einzige Fassung, Seite und Ausschnitte aus Actions
Wunsch D. Eckenstein: Nutzung sparen, mehr in Git auslagern.
- Diese Datei (`spurplan/UEBERGABE.md`) ersetzt `spurplan_uebergabe.md` im Projekt «Topo Karte». Nachträge per Commit anhängen, nicht mehr ganz lesen und neu schreiben.
- `spurplan/werkstatt/olten/` = Stand der bisherigen Arbeitsordner (Spurpläne Region Olten, Referenzen `reg/`, `feedback/` mit `bauen.py`, `zusatz_plaene.json`, `regionalplaene.json`, Vergleichsständen). Ohne PNG und Wegwerfordner.
- Workflow `seite`: baut `feedback/index.html` aus der Werkstatt plus allen Regionalplänen vom Branch `ergebnisse` (`region_<key>/region.svg` → `feedback/region_<key>.svg`), schreibt `ergebnisse/seite/index.html`, `plaene/<key>.svg` und mit `code/ausschnitte.py` je offenem Hinweis (`spurplan/hinweise.json`) einen 600-px-Ausschnitt `ausschnitte/<id>.png` + `index.json`. Läuft nach `plaene`/`regionen`, bei Änderungen in `werkstatt/` oder `hinweise.json` und von Hand.
- Ablauf einer Runde (kurz, möglichst neue Sitzung): Hinweise mit ArtifactData in Dateien holen → `spurplan/hinweise.json` schreiben und committen → nur die Ausschnitte der neuen Hinweise ansehen → Override/Lage/Code committen → Bericht (`bericht.json`) lesen, Ausschnitte erneut ansehen → `ergebnisse/seite/index.html` holen und veröffentlichen (nicht lesen) → Hinweise beantworten.
- Nicht mehr: ganze Skripte oder diese Datei ins Projekt schreiben oder daraus lesen, ganze Regionalpläne als Bild ansehen (nur Ausschnitte), Logs ganz ausgeben.
- Region MOB: Workflow `regionen` (Lauf 39584225141 erfolgreich), Konfig `spurplan/regionen/mob/region.json`. Offen: Montreux/Glion-Lage, La Tine/Montbovon-Schlaufe, Halte/Namen braun, Zweisimmen dichter, G2 52 / G6 6 / G7 2 / G8 8.
- 23.10. spät: `spurplan/werkstatt/ne/` = Arbeitsordner Region Neuchâtel (Bahnhöfe, Overrides, Vorlagen, `ne_region_lage.json`, `ne_region.json`, `topo3/`; ohne PNG, Rohausschnitte `*_roh.json` und Schweiz-Datei – bei Bedarf mit `ausschnitt.py`/`cut.py` neu schneiden). Damit ist kein Arbeitsstand mehr nur in einer Sitzung.

### 24.10.2026 – Runde: keine neuen Hinweise; MOB Montreux/Glion-Lage
- Hinweise: 19 offen, keiner neu seit 23.10. (`hinweise.json` unverändert).
- MOB: Glion-Alpes (Halt 250 m von Glion) hatte keine eigene Weiche, sein 700-m-Ausschnitt deckte dieselben 8 Weichen wie Glion → zwei deckungsgleiche Pläne (G8), Glion als Stumpf unter Linie 100. Fix: `integriert` {"Glion-Alpes": "Glion"} in `regionen/mob/region.json`. Lokal: G2 52→48, G6 6→5, G8 8→6; Reihenfolge Montreux – Les Planches – Toveyre/Valmont – Glion – Glion-Collège – Caux.
- Offen MOB: Bahnhofsplan Glion (Perrons Glion fehlen, Kreuzungsgleis als Stumpf links, Schiebebühne Depot als Punktreihe, Z-Knick bei Glion-Collège), Montreux G2/G6, La Tine/Montbovon-Schlaufe, Halte/Namen braun, Zweisimmen dichter.
- OSM-Release ist aus der Sitzung per curl ladbar (`releases/download/daten/schweiz_bahn.json.gz`); `region_lauf.py mob --daten …` lokal in ~2 min.

### 25.10.2026 – Entscheide zu den offenen Fragen im Regelwerk
- Eingetragen im Doc (Haupttab und Katalog-Tab) und in `REGELN.md`: B14 für alle Pläne, B13 für jeden Bahnhof, N2 neue Rangfolge (gerade Strecken vor Kartenachse, Kerzers als X), B7 immer zusammenrücken, Galmiz Perron südlich + Kreuzungsgleis grün. N11-Frage war überholt (alle fünf Halte seit Entwurf 19 im Regionalplan NE).
- Umsetzung offen: Galmiz-Override (werkstatt/ne), Kerzers als X im Regionalplan NE, B14 in Olten/Bern/Basel prüfen, B13 SBB-Perrons für NE-Bahnhöfe, B7-Verhalten im Code prüfen.
- Regelkatalog-Entwurf (24.10.) wartet auf Daniels Entscheide; danach `spurplan/regeln.json` + Planmodell.

### 25.10.2026 abends – Netzmodell (Test Konolfingen)
- `spurplan_schema.py` schreibt im Standardlauf `<b>_netz.json`: Gleisstücke (Way, OSM-Knoten, Ebene, Plan-y, pax, service, Gleisnummer, Spur), Knoten mit Karten- und Plankoordinaten, OSM-Weichen im Fenster (`im_plan`), gezeichnete Perrons und Nummern (aus dem SVG), OSM-Perrons, Abgänge. Zeichnung unverändert (Kerzers und Neuchâtel byte-gleich geprüft).
- Neu `code/netz_pruefung.py <b>`: Befunde mit Regel-ID des Katalogs: T10 Durchfahrgleis schwarz (beidseitig ohne Richtungswechsel ans Hauptgleis, ≥ 200 m Nebengleis, Gleis selbst ≥ 100 m oder mit Gleisnummer, nicht yard/crossover), A5 Gleis durch Perron, D11 Nummer ohne Perron / OSM-Perron-ref ohne Nummer, D12 Perrons unvollständig, S1 Weiche am Hauptgleis nicht gezeichnet, D6 Stillgelegtes, Z2 Abgang ohne Richtungsort. In `lauf.py` eingebunden (`bericht.json` → `netz`, Ergebnisse `netz.json`, `netz_befunde.json`).
- Konolfingen neu in `bahnhoefe.json` (ohne Overrides): T10 3 (Gleis 6, Gleis 44), D11 4, D12 1 (nur 1 OSM-Perron → SBB-Perrons nötig, B13), Z2 3. Kerzers: D11 2 (Nummer 2 und 5 ohne Perron – Frage an Daniel). Neuchâtel: T10 1.
- Offen: netz_pruefung auch in `region_lauf.py`; T2/T3 (Weichenseite, Reihenfolge) und A1 auf dem Netzmodell; Befunde auf der Feedback-Seite anzeigen.

### 25.10.2026 spät – Netzprüfung erweitert, Kerzers Nummern
- `netz_pruefung.py` liest jetzt auch `<b>_spurplan.svg`: Z2 Pfeilrichtung der Abgangsbeschriftung gegen Abgangsrichtung (Konolfingen «Steffisburg →» zeigt falsch), W2 Stücke ≠ 0°/60° inkl. S-Kurven (Mitte), F2 Knick > 60° ohne Weiche, A1 parallele Gleise enger als 20 px (Haupt) bzw. 9.6 px (mit Nebengleis).
- T10 geschärft: Durchfahrgleis nur mit höchstens 2 Weichen je Ende bis zum Hauptgleis (Thun-Abstellgruppen 3–9 Weichen fielen sonst rein), ≥ 200 m, Gleis ≥ 100 m oder mit Nummer.
- Gegenprobe Referenzen (SVG byte-gleich): Thun A1 1, D11 5, T10 1 (Gl. 233), Z2 1; Ins D11 1, T10 1, W2 1; Murten A1 1; Kerzers keine.
- Kerzers (Entscheid D. Eckenstein 25.10.): Zwischengleise 2 und 5 ohne Perron → `nummern_weg` + 2, 5; SVG in `werkstatt/olten/reg` neu (Differenz nur die zwei Nummern).

### 25.10.2026 abends – Hinweise (Runde)
- Tüscherz (yfi1pm6102v50sop5euu): OSM hat zwei gegenläufige Spurwechsel (184190241 1→2, 184190242 2→1); Vorlage `anzahl 2, richtung fallend`. `vorlage.py`: bei `anzahl 2` gilt jetzt `richtung` (fallend zuerst), Standard unverändert. Werkstatt NE + `zusatz_plaene.json` aktualisiert. Regionalplan NE noch mit altem `tuscherz_bare.svg` gebaut.
- Ins (drd6z7fe3szw6rearb6e): Meterspur-Abgang ab letztem Punkt auf der Meterspurebene gerade unter 60° statt steilem Zwischenstück + 45° (`meterspur_cfg.abgang_60`, Standard an). Netzprüfung W2 weg; Differenz nur diese Stelle. SVG in `werkstatt/olten/reg`.
- Neuchâtel (yj1ralip1fvp5982bby2): Pfeil «läuft weiter» (CONT38/E2) jetzt am Ende eines 14-px-Stummels hinter der Weiche (`cfg.pfeil_stummel_px`, 0 = alt). Thun, Murten, Kerzers byte-gleich; Neuchâtel nur diese Stelle.
- Rothrist (5rte65pcbd37z01tvuqd): OSM: Linie 400 läuft unten durch (tunnel=yes, layer −1) → Unterführung mit Brückenflügeln (B19/T4) zeichnen; offen.
- Neuchâtel Gleis 2 (1v507u9g14qh71941icj, Daniel: «Stummel geradeaus, gebogener Strang schon weg»): `zeichnen` Linie 4 Ecke x:765 → x:769 (Rundung beginnt am Ende von Gleis 2), Linie 5 und `dkw_px` (778.9 → 782.9) um 4 px mit. G7 1 → 0. `zusatz_plaene.json` neuchatel aus dem Repo-Lauf erneuert.
- Entscheide 25.10.: «Anbindung hier» (Region NE) = eigener Plan Vauseyon (R8); Region Olten zuerst in den Workflow `regionen`, dann deren 12 Hinweise; Hinweis-Pins an OSM-Element binden (Netzmodell) statt Pixel.

### 26.10.2026 – Neuchâtel bis Saint-Blaise (Hinweis eh1civ1dzr80annhem8g)
- OSM-Abgleich Korridor Neuchâtel–Saint-Blaise CFF/Lac: 92 Weichen, 43 in Plänen (Neuchâtel, Saint-Blaise CFF/Lac). Nicht gezeichnet war der Ostkopf Neuchâtel bei s=4144–4322 m (0.8–1.1 km östlich): Spurwechsel 49695777 (Linie 210), Weichen 416783522/416784036 ins Nebengleis bzw. Abstellanlage, 11343288453 auf BLS 220; dahinter Abstellanlage Neuchâtel-Est (~30 Weichen, yard, im Hauptgleis-Plan als Pfeile). Von 1.2 km bis Saint-Blaise keine Weichen. Frühere Antwort («keine weiteren Weichen») war falsch (nur das alte Fenster geprüft).
- Neuchâtel `cfg.s_max_fix` 4400, `kein_pax` [49695777] (E1: Spurwechsel schwarz). Code: Regel 43 respektiert jetzt `kein_pax`. Handzeichnungen unverändert (Differenz nur Ostteil).
- Verbindungsprüfung meldet Gleis 5 Ost «OSM 1 / Plan 3» (vorher OSM 3 / Plan 3, Plan gleich) → vermutlich Zuordnung der neuen Planrand-Abgänge zu OSM in verbindungen_pruefen; offen.

### 26.10.2026 – Region Olten gezügelt (Workflow `seite`)
- Neu `code/region_olten_lauf.py` + Konfig `werkstatt/olten/region_olten.json`: baut in einer Kopie der Werkstatt die Bahnhofspläne der Region (ganze Kette wie run.sh; Däniken, Olten, Olten Hammer mit `--hauptgleise`), Netzprüfung je Bahnhof, dann `netz_lage.py olten_region "Region Olten" feedback/region.svg` (+ `--pruefen`) und schreibt Plan/bare/ports/warp/region.svg in die Werkstatt zurück. Läuft im Workflow `seite` vor `bauen.py`; Bericht `ergebnisse/seite/region_olten.json`.
- Nachbau geprüft: 12 Bahnhöfe und Regionalplan byte-gleich. Fest als Eingabe (eigener Bauweg): Hagendorf, Olten Ost, Regionalvarianten Rothrist und Olten Ost (Unterordner).
- `netz_lage.py` (Olten und NE): `np.cross` mit 2D-Vektoren durch `_cr` ersetzt (numpy 2.5 bricht sonst ab).
- Damit gilt: Änderungen an Overrides/Lage der Region Olten wirken direkt im Workflow, kein Hand-Kopieren von SVG mehr.
- `werkstatt/olten/netz_lage.py`: Mindestabstand zwischen Halten (Lage `halt_abstand_min`, Standard 60 px): reicht das längste gerade Stück nicht, verteilen sich die Halte über die ganze gezeichnete Strecke (Hinweis fw9u: Sommerau/Rümlingen/Buckten 48 → ~105 px). Differenz nur Strecke Tecknau–Läufelfingen (Läufelfingerli).
- Hinweis lld9 (Anschlussgleise südlich Olten): echte OSM-Gleise zwischen den Planfenstern Olten/Olten Hammer (137216805 + Verbindung 137713015 an Rothrist–Olten; 57016117, 137216810, Abstellgleis 480 137216908 an Olten–Hammer), nach R9 richtig gezeichnet. Debug: Env NEBDBG in netz_lage (nur lokal benutzt).
- Region Neuchâtel ebenfalls im Workflow `seite`: `region_olten_lauf.py --konfig werkstatt/ne/region_ne.json` (Skript verallgemeinert: Konfig je Werkstatt-Region, Ausgabe-Pfad relativ, fehlende Hilfsmodule wie `lage_auto.py` aus code/). Nachgebaut wird bisher nur Ins; übrige NE-Bahnhöfe (Typvorlagen) mit bare/ports der Werkstatt. Nachbau ohne Änderungen: Abweichung nur Neuchâtel (bare der Werkstatt neuer als der veröffentlichte Regionalplan), Ins, Tüscherz.
- Meterspur-Perron braun (Hinweis olvnrgp65hwz6p3fsqks): `spurplan_schema.py` Perron am Meterspur-Bezugsgleis in MS_COL. Ins (reg + NE) neu.
- `.gitignore`: erzeugte `*_netz.json`/`*_netz_befunde.json` in der Werkstatt.
