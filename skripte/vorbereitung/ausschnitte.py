"""Ausschnitte für das Zeichnen: je Region (Vieleck aus konfig/regionen.json) und je Betriebspunkt (Kreis).

python3 ausschnitte.py <schweiz_bahn.json.gz> <betriebspunkte.json> <regionen.json> <ausgabeordner>
Ergebnis:
  region_<key>.json.gz        alle Bahnelemente im Vieleck (+ 2 km Rand), Overpass-Format
  bahnhoefe_<key>.zip         je Betriebspunkt <slug>_roh.json (Kreis 2,5 km) und <slug>.json (Kreis Radius, Ways an
                              der Grenze geteilt wie cut.py); genau ein Stationsknoten (railway=station), bei fehlendem
                              OSM-Knoten der Ersatzknoten auf dem Hauptgleis (Onnens-Bonvillars)
  bahnhoefe_<key>.json        Liste: slug, name, radius, Stationsknoten, synthetisch
Radius: 1300 m, Personenbahnhöfe mit > 4 Perronkanten 1600 m (grosse Knoten von Hand nachziehen).
"""
import sys, json, gzip, math, re, unicodedata, zipfile, io
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from gemeinsam import lade_osm, m

src, bpf, regf, aus = sys.argv[1:5]
E = lade_osm(src); BP = json.load(open(bpf)); REG = json.load(open(regf))
def slug(n):
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", n).strip("_")
def keep(e):
    t = e.get("tags", {})
    if e["type"] == "node": return t.get("railway") in ("switch", "buffer_stop", "railway_crossing", "station", "halt")
    return "geometry" in e and (t.get("railway") in ("rail", "platform", "narrow_gauge") or (t.get("public_transport") == "platform" and t.get("train") == "yes"))
E = [e for e in E if keep(e)]

def im_vieleck(la, lo, V):
    c = False; n = len(V)
    for i in range(n):
        (a1, o1), (a2, o2) = V[i], V[(i + 1) % n]
        if (o1 > lo) != (o2 > lo) and la < (a2 - a1) * (lo - o1) / (o2 - o1 + 1e-12) + a1: c = not c
    return c
def nahe_vieleck(la, lo, V, rand_m=2000):
    if im_vieleck(la, lo, V): return True
    return min(m((la, lo), p) for p in V) < rand_m * 3        # grob: Eckpunkte (Rand wird beim Zeichnen geschnitten)

def kreis(st_la, st_lo, R, els):
    kx = 111320 * math.cos(math.radians(st_la))
    inside = lambda g: math.hypot((g["lon"] - st_lo) * kx, (g["lat"] - st_la) * 110540) <= R
    out = []
    for e in els:
        if e["type"] == "node":
            if inside(e): out.append(e)
            continue
        runs, cur = [], []
        for n, g in zip(e["nodes"], e["geometry"]):
            if inside(g): cur.append((n, g))
            elif cur: runs.append(cur); cur = []
        if cur: runs.append(cur)
        for k, r in enumerate(runs):
            if len(r) < 2: continue
            w = dict(e); w["id"] = e["id"] if k == 0 else e["id"] * 100 + k
            w["nodes"] = [n for n, _ in r]; w["geometry"] = [g for _, g in r]; out.append(w)
    return out

for key, R in REG.items():
    V = R["vieleck"]
    reg = [e for e in E if (e["type"] == "node" and nahe_vieleck(e["lat"], e["lon"], V))
           or (e["type"] == "way" and any(nahe_vieleck(g["lat"], g["lon"], V) for g in e["geometry"][::5] + e["geometry"][-1:]))]
    with gzip.open(f"{aus}/region_{key}.json.gz", "wt", encoding="utf-8") as f: json.dump({"elements": reg}, f)
    liste = []; zbuf = io.BytesIO(); z = zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED)
    gesehen = set()
    for b in sorted(BP, key=lambda x: not x.get("osm_node")):        # mit OSM-Stationsknoten zuerst, Namensdubletten weg
        if not im_vieleck(b["lat"], b["lon"], V) or slug(b["name"]) in gesehen: continue
        gesehen.add(slug(b["name"]))
        nid = b.get("osm_node") or b.get("synthetisch_node")
        if not nid: continue
        roh = []
        for e in reg:
            if e["type"] == "node" and e.get("tags", {}).get("railway") in ("station", "halt"): continue   # nur der eigene Knoten
            if e["type"] == "node" and m((e["lat"], e["lon"]), (b["lat"], b["lon"])) > 2500: continue
            if e["type"] == "way" and min(m((g["lat"], g["lon"]), (b["lat"], b["lon"])) for g in e["geometry"]) > 2500: continue
            roh.append(e)
        # Stationsknoten: OSM-Knoten oder Ersatz auf dem Hauptgleis
        pos = next(((g["lat"], g["lon"]) for e in roh if e["type"] == "way" for n, g in zip(e["nodes"], e["geometry"]) if n == nid), (b["lat"], b["lon"]))
        roh.append(dict(type="node", id=nid, lat=pos[0], lon=pos[1], tags=dict(railway="station", name=b["name"],
                        **({"_hinweis": "synthetisch: OSM ohne Stationsknoten"} if not b.get("osm_node") else {}))))
        rad = 1600 if b.get("personenverkehr") and b.get("typ") in ("Bahnhof", "station") else 1300
        s = slug(b["name"])
        z.writestr(f"{s}_roh.json", json.dumps({"elements": roh}))
        z.writestr(f"{s}.json", json.dumps({"elements": kreis(pos[0], pos[1], rad, roh)}))
        liste.append(dict(slug=s, name=b["name"], radius=rad, station_node=nid, synthetisch=not b.get("osm_node"), typ=b.get("typ")))
    z.close(); open(f"{aus}/bahnhoefe_{key}.zip", "wb").write(zbuf.getvalue())
    json.dump(liste, open(f"{aus}/bahnhoefe_{key}.json", "w"), ensure_ascii=False, indent=0)
    print(key, len(reg), "Elemente,", len(liste), "Betriebspunkte")
