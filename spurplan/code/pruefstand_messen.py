"""Messungen des Blaupausen-Prüfstands (Schritt 1, 8.11.2026) – nur messen, nichts korrigieren.

  python3 pruefstand_messen.py <plan.svg> [--lane 10.08] [--json out.json]

Grundsatz (D. Eckenstein 6.11.2026): parallel bleibt parallel im gleichen Querabstand – gemessen quer zum Gleis –, egal
wie der Plan gedreht ist und unter welchem Winkel ein Gleis ihn verlässt. Gemessen wird auf der gezeichneten Geometrie
(alle Transformationen der Bahnhofspläne aufgelöst), in Plan-Pixeln:

  Q   Querabstand: zwei parallele Gleisstücke (< 2°), > 2 Ebenen lang nebeneinander, Abstand 0,3–1,6 Ebenen, aber nicht
      eine Ebene (Toleranz 12 %)                                   -> «zu eng» / «zu weit»
  P   parallel bleibt parallel: zwei Gleisstücke nebeneinander (< 1,6 Ebenen), > 2 Ebenen lang, mit 1,5–20° Winkel
      (eines läuft schräg weg)
  F   Pfeile im Gleisabstand: zwei gleichgerichtete Pfeile (< 5°) näher als 2,5 Ebenen, quer nicht ein Vielfaches der Ebene
  K   nichts unter 90°: Ecke einer Linie, die um mehr als 90° umkehrt (Spitzkehre)
  Z   Zwischengerade: gerades Stück zwischen zwei Ecken (> 8°) kürzer als 2 Ebenen, ohne dass dort ein anderes Gleis
      anschliesst
  E   Ebenenwechsel ohne Weiche: eine Linie versetzt sich quer (0,4–2,5 Ebenen, Richtung danach wie davor) über zwei Ecken,
      an denen kein anderes Gleis anschliesst (keine Weiche, keine Werfung)
  X   Kreuzung ohne Knoten: zwei Gleise kreuzen sich, beide durchgezogen (bei Niveautrennung gehört eine Lücke ins untere)
  T   Strecken am Planrand: je Beschriftung «Linie <ref>» die Zahl der Gleisenden daneben (fehlt eine Strecke oder ein
      Gleis, zeigt die Erwartung des Bausteins den Befund)
  PF  Perronflächen: Zahl der zusammenhängenden Perronflächen und Balken je Fläche (Formen U/L/T = mehrere Balken in
      einer Fläche)
Dazu (aus regel_pruefung.py, gleiche Definitionen wie im Workflow): G2 Weiche ohne Ausrundung, G3 Ecke ohne Ausrundung,
G4 90°, G5 Kreuzung von Spurwechseln, G6 Knubbel, G7 Gleis nicht angebunden, G8 doppelt.
"""
import re, sys, os, json, math, subprocess, argparse, collections
import numpy as np
import xml.etree.ElementTree as ET
from svgpathtools import parse_path, Line, QuadraticBezier, CubicBezier

NS = "{http://www.w3.org/2000/svg}"
GLEISFARBEN = {"#00862f", "#111", "#111111", "#000", "#9a5b1e", "#9a5b1f"}


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


def _tp(M, z): v = M @ np.array([z.real, z.imag, 1.0]); return np.array([v[0], v[1]])


