# Daten holen über GitHub (ersetzt Colab, eingerichtet 13.10.2026)

Die Sandbox erreicht Overpass/Geofabrik nicht, wohl aber GitHub (API, raw, Release-Downloads).
Repo **VXstone/topo-daten** (öffentlich, GitHub-User VXstone = Daniel):
- Workflow `.github/workflows/bahndaten.yml`: monatlich (2., 03:17 UTC) und manuell; Geofabrik Schweiz-PBF → `osmium tags-filter nwr/railway w/public_transport=platform` → `skripte/umwandeln.py` → Release `daten` mit `schweiz_bahn.json.gz` (Overpass-`out geom`-Format, ~11 MB) und `bahn_schweiz.osm.pbf`; `stand.json` im Repo.
- Abholen:
  - `curl -sSL https://raw.githubusercontent.com/VXstone/topo-daten/main/stand.json`
  - `curl -sSL -o schweiz_bahn.json.gz https://github.com/VXstone/topo-daten/releases/download/daten/schweiz_bahn.json.gz`
  - Skripte: `https://raw.githubusercontent.com/VXstone/topo-daten/main/skripte/ausschnitt.py`
- Ausschnitt wie Colab: `python3 ausschnitt.py schweiz_bahn.json.gz kim.json name=S,W,N,E …` (`--alles` alle Bahnelemente inkl. Signale, `--flach` direkte Overpass-Antwort).
- Erster Lauf 13.10.2026 (OSM-Stand 12.10.): 61 378 Nodes, 73 572 Ways. Abgleich Thun 249 Elemente (Colab früher 248).
- Grenzen: endet an der Landesgrenze; keine Relationen.
- Actions-Versionen: checkout@v6, setup-python@v6 (Node 24).
- Meterspur ist enthalten (`railway=narrow_gauge`, `gauge=1000`). Ins 14.10.: Ways mit gauge 1000 im Rechteck 46.995,7.085–47.02,7.12 → `reg/ins_meter.json` (9 Ways, asm Gleis 11 + Abstellgleis + Strecke Biel); Override `meterspur` / `meterspur_cfg` (bezug, d_max, m_pro_lane, max_innen, abstand_lanes, ausfahrt_lanes, ziel).
