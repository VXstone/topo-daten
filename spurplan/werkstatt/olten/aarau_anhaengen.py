"""Aarau an den Regionalplan Olten anhängen (Wunsch D. Eckenstein 8.11.2026, Testfall Schritt P).

  python3 aarau_anhaengen.py <schweiz_bahn.json.gz>

Einmalig (Werkstatt): die bisherigen Abgänge «540 Aarau» (#36) und «650 Aarau» (#42) am Ostrand der Region werden zu
Kanten Schönenwerd–Aarau (540) und Abzweig #28–Aarau (650); neu ein Abgang 650 Richtung Lenzburg im Wald vor Rupperswil.
Kantengeometrie = kürzester Weg über Streckengleise (wie ne/topo_ergaenzen.py), in den Koordinaten der bestehenden
Topologie (Bezugspunkt = Mitte von region.json, unverändert). Schreibt ausserdem olten_region_osm.json = region.json plus
die Bahnelemente bis Aarau/Rupperswil (für Spurwechsel auf freier Strecke in netz_lage, Lage «osm» + «osm_versatz»).
Wiederholt aufrufbar: arbeitet immer vom Stand ohne Aarau (Knoten #36/#42 oder schon vorhandenes Aarau werden ersetzt).
"""
import json, gzip, math, sys, os
import networkx as nx
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "skripte"))
import ausschnitt as AU

SRC = sys.argv[1]
T = json.load(open("olten_region_topologie.json"))
R = json.load(open("region.json"))["elements"]
lats = [g["lat"] for e in R if e["type"] == "way" for g in e["geometry"]]; lons = [g["lon"] for e in R if e["type"] == "way" for g in e["geometry"]]
LAT0, LON0 = (min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110540
xy = lambda la, lo: ((lo - LON0) * KX, (la - LAT0) * KY)

CH = json.load(gzip.open(SRC)); CH = CH["elements"] if isinstance(CH, dict) else CH
BB = (47.33, 7.95, 47.42, 8.11)          # S, W, N, E: Schönenwerd/Däniken bis Wald vor Rupperswil
el = [e for e in CH if AU.wie_colab(e) and ((e["type"] == "node" and BB[0] <= e["lat"] <= BB[2] and BB[1] <= e["lon"] <= BB[3])
      or (e["type"] == "way" and AU.schneidet(e.get("geometry", []), *BB)))]
G = nx.Graph(); P = {}
for w in el:
    if w["type"] != "way" or w["tags"].get("railway") != "rail" or w["tags"].get("gauge", "1435") != "1435": continue
    if w["tags"].get("service") not in (None, "crossover"): continue        # Spurwechsel ja, Abstellgleise nein
    for n, g in zip(w["nodes"], w["geometry"]): P[n] = xy(g["lat"], g["lon"])
    for u, v in zip(w["nodes"], w["nodes"][1:]): G.add_edge(u, v, w=math.dist(P[u], P[v]) * (3 if w["tags"].get("service") else 1))
G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
def near(x, y): return min(G.nodes, key=lambda n: math.hypot(P[n][0] - x, P[n][1] - y))
def weg(a, b):
    p = nx.shortest_path(G, a, b, weight="w")
    g = [[round(P[n][0], 1), round(P[n][1], 1)] for n in p]
    step = max(1, len(g) // 40); g = g[::step] + ([g[-1]] if (len(g) - 1) % step else [])
    return g, round(sum(math.dist(u, v) for u, v in zip(g, g[1:])))

# Stand ohne Aarau herstellen
alt = {n["id"] for n in T["nodes"] if n["name"] == "Aarau" or (n["kind"] == "exit" and n.get("town") in ("Aarau", "Lenzburg") and n.get("ref") in ("540", "650"))}
T["nodes"] = [n for n in T["nodes"] if n["id"] not in alt]
T["edges"] = [e for e in T["edges"] if e["a"] not in alt and e["b"] not in alt]
N = {n["id"]: n for n in T["nodes"]}
# Nummern der alten Abgänge #36/#42 wiederverwenden: netz_lage nummeriert eigene Abzweige ab max+1 weiter (#43 steht in der Lage)
nid, nid_ost = 36, 42
ax, ay = xy(47.3914562, 8.0513072)                       # Bahnhofknoten Aarau (OSM 1569788470)
aarau = dict(name="Aarau", kind="station", x=ax, y=ay, id=nid, tracks=6)
ex, ey = xy(47.3983, 8.0980)                             # Abgang Ost (Wald vor Rupperswil)
ost = dict(name="Abgang 650", kind="exit", x=ex, y=ey, ref="650", town="Lenzburg", id=nid_ost)
T["nodes"] += [aarau, ost]
na = near(ax, ay); ne_ = near(ex, ey)
# 540 von Schönenwerd: Weg über Gleise mit ref 540 bis Aarau West (OSM taggt dort schon 650)
for (a, b, ref, tr) in ((11, None, "540", 2), (28, None, "650", 2)):
    g, L = weg(near(N[a]["x"], N[a]["y"]), na)
    T["edges"].append(dict(a=a, b=nid, ref=ref, tracks=tr, length=L, geom=g, refs=[ref]))
    print(f"Kante {N[a]['name']} #{a} – Aarau ({ref}): {L} m")
g, L = weg(na, ne_)
T["edges"].append(dict(a=nid, b=nid_ost, ref="650", tracks=4, length=L, geom=g, refs=["650"]))
print(f"Kante Aarau – Abgang 650 Lenzburg: {L} m")
xs = [n["x"] for n in T["nodes"]]; ys = [n["y"] for n in T["nodes"]]
T["bbox"] = [min(xs), min(ys), max(xs), max(ys)]
json.dump(T, open("olten_region_topologie.json", "w"), ensure_ascii=False)
print("Aarau #%d, Abgang Ost #%d" % (nid, nid_ost))

# OSM der Region um Aarau erweitert (eigene Datei; region.json bleibt Bezug der Topologie)
ids = {(e["type"], e["id"]) for e in R}
neu = R + [e for e in el if (e["type"], e["id"]) not in ids]
json.dump({"elements": neu}, open("olten_region_osm.json", "w"), ensure_ascii=False)
la2 = [g["lat"] for e in neu if e["type"] == "way" for g in e["geometry"]]; lo2 = [g["lon"] for e in neu if e["type"] == "way" for g in e["geometry"]]
L2, O2 = (min(la2) + max(la2)) / 2, (min(lo2) + max(lo2)) / 2
vers = [round((LON0 - O2) * 111320 * math.cos(math.radians(L2)), 1), round((LAT0 - L2) * KY, 1)]
print("osm_versatz für olten_region_osm.json:", vers)
