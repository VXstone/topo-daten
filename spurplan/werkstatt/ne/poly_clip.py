"""Daten auf das Perimeter-Vieleck zuschneiden (Region Neuchâtel mit Kerzers/Murten, 15.10.2026 abends).
  python3 poly_clip.py ein.json rand.json aus.json
Ways: Stücke mit Knoten im Vieleck (+1 Knoten über den Rand), Knoten (Bahnhöfe, Weichen): nur im Vieleck."""
import json, sys
from shapely.geometry import Polygon, Point, LineString
src, rand, out = sys.argv[1:4]
POLY = Polygon([(lo, la) for la, lo in json.load(open(rand))])
inside = lambda g: POLY.contains(Point(g["lon"], g["lat"]))
E = json.load(open(src))["elements"]; R = []
for e in E:
    if e["type"] == "node":
        if inside(e): R.append(e)
        continue
    ins = [inside(g) for g in e["geometry"]]; n = len(ins); k = 0; i = 0
    while i < n:
        if not ins[i]: i += 1; continue
        j = i
        while j + 1 < n and ins[j + 1]: j += 1
        a, b = max(i - 1, 0), min(j + 1, n - 1)
        if b > a:
            w = dict(e); w["nodes"] = e["nodes"][a:b + 1]; geo = [dict(g) for g in e["geometry"][a:b + 1]]
            for q, r in ((0, 1), (-1, -2)):          # Punkt jenseits des Randes auf den Rand ziehen
                if len(geo) > 1 and not inside(geo[q]):
                    seg = LineString([(geo[r]["lon"], geo[r]["lat"]), (geo[q]["lon"], geo[q]["lat"])]).intersection(POLY.exterior)
                    if not seg.is_empty:
                        p = seg if seg.geom_type == "Point" else list(seg.geoms)[0]
                        geo[q] = {"lat": p.y, "lon": p.x}
            w["geometry"] = geo
            if k: w["id"] = e["id"] * 100 + k
            R.append(w); k += 1
        i = j + 1
json.dump({"elements": R}, open(out, "w"))
print(len(E), "->", len(R))
