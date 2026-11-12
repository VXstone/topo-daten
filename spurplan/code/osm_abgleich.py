"""Abgleich Plan gegen OSM (Schritt V1, 12.11.2026 – D. Eckenstein «wir übersehen was»: Zähler messen die Topologie nicht;
Konolfingen sah mit Regionsregeln nach Zahlen besser aus, aber DKW 1689230829 fehlte und das Gleisfeld West hing an Gl. 5).

  python3 osm_abgleich.py <plan.svg> <netz.json> --osm <schweiz_bahn.json.gz> [--json out.json] [--key name]
  python3 osm_abgleich.py --alle <plaene_dir> <netz_dir> --osm <...> --out <ordner>     (alle Pläne mit Netzmodell)

Vergleicht die GEZEICHNETE Geometrie (SVG wie auf der Seite) mit OSM über das Netzmodell des Bahnhofs (<key>_netz.json aus
spurplan_schema: OSM-Knoten mit Plankoordinaten). Befunde (Regel, x, y, Text, OSM-IDs):
  VA1  OSM-DKW/EKW (railway:switch=double_slip/single_slip) im Plan nicht als DKW gezeichnet (keine DKW-Bögen)
  VA2  im Plan als DKW gezeichnet, in OSM keine DKW/EKW
  VB1  OSM-Weiche im Plan (Knoten auf gezeichnetem Gleis) ohne Abzweig im Plan
  VB2  Abzweig im Plan (>= 3 Richtungen), in OSM dort keine Weiche, DKW oder Kreuzung (auch «Gleis über Gleis»)
  VC1  Abzweig im Plan an einer OSM-Weiche, aber ein angeschlossenes Gleis gehört in OSM nicht zu dieser Weiche
       (falsch angebunden, z. B. Gleisfeld an Gl. 5 statt an Gl. 4)
  VD1  Gleis auf Gleis: zwei Gleise laufen über mehr als 12 px aufeinander (0,5 px Toleranz)
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


def _richtung(g, p, weg=15.0):
    """Richtungen (Grad) der Äste eines Gleises am Punkt p: Ende -> eine, Inneres -> zwei"""
    L = g.length; t = g.project(p); out = []
    for s_ in (-1, 1):
        u = t + s_ * min(weg, L)
        u = min(max(u, 0.0), L)
        if abs(u - t) < 1.0: continue
        q = g.interpolate(u)
        out.append(math.degrees(math.atan2(q.y - p.y, q.x - p.x)) % 360)
    return out


def _verschieden(R, tol=8.0):
    V = []
    for r in R:
        if all(min(abs(r - v), 360 - abs(r - v)) > tol for v in V): V.append(r)
    return V


def plan_knoten(gleise, luecken):
    """Abzweige im Plan: Punkte, an denen sich Gleise berühren und mindestens drei verschiedene Richtungen abgehen
    (Weiche, Kreuzung, DKW). Zwei Enden in einer Flucht (Stummel über Streckengleis, Teilpfade) zählen nicht.
    [(x, y, art, {gleis-idx}, n_richtungen)]"""
    G = [g["geo"] for g in gleise]
    tree = STRtree(G)
    gap = lambda p: any(l.contains(p) for l in luecken)
    kand = []
    for i, g in enumerate(G):
        kand += [Point(g.coords[0]), Point(g.coords[-1])]
        for j in tree.query(g):
            j = int(j)
            if j <= i: continue
            x = g.intersection(G[j])
            for q in getattr(x, "geoms", [x]):
                if not q.is_empty and q.geom_type == "Point": kand.append(q)
    seen, out = [], []
    for p in kand:
        if any(p.distance(s_) < 3 for s_ in seen): continue
        seen.append(p)
        if gap(p): continue
        idx = [int(j) for j in tree.query(p.buffer(1.2)) if G[int(j)].distance(p) < 1.2]
        if len(idx) < 2: continue
        R = _verschieden([r for j in idx for r in _richtung(G[j], p)])
        if len(R) >= 3:
            art = "X" if len(R) >= 4 and all(G[j].project(p) > 1.5 and G[j].project(p) < G[j].length - 1.5 for j in idx) else "W"
            out.append([p.x, p.y, art, set(idx), len(R)])
    # ein Abzweig im Plan liefert oft zwei Punkte (Teilpfad endet an der Weiche, Ast beginnt 2–5 px daneben): 6 px zusammen
    zus = []
    for o in out:
        for z in zus:
            if math.hypot(z[0] - o[0], z[1] - o[1]) < 6: z[3] |= o[3]; z[4] = max(z[4], o[4]); break
        else: zus.append(o)
    return [tuple(z) for z in zus]


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
    G = [g["geo"] for g in gleise]
    tree = STRtree(G) if G else None
    # Versatz Netzmodell -> gezeichneter Plan (Ins 12.11.: ganzer Plan 10,8 px tiefer gezeichnet als im Netzmodell):
    # je Weiche die senkrechten Abstände zu den Gleisen an ihrem x; der häufigste Wert gewinnt, wenn er klar vor 0 liegt
    stimmen = collections.Counter()
    for n, v in KN.items():
        if typ(n) != "switch" or tree is None: continue
        sonde = LineString([(v["x"], v["y"] - 60), (v["x"], v["y"] + 60)])
        for j in tree.query(sonde):
            q = G[int(j)].intersection(sonde)
            for t in getattr(q, "geoms", [q]):
                if not t.is_empty and t.geom_type == "Point": stimmen[round((t.y - v["y"]) * 2) / 2] += 1
    versatz = 0.0
    if stimmen:
        dy, c = stimmen.most_common(1)[0]
        if dy != 0 and c >= 3 and c > 1.5 * stimmen.get(0.0, 0): versatz = dy
    if versatz:
        KN = {n: dict(v, y=v["y"] + versatz) for n, v in KN.items()}
    # mögliche Lagen eines Knotens quer: eigene Ebene und die Ebenen aller Gleisstücke, zu denen er gehört (eine Weiche
    # hat ihre «Heimat» oft auf dem abzweigenden Gleis, gezeichnet wird sie am durchgehenden)
    lagen = collections.defaultdict(set)
    for gl in N["gleise"]:
        if gl.get("y") is None: continue
        for n in gl["knoten"]:
            if n in KN: lagen[n].add(gl["y"] + versatz)
    for n, v in KN.items(): lagen[n].add(v["y"])
    # Knoten, die nicht auf einem gezeichneten Gleis liegen (Olten 12.11.: 18 % der Knoten um 1 Ebene daneben – das
    # Netzmodell folgt einer späteren Ebenenverschiebung nicht): zusätzlich die nächste gezeichnete Lage an ihrem x
    neben = set()
    for n, v in KN.items():
        p = Point(v["x"], v["y"])
        if tree is None or any(G[int(j)].distance(p) < 1.5 for j in tree.query(p.buffer(1.5))): continue
        neben.add(n)
        sonde = LineString([(v["x"], v["y"] - 30), (v["x"], v["y"] + 30)])
        ys = [t.y for j in tree.query(sonde) for q in [G[int(j)].intersection(sonde)] for t in getattr(q, "geoms", [q])
              if not t.is_empty and t.geom_type == "Point"]
        if ys: lagen[n].add(min(ys, key=lambda y: abs(y - v["y"])))
    osm_kn = {n: v for n, v in KN.items() if typ(n) in ("switch", "railway_crossing") or len(nachbarn[n]) >= 3}
    # Plan-Gleis -> Ways (Knoten mit Plankoordinate auf dem Gleis)
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
    # Zuordnung OSM-Knoten <-> Plan-Abzweig eins zu eins (nächste zuerst). Längs des Gleises darf der Plan den Abzweig
    # verschieben (Spurwechsel in Standardlänge, Entzerrung): Abstand quer zählt vierfach, Grenze 40 px längs.
    def kosten(n, p):
        v = KN[n]; dx = abs(v["x"] - p[0])
        dy = min(abs(y - p[1]) for y in lagen[n])
        return math.hypot(dx, 4 * dy) if dy < 10 else 1e9
    paare = sorted((kosten(n, p), n, i) for n in osm_kn for i, p in enumerate(PK))
    zu_osm, zu_plan = {}, {}
    for c, n, i in paare:
        if c > 40: break
        if n in zu_osm or i in zu_plan: continue
        zu_osm[n] = i; zu_plan[i] = n
    # zweiter Durchgang über die Topologie (Olten 12.11.: Weichenstrassen im Plan stark gestaucht, Abzweig > 40 px längs
    # neben der OSM-Weiche): gleiche Lage quer, bis 150 px längs, und mindestens zwei Äste des Abzweigs gehören zu Ways
    # dieser Weiche
    def aeste(i):
        return sum(1 for j in PK[i][3] if g_ways.get(j) and g_ways[j] & way_von_knoten.get(n_, set()))
    paare2 = []
    for n_ in osm_kn:
        if n_ in zu_osm: continue
        v = KN[n_]
        for i, p in enumerate(PK):
            if i in zu_plan: continue
            dy = min(abs(y - p[1]) for y in lagen[n_]); dx = abs(v["x"] - p[0])
            if dy < 4 and dx < 150 and aeste(i) >= 2: paare2.append((dx, n_, i))
    for c, n_, i in sorted(paare2):
        if n_ in zu_osm or i in zu_plan: continue
        zu_osm[n_] = i; zu_plan[i] = n_
    # zwei OSM-Weichen dicht beieinander (< 12 m) zeichnet der Plan oft als einen Abzweig: zweite gilt als gezeichnet
    for n, v in osm_kn.items():
        if n in zu_osm: continue
        for m, i in list(zu_osm.items()):
            w = osm_kn[m]
            if m in nachbarn[n] and kosten(n, PK[i]) < 40: zu_osm[n] = i; break
    # VB1: OSM-Weiche ohne Abzweig im Plan (DKW zählt über VA1)
    for n, v in KN.items():
        if typ(n) != "switch" or "slip" in swt(n) or n in zu_osm: continue
        if len(nachbarn[n]) < 3: continue           # Ast nicht gezeichnet (stillgelegt, ausserhalb): kein Befund hier
        bef("VB1", v["x"], v["y"], f"OSM-Weiche {n} ohne Abzweig im Plan", osm=n)
    # VB2 / VC1
    for i, (x, y, art, idx, nr) in enumerate(PK):
        n0 = zu_plan.get(i)
        if n0 is None:
            if any(math.hypot(c[0] - x, c[1] - y) < R_DKW for c in dkw_plan): continue
            bef("VB2", x, y, f"Gleise {'kreuzen' if art == 'X' else 'berühren'} sich ({nr} Richtungen), in OSM keine Weiche/Kreuzung",
                ways=sorted({w for j in idx for w in g_ways.get(j, ())}))
            continue
        umg = {n0}
        for _ in range(3): umg |= {m for k in umg for m in nachbarn[k]}
        for j in idx:
            ws = g_ways.get(j)
            if ws and not any(any(k in WAYN.get(w, ()) for k in umg) for w in ws):
                bef("VC1", x, y, f"Gleis (Way {sorted(ws)[0]}) im Plan an Knoten {n0} angebunden, in OSM nicht", osm=n0, ways=sorted(ws))
    # VD1 Gleis auf Gleis
    for i, g in enumerate(G):
        for j in tree.query(g.buffer(0.5)) if tree else []:
            j = int(j)
            if j <= i: continue
            ov = g.intersection(G[j].buffer(0.5))      # 0,5 px: Abzweig mit Ausrundung liegt nur wenige px tangential an
            if ov.length > 12 and G[j].intersection(g.buffer(0.5)).length > 12:
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
    return BEF, dict(gleise=len(G), knoten_plan=len(PK), dkw_plan=len(dkw_plan), knoten_osm=len(osm_kn), versatz_y=versatz,
                    netz_auf_plan=round(1 - len(neben) / max(1, len(KN)), 2))


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
