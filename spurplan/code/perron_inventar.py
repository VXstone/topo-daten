"""Perron-Inventar (Schritt P «Verbundene Perrons», Entscheid D. Eckenstein 8.11.2026, Teil 1 – nur messen, nichts zeichnen).

  python3 perron_inventar.py <schweiz_bahn.json.gz> <perronoberflache.geojson.gz> <ausgabe.json> [<bahnhof> ...]

Je Perronfläche (OSM railway=platform / public_transport=platform, Bushalte ausgenommen) im Umkreis des Bahnhofs:
  - bediente Gleiskanten: Gleisstücke, die auf ≥ 15 m Länge höchstens «kante_m» (3,5 m) neben dem Perronrand laufen,
    mit Gleisnummer (railway:track_ref), Seite gegenüber der Längsachse des Perrons (links/rechts) und Länge;
  - Kopfkanten: Gleisenden (Prellbock oder offenes Way-Ende) höchstens 6 m vor dem Perronrand, Gleis etwa quer zum
    Rand (Querperron, «über Eck»);
  - verbunden: andere Perronflächen, die diese berühren (≤ 1 m) – zusammenhängende Perronanlage.
Form (Vorschlag, für die Tabelle an Daniel): Seitenperron (eine Seite), Mittelperron (zwei Gleise, je eine Seite),
beidseitig (dasselbe Gleis auf beiden Seiten oder ≥ 2 Gleise auf einer Seite), über Eck (Längskante + Kopfkante:
L, zwei Längskanten + Kopfkante: U), verbunden (Teil einer zusammenhängenden Anlage).
Dazu die SBB-Einträge (perronoberflache: p_nr, perrontyp, Länge) des Betriebspunkts.
"""
import json, gzip, math, sys, collections, unicodedata
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union

BAHNHOEFE = {     # Name: (lat, lon, Radius m, SBB-Name)
    "Montreux": (46.4353, 6.9104, 450, "Montreux"),
    "Zweisimmen": (46.5550, 7.3772, 450, "Zweisimmen"),
    "Thun": (46.7547, 7.6297, 700, "Thun"),
    "Bern": (46.9490, 7.4380, 800, "Bern"),
    "Basel SBB": (47.5475, 7.5895, 900, "Basel SBB"),
    "Aarau": (47.3914, 8.0513, 450, "Aarau"),
}
KANTE_M, KOPF_M, MIN_LAUF = 3.5, 6.0, 15.0

def norm(t): return "".join(c for c in unicodedata.normalize("NFKD", t or "") if not unicodedata.combining(c)).lower().replace("-", "").replace(" ", "")

