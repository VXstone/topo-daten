"""Perrons aus SBB Open Data (perronoberflache) als Override "platforms" mit s-Bereich (17.10.2026; B13 im Workflow 26.10.2026).
Aufruf: python3 sbb_perrons.py <bahnhof> ["<bps_name>"] [--schreiben] [--auto]
Ohne bps_name: Name des Bahnhofsknotens aus <bahnhof>.json (railway=station, sonst halt; uic_name vor name).
--auto (Workflow «plaene»): schreibt nur, wenn das Override noch keine «platforms» hat (Handarbeit geht vor) und die
SBB-Daten den Bahnhof kennen; Quelle SBB_PO oder Release-Datei perronoberflache.geojson.gz.
Braucht <bahnhof>_fenster.json (SPUR_FENSTER=1 python3 spurplan_schema.py --src <bahnhof>.json).
p_nr "a/b" -> between [a, b]; einzelne Nummer -> outer (Seite aus der Lage der Punkte gegenüber dem Gleis)."""
import json, gzip, sys, math, os, collections
import numpy as np
from shapely.geometry import LineString, Point
_pos = [a for a in sys.argv[1:] if not a.startswith("--")]
key = _pos[0]
def _elemente():
    r_ = json.load(open(f"{key}.json"))
    if isinstance(r_, dict) and "elements" not in r_: r_ = r_.get(key) or next(iter(r_.values()))
    return r_["elements"] if isinstance(r_, dict) else r_
def _bps_aus_osm():
    E_ = _elemente()
    st_ = [e for e in E_ if e["type"] == "node" and e.get("tags", {}).get("railway") in ("station", "halt")]
    st_.sort(key=lambda e: (e["tags"].get("railway") != "station", "uic_ref" not in e["tags"]))
    return (st_[0]["tags"].get("uic_name") or st_[0]["tags"].get("name")) if st_ else None
bps = _pos[1] if len(_pos) > 1 else _bps_aus_osm()
SRC = os.environ.get("SBB_PO", "perronoberflache.geojson.gz")
AUTO = "--auto" in sys.argv
if AUTO:
    _o = json.load(open(f"{key}_override.json")) if os.path.exists(f"{key}_override.json") else {}
    if _o.get("platforms") is not None or not os.path.exists(SRC) or not bps:
        print(f"SBB-Perrons {key}: nichts zu tun ({'Override hat platforms' if _o.get('platforms') is not None else 'keine Daten/kein Name'})"); sys.exit(0)
F = json.load(open(f"{key}_fenster.json"))
lat0, lon0 = F["achse"][0]; kx = 111320 * math.cos(math.radians(lat0)); ky = 110540
xy = lambda la, lo: ((lo - lon0) * kx, (la - lat0) * ky)
A = LineString([xy(a, b) for a, b in F["achse"]]); s0 = F["s"][0]
import unicodedata
_norm = lambda t: "".join(c for c in unicodedata.normalize("NFKD", t or "") if not unicodedata.combining(c)).lower().replace("-", "").replace(" ", "").replace(".", "")
feats = [f for f in json.load(gzip.open(SRC))["features"] if _norm(f["properties"].get("bps_name")) == _norm(bps)]   # SBB ohne Akzente/Bindestrich
if not feats:
    print(f"SBB-Perrons {key}: «{bps}» nicht in den SBB-Daten"); sys.exit(0)
grp = collections.defaultdict(list)
for f in feats:
    lo, la = f["geometry"]["coordinates"][:2]
    grp[(f["properties"]["p_nr"], f["properties"]["perrontyp"], f["properties"]["p_lange"])].append(xy(la, lo))
# Gleise und OSM-Perrons des Bahnhofs (Lage längs der Achse)
def _elemente():
    r_ = json.load(open(f"{key}.json"))
    if isinstance(r_, dict) and "elements" not in r_: r_ = r_.get(key) or next(iter(r_.values()))
    return r_["elements"] if isinstance(r_, dict) else r_
E = _elemente()
span = collections.defaultdict(list); trk = collections.defaultdict(list); osm_pl = []
for e in E:
    if e["type"] != "way": continue
    g = [xy(q["lat"], q["lon"]) for q in e.get("geometry", [])]
    if len(g) < 2: continue
    if e["tags"].get("railway") == "rail" and e["tags"].get("railway:track_ref"):
        r = e["tags"]["railway:track_ref"]; span[r] += [s0 + A.project(Point(p)) for p in g]; trk[r].append(LineString(g))
    elif e["tags"].get("railway") == "platform":
        osm_pl.append(LineString(g))
def tr_span(r):
    v = [x for x in span.get(r, []) if F["s_min"] - 50 <= x <= F["s_max"] + 50]
    return (min(v), max(v)) if v else None
ALLS = sorted(s0 + A.project(Point(p)) for v in grp.values() for p in v); C_PREF = ALLS[len(ALLS) // 2] if ALLS else 0
out = []
for (nr, typ, L), pts in sorted(grp.items()):
    ss = [s0 + A.project(Point(p)) for p in pts]; L = float(L or 150)
    tr = nr.split("/")[:2]
    sp = [tr_span(t) for t in tr if tr_span(t)]
    lo_s, hi_s = (max(a for a, b in sp), min(b for a, b in sp)) if sp else (min(ss) - L, max(ss) + L)
    if sp and (max(ss) < lo_s - 60 or min(ss) > hi_s + 60):      # SBB-Perron liegt nicht an dem OSM-Gleis mit dieser Nummer
        print(nr, typ, L, [round(v) for v in ss], f"→ übersprungen: Gleis {'/'.join(tr)} in OSM bei {round(lo_s)}–{round(hi_s)}, SBB-Punkte daneben")
        continue
    # 1) OSM-Perron neben diesen Gleisen und nahe an den SBB-Punkten: dessen Lage
    cand = [pl for pl in osm_pl if all(min((ln.distance(pl.centroid) for ln in trk.get(t, [])), default=99) < 14 for t in tr)
            and min(pl.distance(Point(p)) for p in pts) < 30]
    if cand:
        v = [s0 + A.project(Point(c)) for pl in cand for c in pl.coords]; lo_, hi_ = min(v), max(v); src = "OSM-Perron"
    else:
        # 2) Länge L, alle SBB-Punkte enthalten, innerhalb der gemeinsamen Gleislänge, möglichst mittig
        lo_ = min(max(C_PREF - L / 2, max(ss) - L, lo_s), min(ss), hi_s - L); hi_ = lo_ + L; src = "SBB-Länge, um Bahnhofsmitte"
    if "/" in nr:
        a, b = nr.split("/")[:2]; out.append({"between": [a, b], "s": [round(lo_), round(hi_)], "_sbb": f"{nr} {typ} {L:.0f} m"})
    else:
        out.append({"outer": nr, "s": [round(lo_), round(hi_)], "_sbb": f"{nr} {typ} {L:.0f} m"})
    print(nr, typ, L, [round(v) for v in ss], "→", round(lo_), round(hi_), src)
if "--schreiben" in sys.argv or (AUTO and out):
    fo = f"{key}_override.json"; O = json.load(open(fo)) if os.path.exists(fo) else {}
    O["platforms"] = out
    O.setdefault("pax", [])
    for p in out:
        for g in (p.get("between") or [p.get("outer")]):
            if g not in O["pax"]: O["pax"].append(g)
    O["_perrons"] = f"SBB Open Data perronoberflache «{bps}» (sbb_perrons.py{' automatisch im Lauf' if AUTO else ''})"
    json.dump(O, open(fo, "w"), ensure_ascii=False, indent=1); print("geschrieben", fo)
