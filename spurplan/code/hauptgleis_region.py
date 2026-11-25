"""HT auf den Regionalplänen (Schritt HT-R, Entscheid D. Eckenstein 25.11.2026: «HT auch auf den Regionalplänen – Gleise auf
OSM-Ways zurückführen, jede Linie kommt mit Pfeil an, Kreuzung nur mit OSM-Grund»; Testfall Region SZU: 713 über das Depot
Giesshübel, 717 fehlt). REGELN 0.1 und Kopf «HT».

Ein Regionalplan besteht aus den Bahnhofsgruppen (<g data-st=… transform=…>, Inhalt = Bahnhofplan bare) und den Linien der
Region dazwischen (Strecken, Abgänge, Spurwechsel auf freier Strecke). Gemessen wird nur, was der Regionalplan selbst zeichnet –
der Inhalt der Bahnhofsgruppen ist im Bahnhofplan schon mit HT1–HT5 gemessen (REGELN 4.x «Regionalplan wie Bahnhofplan»).

  HT6  Linie kommt nicht an: ein Abgang eines Bahnhofs (Netzmodell «abgaenge», Liniennummer) hat im Regionalplan keine
       Fortsetzung – weder eine Strecke zum Nachbarbahnhof noch einen Pfeil/Abgang mit Beschriftung (Giesshübel 717, v185).
       Ebenso ein Linienende der Region, das weder an einem Abgang, an einer anderen Linie noch an einer Beschriftung endet.
  HT7  Kreuzung ohne OSM-Grund: eine Linie der Region schneidet ein gezeichnetes Gleis (Bahnhofsgruppe oder andere Linie),
       und die OSM-Ways der beiden (Linie: Weg im OSM-Netz zwischen ihren Abgängen; Gleis: Way aus dem Netzmodell) kreuzen sich
       nicht (Giesshübel: 713 nach Binz durch das Depot, v185). Echte Kreuzungen (Niveau oder Brücke) bleiben erlaubt.

Zuordnung Plan → OSM («Gleise auf OSM-Ways zurückführen»): Abgang = Netzmodell-Abgang (way, knoten, ll) des Bahnhofs, in die
Regionlage transformiert; Linie = gezeichneter Pfad, dessen Enden an Abgängen liegen; ihr OSM-Weg ist der kürzeste Weg im
OSM-Gleisnetz zwischen den Abgangs-Knoten (nur Ways ohne service, falls möglich), sonst die Abgangs-Ways selbst.
"""
import collections, json, math, os, re, sys
import numpy as np
from shapely.geometry import LineString, Point, MultiLineString
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

TRACK_COL = {"#00862f", "#111", "#111111", "#8b5a2b", "#7a4a1e", "#9b6a3c", "#a0522d"}
NICHT_COL = {"#fff", "#ffffff", "#8a8a8a", "#888"}
TOL_PORT = 4.0        # px Regionalplan: Linienende am Abgang
TOL_END = 6.0         # px: Kreuzung so nah an einem Ende zählt als Anschluss, nicht als Kreuzung


# ---------------------------------------------------------------- SVG lesen
def _num(s): return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", s)]


