"""Perronkanten (SBB BehiG-Haltekantenpunkte, Datensatz 21196_behig-haltekantepunkt) zu je einer Kante verdichten.

python3 perronkanten.py <eingang/perronkante.geojson> <aus/perronkanten.json>
Der Datensatz hat einen Punkt pro Meter Kante (~500 000 Punkte). Je perronkante_fid entsteht ein Eintrag:
{bps, abk, gleis (kundengleisnr), laenge, linie, lat/lon von Anfang, Mitte, Ende}. Damit sind Gleisnummer und Lage jeder
Perronkante bekannt (Quelle für Gleisnummern: SBB vor OSM, Regel 20.10.2026).
"""
import sys, json, math, collections


def lv95_zu_wgs84(e, n):
    """swisstopo-Näherungsformel LV95 -> WGS84 (Genauigkeit ~1 m)."""
    y = (e - 2600000) / 1e6; x = (n - 1200000) / 1e6
    lon = 2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x * x - 0.0436 * y ** 3
    lat = 16.9023892 + 3.238272 * x - 0.270978 * y * y - 0.002528 * x * x - 0.0447 * y * y * x - 0.0140 * x ** 3
    return lat * 100 / 36, lon * 100 / 36


ein, aus = sys.argv[1], sys.argv[2]
fs = json.load(open(ein))["features"]
K = collections.defaultdict(list)
for f in fs:
    p = f.get("properties") or {}
    k = p.get("perronkante_fid") or p.get("haltekante_fid")
    if k is None: continue
    if p.get("e") and p.get("n"): q = lv95_zu_wgs84(float(p["e"]), float(p["n"]))
    elif (f.get("geometry") or {}).get("type") == "Point": q = tuple(f["geometry"]["coordinates"][::-1])
    else: continue
    K[k].append((p.get("punkt_stationierung") or 0, q, p))
out = []
for k, pts in K.items():
    pts.sort(key=lambda t: t[0]); p0 = pts[0][2]
    a, m, b = pts[0][1], pts[len(pts) // 2][1], pts[-1][1]
    out.append(dict(id=int(k), bps=p0.get("bps"), abk=p0.get("bps_abk"), gleis=p0.get("kundengleisnr"),
                    laenge=round(p0.get("perronkante_laenge") or p0.get("haltekante_laenge") or 0, 1), linie=p0.get("linie"),
                    anfang=[round(a[0], 6), round(a[1], 6)], mitte=[round(m[0], 6), round(m[1], 6)], ende=[round(b[0], 6), round(b[1], 6)]))
out.sort(key=lambda x: (x["bps"] or "", str(x["gleis"])))
json.dump(out, open(aus, "w"), ensure_ascii=False)
print(len(out), "Perronkanten,", len({x["bps"] for x in out}), "Betriebspunkte")
