"""Betriebspunkte = Liste aller Bahnhöfe/Betriebspunkte, für die ein Spurplan nötig ist.
Regel (D. Eckenstein 20.10.2026): alles mit einem SBB-Betriebspunkt (Bahnhof, Haltestelle, Kreuzungs-/Dienststation,
Abzweigstelle) bekommt einen eigenen Plan; reine Anschlussgleise bleiben Nebengleise auf der freien Strecke.

python3 betriebspunkte.py <eingang> <aus.json>
Quellen: SBB "linie-mit-betriebspunkten" (alle Betriebspunkte mit Lage), SBB "perronoberflache" (Personenverkehr),
OSM railway=station/halt (auch Privatbahnen: BLS, TPF, …). Abgleich über Lage (< 600 m) und Namen.
Ausgabe je Punkt: name, abk, typ, lat, lon, quellen, osm_node (Stationsknoten oder null), personenverkehr,
synthetisch_node (Knoten auf dem Hauptgleis, wenn OSM keinen Stationsknoten hat; z. B. Onnens-Bonvillars).
"""
import sys, json, math, collections
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from gemeinsam import lade_osm, lade_geojson, feld, punkt, m, normalspur, name_gleich

ein, aus = sys.argv[1], sys.argv[2]
E = lade_osm(f"{ein}/schweiz_bahn.json.gz")
# Normalspur-Knoten für Lage-Abgleich (Raster 0.01°)
raster = collections.defaultdict(list)
haupt = collections.defaultdict(list)
for e in E:
    if not normalspur(e): continue
    for n, g in zip(e["nodes"], e["geometry"]):
        k = (round(g["lat"], 2), round(g["lon"], 2)); raster[k].append((g["lat"], g["lon"]))
        if not e["tags"].get("service"): haupt[k].append((n, g["lat"], g["lon"], e["tags"].get("usage")))
def naechst(la, lo, tab, r=600):
    best = None
    for dk in ((0, 0), (0.01, 0), (-0.01, 0), (0, 0.01), (0, -0.01), (0.01, 0.01), (-0.01, -0.01), (0.01, -0.01), (-0.01, 0.01)):
        for x in tab.get((round(la + dk[0], 2), round(lo + dk[1], 2)), []):
            d = m((la, lo), (x[-3], x[-2]) if len(x) == 4 else x)
            if d < r and (best is None or d < best[0]): best = (d, x)
    return best

punkte = []
# 1) SBB Betriebspunkte
bp = lade_geojson(f"{ein}/betriebspunkte.geojson")
for f in bp:
    p = f.get("properties", {})
    k_n = feld(p, "bezeichnung", "name", ausser=("linie", "strecke")); k_a = feld(p, "abk", "kurz"); k_t = feld(p, "typ", "art")
    q = punkt(f.get("geometry")) or (lambda g: (g["lat"], g["lon"]) if isinstance(g, dict) else None)(p.get(feld(p, "geo") or "", None))
    if not q or not p.get(k_n): continue
    punkte.append(dict(name=p.get(k_n), abk=p.get(k_a), typ=p.get(k_t), lat=q[0], lon=q[1], quellen=["SBB-Betriebspunkt"]))
# doppelte (ein Betriebspunkt auf mehreren Linien) zusammenfassen
uniq = {}
for x in punkte:
    k = (x["abk"] or x["name"])
    if k in uniq: continue
    uniq[k] = x
punkte = list(uniq.values())
# 2) Perrons SBB -> Personenverkehr
for f in lade_geojson(f"{ein}/perronoberflache.geojson"):
    p = f["properties"]; q = punkt(f.get("geometry")); nm = p.get("bps_name")
    if not q or not nm: continue
    t = [x for x in punkte if m((x["lat"], x["lon"]), q) < 800 and name_gleich(x["name"], nm)]
    if t: t[0]["personenverkehr"] = True
    elif not any(x["name"] == nm for x in punkte):
        punkte.append(dict(name=nm, abk=p.get("bps"), typ="Haltestelle", lat=q[0], lon=q[1], quellen=["SBB-Perron"], personenverkehr=True))
# 3) OSM-Stationen (auch Privatbahnen)
osm_st = [e for e in E if e.get("type") == "node" and e.get("tags", {}).get("railway") in ("station", "halt")
          and e["tags"].get("station") not in ("funicular", "subway", "light_rail")]
for e in osm_st:
    if not naechst(e["lat"], e["lon"], raster, 40): continue          # nur an Normalspur
    nm = e["tags"].get("name")
    t = [x for x in punkte if m((x["lat"], x["lon"]), (e["lat"], e["lon"])) < 600 and name_gleich(x["name"], nm)]
    if t:
        t[0]["osm_node"] = e["id"]; t[0]["quellen"].append("OSM")
    else:
        punkte.append(dict(name=nm, abk=None, typ=e["tags"]["railway"], lat=e["lat"], lon=e["lon"], quellen=["OSM"], osm_node=e["id"],
                           personenverkehr=e["tags"].get("railway") == "halt" or e["tags"].get("public_transport") == "station"))
# 4) Punkte ohne OSM-Stationsknoten: Knoten auf dem Hauptgleis als Ersatz (Onnens-Bonvillars, Abzweigstellen)
for x in punkte:
    x.setdefault("osm_node", None); x.setdefault("personenverkehr", False)
    if x["osm_node"] is None:
        b = naechst(x["lat"], x["lon"], haupt, 300)
        x["synthetisch_node"] = b[1][0] if b else None
        x["ohne_gleis"] = b is None              # liegt nicht an einer Normalspur (z. B. Meterspur, Bus)
punkte = [x for x in punkte if not x.get("ohne_gleis")]
json.dump(punkte, open(aus, "w"), ensure_ascii=False, indent=0)
c = collections.Counter(tuple(sorted(set(x["quellen"]))) for x in punkte)
print(len(punkte), "Betriebspunkte;", dict(c), "; ohne OSM-Stationsknoten:", sum(1 for x in punkte if not x["osm_node"]))
