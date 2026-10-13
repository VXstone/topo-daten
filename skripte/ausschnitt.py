"""
Ausschnitte aus der Schweiz-Datei schneiden – liefert dasselbe wie die bisherige Colab-Abfrage.

  python3 ausschnitt.py schweiz_bahn.json.gz kim.json kerzers=46.966,7.180,46.986,7.212 ins=46.997,7.090,47.015,7.122
  python3 ausschnitt.py schweiz_bahn.json.gz region.json --flach olten_region=47.25,7.75,47.45,8.05 --alles

bbox wie bei Overpass: Süd,West,Nord,Ost.
Standard-Filter = Colab-Abfrage:
  way[railway~"^(rail|platform)$"], way[public_transport=platform][train=yes],
  node[railway~"^(switch|buffer_stop|railway_crossing|station|halt)$"]
--alles   alle Elemente der Schweiz-Datei im Ausschnitt (auch Signale, Schmalspur, Tram …)
--flach   bei genau einem Ausschnitt die Overpass-Antwort direkt statt {name: …}
Ways werden wie bei Overpass vollständig ausgegeben, sobald sie den Ausschnitt schneiden.
"""
import gzip, json, sys

NODE_RW = {"switch", "buffer_stop", "railway_crossing", "station", "halt"}


def wie_colab(el):
    t = el.get("tags", {})
    if el["type"] == "node":
        return t.get("railway") in NODE_RW
    return t.get("railway") in ("rail", "platform") or (t.get("public_transport") == "platform" and t.get("train") == "yes")


def schneidet(geom, s, w, n, e):
    """Liegt ein Punkt im Rechteck oder schneidet ein Segment es (Liang-Barsky)?"""
    for g in geom:
        if s <= g["lat"] <= n and w <= g["lon"] <= e:
            return True
    for a, b in zip(geom, geom[1:]):
        x0, y0, dx, dy = a["lon"], a["lat"], b["lon"] - a["lon"], b["lat"] - a["lat"]
        t0, t1, ok = 0.0, 1.0, True
        for p, q in ((-dx, x0 - w), (dx, e - x0), (-dy, y0 - s), (dy, n - y0)):
            if p == 0:
                if q < 0: ok = False; break
                continue
            r = q / p
            if p < 0:
                if r > t1: ok = False; break
                t0 = max(t0, r)
            else:
                if r < t0: ok = False; break
                t1 = min(t1, r)
        if ok and t0 <= t1:
            return True
    return False


def ausschneiden(elemente, bbox, alles=False):
    s, w, n, e = bbox
    out = []
    for el in elemente:
        if not alles and not wie_colab(el):
            continue
        if el["type"] == "node":
            if s <= el["lat"] <= n and w <= el["lon"] <= e:
                out.append(el)
        else:
            b = el["bounds"]
            if b["maxlat"] < s or b["minlat"] > n or b["maxlon"] < w or b["minlon"] > e:
                continue
            if schneidet(el["geometry"], s, w, n, e):
                out.append(el)
    return out


def main(argv):
    src, dst = argv[0], argv[1]
    alles, flach = "--alles" in argv, "--flach" in argv
    auftraege = {}
    for a in argv[2:]:
        if a.startswith("--"): continue
        name, bb = a.split("=", 1)
        auftraege[name] = [float(v) for v in bb.split(",")]
    op = gzip.open if src.endswith(".gz") else open
    with op(src, "rt", encoding="utf-8") as f:
        daten = json.load(f)
    kopf = {k: v for k, v in daten.items() if k != "elements"}
    erg = {}
    for name, bb in auftraege.items():
        el = ausschneiden(daten["elements"], bb, alles)
        erg[name] = dict(kopf, elements=el)
        print(f"{name}: {len(el)} Elemente")
    res = erg[next(iter(erg))] if (flach and len(erg) == 1) else erg
    json.dump(res, open(dst, "w"), ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
