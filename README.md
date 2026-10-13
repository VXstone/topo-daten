# topo-daten

Bahn-Topologie der Schweiz aus OpenStreetMap, automatisch aufbereitet für die schematischen Spur- und Netzpläne (Projekt «Topo Karte»).

Ein GitHub-Workflow lädt monatlich (und auf Knopfdruck) den Schweiz-Extrakt von Geofabrik, filtert alle Bahnelemente heraus und veröffentlicht sie als Release `daten`:

| Datei | Inhalt |
|---|---|
| `schweiz_bahn.json.gz` | Gleise, Perrons, Weichen, Prellböcke, Bahnhöfe, Signale usw. im Format von Overpass `out geom;` |
| `bahn_schweiz.osm.pbf` | dasselbe als OSM-PBF (für osmium/QGIS) |
| `stand.json` (im Repo) | Zeitpunkt, OSM-Stand, Anzahl Elemente |

Download-Adresse (öffentliches Repo):
`https://github.com/<benutzer>/topo-daten/releases/download/daten/schweiz_bahn.json.gz`

## Ausschnitte schneiden

`skripte/ausschnitt.py` liefert dasselbe wie die bisherige Colab-Abfrage (gleicher Filter, Ways vollständig, sobald sie den Ausschnitt schneiden):

```
python3 skripte/ausschnitt.py schweiz_bahn.json.gz kim.json kerzers=46.966,7.180,46.986,7.212 ins=46.997,7.090,47.015,7.122
python3 skripte/ausschnitt.py schweiz_bahn.json.gz region.json --flach olten_region=47.25,7.75,47.45,8.05
```

bbox = Süd,West,Nord,Ost. `--alles` nimmt alle Bahnelemente (auch Signale, Schmalspur, Tram), `--flach` gibt bei einem Ausschnitt die Overpass-Antwort direkt aus.

## Grenzen

- Der Geofabrik-Extrakt endet an der Landesgrenze (inkl. Liechtenstein). Strecken ins Ausland sind dort abgeschnitten.
- Relationen (Streckenrelationen `route=tracks/train`) sind nicht enthalten; Liniennummern kommen wie bisher aus dem `ref` der Gleise.

Daten © OpenStreetMap-Mitwirkende, Lizenz ODbL.
