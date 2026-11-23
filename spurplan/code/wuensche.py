"""Wünsche 5.3 / 5.5 / 5.6 (REGELN 5, Entscheid D. Eckenstein 13.11.2026: der Code darf Pläne verbessern – weniger
S-Kurven, gleichmässigerer Bahnhofsabstand, kürzere Bahnhöfe). Messung nur auf dem SVG (+ Regionstopologie für 5.5).

  python3 wuensche.py <plan.svg> [--topo <region_topologie.json>] [--json out.json]

  W53  S-Kurven: auf einem durchgehenden Gleis (über Planränder verkettet) zwei Gegenknicke > 8°, Netto < 6°, Abstand
       < 200 px, mindestens eine der beiden Ecken ohne Anschluss (Weiche/Pfeil/Prellbock). Zahl = Anzahl.
  W55  Bahnhofsabstand (nur Regionalpläne): je benachbartes Bahnhofspaar px / km^0.75 (gestauchte Distanz wie lage_auto);
       Zahl = Variationskoeffizient in % / 10, gerundet (0 = gleichmässig).
  W56  Bahnhofslänge (nur Bahnhofspläne): Leerlänge längs der Hauptachse – Stücke ohne Weiche, Perron oder Gleisende
       (je ± 40 px), abzüglich 120 px Ausfahrt an beiden Planenden; Zahl = Leerlänge / 100 px, gerundet.
       Stand 17.11.: Onnens-Bonvillars 5, Rothrist 4, Tecknau 1 (Anlass Daniel), Konolfingen/Montreux 0.
  W59  Kurze Nebengleise (nur Bahnhofspläne, REGELN 5.9, V4 20.11.2026): je dünnes Gleis (Neben-/Abstell-/Anschlussgleis,
       Strichbreite < 2,5) die Länge über 80 px hinaus; Zahl = Summe / 100 px, gerundet. Nur Messung (Gewicht 0), bis
       Daniel die Gewichtung festlegt – Grundlage der Liste «Vorschlag: einfacher als abgenommen».
Gewichte (REGELN 5): W53 6, W55 3, W56 3, T7 8, W59 0 – Summe in alle_plaene_pruefen «Wunsch-Summe».
"""
import collections, json, math, os, re, sys
import numpy as np
import xml.etree.ElementTree as ET
from svgpathtools import parse_path, Line

GEWICHT = {"T7": 8, "W53": 6, "W55": 3, "W56": 3, "W59": 0}
HERE = os.path.dirname(os.path.abspath(__file__))
NS = "{http://www.w3.org/2000/svg}"


def _mat(tr):
    M = np.eye(3)
    for f, a in re.findall(r"(\w+)\(([^)]*)\)", tr or ""):
        v = [float(x) for x in re.split(r"[ ,]+", a.strip()) if x]
        if f == "translate": T = np.array([[1, 0, v[0]], [0, 1, v[1] if len(v) > 1 else 0], [0, 0, 1]])
        elif f == "scale": T = np.diag([v[0], v[1] if len(v) > 1 else v[0], 1])
        elif f == "rotate":
            c, s = math.cos(math.radians(v[0])), math.sin(math.radians(v[0]))
            T = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
            if len(v) == 3: T = np.array([[1, 0, v[1]], [0, 1, v[2]], [0, 0, 1]]) @ T @ np.array([[1, 0, -v[1]], [0, 1, -v[2]], [0, 0, 1]])
        else: continue
        M = M @ T
    return M


