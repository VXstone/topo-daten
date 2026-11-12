"""Abgleich Plan gegen OSM (Schritt V1, 12.11.2026 – D. Eckenstein «wir übersehen was»: Zähler messen die Topologie nicht;
Konolfingen sah mit Regionsregeln nach Zahlen besser aus, aber DKW 1689230829 fehlte und das Gleisfeld West hing an Gl. 5).

  python3 osm_abgleich.py <plan.svg> <netz.json> --osm <schweiz_bahn.json.gz> [--json out.json] [--key name]
  python3 osm_abgleich.py --alle <plaene_dir> <netz_dir> --osm <...> --out <ordner>     (alle Pläne mit Netzmodell)

Vergleicht die GEZEICHNETE Geometrie (SVG wie auf der Seite) mit OSM über das Netzmodell des Bahnhofs (<key>_netz.json aus
spurplan_schema: OSM-Knoten mit Plankoordinaten). Befunde (Regel, x, y, Text, OSM-IDs):
  VA1  OSM-DKW/EKW (railway:switch=double_slip/single_slip) im Plan nicht als DKW gezeichnet (keine DKW-Bögen)
  VA2  im Plan als DKW gezeichnet, in OSM keine DKW/EKW
  VB1  OSM-Weiche im Plan (Knoten auf gezeichnetem Gleis) ohne Abzweig im Plan
  VB2  zwei Gleise berühren/kreuzen sich im Plan, in OSM dort keine Weiche, DKW oder Kreuzung (auch «Gleis über Gleis»)
  VC1  Abzweig im Plan an einer OSM-Weiche, aber ein angeschlossenes Gleis gehört in OSM nicht zu dieser Weiche
       (falsch angebunden, z. B. Gleisfeld an Gl. 5 statt an Gl. 4)
  VD1  Gleis auf Gleis: zwei Gleise laufen über mehr als 8 px aufeinander (0,5 px Toleranz)
  VD2  Perron auf Gleis: ein Gleis läuft durch ein gezeichnetes Perron
Niveaugetrennte Kreuzungen (weisse Lücke im Plan) zählen nicht als Berührung. Exit-Stummel ohne Netzbezug werden nur für
VB2/VD geprüft. Toleranzen in Plan-px (Gleisabstand 24 px): Knoten 9 px, DKW 16 px.
"""
import argparse, collections, gzip, json, math, os, re, sys
import xml.etree.ElementTree as ET
import numpy as np
from svgpathtools import parse_path
from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree

TRACK = {"#00862f": "gruen", "#111": "schwarz", "#111111": "schwarz", "#000": "schwarz", "#9a5b1e": "braun"}
R_KNOTEN, R_DKW = 9.0, 16.0


def mat(tr):
    M = np.eye(3)
    for f, a in re.findall(r"(\w+)\(([^)]*)\)", tr or ""):
        v = [float(x) for x in re.split(r"[ ,]+", a.strip()) if x]
        if f == "translate": T = np.array([[1, 0, v[0]], [0, 1, v[1] if len(v) > 1 else 0], [0, 0, 1]])
        elif f == "scale": T = np.diag([v[0], v[1] if len(v) > 1 else v[0], 1])
        elif f == "rotate":
            c, s = math.cos(math.radians(v[0])), math.sin(math.radians(v[0]))
            T = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
            if len(v) == 3: T = np.array([[1, 0, v[1]], [0, 1, v[2]], [0, 0, 1]]) @ T @ np.array([[1, 0, -v[1]], [0, 1, -v[2]], [0, 0, 1]])
        elif f == "matrix": T = np.array([[v[0], v[2], v[4]], [v[1], v[3], v[5]], [0, 0, 1]])
        else: continue
        M = M @ T
    return M


