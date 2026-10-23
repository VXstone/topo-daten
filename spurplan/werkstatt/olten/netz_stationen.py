"""
Bahnhofsdaten für den Netzplan: Perrongleise (Nummern, Querreihenfolge), Perrons (Override oder Annahme),
Neben-/Abstell-/Güteranlagen (Anzahl, Seite).  Schreibt <name>_stationen.json und <name>_stlen.json.
Aufruf: python3 netz_stationen.py region.json olten_region
"""
import json, math, sys, os, collections
import numpy as np

SRC, NAME = sys.argv[1], sys.argv[2]
F = 2.4                     # px je Layout-Einheit (muss zu netz_render.py passen)
GAP = 15                    # Abstand Perrongleise [px]
D = json.load(open(SRC))["elements"]
lats = [g["lat"] for e in D if e["type"] == "way" for g in e["geometry"]]
lons = [g["lon"] for e in D if e["type"] == "way" for g in e["geometry"]]
LAT0, LON0 = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110540
xy = lambda la, lo: np.array(((lo - LON0) * KX, (la - LAT0) * KY))
ST = {}
for e in D:
    if e["type"] == "node" and e.get("tags", {}).get("railway") == "station":
        ST[e["tags"]["name"].split("/")[0].strip()] = (e, e["tags"]["name"])
rails = [e for e in D if e["type"] == "way" and e["tags"].get("railway") == "rail"]
RP = {e["id"]: np.array([xy(g["lat"], g["lon"]) for g in e["geometry"]]) for e in rails}

def slug(s):
    import unicodedata, re
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")

out, stlen = {}, {}
for name, (node, full) in ST.items():
    c = xy(node["lat"], node["lon"])
    ovr = {}
    for cand in (slug(full), slug(name)):
        if os.path.exists(f"{cand}_override.json"): ovr = json.load(open(f"{cand}_override.json")); break
    # numerierte Gleise im Bahnhof
    pts = collections.defaultdict(list)
    for e in rails:
        r = e["tags"].get("railway:track_ref")
        if not r or e["tags"].get("service") == "yard": continue
        P = RP[e["id"]]; d = np.hypot(*(P - c).T)
        if d.min() > 220: continue
        if ovr.get("pax") and r not in ovr["pax"]: continue
        if not ovr.get("pax") and not (r.isdigit() and int(r) <= 12): continue
        pts[r].extend(P[d < 300].tolist())
    tracks = [r for r in pts if pts[r]]
    missing = [r for r in ovr.get("pax", []) if r not in tracks]
    # Hauptrichtung (PCA) und Querlage
    allp = np.array([p for r in tracks for p in pts[r]]) if tracks else np.array([c])
    if len(allp) > 2:
        u, s_, vt = np.linalg.svd(allp - allp.mean(0)); ax = vt[0]
    else: ax = np.array([1.0, 0.0])
    lat = {r: float(np.median([(np.array(p) - c) @ np.array([-ax[1], ax[0]]) for p in pts[r]])) for r in tracks}
    # Neben-/Abstellanlagen
    ys = [e for e in rails if e["tags"].get("service") in ("yard", "spur") and np.hypot(*(RP[e["id"]] - c).T).min() < 600]
    ylat = [float(np.mean([(p - c) @ np.array([-ax[1], ax[0]]) for p in RP[e["id"]]])) for e in ys]
    n = max(len(tracks), 1)
    Ls_px = 2 * ((n - 1) * GAP / 2 / math.tan(math.radians(60)) + 14) + 90
    stlen[name] = Ls_px / F
    out[name] = dict(full=full, axis=ax.tolist(), tracks=tracks, lat=lat, missing=missing,
                     platforms=ovr.get("platforms"), platforms_source="Ortskenntnis" if ovr.get("platforms") else "Annahme",
                     yard_n=len(ys), yard_side=(float(np.sign(np.mean(ylat))) if ylat else 0.0))
    print(f"{name:20s} Gleise {sorted(tracks, key=lambda r: lat[r])}  fehlend {missing}  Anlagen {len(ys)}  Perrons {out[name]['platforms_source']}")
json.dump(out, open(f"{NAME}_stationen.json", "w"), ensure_ascii=False)
json.dump(stlen, open(f"{NAME}_stlen.json", "w"), ensure_ascii=False)
