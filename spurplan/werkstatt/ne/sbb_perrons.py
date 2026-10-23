"""Perrons aus SBB Open Data (perronoberflache) als Override "platforms" mit s-Bereich (17.10.2026).
Aufruf: python3 sbb_perrons.py <bahnhof> "<bps_name>" [--schreiben]
Braucht <bahnhof>_fenster.json (SPUR_FENSTER=1 python3 spurplan_schema.py --src <bahnhof>.json).
p_nr "a/b" -> between [a, b]; einzelne Nummer -> outer (Seite aus der Lage der Punkte gegenüber dem Gleis)."""
import json, gzip, sys, math, os, collections
import numpy as np
from shapely.geometry import LineString, Point
key, bps = sys.argv[1], sys.argv[2]
SRC = os.environ.get("SBB_PO", "/tmp/claude-0/sbb/po.geojson.gz")
F = json.load(open(f"{key}_fenster.json"))
lat0, lon0 = F["achse"][0]; kx = 111320 * math.cos(math.radians(lat0)); ky = 110540
xy = lambda la, lo: ((lo - lon0) * kx, (la - lat0) * ky)
A = LineString([xy(a, b) for a, b in F["achse"]]); s0 = F["s"][0]
feats = [f for f in json.load(gzip.open(SRC))["features"] if f["properties"].get("bps_name") == bps]
grp = collections.defaultdict(list)
for f in feats:
    lo, la = f["geometry"]["coordinates"][:2]
    grp[(f["properties"]["p_nr"], f["properties"]["perrontyp"], f["properties"]["p_lange"])].append(xy(la, lo))
# Gleise und OSM-Perrons des Bahnhofs (Lage längs der Achse)
E = json.load(open(f"{key}.json"))["elements"]
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
if "--schreiben" in sys.argv:
    fo = f"{key}_override.json"; O = json.load(open(fo)) if os.path.exists(fo) else {}
    O["platforms"] = out
    O.setdefault("pax", [])
    for p in out:
        for g in (p.get("between") or [p.get("outer")]):
            if g not in O["pax"]: O["pax"].append(g)
    O["_perrons"] = "SBB Open Data perronoberflache (sbb_perrons.py, 17.10.2026)"
    json.dump(O, open(fo, "w"), ensure_ascii=False, indent=1); print("geschrieben", fo)
