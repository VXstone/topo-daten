"""Fehlende Kante in <name>_topologie.json ergänzen: kürzester Weg über Streckengleise zwischen zwei Knoten.
  python3 topo_ergaenzen.py <name> <daten.json> <knoten_a> <knoten_b> <ref>   (Chambrelien Spitzkehre, 15.10.2026)"""
import json, math, sys, networkx as nx
name, src, a, b, ref = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
D = json.load(open(src))["elements"]
lats = [g["lat"] for e in D if e["type"] == "way" for g in e["geometry"]]; lons = [g["lon"] for e in D if e["type"] == "way" for g in e["geometry"]]
LAT0, LON0 = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
KX = 111320 * math.cos(math.radians(LAT0)); xy = lambda g: ((g["lon"] - LON0) * KX, (g["lat"] - LAT0) * 110540)
G = nx.Graph(); P = {}
for w in D:
    if w["type"] != "way" or w["tags"].get("railway") != "rail" or w["tags"].get("service") or w["tags"].get("gauge", "1435") != "1435": continue
    for n, g in zip(w["nodes"], w["geometry"]): P[n] = xy(g)
    for u, v in zip(w["nodes"], w["nodes"][1:]): G.add_edge(u, v, w=math.dist(P[u], P[v]))
T = json.load(open(f"{name}_topologie.json")); N = {n["id"]: n for n in T["nodes"]}
near = lambda k: min(G.nodes, key=lambda n: math.hypot(P[n][0] - N[k]["x"], P[n][1] - N[k]["y"]))
p = nx.shortest_path(G, near(a), near(b), weight="w")
geom = [[round(P[n][0], 1), round(P[n][1], 1)] for n in p]
T["edges"].append(dict(a=a, b=b, ref=ref, tracks=1, length=round(sum(math.dist(u, v) for u, v in zip(geom, geom[1:]))), geom=geom, refs=[ref]))
json.dump(T, open(f"{name}_topologie.json", "w"), ensure_ascii=False)
print("Kante", N[a]["name"], "-", N[b]["name"], round(T["edges"][-1]["length"]), "m", len(geom), "Punkte")