def inventar(EL, SBB, name, lat0, lon0, rad, sbb_name):
    kx = 111320 * math.cos(math.radians(lat0)); ky = 110540
    xy = lambda g: ((g["lon"] - lon0) * kx, (g["lat"] - lat0) * ky)
    nah = lambda geo: any(math.hypot(*xy(g)) < rad for g in geo)
    ways = [e for e in EL if e["type"] == "way" and e.get("geometry") and nah(e["geometry"])]
    btag = {e["id"]: e.get("tags", {}) for e in EL if e["type"] == "node" and math.hypot((e["lon"] - lon0) * kx, (e["lat"] - lat0) * ky) < rad + 200}
    gleise = [w for w in ways if w["tags"].get("railway") in ("rail", "narrow_gauge", "light_rail") and not w["tags"].get("disused")]
    grad = collections.Counter(n for w in gleise for n in (w["nodes"][0], w["nodes"][-1]))
    innen = collections.Counter(n for w in gleise for n in w["nodes"][1:-1])
    perr = []
    for w in ways:
        t = w["tags"]
        if not (t.get("railway") == "platform" or t.get("public_transport") == "platform"): continue
        if t.get("highway") == "platform" and t.get("railway") != "platform": continue          # Bushalt
        if t.get("disused") == "yes" or "disused:public_transport" in t: continue
        pts = [xy(g) for g in w["geometry"]]
        geo = Polygon(pts) if len(pts) >= 4 and w["nodes"][0] == w["nodes"][-1] else LineString(pts).buffer(1.5)
        if not geo.is_valid: geo = geo.buffer(0)
        perr.append(dict(id=w["id"], ref=t.get("ref") or t.get("railway:platform_ref") or t.get("local_ref"), geo=geo,
                         spur=t.get("gauge") or ("1000" if t.get("railway:gauge") == "1000" else None)))
    # Gleisstücke (Segment für Segment) und ihre Nummer
    seg = []
    for w in gleise:
        p = [xy(g) for g in w["geometry"]]
        for a, b in zip(p, p[1:]): seg.append((w, LineString([a, b])))
    aus = []
    for P in perr:
        mrr = P["geo"].minimum_rotated_rectangle
        c = list(mrr.exterior.coords)[:4]
        e1 = (c[1][0] - c[0][0], c[1][1] - c[0][1]); e2 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
        u = e1 if math.hypot(*e1) >= math.hypot(*e2) else e2; L_ = math.hypot(*u); u = (u[0] / L_, u[1] / L_)
        n = (-u[1], u[0]); cx, cy = P["geo"].centroid.x, P["geo"].centroid.y
        rand = P["geo"].boundary
        # Mittellinie (gebogene Perrons, Bern/Basel): je 5 m quer zur Längsachse schneiden, Mitte der Schnittstrecke
        mitte = []
        for t_ in [x * 5.0 for x in range(int(-L_ / 10) - 1, int(L_ / 10) + 2)]:
            ox, oy = cx + u[0] * t_, cy + u[1] * t_
            q_ = LineString([(ox - n[0] * 60, oy - n[1] * 60), (ox + n[0] * 60, oy + n[1] * 60)]).intersection(P["geo"])
            if not q_.is_empty and q_.length > 0.5: mitte.append((q_.centroid.x, q_.centroid.y))
        ML = LineString(mitte) if len(mitte) >= 2 else LineString([(cx - u[0] * L_ / 2, cy - u[1] * L_ / 2), (cx + u[0] * L_ / 2, cy + u[1] * L_ / 2)])
        def seite(pt):
            d_ = ML.project(pt); a_ = ML.interpolate(max(0, d_ - 2)); b_ = ML.interpolate(min(ML.length, d_ + 2)); c_ = ML.interpolate(d_)
            return (b_.x - a_.x) * (pt.y - c_.y) - (b_.y - a_.y) * (pt.x - c_.x)
        kanten = collections.defaultdict(lambda: dict(l=0.0, d=[]))
        for w, s in seg:
            if s.distance(rand) > KANTE_M: continue
            stueck = s.intersection(rand.buffer(KANTE_M)).difference(P["geo"].buffer(-0.3))
            if stueck.is_empty or stueck.length < 1: continue
            m = stueck.interpolate(0.5, normalized=True)
            q = seite(m)
            sx, sy = s.coords[1][0] - s.coords[0][0], s.coords[1][1] - s.coords[0][1]
            _d = ML.project(m); _a = ML.interpolate(max(0, _d - 3)); _b = ML.interpolate(min(ML.length, _d + 3))
            _t = (_b.x - _a.x, _b.y - _a.y); _tl = max(1e-9, math.hypot(*_t))
            par = abs(sx * _t[0] + sy * _t[1]) / max(1e-9, math.hypot(sx, sy)) / _tl
            if par < 0.8: continue                                      # quer laufende Stücke: siehe Kopfkanten
            k = (w["tags"].get("railway:track_ref") or f"(way {w['id']})", "links" if q > 0 else "rechts")
            kanten[k]["l"] += stueck.length
            kanten[k]["spur"] = w["tags"].get("gauge", "1435"); kanten[k]["service"] = w["tags"].get("service")
        kl = [dict(gleis=g, seite=sd, laenge=round(v["l"]), spur=v["spur"], service=v["service"]) for (g, sd), v in kanten.items() if v["l"] >= MIN_LAUF]
        kopf = []
        for w in gleise:
            for i_ in (0, -1):
                nd = w["nodes"][i_]
                if grad[nd] != 1 or innen[nd]: continue
                pe = Point(xy(w["geometry"][i_]))
                if pe.distance(P["geo"]) > KOPF_M: continue
                q2 = w["geometry"][1 if i_ == 0 else -2]; v = (xy(q2)[0] - pe.x, xy(q2)[1] - pe.y)
                par = abs(v[0] * u[0] + v[1] * u[1]) / max(1e-9, math.hypot(*v))
                ende = (pe.x - cx) * u[0] + (pe.y - cy) * u[1]
                kopf.append(dict(gleis=w["tags"].get("railway:track_ref") or f"(way {w['id']})", prellbock=btag.get(nd, {}).get("railway") == "buffer_stop",
                                 abstand=round(pe.distance(P["geo"]), 1), ende="Stirnseite" if abs(ende) > 0.35 * L_ else "Längsseite", laengs=round(par, 2)))
        aus.append(dict(osm=P["id"], ref=P["ref"], laenge=round(L_), kanten=sorted(kl, key=lambda k: (k["seite"], str(k["gleis"]))), kopf=kopf))
    # verbundene Perrons
    for a in aus:
        ga = next(P["geo"] for P in perr if P["id"] == a["osm"])
        a["verbunden"] = [b["ref"] or f"(way {b['osm']})" for b in aus if b is not a and ga.distance(next(P["geo"] for P in perr if P["id"] == b["osm"])) <= 1.0]
    # Form vorschlagen
    for a in aus:
        seiten = collections.defaultdict(set)
        for k in a["kanten"]:
            if k["service"] in ("yard", "spur") and k["gleis"].startswith("(way"): continue
            seiten[k["seite"]].add(k["gleis"])
        alle = [g for s in seiten.values() for g in s]
        stirn = [k for k in a["kopf"] if k["ende"] == "Stirnseite"]
        if not alle and not a["kopf"]: f = "ohne Gleis"
        elif len(seiten) == 2 and set(seiten["links"]) & set(seiten["rechts"]): f = "beidseitig (dasselbe Gleis)"
        elif len(seiten) == 2: f = "Mittelperron"
        elif len(alle) >= 2: f = "eine Seite, mehrere Gleise"
        elif alle: f = "Seitenperron"
        else: f = "nur Kopf"
        if stirn: f += (" + Kopfkante (U)" if len(seiten) == 2 else " + Kopfkante (L)")
        elif a["kopf"]: f += " + Stumpen an der Längsseite"
        if a["verbunden"]: f += " · verbunden"
        a["form"] = f
    sbb = [dict(p_nr=f["properties"]["p_nr"], typ=f["properties"]["perrontyp"], laenge=f["properties"]["p_lange"])
           for f in SBB if norm(f["properties"].get("bps_name")) == norm(sbb_name)]
    return dict(bahnhof=name, perrons=aus, sbb=sorted(sbb, key=lambda s: str(s["p_nr"])))