def plan_lesen(svg_text):
    """Gleise (Teilpfade als Polylinien), DKW-Bögen, Perrons, Lücken (Niveautrennung) aus dem SVG"""
    root = ET.fromstring(re.sub(r'\sxmlns="[^"]+"', "", svg_text, count=1))
    gleise, boegen, perrons, luecken = [], [], [], []

    def walk(el, st, M):
        if el.get("class") == "befund": return
        st = dict(st); M = M @ mat(el.get("transform"))
        for k in ("stroke", "stroke-width", "fill", "stroke-opacity", "stroke-dasharray"):
            if el.get(k) is not None: st[k] = el.get(k)
        tag = el.tag.split("}")[-1]
        tp = lambda P: [tuple((M @ np.array([x, y, 1.0]))[:2]) for x, y in P]
        if tag == "path" and el.get("d") and not el.get("data-pfeil"):
            col, w = st.get("stroke"), float(st.get("stroke-width", "1") or 1)
            if col in ("#fff", "#ffffff", "white") and w >= 5:
                for sp in _teilpfade(el.get("d")): luecken.append(LineString(tp(sp)).buffer(w / 2))
            elif col in TRACK and 1.3 <= w <= 4.5 and st.get("fill", "none") == "none":
                tps = [tp(sp) for sp in _teilpfade(el.get("d"))]
                L = sum(LineString(p).length for p in tps if len(p) > 1)
                if float(st.get("stroke-opacity", "1")) < 0.9 or (len(tps) == 1 and L < 9 and "Q" in el.get("d")):
                    boegen.append(LineString(tps[0]).interpolate(0.5, normalized=True))
                else:
                    for p in tps:
                        if len(p) > 1 and LineString(p).length > 0.5:
                            gleise.append(dict(geo=LineString(p), farbe=TRACK[col], breite=w))
        elif tag == "rect" and el.get("height") == "8" and el.get("rx"):
            x, y, w_ = float(el.get("x")), float(el.get("y")), float(el.get("width"))
            perrons.append(LineString(tp([(x, y + 4), (x + w_, y + 4)])))
        for ch in el: walk(ch, st, M)
    walk(root, {}, np.eye(3))
    return gleise, boegen, perrons, luecken


def _teilpfade(d):
    out = []
    for sub in parse_path(d).continuous_subpaths():
        P = []
        for seg in sub:
            n = 1 if type(seg).__name__ == "Line" else 6
            for t in np.linspace(0, 1, n + 1)[(1 if P else 0):]:
                z = seg.point(t); P.append((round(z.real, 2), round(z.imag, 2)))
        if len(P) > 1: out.append(P)
    return out


def plan_knoten(gleise, luecken):
    """Berührungspunkte: Ende an Ende (>= 3 Enden), Ende auf Gleis (T), Gleis über Gleis (X). [(x, y, art, {gleis-idx})]"""
    G = [g["geo"] for g in gleise]
    tree = STRtree(G)
    pk = []
    gap = lambda p: any(l.contains(p) for l in luecken)
    enden = []
    for i, g in enumerate(G):
        enden += [(i, Point(g.coords[0])), (i, Point(g.coords[-1]))]
    # Enden clustern (1 px)
    cl = []
    for i, p in enden:
        for c in cl:
            if c["p"].distance(p) < 1.2: c["e"].append(i); break
        else: cl.append(dict(p=p, e=[i]))
    for c in cl:
        p = c["p"]
        auf = {int(j) for j in tree.query(p.buffer(1.2)) if int(j) not in c["e"] and G[int(j)].distance(p) < 1.2}
        n = len(c["e"]) + 2 * len(auf)
        if n >= 3 and not gap(p):
            pk.append((p.x, p.y, "T" if auf else "E", set(c["e"]) | auf))
    # Kreuzungen im Inneren
    for i, g in enumerate(G):
        for j in tree.query(g):
            j = int(j)
            if j <= i: continue
            x = g.intersection(G[j])
            for q in getattr(x, "geoms", [x]):
                if q.is_empty or q.geom_type != "Point": continue
                if min(q.distance(Point(g.coords[0])), q.distance(Point(g.coords[-1])),
                       q.distance(Point(G[j].coords[0])), q.distance(Point(G[j].coords[-1]))) < 1.5: continue
                if not gap(q): pk.append((q.x, q.y, "X", {i, j}))
    # zusammenfassen (3 px)
    out = []
    for p in pk:
        for o in out:
            if math.hypot(o[0] - p[0], o[1] - p[1]) < 3: o[3].update(p[3]); break
        else: out.append([p[0], p[1], p[2], set(p[3])])
    return out


def osm_tags(pfad):
    T, W = {}, {}
    D = json.load(gzip.open(pfad) if pfad.endswith(".gz") else open(pfad))
    for e in (D["elements"] if isinstance(D, dict) else D):
        if e["type"] == "node": T[e["id"]] = e.get("tags", {})
        elif e["type"] == "way": W[e["id"]] = e.get("nodes", [])
    return T, W


