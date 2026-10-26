"""Endbahnhöfe je Streckennummer (OSM ref) aus der Schweiz-Datei (26.10.2026, Solothurn: Richtungsorte falsch).

  python3 linienenden.py schweiz_bahn.json.gz [linienenden.json]

Für jede Streckennummer (railway=rail, usage main/branch, ref gesetzt) werden die Enden des Streckennetzes gesucht
(Knoten, an denen nur ein Way dieser Nummer endet und die weit vom Rest entfernt sind) und dem nächsten Bahnhof
(railway=station, sonst halt) zugeordnet. spurplan_schema.py nimmt daraus den Richtungsort eines Abgangs, wenn
weder das Override («abgang») noch eine Linientabelle der Region (region_lines.json) ihn festlegt.
Dazu je Nummer die Orte aus der festen Ortsliste von spurplan_schema.py («towns»), die an dieser Strecke liegen
(höchstens 1.5 km von ihren Gleisen): Ergebnis {ref: {"enden": [[Name, lat, lon], ...], "orte": [Name, ...]}}.
"""
import gzip, json, math, sys, collections

src = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else "linienenden.json"
E = json.load(gzip.open(src)); E = E["elements"] if isinstance(E, dict) else E
KM = lambda a, b: math.hypot((a[0] - b[0]) * 111.0, (a[1] - b[1]) * 75.5)
st = [(e["tags"].get("name"), e["lat"], e["lon"], e["tags"].get("railway"))
      for e in E if e["type"] == "node" and e.get("tags", {}).get("railway") in ("station", "halt") and e["tags"].get("name")]
def bahnhof(p):
    best = None
    for name, la, lo, rw in st:
        d = KM(p, (la, lo)) + (0 if rw == "station" else 0.8)          # Bahnhof vor Haltestelle
        if best is None or d < best[0]: best = (d, name, la, lo)
    return best

ways = collections.defaultdict(list)
for e in E:
    t = e.get("tags", {})
    if e["type"] == "way" and t.get("railway") == "rail" and t.get("usage") in ("main", "branch") and t.get("ref") \
            and not t.get("service") and len(e.get("geometry", [])) > 1:
        for r in t["ref"].replace(",", ";").split(";"):
            ways[r.strip()].append(e)
import os, re, ast
_t = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "spurplan_schema.py")).read()
TOWNS = ast.literal_eval(re.search(r"towns=(\{.*?\}),\n\)", _t, re.S).group(1))
res = {}
for ref, W in sorted(ways.items()):
    ende = collections.Counter(); pos = {}
    for w in W:
        for i in (0, -1):
            n = w["nodes"][i]; ende[n] += 1; pos[n] = (w["geometry"][i]["lat"], w["geometry"][i]["lon"])
        for n, g in zip(w["nodes"][1:-1], w["geometry"][1:-1]): ende[n] += 2; pos[n] = (g["lat"], g["lon"])
    kand = [pos[n] for n, c in ende.items() if c == 1]
    if not kand: continue
    pts = [(g["lat"], g["lon"]) for w in W for g in w["geometry"][::5]]
    # Enden, die weit vom Schwerpunkt liegen, zu Gruppen (8 km) zusammenfassen; je Gruppe das äusserste
    cz = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    kand.sort(key=lambda p: -KM(p, cz)); grp = []
    for p in kand:
        if all(KM(p, q) > 8 for q in grp): grp.append(p)
    span = max(KM(a, cz) for a in pts)
    grp = [p for p in grp if KM(p, cz) > 0.5 * span][:4]
    orte = []
    allp = [(g["lat"], g["lon"]) for w in W for g in w["geometry"]]
    def bahnhof_an_linie(p):     # Bahnhof an dieser Strecke (höchstens 0.4 km von ihren Gleisen), sonst der nächste
        nah_ = [(KM(p, (la, lo)), n_, la, lo) for n_, la, lo, rw in st if rw == "station" and "[" not in n_ and KM(p, (la, lo)) < 4]
        nah_ = [b for b in sorted(nah_) if any(KM((b[2], b[3]), q) < 0.4 for q in allp)]
        return nah_[0] if nah_ else bahnhof(p)
    for p in grp:
        b = bahnhof(p)
        if b and b[0] < 3 and b[1] not in [o[0] for o in orte]: orte.append([b[1], round(b[2], 4), round(b[3], 4)])
    nah = [n for n, (la, lo) in TOWNS.items() if any(KM((la, lo), q) < 1.5 for q in pts) or any(KM((la, lo), q) < 6 for q in grp)]   # auch Ort kurz nach dem Linienende (Bern bei Gümligen)
    if orte or nah: res[ref] = dict(enden=orte, orte=sorted(set(nah)))
json.dump(res, open(out, "w"), ensure_ascii=False, indent=0)
print(len(res), "Streckennummern →", out)
for r in ("410", "415", "420", "421", "430", "460", "450", "500", "210"):
    print(" ", r, res.get(r))