def lesen(svg_text):
    """Gleislinien in Plan-Koordinaten: [(breite, pts, bahnhof)], Kreise, Bahnhofsmitten {name: (x, y)}."""
    try: root = ET.fromstring(svg_text)
    except ET.ParseError:            # Basel/Bern (fest seit 23.10.): «</text<circle» – der Browser verzeiht es
        t = re.sub(r"</(\w+)<", r"</\1><", svg_text)
        t = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", t)
        try: root = ET.fromstring(t)
        except ET.ParseError: return [], [], {}
    linien, kreise, mitten = [], [], {}
    def walk(el, M, st, col, w):
        tag = el.tag.replace(NS, ""); M = M @ _mat(el.get("transform"))
        if el.get("data-st"):
            st = el.get("data-name") or el.get("data-st"); v = M @ np.array([0.0, 0.0, 1.0]); mitten[st] = (float(v[0]), float(v[1]))
        col = el.get("stroke", col); w = el.get("stroke-width", w)
        if tag == "circle":
            v = M @ np.array([float(el.get("cx", 0)), float(el.get("cy", 0)), 1.0]); kreise.append((float(v[0]), float(v[1])))
        if tag == "path" and el.get("d") and not el.get("stroke-opacity") and not el.get("data-fluegel") \
                and not el.get("stroke-dasharray") and (col or "none").lower() not in ("none", "#fff", "#ffffff", "#8a8a8a") \
                and el.get("fill", "none") in ("none", None):
            try: P = parse_path(el.get("d"))
            except Exception: P = []
            sc = math.sqrt(abs(np.linalg.det(M[:2, :2]))) or 1
            for sub in (P.continuous_subpaths() if P else []):
                pts = []
                for sg in sub:
                    if sg.length() < 0.3: continue
                    q = [sg.start, sg.end] if isinstance(sg, Line) else [sg.point(t) for t in np.linspace(0, 1, 6)]
                    for z in q:
                        v = M @ np.array([z.real, z.imag, 1.0]); p = (float(v[0]), float(v[1]))
                        if not pts or math.dist(p, pts[-1]) > 0.3: pts.append(p)
                if len(pts) >= 2: linien.append((float(w or 1) * sc, np.array(pts), st))
        for ch in el: walk(ch, M, st, col, w)
    walk(root, np.eye(3), None, None, None)
    return linien, kreise, mitten


def _dp(pts, tol=2.5):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; ab = b - a; L = np.linalg.norm(ab) or 1e-9
    r = pts[1:-1] - a; d = np.abs(ab[0] * r[:, 1] - ab[1] * r[:, 0]) / L
    i = int(np.argmax(d)) + 1
    if d[i - 1] <= tol: return np.array([a, b])
    return np.vstack([_dp(pts[:i + 1], tol)[:-1], _dp(pts[i:], tol)])


def verketten(linien, tol=1.5):
    """Linien, die Ende an Ende tangential weiterlaufen (genau zwei Enden im Punkt), zu einem Gleis zusammenhängen –
    so läuft ein Gleis über den Planrand in die Strecke und in den Nachbarplan weiter."""
    L = [np.array(p) for _, p, _ in linien]
    ends = []
    for i, p in enumerate(L):
        ends.append((i, 0, p[0], p[0] - p[min(1, len(p) - 1)])); ends.append((i, 1, p[-1], p[-1] - p[max(-2, -len(p))]))
    nb = collections.defaultdict(list)
    for a in range(len(ends)):
        for b in range(a + 1, len(ends)):
            if ends[a][0] != ends[b][0] and math.dist(ends[a][2], ends[b][2]) <= tol: nb[a].append(b); nb[b].append(a)
    paar = {}
    for a, bs in nb.items():
        if len(bs) != 1 or len(nb[bs[0]]) != 1: continue
        b = bs[0]; u, v = ends[a][3], -ends[b][3]
        nu, nv = np.linalg.norm(u), np.linalg.norm(v)
        if nu < 1e-6 or nv < 1e-6: continue
        if math.degrees(math.acos(max(-1, min(1, float(u @ v) / (nu * nv))))) < 25: paar[a] = b
    seen, out = set(), []
    for i in range(len(L)):
        if i in seen: continue
        # zum Anfang der Kette laufen
        cur, side = i, 0; guard = 0
        while (2 * cur + side) in paar and guard < len(L):
            j = paar[2 * cur + side]; cur, side = ends[j][0], 1 - ends[j][1]; guard += 1
            if cur == i: break
        start, sside = cur, side
        pts = []; cur, side = start, sside; guard = 0
        while guard <= len(L):
            seen.add(cur); p = L[cur] if side == 0 else L[cur][::-1]
            pts.extend(p.tolist() if not pts else p[1:].tolist())
            k = 2 * cur + (1 - side)
            if k not in paar: break
            j = paar[k]; cur, side = ends[j][0], ends[j][1]; guard += 1
            if cur in seen: break
        out.append(np.array(pts))
    return out


