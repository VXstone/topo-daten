"""
Achse eines Spurplans aus einer Folge von OSM-Ways (z. B. durch das Gleis, durch das die Streckenachse wirklich läuft).
  python3 achse_aus_ways.py <bahnhof.json> <ausgabe_axis.json> way1 way2 ...
Die Ways werden in der angegebenen Reihenfolge aneinandergehängt (Richtung wird automatisch gedreht).
"""
import json, sys
src, out, ids = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3:]]
W = {e["id"]: e for e in json.load(open(src))["elements"] if e["type"] == "way"}
pts = []
for k, i in enumerate(ids):
    g = [(p["lat"], p["lon"]) for p in W[i]["geometry"] if p]
    if pts:
        if min(((g[0][0]-pts[-1][0])**2 + (g[0][1]-pts[-1][1])**2), ((g[-1][0]-pts[-1][0])**2 + (g[-1][1]-pts[-1][1])**2)) == ((g[-1][0]-pts[-1][0])**2 + (g[-1][1]-pts[-1][1])**2):
            g = g[::-1]
    elif len(ids) > 1:
        h = [(p["lat"], p["lon"]) for p in W[ids[1]]["geometry"] if p]
        d = lambda a, b: (a[0]-b[0])**2 + (a[1]-b[1])**2
        if min(d(g[0], h[0]), d(g[0], h[-1])) < min(d(g[-1], h[0]), d(g[-1], h[-1])): g = g[::-1]
    pts += g if not pts else g[1:]
json.dump({"ref": "ways " + " ".join(map(str, ids)), "coords": [list(p) for p in pts]}, open(out, "w"))
print(len(pts), "Punkte")
