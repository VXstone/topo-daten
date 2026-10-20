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

## Release `vorbereitung`
`betriebspunkte.json`, `gleisnummern.json`, `region_<key>.json.gz`, `bahnhoefe_<key>.zip/.json`, `aenderungen.json`,
`schweiz_bahn_vorher.json.gz` (Vergleichsbasis für den nächsten Monat).

## Getestet (Sandbox, OSM-Stand 12.10., SBB perronoberflache)
- Betriebspunkte: 1087 (713 SBB+OSM, 90 nur SBB-Perron, 284 nur OSM). Ohne OSM-Stationsknoten u. a. Onnens-Bonvillars,
  Ligerz, Neuchâtel-Vauseyon, Vaumarcus, Montmollin-Montezillon, Boveresse.
- Gleisnummern: gleiche Ergebnisse wie die in Neuchâtel geprüfte Zuordnung (Grandson 1|2|3, Gorgier 3|2|1, Concise, Bevaix,
  Avenches, Cressier, Galmiz); grosse Knoten (> 5 Gleisnummern: Neuchâtel, Olten, Bern, Biel) → `gross: true`, von Hand.
- Ausschnitte: Region Neuchâtel 61, Olten 24 Betriebspunkte, 7 s.
- Nicht getestet: SBB «linie-mit-betriebspunkten» und «perronkante» (Sandbox ohne Zugriff). Feldnamen werden per Stichwort
  gesucht; beim ersten Lauf das Log ansehen. `perronkante` lieferte am 15.10. 404 – Export-ID auf data.sbb.ch prüfen.

## Einbau
Ordner ins Repo kopieren, committen, unter Actions «vorbereitung» einmal von Hand starten.

## Nächster Schritt (Stufe 2)
Spurplan-Skripte und Bahnhofs-Overrides ins Repo; Workflow zeichnet bei jeder Änderung alle Bahnhöfe und Regionalpläne,
läuft Prüfstand, Regelprüfung und Differenzbild und legt alles als Release ab.