def s_kurven(linien, kreise, min_breite=1.0):
    alle = [p for w, p, _ in linien if w >= min_breite]
    if not alle: return []
    ketten = verketten([(w, p, s) for w, p, s in linien if w >= min_breite])
    from shapely.geometry import LineString, Point
    from shapely.strtree import STRtree
    segs = [LineString(p) for p in alle if len(p) >= 2]
    tree = STRtree(segs)
    def motiv(p, eigen):
        if any(math.dist(p, k) <= 8 for k in kreise): return True
        # anderes Gleis näher als 3 px (Weiche/Anschluss), das nicht Teil der eigenen Kette ist
        own = LineString(eigen); P = Point(p)
        for i in tree.query(P.buffer(3.0)):
            g = segs[int(i)]
            if g.distance(P) <= 3.0 and g.difference(own.buffer(0.8)).length > 1.0 and g.difference(own.buffer(0.8)).distance(P) <= 3.0:
                return True
        return False
    bef = []
    for k in ketten:
        q = _dp(k)
        if len(q) < 4: continue
        tw = []
        for i in range(1, len(q) - 1):
            u, v = q[i] - q[i - 1], q[i + 1] - q[i]
            tw.append(math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u @ v)) if np.linalg.norm(u) > 1e-6 and np.linalg.norm(v) > 1e-6 else 0.0)
        idx = [i for i, t in enumerate(tw) if abs(t) > 8]
        for a, b in zip(idx, idx[1:]):
            ta, tb = tw[a], tw[b]
            if ta * tb >= 0 or abs(ta + tb) >= 6: continue
            pa, pb = q[a + 1], q[b + 1]
            if np.linalg.norm(pb - pa) >= 200: continue
            if motiv(pa, k) and motiv(pb, k): continue
            m = (pa + pb) / 2
            if any(math.dist(m, (x["x"], x["y"])) < 15 for x in bef): continue
            bef.append(dict(regel="W53", x=round(float(m[0]), 1), y=round(float(m[1]), 1), winkel=round(abs(ta), 1)))
    return bef


def bahnhofsabstand(mitten, topo):
    """Variationskoeffizient px / km^0.75 über benachbarte Bahnhofspaare (Ketten über Nicht-Bahnhofsknoten)."""
    T = json.load(open(topo)) if isinstance(topo, str) else topo
    nodes = {n["id"]: n for n in T["nodes"]}
    adj = collections.defaultdict(list)
    for e in T["edges"]: adj[e["a"]].append((e["b"], e["length"])); adj[e["b"]].append((e["a"], e["length"]))
    st = {i for i, n in nodes.items() if n.get("kind") == "station" and n.get("name") in mitten}
    paare = {}
    for s in st:
        stack = [(s, 0.0, {s})]
        while stack:
            u, d, vis = stack.pop()
            for v, l in adj[u]:
                if v in vis: continue
                if v in st:
                    key = tuple(sorted((s, v))); paare[key] = min(paare.get(key, 1e18), d + l)
                elif nodes[v].get("kind") != "station" and d + l < 60000:
                    stack.append((v, d + l, vis | {v}))
    r = []
    for (a, b), m in paare.items():
        km = m / 1000.0
        if km < 0.2: continue
        px = math.dist(mitten[nodes[a]["name"]], mitten[nodes[b]["name"]])
        r.append(px / km ** 0.75)
    if len(r) < 3: return None, len(r)
    r = np.array(r); cv = float(np.std(r) / np.mean(r))
    return int(round(cv * 10)), len(r)


def _rects(svg_text):
    """Perrons (rect mit Höhe ≤ 10) als Punktpaare in Plan-Koordinaten (nur Bahnhofspläne, ohne Transform)."""
    out = []
    for r in re.findall(r"<rect\b[^>]*>", svg_text):
        g = {k: float(v) for k, v in re.findall(r'\s(x|y|width|height)="([-\d.]+)"', r)}
        if "width" in g and "height" in g and g["height"] <= 10 and g["width"] > 5:
            out.append(((g.get("x", 0), g.get("y", 0) + g["height"] / 2), (g.get("x", 0) + g["width"], g.get("y", 0) + g["height"] / 2)))
    return out


