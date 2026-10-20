# Vorbereitung Spurpläne (Ergänzung für VXstone/topo-daten, 20.10.2026)

Ein zweiter Workflow `vorbereitung` läuft nach dem monatlichen Datenabzug (`bahndaten`) oder von Hand und legt die Ergebnisse
ins Release **`vorbereitung`**. Die Sitzungen holen dort fertige Daten, statt sie jedes Mal selbst aufzubereiten.

## Dateien
| Datei | Inhalt |
|---|---|
| `.github/workflows/vorbereitung.yml` | Workflow (benötigt keine Geheimnisse, nur `contents: write`) |
| `skripte/vorbereitung/gemeinsam.py` | Hilfen (Laden, Abstände, Feldsuche in SBB-Exporten) |
| `skripte/vorbereitung/betriebspunkte.py` | Liste aller Betriebspunkte: SBB «Linie mit Betriebspunkten» + SBB-Perrons + OSM-Stationen; Ersatzknoten auf dem Hauptgleis, wo OSM keinen Stationsknoten hat |
| `skripte/vorbereitung/gleisnummern.py` | Gleisnummern je Betriebspunkt nach den Regeln vom 20.10. (SBB vor OSM, nur Gleise mit Perron, Einzelgleis-Halt ohne Nummer, stillgelegt zählt nicht, «?» wo keine Quelle) |
| `skripte/vorbereitung/ausschnitte.py` | je Region: `region_<key>.json.gz`; je Betriebspunkt: `bahnhoefe_<key>.zip` mit `<slug>.json` (Kreis wie `cut.py`) und `<slug>_roh.json` |
| `skripte/vorbereitung/aenderungen.py` | Änderungen gegenüber dem Vormonat je Betriebspunkt → welche Pläne neu zeichnen |
| `konfig/regionen.json` | Vielecke der Regionen (Olten, Neuchâtel); neue Region = neuer Eintrag |

## SBB-Datensätze (data.sbb.ch, Stand 20.10.2026)
| Ziel | Datensatz | Inhalt |
|---|---|---|
| Perronflächen | `perronoberflache` | 2212 Perrons, p_nr «a/b», perrontyp |
| Perronkanten | `21196_behig-haltekantepunkt` | ~500 000 Punkte (1 m), `kundengleisnr`, Kantenlänge, LV95 → verdichtet zu `perronkanten.json` (2799 Kanten, 978 Betriebspunkte) |
| Betriebspunkte | `linie-mit-betriebspunkten` | 1894 Punkte je Linie, `abkurzung_bpk`, `bezeichnung_offiziell` (z. B. «Olten Ost (Abzw)»), km |
Die früheren IDs `perronkante`, `haltestelle-perronkante(-inkl-bls)` liefern 404; `haltestelle-haltekante` enthält nur Haltestellen ohne Kanten.
`sbb_laden.py` versucht bekannte IDs, sucht sonst im Katalog und protokolliert alles.

## stand.json (Schlüssel `vorbereitung`)
Weil die Lauf-Logs ausserhalb von GitHub nicht lesbar sind, schreibt jeder Lauf: Zeitpunkt und Lauf-Link, Ergebnis jedes Schritts
(OK/failure), je SBB-Datensatz Status OK/fehlt mit ID, Anzahl, Feldern, Versuchen und Katalog-Kandidaten, Musterzeilen, Zahlen der
Ergebnisse und Stichproben (Betriebspunkte Olten/Rothrist/Neuchâtel …, Gleisnummern, Perronkanten je Bahnhof).
Der Workflow «Bahndaten Schweiz» lässt diesen Schlüssel beim Überschreiben von stand.json stehen.

## Release `vorbereitung`
`betriebspunkte.json`, `gleisnummern.json`, `perronkanten.json`, `sbb_perronoberflache.geojson.gz`, `sbb_betriebspunkte.geojson.gz`, `region_<key>.json.gz`, `bahnhoefe_<key>.zip/.json`, `aenderungen.json`,
`schweiz_bahn_vorher.json.gz` (Vergleichsbasis für den nächsten Monat).

## Getestet (Sandbox, OSM-Stand 12.10., SBB perronoberflache)
- Betriebspunkte: 1087 (713 SBB+OSM, 90 nur SBB-Perron, 284 nur OSM). Ohne OSM-Stationsknoten u. a. Onnens-Bonvillars,
  Ligerz, Neuchâtel-Vauseyon, Vaumarcus, Montmollin-Montezillon, Boveresse.
- Gleisnummern: gleiche Ergebnisse wie die in Neuchâtel geprüfte Zuordnung (Grandson 1|2|3, Gorgier 3|2|1, Concise, Bevaix,
  Avenches, Cressier, Galmiz); grosse Knoten (> 5 Gleisnummern: Neuchâtel, Olten, Bern, Biel) → `gross: true`, von Hand.
- Ausschnitte: Region Neuchâtel 61, Olten 24 Betriebspunkte, 7 s.
- Nicht getestet: SBB «linie-mit-betriebspunkten» und «perronkante» (Sandbox ohne Zugriff). Feldnamen werden per Stichwort
  gesucht; beim ersten Lauf das Log ansehen. `perronkante` lieferte am 15.10. 404 – Export-ID auf data.sbb.ch prüfen.

## Eingebaut 20.10.2026
Erster Lauf erfolgreich (alle Schritte OK). Alte Datei `sbb_perronkante.geojson.gz` (17 MB Rohdaten eines Zwischenlaufs) kann im Release gelöscht werden.

## Nächster Schritt (Stufe 2)
Spurplan-Skripte und Bahnhofs-Overrides ins Repo; Workflow zeichnet bei jeder Änderung alle Bahnhöfe und Regionalpläne,
läuft Prüfstand, Regelprüfung und Differenzbild und legt alles als Release ab.