if __name__ == "__main__":
    EL = json.load(gzip.open(sys.argv[1])); EL = EL["elements"] if isinstance(EL, dict) else EL
    SBB = json.load(gzip.open(sys.argv[2]))["features"]
    wahl = sys.argv[4:] or list(BAHNHOEFE)
    res = [inventar(EL, SBB, b, *BAHNHOEFE[b]) for b in wahl]
    json.dump(res, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
    for r in res:
        print(f"\n== {r['bahnhof']}  ({len(r['perrons'])} OSM-Perrons, {len(r['sbb'])} SBB-Einträge)")
        for a in sorted(r["perrons"], key=lambda a: str(a["ref"])):
            k_ = "; ".join(f"{k['gleis']} {k['seite']} {k['laenge']} m" for k in a["kanten"])
            kk = "; ".join(f"Kopf {k['gleis']} ({k['ende']}{', Prellbock' if k['prellbock'] else ''})" for k in a["kopf"])
            print(f"  {str(a['ref']):10} {a['laenge']:4} m  {a['form']:45}  {k_}  {kk}  {'verb.: ' + ','.join(map(str, a['verbunden'])) if a['verbunden'] else ''}")
        print("  SBB:", ", ".join(f"{s['p_nr']} {s['typ']} {s['laenge']}" for s in r["sbb"]))