def laenge(linien, perrons=(), rand=120.0, nah=40.0):
    """Bahnhofslänge (REGELN 5.6): Leerlänge längs der Hauptachse = Stücke ohne Inhalt (Weiche, Perron, Prellbock/Gleisende
    ± nah px), abzüglich je rand px an beiden Planenden für die Ausfahrt. Rückgabe (Leerlänge px, Länge px, Weichen)."""
    L = [p for w, p, _ in linien if w >= 1.0]
    if not L: return None, None, 0
    P = np.vstack(L); m0 = P.mean(0); c = P - m0
    _, _, vt = np.linalg.svd(c, full_matrices=False); ax = vt[0]
    s = c @ ax; lo, hi = float(s.min()), float(s.max())
    ev = []
    for i, p in enumerate(L):
        for e in (p[0], p[-1]):
            pe = float((e - m0) @ ax)
            if pe - lo < 2 or hi - pe < 2: continue            # Planrand / Pfeil
            for j, q in enumerate(L):
                if i == j: continue
                d = np.hypot(*(q - e).T)
                if float(d.min()) <= 2.0: ev.append((pe - nah, pe + nah)); break
            else: ev.append((pe - nah, pe + nah))              # freies Gleisende (Prellbock)
    weichen = len(ev)
    for a_, b_ in perrons:
        pa, pb = float((np.array(a_) - m0) @ ax), float((np.array(b_) - m0) @ ax)
        ev.append((min(pa, pb) - nah, max(pa, pb) + nah))
    ev.append((lo, lo + rand)); ev.append((hi - rand, hi))
    ev.sort(); bedeckt = 0.0; cur = None
    for a_, b_ in ev:
        a_, b_ = max(a_, lo), min(b_, hi)
        if b_ <= a_: continue
        if cur and a_ <= cur[1]: cur[1] = max(cur[1], b_)
        else:
            if cur: bedeckt += cur[1] - cur[0]
            cur = [a_, b_]
    if cur: bedeckt += cur[1] - cur[0]
    return max(0.0, (hi - lo) - bedeckt), hi - lo, weichen


def messen(svg_text, key="", topo=None):
    linien, kreise, mitten = lesen(svg_text)
    region = key.startswith("region")
    out = {"W53": len(s_kurven(linien, kreise, 1.0 if region else 3.0))}
    if region and topo:
        try:
            v, n = bahnhofsabstand(mitten, topo)
            if v is not None: out["W55"] = v
        except Exception as e: print("W55", key, e, file=sys.stderr)
    if not region:
        leer, _, _ = laenge(linien, _rects(svg_text))
        if leer is not None: out["W56"] = int(round(leer / 100.0))
        out["W59"] = int(round(nebengleis_ueberlaenge(linien) / 100.0))
    return out


def nebengleis_ueberlaenge(linien, frei=80.0):
    """W59 (REGELN 5.9): leere Länge dünner Gleise über `frei` px hinaus. Seit 23.11.2026 (V4d, Daniel: Cornaux «wirkt gut
    gedrängt», Onnens-Bonvillars «eher zu lang»): gezählt wird nur ein gerades Stück eines dünnen Gleises zwischen zwei
    Ereignissen des Plans (Knickpunkt/Weiche/Ende irgendeines Gleises in der Längsrichtung) – ein Gleisfeld mit vielen
    Weichen nebeneinander ist nicht zu lang, ein einzelnes Abstellgleis ohne Nachbarn schon."""
    xs = np.array(sorted({round(float(p_[0]), 1) for _, pts, _ in linien for p_ in pts}))
    tot = 0.0
    for w, pts, _ in linien:
        if w >= 2.5: continue
        P_ = np.asarray(pts, float)
        for a_, b_ in zip(P_[:-1], P_[1:]):
            dx, dy = abs(b_[0] - a_[0]), abs(b_[1] - a_[1])
            if dx <= frei or dy > 0.05 * dx: continue
            x0, x1 = sorted((float(a_[0]), float(b_[0])))
            ev = [x0] + [x for x in xs if x0 + 0.5 < x < x1 - 0.5] + [x1]
            tot += sum(max(0.0, e1 - e0 - frei) for e0, e1 in zip(ev[:-1], ev[1:]))
    return tot


def summe(z):
    return sum(GEWICHT.get(k, 0) * v for k, v in z.items())


if __name__ == "__main__":
    f = sys.argv[1]; opt = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
    key = os.path.basename(f)[:-4]
    z = messen(open(f).read(), key, opt("--topo"))
    print(key, z, "Summe", summe(z))
    if opt("--json"): json.dump(z, open(opt("--json"), "w"))
