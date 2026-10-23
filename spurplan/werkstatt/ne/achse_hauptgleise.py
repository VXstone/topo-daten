"""Achse (Regel 25) als kürzester Weg über Hauptgleise zwischen zwei Randpunkten.
  python3 achse_hauptgleise.py <bahnhof> <lat1,lon1> <lat2,lon2>"""
import json, math, sys, heapq, collections
key = sys.argv[1]
ziele = [tuple(map(float, a.split(","))) for a in sys.argv[2:4]]
E = json.load(open(f"{key}.json"))["elements"]
W = [w for w in E if w["type"] == "way" and w["tags"].get("railway") == "rail" and w["tags"].get("gauge", "1435") == "1435"
     and w["tags"].get("service") in (None, "siding", "crossover")]
LL = {n: (g["lat"], g["lon"]) for w in W for n, g in zip(w["nodes"], w["geometry"])}
lat0 = sum(v[0] for v in LL.values()) / len(LL)
kx = 111320 * math.cos(math.radians(lat0))
xy = lambda p: (p[1] * kx, p[0] * 110540)
G = collections.defaultdict(list)
for w in W:
    f = 1.0 if w["tags"].get("usage") == "main" else (1.3 if not w["tags"].get("service") else 3.0)
    for a, b in zip(w["nodes"], w["nodes"][1:]):
        L = math.dist(xy(LL[a]), xy(LL[b])) * f
        G[a].append((b, L)); G[b].append((a, L))
def nah(p):
    return min((n for w in W if not w["tags"].get("service") for n in w["nodes"]), key=lambda n: math.dist(xy(LL[n]), xy(p)))
A, B = nah(ziele[0]), nah(ziele[1])
dist = {A: 0}; prev = {}; pq = [(0, A)]
while pq:
    d, u = heapq.heappop(pq)
    if u == B: break
    if d > dist[u]: continue
    for v, L in G[u]:
        if d + L < dist.get(v, 1e18): dist[v] = d + L; prev[v] = u; heapq.heappush(pq, (d + L, v))
p = [B]
while p[-1] != A: p.append(prev[p[-1]])
p = p[::-1]
json.dump({"ref": f"hauptgleise {A}-{B}", "coords": [list(LL[n]) for n in p]}, open(f"{key}_axis.json", "w"))
print(len(p), "Punkte, Länge", round(sum(math.dist(xy(LL[a]), xy(LL[b])) for a, b in zip(p, p[1:]))), "m")