def abgleich(svg_text, N, TAGS, WAYN):
    gleise, boegen, perrons, luecken = plan_lesen(svg_text)
    BEF = []
    bef = lambda r, x, y, t, **o: BEF.append(dict(regel=r, x=round(x, 1), y=round(y, 1), text=t, **o))
    KN = {int(k): v for k, v in N["knoten"].items() if v.get("y") is not None}
    # OSM-Graph aus den gezeichneten Gleisstücken (Kanten zwischen aufeinanderfolgenden Knoten der ganzen Ways)
    ways = {g["way"] for g in N["gleise"]}
    nachbarn = collections.defaultdict(set)
    for w in ways:
        nd = WAYN.get(w, [])
        for a, b in zip(nd, nd[1:]): nachbarn[a].add(b); nachbarn[b].add(a)
    way_von_knoten = collections.defaultdict(set)
    for w in ways:
        for a in WAYN.get(w, []): way_von_knoten[a].add(w)
    typ = lambda n: TAGS.get(n, {}).get("railway")
    swt = lambda n: TAGS.get(n, {}).get("railway:switch", "")
    osm_kn = {n: v for n, v in KN.items() if typ(n) in ("switch", "railway_crossing") or len(nachbarn[n]) >= 3}
    # Plan-Gleis -> Ways (Knoten mit Plankoordinate auf dem Gleis)
    G = [g["geo"] for g in gleise]
    tree = STRtree(G) if G else None
    g_ways = collections.defaultdict(set)
    for gl in N["gleise"]:
        for n in gl["knoten"]:
            v = KN.get(n)
            if not v or tree is None: continue
            p = Point(v["x"], v["y"])
            for j in tree.query(p.buffer(1.5)):
                if G[int(j)].distance(p) < 1.5: g_ways[int(j)].add(gl["way"])
    # doppelt gezeichnete Stücke (Abgangsstummel über dem Streckengleis, gleiches Gleis zweimal) weglassen: Linie liegt
    # fast ganz auf einer anderen, gleiche Farbe, und ihre Ways sind dort schon gezeichnet (oder sie hat keine)
    weg = set()
    for i, g in enumerate(G):
        for j in tree.query(g.buffer(1.0)) if tree else []:
            j = int(j)
            if j == i or j in weg or gleise[i]["farbe"] != gleise[j]["farbe"]: continue
            if g.length <= G[j].length + 1e-6 and g.intersection(G[j].buffer(1.0)).length >= 0.9 * g.length \
                    and g_ways.get(i, set()) <= g_ways.get(j, set()) and (g.length < G[j].length or i > j):
                weg.add(i); break
    if weg:
        alt = list(range(len(G))); keep = [i for i in alt if i not in weg]
        gleise = [gleise[i] for i in keep]; G = [G[i] for i in keep]
        g_ways = collections.defaultdict(set, {n: g_ways[o] for n, o in enumerate(keep) if o in g_ways})
        tree = STRtree(G) if G else None
    PK = plan_knoten(gleise, luecken) if G else []
    # DKW-Bögen clustern
    dkw_plan = []
    for b in boegen:
        for c in dkw_plan:
            if math.hypot(c[0] - b.x, c[1] - b.y) < 12: c[2] += 1; break
        else: dkw_plan.append([b.x, b.y, 1])
    # VA1 / VA2
    for n, v in KN.items():
        if typ(n) == "switch" and ("double_slip" in swt(n) or "single_slip" in swt(n)):
            if not any(math.hypot(c[0] - v["x"], c[1] - v["y"]) < R_DKW for c in dkw_plan):
                bef("VA1", v["x"], v["y"], f"OSM-{'DKW' if 'double' in swt(n) else 'EKW'} {n} im Plan nicht als DKW gezeichnet", osm=n)
    for c in dkw_plan:
        if not any(("slip" in swt(n)) and math.hypot(c[0] - v["x"], c[1] - v["y"]) < R_DKW for n, v in KN.items()):
            bef("VA2", c[0], c[1], "im Plan als DKW gezeichnet, in OSM keine DKW/EKW in der Nähe")
    # VB1: OSM-Weiche ohne Abzweig im Plan (DKW zählt über VA1)
    for n, v in KN.items():
        if typ(n) != "switch" or "slip" in swt(n): continue
        if len(nachbarn[n]) < 3: continue           # Weiche auf nicht gezeichnetem Ast: Ast fehlt -> nur, wenn Ast gezeichnet
        if not any(math.hypot(p[0] - v["x"], p[1] - v["y"]) < R_KNOTEN for p in PK):
            bef("VB1", v["x"], v["y"], f"OSM-Weiche {n} ohne Abzweig im Plan", osm=n)
    # VB2 / VC1
    for x, y, art, idx in PK:
        nah = [(math.hypot(v["x"] - x, v["y"] - y), n) for n, v in osm_kn.items()]
        nah = sorted(d for d in nah if d[0] < (R_DKW if "slip" in swt(d[1]) else R_KNOTEN))
        if not nah:
            if any(math.hypot(c[0] - x, c[1] - y) < R_DKW for c in dkw_plan): continue
            bef("VB2", x, y, f"Gleise berühren/kreuzen sich ({art}), in OSM keine Weiche/Kreuzung",
                ways=sorted({w for i in idx for w in g_ways.get(i, ())}))
            continue
        kandid = {n for _, n in nah}
        for i in idx:
            ws = g_ways.get(i)
            if not ws: continue
            if not any(any(k in WAYN.get(w, ()) for k in kandid) for w in ws):
                # verbunden über ein kurzes Stück ohne eigene Planknoten? zwei OSM-Kanten weit zulassen
                umg = set(kandid)
                for _ in range(3): umg |= {m for k in umg for m in nachbarn[k]}
                if not any(any(k in WAYN.get(w, ()) for k in umg) for w in ws):
                    bef("VC1", x, y, f"Gleis (Way {sorted(ws)[0]}) im Plan an Knoten {sorted(kandid)[0]} angebunden, in OSM nicht",
                        osm=sorted(kandid)[0], ways=sorted(ws))
    # VD1 Gleis auf Gleis
    for i, g in enumerate(G):
        for j in tree.query(g.buffer(0.5)) if tree else []:
            j = int(j)
            if j <= i: continue
            ov = g.intersection(G[j].buffer(0.5))      # 0,5 px: Abzweig mit Ausrundung liegt nur wenige px tangential an
            if ov.length > 8 and G[j].intersection(g.buffer(0.5)).length > 8:
                c = ov.centroid
                if not any(l.contains(c) for l in luecken):
                    bef("VD1", c.x, c.y, f"zwei Gleise {ov.length:.0f} px aufeinander")
    # VD2 Perron auf Gleis
    for p in perrons:
        pb = p.buffer(3.0, cap_style=2)
        for j in tree.query(pb) if tree else []:
            L = G[int(j)].intersection(pb).length
            if L > 4:
                c = G[int(j)].intersection(pb).centroid
                bef("VD2", c.x, c.y, f"Gleis läuft {L:.0f} px durch ein Perron")
    return BEF, dict(gleise=len(G), knoten_plan=len(PK), dkw_plan=len(dkw_plan), knoten_osm=len(osm_kn))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a"); ap.add_argument("b"); ap.add_argument("--osm", required=True)
    ap.add_argument("--json"); ap.add_argument("--key"); ap.add_argument("--alle", action="store_true"); ap.add_argument("--out")
    A = ap.parse_args()
    TAGS, WAYN = osm_tags(A.osm)
    jobs = []
    if A.alle:
        for f in sorted(os.listdir(A.b)):
            k = f[:-len("_netz.json")] if f.endswith("_netz.json") else f[:-5] if f.endswith(".json") else None
            if k and os.path.exists(os.path.join(A.a, f"{k}.svg")): jobs.append((k, os.path.join(A.a, f"{k}.svg"), os.path.join(A.b, f)))
        os.makedirs(A.out, exist_ok=True)
    else:
        jobs = [(A.key or os.path.basename(A.a)[:-4], A.a, A.b)]
    summe = {}
    for k, s, n in jobs:
        try:
            B, info = abgleich(open(s).read(), json.load(open(n)), TAGS, WAYN)
        except Exception as e:
            print(k, "Fehler", e, file=sys.stderr); summe[k] = dict(fehler=str(e)[:200]); continue
        z = dict(collections.Counter(b["regel"] for b in B))
        summe[k] = dict(z, **info)
        print(f"{k:<34} {z}")
        ziel = os.path.join(A.out, f"{k}.json") if A.alle else A.json
        if ziel: json.dump(dict(plan=k, befunde=B, info=info), open(ziel, "w"), ensure_ascii=False, indent=0)
    if A.alle:
        json.dump(summe, open(os.path.join(A.out, "_summe.json"), "w"), ensure_ascii=False, indent=1)
        t = collections.Counter()
        for v in summe.values(): t.update({r: c for r, c in v.items() if r[:1] == "V" and isinstance(c, int)})
        print("OSM-Abgleich:", len(summe), "Pläne", dict(sorted(t.items())))


if __name__ == "__main__":
    main()