def lesen(svg_text):
    """-> linien [(pts Nx2, breite)], pfeile [(spitze, richtung)], perrons [Polygon 4x2], punkte"""
    root = ET.fromstring(svg_text)
    linien, pfeile, perrons, punkte = [], [], [], []
    texte = []

    def walk(el, M, col, w, fill):
        tag = el.tag.replace(NS, "")
        M = M @ _mat(el.get("transform"))
        col = el.get("stroke", col); w = el.get("stroke-width", w); fill = el.get("fill", fill)
        if tag == "text":
            t_ = "".join(el.itertext()).strip()
            if t_: texte.append((_tp(M, complex(float(el.get("x", 0)), float(el.get("y", 0)))), t_))
            return
        if tag == "circle":
            punkte.append(_tp(M, complex(float(el.get("cx", 0)), float(el.get("cy", 0)))))
        if tag == "rect" and el.get("fill") in GLEISFARBEN and float(el.get("height", 0)) <= 10:
            x, y, W, H = (float(el.get(k, 0)) for k in ("x", "y", "width", "height"))
            perrons.append(np.array([_tp(M, complex(a, b)) for a, b in ((x, y), (x + W, y), (x + W, y + H), (x, y + H))]))
        if tag == "path" and el.get("d"):
            if el.get("stroke-opacity") or el.get("data-fluegel") or el.get("stroke-dasharray"): return
            try: P = parse_path(el.get("d"))
            except Exception: return
            sc = math.sqrt(abs(np.linalg.det(M[:2, :2])))
            if col in GLEISFARBEN and (fill in (None, "none")):
                for sub in P.continuous_subpaths():
                    pts = []
                    for seg in sub:
                        if seg.length() < 0.05: continue
                        if isinstance(seg, Line): q = [seg.start, seg.end]
                        elif isinstance(seg, QuadraticBezier): q = [seg.start, seg.control, seg.end]       # Ausrundung -> Ecke
                        else: q = [seg.point(t) for t in np.linspace(0, 1, 6)]
                        for z in q:
                            p = _tp(M, z)
                            if not pts or np.linalg.norm(p - pts[-1]) > 0.05: pts.append(p)
                    if len(pts) >= 2: linien.append((np.array(pts), float(w or 1) * sc))
            elif fill in GLEISFARBEN and (col in (None, "none") or el.get("stroke") is None):
                pts = [_tp(M, s.start) for s in P]
                if 3 <= len(pts) <= 4:
                    pts = pts[:3]
                    kanten = [(np.linalg.norm(pts[i] - pts[(i + 1) % 3]), i) for i in range(3)]
                    _, i = min(kanten)                       # kürzeste Kante = Grundlinie
                    a, b = pts[i], pts[(i + 1) % 3]; tip = pts[(i + 2) % 3]
                    d = tip - (a + b) / 2
                    if np.linalg.norm(d) > 0.5: pfeile.append((tip, d / np.linalg.norm(d)))
        for c in el: walk(c, M, col, w, fill)

    walk(root, np.eye(3), None, None, None)
    lesen.texte = texte
    return linien, pfeile, perrons, punkte


def _dp(pts, tol=0.35):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; ab = b - a; L = np.linalg.norm(ab)
    d = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / L if L > 1e-9 else np.linalg.norm(pts - a, axis=1)
    i = int(np.argmax(d))
    if d[i] > tol: return np.vstack([_dp(pts[:i + 1], tol)[:-1], _dp(pts[i:], tol)])
    return np.array([a, b])


def _winkel(u, v):
    c = float(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v)), -1, 1)); return math.degrees(math.acos(c))


