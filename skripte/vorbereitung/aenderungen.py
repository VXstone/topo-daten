"""Änderungen im OSM-Abzug gegenüber dem Vormonat, je Betriebspunkt (welche Spurpläne neu zeichnen?).

python3 aenderungen.py <vorher.json.gz> <jetzt.json.gz> <betriebspunkte.json> <aus.json>
Verglichen werden Bahn-Ways (Knotenfolge, railway/service/usage/track_ref/gauge/ref) und Weichen-/Prellbockknoten.
Jede Änderung wird dem nächsten Betriebspunkt (< 2 km) zugeordnet, sonst "freie Strecke".
"""
import sys, json, hashlib
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from gemeinsam import lade_osm, m

alt, neu, bpf, aus = sys.argv[1:5]
BP = json.load(open(bpf))
TAGS = ("railway", "service", "usage", "railway:track_ref", "gauge", "ref", "disused", "bridge", "tunnel")
def sig(e):
    t = e.get("tags", {})
    if e["type"] == "way": return hashlib.md5(json.dumps([e["nodes"], [t.get(k) for k in TAGS]]).encode()).hexdigest()
    return hashlib.md5(json.dumps([round(e["lat"], 6), round(e["lon"], 6), t.get("railway"), t.get("railway:switch")]).encode()).hexdigest()
def lage(e):
    if e["type"] == "node": return (e["lat"], e["lon"])
    g = e["geometry"][len(e["geometry"]) // 2]; return (g["lat"], g["lon"])
def relevant(e):
    t = e.get("tags", {})
    return (e["type"] == "way" and "geometry" in e and t.get("railway") in ("rail", "platform")) or \
           (e["type"] == "node" and t.get("railway") in ("switch", "buffer_stop", "station", "halt"))
A = {(e["type"], e["id"]): e for e in lade_osm(alt) if relevant(e)}
B = {(e["type"], e["id"]): e for e in lade_osm(neu) if relevant(e)}
res = {}
for k in set(A) | set(B):
    a, b = A.get(k), B.get(k)
    if a and b and sig(a) == sig(b): continue
    art = "neu" if not a else "weg" if not b else "geändert"
    q = lage(b or a)
    near = min(BP, key=lambda x: m((x["lat"], x["lon"]), q)) if BP else None
    nm = near["name"] if near and m((near["lat"], near["lon"]), q) < 2000 else "freie Strecke"
    r = res.setdefault(nm, {"neu": 0, "weg": 0, "geändert": 0, "beispiele": []})
    r[art] += 1
    if len(r["beispiele"]) < 5: r["beispiele"].append(f"{k[0]} {k[1]} {art}")
json.dump(dict(sorted(res.items(), key=lambda t: -(t[1]["neu"] + t[1]["weg"] + t[1]["geändert"]))), open(aus, "w"), ensure_ascii=False, indent=1)
print(len(res), "Betriebspunkte mit Änderungen")