def pfad_linien(d, schritt=6):
    """d-Attribut (M/L/H/V/Q/C, absolut) -> Liste von Polylinien [(x,y), …]; Kurven grob abgetastet"""
    out, cur, p = [], [], None
    for cmd, arg in re.findall(r"([MLHVQCZmlhvqcz])([^MLHVQCZmlhvqcz]*)", d):
        a = _num(arg)
        if cmd == "M":
            if len(cur) > 1: out.append(cur)
            p = (a[0], a[1]); cur = [p]
            for i in range(2, len(a) - 1, 2): p = (a[i], a[i + 1]); cur.append(p)
        elif cmd == "L":
            for i in range(0, len(a) - 1, 2): p = (a[i], a[i + 1]); cur.append(p)
        elif cmd == "H":
            for v in a: p = (v, p[1]); cur.append(p)
        elif cmd == "V":
            for v in a: p = (p[0], v); cur.append(p)
        elif cmd == "Q":
            for i in range(0, len(a) - 3, 4):
                c, e = (a[i], a[i + 1]), (a[i + 2], a[i + 3])
                for t in np.linspace(0, 1, schritt)[1:]:
                    cur.append(((1 - t) ** 2 * p[0] + 2 * (1 - t) * t * c[0] + t * t * e[0], (1 - t) ** 2 * p[1] + 2 * (1 - t) * t * c[1] + t * t * e[1]))
                p = e
        elif cmd == "C":
            for i in range(0, len(a) - 5, 6):
                c1, c2, e = (a[i], a[i + 1]), (a[i + 2], a[i + 3]), (a[i + 4], a[i + 5])
                for t in np.linspace(0, 1, schritt)[1:]:
                    u = 1 - t
                    cur.append((u ** 3 * p[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * e[0],
                                u ** 3 * p[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * e[1]))
                p = e
        elif cmd in "Zz" and cur:
            cur.append(cur[0])
    if len(cur) > 1: out.append(cur)
    return out


def _matrix(tr):
    """SVG transform (translate/rotate/scale, von links nach rechts) -> 3x3"""
    M = np.eye(3)
    for f, arg in re.findall(r"(translate|rotate|scale)\(([^)]*)\)", tr):
        a = _num(arg)
        if f == "translate": T = np.array([[1, 0, a[0]], [0, 1, a[1] if len(a) > 1 else 0], [0, 0, 1]])
        elif f == "scale": T = np.array([[a[0], 0, 0], [0, a[1] if len(a) > 1 else a[0], 0], [0, 0, 1]])
        else:
            r = math.radians(a[0]); c, s = math.cos(r), math.sin(r); T = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        M = M @ T
    return M


def _tf(M, p): q = M @ np.array([p[0], p[1], 1.0]); return (float(q[0]), float(q[1]))


def _attr(t, k):
    m = re.search(r'\b%s="([^"]*)"' % k, t); return m.group(1) if m else None


def _ist_gleis(tag):
    col = (_attr(tag, "stroke") or "").lower(); w = float(_attr(tag, "stroke-width") or 0)
    if not col or col in NICHT_COL or col == "none": return False
    if _attr(tag, "stroke-opacity") or _attr(tag, "data-pfeil") is not None: return False
    if (_attr(tag, "fill") or "none") not in ("none", ""): return False
    return True, w


def _gruppen_teilen(svg):
    """Bahnhofsgruppen <g data-st=…> mit verschachtelten <g> -> [(st, transform, body)], Rest-SVG"""
    out, rest, i = [], [], 0
    for m in re.finditer(r'<g data-st="([^"]+)"[^>]*?transform="([^"]+)"[^>]*>', svg):
        if m.start() < i: continue
        rest.append(svg[i:m.start()]); tiefe, j = 1, m.end()
        for t in re.finditer(r"<g\b|</g>", svg[m.end():]):
            tiefe += 1 if t.group(0) == "<g" else -1
            if tiefe == 0: j = m.end() + t.start(); break
        out.append((m.group(1), m.group(2), svg[m.end():j])); i = j + 4
    rest.append(svg[i:])
    return out, "".join(rest)


def lesen(svg):
    """-> gruppen {st: dict(M, linien[(poly, way?)])}, linien der Region [(poly, col, w)], texte [(x, y, text)]"""
    gruppen = {}; G_, rest = _gruppen_teilen(svg)
    for st, tr, body in G_:
        M = _matrix(tr)
        L = []
        for pm in re.finditer(r"<path\b[^>]*>", body):
            t = pm.group(0); g = _ist_gleis(t); d = _attr(t, "d")
            if not g or not d: continue
            col = (_attr(t, "stroke") or "").lower()
            if col not in ("#00862f", "#111", "#111111") and not col.startswith("#8") and not col.startswith("#7") and not col.startswith("#9"): continue
            for poly in pfad_linien(d): L.append([_tf(M, p) for p in poly])
        gruppen.setdefault(st, dict(M=M, linien=[]))["linien"] += L
    linien = []
    for pm in re.finditer(r"<path\b[^>]*>", rest):
        t = pm.group(0); g = _ist_gleis(t); d = _attr(t, "d")
        if not g or not d: continue
        w = g[1]; col = (_attr(t, "stroke") or "").lower()
        if w >= 4.0 or w > 6: continue                     # Perronstriche der Halte (4.2) und Bahnhof-Hintergründe
        for poly in pfad_linien(d):
            if LineString(poly).length > 0.5: linien.append((poly, col, w))
    kreise = [(float(x), float(y)) for x, y in re.findall(r'<circle[^>]*\bcx="(-?[\d.]+)" cy="(-?[\d.]+)"', rest)]
    texte = [(float(x), float(y), re.sub("<[^>]+>", "", t)) for x, y, t in re.findall(r'<text[^>]*\bx="(-?[\d.]+)" y="(-?[\d.]+)"[^>]*>(.*?)</text>', rest, re.S)]
    return gruppen, linien, texte, kreise


# ---------------------------------------------------------------- OSM-Netz
def _osm_graph(osm, bbox):
    T, W, K, WT = osm
    la0, lo0, la1, lo1 = bbox
    import networkx as nx
    G = nx.Graph()
    for w, ns in W.items():
        t = WT.get(w, {})
        if t.get("railway") not in ("rail", "narrow_gauge", "light_rail", "subway", "tram", "funicular"): continue
        pts = [K.get(n) for n in ns]
        if not any(p and la0 <= p[0] <= la1 and lo0 <= p[1] <= lo1 for p in pts): continue
        f = 1.0 if not t.get("service") else 3.0
        for a, b in zip(ns, ns[1:]):
            if a in K and b in K:
                G.add_edge(a, b, w=f * _dist_m(K[a], K[b]), way=w)
    return G


def _dist_m(a, b):
    return math.hypot((a[0] - b[0]) * 111200, (a[1] - b[1]) * 111200 * math.cos(math.radians(a[0])))


def _xy_m(ll, lat0): return ((ll[1] - 8.0) * 111200 * math.cos(math.radians(lat0)), (ll[0] - 47.0) * 111200)


# ---------------------------------------------------------------- Prüfung
def pruefen(svg, netze, osm, key=""):
    """netze: {st: Netzmodell}. -> dict(zaehl {HT6, HT7}, befunde […])"""
    gruppen, linien, texte, kreise = lesen(svg)
    T, W, K, WT = osm
    befunde = []
    # Abgänge in Regionlage
    ports = []
    for st, g in gruppen.items():
        N = netze.get(st)
        if not N: continue
        for a in N.get("abgaenge", []):
            q = _tf(g["M"], (a["x"], a["y"]))
            ports.append(dict(st=st, titel=N.get("titel", st), xy=q, ref=a.get("ref"), town=a.get("town"), way=a.get("way"),
                              knoten=a.get("knoten"), ll=a.get("ll") or [a.get("lat"), a.get("lon")], kind=a.get("kind")))
    # Gleise der Bahnhofsgruppen mit Way (Netzmodell): Knotenlage je Gleis transformiert
    gl_way = []
    for st, g in gruppen.items():
        N = netze.get(st)
        if not N: continue
        KN = N.get("knoten", {})
        for gl in N.get("gleise", []):
            ks = [KN.get(str(k)) for k in gl.get("knoten", [])]
            if len(ks) < 2 or not all(ks) or any(k.get("x") is None or k.get("y") is None for k in ks): continue
            pts = [_tf(g["M"], (k["x"], k["y"])) for k in ks]
            if math.dist(pts[0], pts[-1]) < 0.5: continue
            gl_way.append((LineString(pts), gl.get("way"), st))
    # ------------------------------------------------ HT6: jeder Abgang hat eine Fortsetzung
    ends = []
    for i, (poly, col, w) in enumerate(linien): ends += [(poly[0], i), (poly[-1], i)]
    def _an_port(p): return [q for q in ports if math.dist(p, q["xy"]) <= 12]
    _lg = [LineString(p) for p, _, _ in linien]
    for q in ports:
        if any(L.distance(Point(q["xy"])) <= TOL_PORT for L in _lg): continue      # Linie beginnt am Abgang oder läuft durch ihn
        # REGELN 4.12: Stummel entfällt, die Strecke beginnt an der Weiche im Bahnhof (Muntelier) – Linienende auf einem Gleis
        # desselben Bahnhofs, höchstens 60 px vom Abgang
        _gl = [LineString(p) for p in gruppen[q["st"]]["linien"] if len(p) > 1]
        if (not any(g.distance(Point(q["xy"])) <= 1.5 for g in _gl)          # Stummel weg: der Abgangspunkt liegt frei
                and any(math.dist(e, q["xy"]) <= 60 and any(g.distance(Point(e)) <= 1.5 for g in _gl) for e, _ in ends)): continue
        # gleicher Punkt in einem anderen Bahnhof (zwei Pläne stossen direkt aneinander)
        if any(r is not q and r["st"] != q["st"] and math.dist(r["xy"], q["xy"]) <= TOL_PORT for r in ports): continue
        befunde.append(dict(regel="HT6", x=round(q["xy"][0], 1), y=round(q["xy"][1], 1), st=q["st"], way=q["way"],
                            text=f"{q['titel']}: Abgang Linie {q['ref'] or '?'} ({q['town'] or '?'}) ohne Fortsetzung im Regionalplan (kein Pfeil, keine Strecke)"))
    # lose Enden der Regionslinien
    alle_geo = [LineString(p) for p, _, _ in linien]
    gr_geo = [LineString(p) for g in gruppen.values() for p in g["linien"] if len(p) > 1]
    for e, i in ends:
        if _an_port(e): continue
        P = Point(e)
        if any(j != i and alle_geo[j].distance(P) <= TOL_PORT for j in range(len(alle_geo))): continue
        if any(g.distance(P) <= TOL_PORT for g in gr_geo): continue
        if any(math.dist(e, (x, y)) <= 60 for x, y, t in texte if t.strip()): continue     # Abgang mit Beschriftung (Pfeil-Text)
        if any(math.dist(e, k) <= 5 for k in kreise): continue                              # Prellbock
        befunde.append(dict(regel="HT6", x=round(e[0], 1), y=round(e[1], 1), text="Linie der Region endet lose (kein Abgang, kein Pfeil, keine Beschriftung)"))
    # ------------------------------------------------ HT7: Kreuzungen nur mit OSM-Grund
    lat0 = np.mean([q["ll"][0] for q in ports if q["ll"] and q["ll"][0]] or [47.0])
    if ports:
        lls = [q["ll"] for q in ports if q["ll"] and q["ll"][0]]
        bb = (min(a for a, b in lls) - 0.02, min(b for a, b in lls) - 0.03, max(a for a, b in lls) + 0.02, max(b for a, b in lls) + 0.03)
        G = _osm_graph(osm, bb)
    else: G = None
    def _way_geo(w):
        ns = W.get(w, []); pts = [_xy_m(K[n], lat0) for n in ns if n in K]
        return LineString(pts) if len(pts) > 1 else None
    # Linienketten: Stücke der Regionslinien, die Ende an Ende liegen (Strecken sind in Teilpfade zerlegt)
    from shapely.ops import linemerge
    _snap = lambda p: (round(p[0] * 2) / 2, round(p[1] * 2) / 2)
    ketten = linemerge(MultiLineString([[_snap(p) for p in poly] for poly, _, _ in linien if len(poly) > 1]))
    ketten = list(ketten.geoms) if hasattr(ketten, "geoms") else [ketten]
    def _kette(i):
        m = LineString(linien[i][0]).interpolate(0.5, normalized=True)
        return min(range(len(ketten)), key=lambda k: ketten[k].distance(m))
    def _route(qa, qb):
        if G is None: return None
        import networkx as nx
        best = None
        for a in qa:
            for b in qb:
                na, nb = a.get("knoten"), b.get("knoten")
                na = na if na in G else (W.get(a["way"], [None])[0] if a.get("way") in W else None)
                nb = nb if nb in G else (W.get(b["way"], [None])[0] if b.get("way") in W else None)
                if na in G and nb in G and na != nb:
                    try:
                        pfad = nx.shortest_path(G, na, nb, weight="w")
                        L = LineString([_xy_m(K[n], lat0) for n in pfad])
                        if best is None or L.length < best.length: best = L
                    except Exception: pass
        return best
    kcache = {}
    def _kette_osm(k):
        """-> (OSM-Weg zwischen den Abgängen an den Kettenenden oder None, Geometrie der Abgangs-Ways)"""
        if k in kcache: return kcache[k]
        C = ketten[k]; qa, qb = _an_port(C.coords[0]), _an_port(C.coords[-1])
        geos = [g_ for g_ in (_way_geo(q["way"]) for q in qa + qb if q.get("way")) if g_ is not None]
        r = _route(qa, qb) if qa and qb else None
        kcache[k] = (r, unary_union(geos + ([r] if r is not None else [])) if geos or r is not None else None, qa + qb)
        return kcache[k]
    def _linie_osm(i): return _kette_osm(_kette(i))[1]
    def _geo_ort(P):
        """Kreuzungspunkt im Plan -> Lage in OSM (m): über die nächste Kette mit OSM-Weg, anteilig längs"""
        for k in sorted(range(len(ketten)), key=lambda k: ketten[k].distance(P))[:6]:
            r = _kette_osm(k)[0]
            if r is None or ketten[k].distance(P) > 40: continue
            f = ketten[k].project(P) / (ketten[k].length or 1); return r.interpolate(f * r.length)
        return None
    # OSM-Kreuzungen im Gebiet: Knoten railway=railway_crossing und Ways, die sich ohne gemeinsamen Knoten schneiden (Brücke/Tunnel)
    from shapely.strtree import STRtree
    _seg, _segw = [], []
    if G is not None:
        for u, v, d in G.edges(data=True):
            _seg.append(LineString([_xy_m(K[u], lat0), _xy_m(K[v], lat0)])); _segw.append((d["way"], u, v))
    _tree = STRtree(_seg) if _seg else None
    _xnodes = [Point(_xy_m(K[n], lat0)) for n in (G.nodes if G is not None else []) if T.get(n, {}).get("railway") in ("railway_crossing", "crossing")]
    def _osm_kreuzung_bei(ort, r=80):
        if ort is None or _tree is None: return False
        if any(ort.distance(x) <= r for x in _xnodes): return True
        idx = list(_tree.query(ort.buffer(r)))
        for a_ in idx:
            for b_ in idx:
                if b_ <= a_ or _segw[a_][0] == _segw[b_][0]: continue
                if set(_segw[a_][1:]) & set(_segw[b_][1:]): continue
                x_ = _seg[a_].intersection(_seg[b_])
                if not x_.is_empty and x_.geom_type == "Point" and x_.distance(ort) <= r: return True
        return False
    osm_cache = {}
    def _kreuzt_osm(ga, gb):
        if ga is None or gb is None: return False
        return ga.buffer(3).intersects(gb)
    def _richt(L, P):
        d = L.project(P); a = L.interpolate(max(0, d - 3)); b = L.interpolate(min(L.length, d + 3))
        v = np.array([b.x - a.x, b.y - a.y]); n = np.linalg.norm(v); return v / n if n else v
    def _schleifend(La, Lb, P):        # Linien laufen ineinander (Ausrundung an einer Weiche) statt sich zu kreuzen
        return abs(float(_richt(La, P) @ _richt(Lb, P))) > math.cos(math.radians(12))
    for i, (poly, col, w) in enumerate(linien):
        Li = LineString(poly)
        kand = []
        for g in gr_geo:
            x = Li.intersection(g)
            if not x.is_empty: kand.append(("gleis", x, g))
        for j in range(len(linien)):
            if j == i: continue
            x = Li.intersection(alle_geo[j])
            if not x.is_empty: kand.append((j, x, alle_geo[j]))
        for art, x, Lg in kand:
            pts = [x] if x.geom_type == "Point" else (list(x.geoms) if hasattr(x, "geoms") else [x])
            for P in pts:
                if P.geom_type != "Point": continue           # Überlappung (Linie läuft auf dem Gleis) ist kein Schnitt
                if _schleifend(Li, Lg, P): continue
                if math.dist((P.x, P.y), poly[0]) <= TOL_END or math.dist((P.x, P.y), poly[-1]) <= TOL_END: continue
                if art != "gleis":
                    pj = linien[art][0]
                    if math.dist((P.x, P.y), pj[0]) <= TOL_END or math.dist((P.x, P.y), pj[-1]) <= TOL_END: continue
                    if art < i: continue                      # Paar nur einmal
                    if i not in osm_cache: osm_cache[i] = _linie_osm(i)
                    if art not in osm_cache: osm_cache[art] = _linie_osm(art)
                    if _kreuzt_osm(osm_cache[i], osm_cache[art]): continue
                    if (osm_cache[i] is None or osm_cache[art] is None) and _osm_kreuzung_bei(_geo_ort(P)): continue   # nur ohne direkte Zuordnung
                    was = "einer anderen Linie"
                else:
                    near = sorted(gl_way, key=lambda t: t[0].distance(P))
                    gw = near[0] if near and near[0][0].distance(P) <= 6 else None
                    if i not in osm_cache: osm_cache[i] = _linie_osm(i)
                    if gw is not None and gw[1] and _kreuzt_osm(osm_cache[i], _way_geo(gw[1])): continue
                    if (gw is None or osm_cache[i] is None) and _osm_kreuzung_bei(_geo_ort(P)): continue   # nur ohne direkte Zuordnung
                    was = f"Gleis {gw[2]} Way {gw[1]}" if gw else "einem Bahnhofsgleis"
                if any(b["regel"] == "HT7" and math.dist((b["x"], b["y"]), (P.x, P.y)) < 3 for b in befunde): continue
                _qs = _kette_osm(_kette(i))[2]; _w = sorted({q["way"] for q in _qs if q.get("way")})
                befunde.append(dict(regel="HT7", x=round(P.x, 1), y=round(P.y, 1), linie_ways=_w, osm_ort=_geo_ort(P) is not None,
                                    text=f"Linie der Region ({'/'.join(sorted({str(q['ref']) for q in _qs})) or 'ohne Abgang'}) kreuzt {was} ohne OSM-Kreuzung"))
    z = collections.Counter(b["regel"] for b in befunde)
    return dict(zaehl={r: z.get(r, 0) for r in ("HT6", "HT7")}, befunde=befunde, n_ports=len(ports), n_linien=len(linien))


def netze_fuer(key, svg, netz_dir):
    """data-st -> Netzmodell; Region SZU/MOB/Vereina: Präfix <region>__, Werkstatt-Regionen ohne Präfix"""
    pref = {"region_szu": "szu__", "region_mob": "mob__", "region_vereina": "vereina__"}.get(os.path.basename(key), "")
    out = {}
    for st in set(re.findall(r'<g data-st="([^"]+)"', svg)):
        for k in (pref + st, st, pref + st + "_regional", "szu__" + st, "mob__" + st, "vereina__" + st):
            for f in (k + "_netz.json", k + ".json"):
                p = os.path.join(netz_dir, f)
                if os.path.exists(p):
                    try: out[st] = json.load(open(p))
                    except Exception: pass
                    break
            if st in out: break
    return out


if __name__ == "__main__":
    import argparse, hauptgleis as HG
    ap = argparse.ArgumentParser(); ap.add_argument("svg"); ap.add_argument("--netz-dir", required=True); ap.add_argument("--osm", required=True)
    ap.add_argument("--json")
    A = ap.parse_args(); s = open(A.svg).read()
    R = pruefen(s, netze_fuer(A.svg[:-4], s, A.netz_dir), HG.osm_laden(A.osm))
    print(json.dumps(R["zaehl"]), "Abgänge", R["n_ports"], "Linien", R["n_linien"])
    for b in R["befunde"]: print(f"  {b['regel']} {b['x']}/{b['y']} {b['text']}")
    if A.json: json.dump(R, open(A.json, "w"), ensure_ascii=False, indent=1)
