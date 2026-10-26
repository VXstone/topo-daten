# Werkstatt

Hier liegen die **Daten** der Regionen Olten und Neuchâtel (OSM-Ausschnitte, Overrides, Lage, feste Eingaben,
Feedbackseite). Der **Code** liegt nur in `spurplan/code/` (seit 26.10.2026; die früheren Kopien von
`spurplan_schema.py`, `netz_lage.py`, `vorlage.py` usw. sind gelöscht, damit es eine einzige Fassung gibt).

- Region Olten / Neuchâtel bauen: `python3 spurplan/code/region_olten_lauf.py [--konfig spurplan/werkstatt/ne/region_ne.json] [--osm schweiz_bahn.json.gz]`
- Die `run.sh` in den Unterordnern brauchen die Skripte aus `spurplan/code/` im selben Ordner; der Lauf kopiert sie selbst.
- Weitere Hilfsskripte (z. B. `gleisnummern_sbb.py`, `typ_vorschlag.py`, `region_winkel.py`, `pruefstand.py`) sind
  noch Werkstatt-Werkzeuge und nicht im Workflow.
