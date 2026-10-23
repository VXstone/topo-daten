"""Kreisförmiger Ausschnitt um den Stationsknoten (Ersatz für das frühere cut.py).
  python3 cut.py <bahnhof> <radius_m> [quelle.json]
Ways werden an der Kreisgrenze geteilt (zusammenhängende Läufe innerhalb des Kreises; der erste Lauf behält die Way-ID,
weitere bekommen ID*100+k). Knoten ausserhalb fallen weg. Ergebnis überschreibt <bahnhof>.json, Original bleibt in <bahnhof>_roh.json."""
import json, math, sys, os, shutil
key, R = sys.argv[1], float(sys.argv[2])
src = sys.argv[3] if len(sys.argv) > 3 else f"{key}_roh.json"
if not os.path.exists(f"{key}_roh.json"): shutil.copy(f"{key}.json", f"{key}_roh.json")
E = json.load(open(src))["elements"]
st = [e for e in E if e["type"] == "node" and e.get("tags", {}).get("railway") == "station"][0]
kx = 111320 * math.cos(math.radians(st["lat"]))
inside = lambda g: math.hypot((g["lon"] - st["lon"]) * kx, (g["lat"] - st["lat"]) * 110540) <= R
out = []
for e in E:
    if e["type"] == "node":
        if inside(e): out.append(e)
        continue
    if e["type"] != "way": out.append(e); continue
    runs, cur = [], []
    for n, g in zip(e["nodes"], e["geometry"]):
        if inside(g): cur.append((n, g))
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    for k, r in enumerate(runs):
        if len(r) < 2: continue
        w = dict(e); w["id"] = e["id"] if k == 0 else e["id"] * 100 + k
        w["nodes"] = [n for n, _ in r]; w["geometry"] = [g for _, g in r]
        out.append(w)
json.dump({"elements": out}, open(f"{key}.json", "w"))
print(key, "Radius", R, "m:", len(out), "Elemente")