def messen(svg_text, lane):
    linien, pfeile, perrons, punkte = lesen(svg_text)
    polys = [(_dp(p), w) for p, w in linien]
    segs = []                         # (a, b, u, L, linie)
    for li, (p, w) in enumerate(polys):
        for a, b in zip(p, p[1:]):
            L = float(np.linalg.norm(b - a))
            if L > 0.5: segs.append((a, b, (b - a) / L, L, li))
    B = []

    def bef(r, p, t, **k): B.append(dict(regel=r, x=round(float(p[0]), 1), y=round(float(p[1]), 1), text=t, **k))

    # Q / P: Paare von Gleisstücken
    ueberlapp_min = 2 * lane; gesehen = set()
    for i in range(len(segs)):
        a1, b1, u1, L1, l1 = segs[i]
        if L1 < ueberlapp_min: continue
        n1 = np.array([-u1[1], u1[0]])
        for j in range(i + 1, len(segs)):
            a2, b2, u2, L2, l2 = segs[j]
            if l1 == l2 or L2 < ueberlapp_min: continue
            w = _winkel(u1, u2); w = min(w, 180 - w)
            if w > 20: continue
            # Längsüberlappung entlang u1
            s2 = sorted((float((a2 - a1) @ u1), float((b2 - a1) @ u1)))
            lo, hi = max(0.0, s2[0]), min(L1, s2[1])
            if hi - lo < ueberlapp_min: continue
            d_a = float((a2 - a1) @ n1); d_b = float((b2 - a1) @ n1)
            # Querabstand in der Mitte der Überlappung
            t_m = (lo + hi) / 2
            pm = a1 + u1 * t_m
            v2 = b2 - a2; tt = float((pm - a2) @ v2 / (v2 @ v2)); q2 = a2 + v2 * min(1, max(0, tt))
            dq = float(abs((q2 - pm) @ n1))
            if dq < 0.3 * lane or dq > 1.6 * lane: continue
            key = (l1, l2) if l1 < l2 else (l2, l1)
            if w < 2:
                if abs(dq - lane) > 0.12 * lane and (key, "Q") not in gesehen:
                    gesehen.add((key, "Q")); bef("Q", pm, f"Querabstand {dq:.1f} px statt {lane:.1f}", wert=round(dq, 2))
            elif w >= 1.5 and (key, "P") not in gesehen:
                gesehen.add((key, "P")); bef("P", pm, f"Gleise nebeneinander nicht parallel ({w:.1f}°)", wert=round(w, 1))

    # F: Pfeile
    for i in range(len(pfeile)):
        for j in range(i + 1, len(pfeile)):
            (p1, d1), (p2, d2) = pfeile[i], pfeile[j]
            if _winkel(d1, d2) > 5 or np.linalg.norm(p2 - p1) > 2.5 * lane: continue
            n = np.array([-d1[1], d1[0]]); q = abs(float((p2 - p1) @ n)); k = round(q / lane)
            if k < 1 or abs(q - k * lane) > 0.15 * lane:
                bef("F", (p1 + p2) / 2, f"Pfeile quer {q:.1f} px auseinander (Ebene {lane:.1f})", wert=round(q, 2))

    # Enden und Anschlusspunkte für «motiviert»
    enden = [(li, p[0], p[1] - p[0]) for li, (p, w) in enumerate(polys)] + [(li, p[-1], p[-2] - p[-1]) for li, (p, w) in enumerate(polys)]
    def anschluss(p, li):
        """schliesst bei p ein anderes Gleis an (nicht nur gerade Fortsetzung)? Weiche, Werfung, Pfeil, Prellbock"""
        for lj, q, v in enden:
            if lj != li and np.linalg.norm(q - p) < 2.5: return True
        for a, b, u, L, lj in segs:
            if lj == li: continue
            t = float((p - a) @ u)
            if -1 < t < L + 1 and abs(float((p - a) @ np.array([-u[1], u[0]]))) < 2.0: return True
        return any(np.linalg.norm(q - p) < 4 for q in punkte) or any(np.linalg.norm(q - p) < 6 for q, _ in pfeile)

    for li, (p, w) in enumerate(polys):
        if len(p) < 3: continue
        ecken = []
        for k in range(1, len(p) - 1):
            u, v = p[k] - p[k - 1], p[k + 1] - p[k]
            t = _winkel(u, v)
            if t > 90.5: bef("K", p[k], f"Spitzkehre {t:.0f}°", wert=round(t))
            if t > 8: ecken.append(k)
        for k1, k2 in zip(ecken, ecken[1:]):
            L = float(np.linalg.norm(p[k2] - p[k1]))
            mot1, mot2 = anschluss(p[k1], li), anschluss(p[k2], li)
            if L < 2 * lane and not (mot1 or mot2):
                bef("Z", (p[k1] + p[k2]) / 2, f"Zwischengerade {L:.1f} px", wert=round(L, 1))
            # Versatz: Richtung vor k1 = nach k2
            u0, u1_ = p[k1] - p[k1 - 1], p[k2 + 1] - p[k2]
            if _winkel(u0, u1_) < 3:
                n0 = np.array([-u0[1], u0[0]]) / np.linalg.norm(u0); q = abs(float((p[k2] - p[k1]) @ n0))
                if 0.4 * lane < q < 2.5 * lane and not (mot1 or mot2):      # grösserer Versatz des ganzen Bündels = Lage (T7)
                    bef("E", (p[k1] + p[k2]) / 2, f"Ebenenwechsel {q:.1f} px ohne Weiche", wert=round(q, 1))

    # X: zwei Gleise kreuzen sich, beide durchgezogen, ohne Knoten (Unter-/Überwerfung muss eine Lücke im unteren haben)
    def _schnitt(a, b, c, d):
        r, q = b - a, d - c; den = r[0] * q[1] - r[1] * q[0]
        if abs(den) < 1e-9: return None
        t = ((c - a)[0] * q[1] - (c - a)[1] * q[0]) / den; u = ((c - a)[0] * r[1] - (c - a)[1] * r[0]) / den
        return a + r * t if 0.02 < t < 0.98 and 0.02 < u < 0.98 else None
    xs = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            a1, b1, u1, L1, l1 = segs[i]; a2, b2, u2, L2, l2 = segs[j]
            if l1 == l2 or _winkel(u1, u2) < 10 or _winkel(u1, u2) > 170: continue
            p_ = _schnitt(a1, b1, a2, b2)
            if p_ is None: continue
            # Ende einer dritten Linie im Schnittpunkt = Knoten (DKW/Kreuzung mit Weiche)
            if any(np.linalg.norm(q - p_) < 2.0 for _, q, _ in enden): continue
            if any(np.linalg.norm(p_ - x) < 3 for x in xs): continue
            xs.append(p_); bef("X", p_, f"Gleise kreuzen sich ohne Knoten und ohne Lücke ({_winkel(u1, u2):.0f}°)")

    # T: Strecke je Linienbeschriftung am Planrand – Zahl der Gleisenden nahe der Beschriftung «Linie <ref>»
    strecken = {}
    for p_, t_ in getattr(lesen, "texte", []):
        m_ = re.match(r"Linien? ?([\d /]*)$", t_)
        if not m_: continue
        n_ = sum(1 for _, q, _ in enden if np.linalg.norm(q - p_) < 45)
        for r_ in (re.findall(r"\d+", m_.group(1)) or ["?"]): strecken.setdefault(r_, []).append(n_)

    # freie Gleisenden (Abgänge am Planrand): Ende ohne anderes Gleis, Prellbock oder Pfeil daneben
    frei = 0
    for li, q, v in enden:
        if any(lj != li and np.linalg.norm(q - q2) < 2.5 for lj, q2, _ in enden): continue
        if any(lj != li and -1 < float((q - a) @ u) < L + 1 and abs(float((q - a) @ np.array([-u[1], u[0]]))) < 2.0 for a, b, u, L, lj in segs): continue
        if any(np.linalg.norm(q - d_) < 6 for d_ in punkte) or any(np.linalg.norm(q - t_) < 16 for t_, _ in pfeile): continue
        frei += 1

    # PF: Perronflächen (Balken, die sich berühren, bilden eine Fläche)
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    pg = [Polygon(r).buffer(0.8) for r in perrons]
    flaechen = []
    if pg:
        u = unary_union(pg); geoms = list(u.geoms) if hasattr(u, "geoms") else [u]
        for g in geoms: flaechen.append(sum(1 for x in pg if x.intersects(g)))
    zaehl = collections.Counter(b["regel"] for b in B)
    return dict(zaehl=dict(zaehl), befunde=B, perron_flaechen=sorted(flaechen, reverse=True), linien=len(polys), pfeile=len(pfeile),
                strecken={k: sorted(v) for k, v in sorted(strecken.items())}, freie_enden=frei)


def regeln(svg_pfad):
    """G2–G8 aus regel_pruefung.py (gleiche Definitionen wie in den Workflows)"""
    here = os.path.dirname(os.path.abspath(__file__)); out = svg_pfad + ".regeln.json"
    subprocess.run([sys.executable, os.path.join(here, "regel_pruefung.py"), svg_pfad, "--json", out], capture_output=True, text=True)
    try: return dict(collections.Counter(b["regel"] for b in json.load(open(out)) if b["regel"] != "G1"))
    except Exception: return {"fehler": 1}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("svg"); ap.add_argument("--lane", type=float, default=24 * 0.42); ap.add_argument("--json")
    A = ap.parse_args()
    m = messen(open(A.svg).read(), A.lane); m["regeln"] = regeln(A.svg)
    if A.json: json.dump(m, open(A.json, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: m[k] for k in ("zaehl", "regeln", "perron_flaechen", "linien", "pfeile", "strecken")}, ensure_ascii=False))
    for b in m["befunde"][:40]: print(" ", b)
