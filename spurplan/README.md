# Spurpläne im Repo

`code/` alle Skripte (eine Fassung für alle Bahnhöfe), `bahnhoefe/<b>/` je Bahnhof OSM-Ausschnitt, Override, Achse,
`bahnhoefe.json` welche Bahnhöfe gebaut werden (mit Optionen), `vergleich/` abgenommene bzw. zuletzt veröffentlichte Fassung.
Workflow `plaene` baut bei jedem Commit unter `spurplan/` und schreibt Ergebnisse und Prüfbericht auf den Branch `ergebnisse`.
Lokal: `python3 spurplan/code/lauf.py neuchatel` → `ergebnisse/neuchatel/`.
