"""Prüfung T7 «unmotivierte Ecke / Treppe» (Ruhe-Kennzahl, 4.11.2026, D. Eckenstein: «Ruhe bedeutet vor allem keine
Treppen oder unmotiviert erscheinende Ecken – unmotiviert, weil es auf kurzer Ebene und ohne sonstige Änderung passiert»).

  python3 ruhe.py <ordner> [--json ruhe.json]          je Bahnhofsplan <b>_spurplan.svg
  (Regionalplan: netz_lage.py --pruefen, gleiche Definition auf den Strecken zwischen den Plänen)

Ein Gleis wird in gerade Stücke zerlegt (Knick > 8°). Eine Ecke ist motiviert, wenn dort ein anderes Gleis anschliesst
(Weiche, ≤ 3 px), ein Anschluss/Pfeil/Prellbock liegt oder sie am Planrand liegt. Befunde:
  T7 Treppe  zwei unmotivierte Ecken in Gegenrichtung (Versatz, Netto-Richtung gleich), dazwischen < 80 px
  T7 Ecke    eine unmotivierte Ecke > 8°, deren Schenkel beide kürzer als 40 px sind (kurzes Hin und Her)
"""
import re, sys, os, glob, json, math
import numpy as np
from svgpathtools import parse_path, Line

def _polys(svg):
    s = open(svg).read(); out = []
    for el in re.findall(r'<path\b[^>]*>', s):
        m_d = re.search(r'\sd="([^"]+)"', el); m_w = re.search(r'stroke-width="([\d.]+)"', el)
        if not m_d or not m_w or 'stroke="none"' in el or '#8a8a8a' in el: continue      # Tunnelportale (grau) zählen nicht
        if 'data-fluegel="1"' in el: continue                                                 # Brückenflügel an Kreuzungen (U-Abgang, 7.11.)
        d, w = m_d.group(1), m_w.group(1)
        try: p = parse_path(d)
        except Exception: continue
        for sub in p.continuous_subpaths():
            pts = []
            for seg in sub:
                if seg.length() < 0.3: continue
                if isinstance(seg, Line): q = [seg.start, seg.end]
                else: q = [seg.point(t) for t in np.linspace(0, 1, 5)]
                for z in q:
                    if not pts or abs(z - pts[-1]) > 0.3: pts.append(z)
            if len(pts) >= 2: out.append((float(w), np.array([[z.real, z.imag] for z in pts])))
    kreise = [(float(re.search(r'cx="([-\d.]+)"', c).group(1)), float(re.search(r'cy="([-\d.]+)"', c).group(1)))
              for c in re.findall(r'<circle\b[^>]*>', s) if 'cx="' in c and 'cy="' in c]
    return out, kreise

def _vereinfachen(pts, tol=1.2):
    """Douglas-Peucker: Bögen der Ausrundung werden zu einer Ecke."""
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; ab = b - a; L = np.linalg.norm(ab) or 1e-9
    r_ = pts[1:-1] - a; d = np.abs(ab[0] * r_[:, 1] - ab[1] * r_[:, 0]) / L
    i = int(np.argmax(d)) + 1
    if d[i - 1] <= tol: return np.array([a, b])
    return np.vstack([_vereinfachen(pts[:i + 1], tol)[:-1], _vereinfachen(pts[i:], tol)])

def ecken(pts):
    """Ecken einer Linie: (Index, Punkt, Winkel mit Vorzeichen in Grad, Länge davor, Länge danach)."""
    q = _vereinfachen(pts); out = []
    for i in range(1, len(q) - 1):
        u, v = q[i] - q[i - 1], q[i + 1] - q[i]
        lu, lv = np.linalg.norm(u), np.linalg.norm(v)
        if lu < 1e-6 or lv < 1e-6: continue
        a = math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u @ v))
        if abs(a) > 8: out.append((i, q[i], a, lu, lv))
    return out, q

def pruefe_linien(linien, motiv, rand=None):
    """linien: [(Breite, pts)], motiv(p) -> True wenn an diesem Punkt etwas anschliesst (Weiche, Anschluss, Prellbock).
    Treppe: innerhalb von 100 px dreht die Linie um mehr als 12° und wieder zurück (Netto < 6°), ohne dass dazwischen
    etwas anschliesst. Ecke: einzelner Knick > 8° mit beiden Schenkeln < 40 px, unbegründet."""
    bef = []
    for w, pts in linien:
        q = _vereinfachen(pts, 2.5)
        if len(q) < 3: continue
        tw = [0.0]
        for i in range(1, len(q) - 1):
            u, v = q[i] - q[i - 1], q[i + 1] - q[i]
            tw.append(math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u @ v)) if np.linalg.norm(u) > 1e-6 and np.linalg.norm(v) > 1e-6 else 0.0)
        tw.append(0.0)
        mot = [motiv(p_) for p_ in q]
        i = 1; belegt = set()
        while i < len(q) - 1:
            if abs(tw[i]) < 2 or mot[i]: i += 1; continue
            cum, mx, j, ok = 0.0, 0.0, i, None
            while j < len(q) - 1 and np.linalg.norm(q[j] - q[i]) < 100:
                if mot[j]: break
                cum += tw[j]; mx = max(mx, abs(cum))
                if j > i and mx > 12 and abs(cum) < 6: ok = j; break
                j += 1
            if ok:
                m_ = (q[i] + q[ok]) / 2
                bef.append(dict(regel="T7", art="Treppe", x=round(float(m_[0]), 1), y=round(float(m_[1]), 1), versatz=round(float(np.linalg.norm(q[ok] - q[i])), 1)))
                belegt |= set(range(i, ok + 1)); i = ok + 1
            else: i += 1
        for i in range(1, len(q) - 1):
            if i in belegt or abs(tw[i]) <= 8 or mot[i]: continue
            lu, lv = np.linalg.norm(q[i] - q[i - 1]), np.linalg.norm(q[i + 1] - q[i])
            if lu < 40 and lv < 40 and not ((lu <= 60 and mot[i - 1]) or (lv <= 60 and mot[i + 1])):
                bef.append(dict(regel="T7", art="Ecke", x=round(float(q[i][0]), 1), y=round(float(q[i][1]), 1), winkel=round(tw[i], 1)))
    # nahe Befunde zusammenfassen (eine Stelle)
    out = []
    for x in bef:
        if any(math.dist((x["x"], x["y"]), (o["x"], o["y"])) < 15 for o in out): continue
        out.append(x)
    return out

def pruefe_plan(svg, ports):
    linien, kreise = _polys(svg)
    P = json.load(open(ports)) if os.path.exists(ports) else {}
    marken = [(q["x"], q["y"]) for q in P.get("ports", []) + P.get("pfeile", [])] + kreise
    x_lo, x_hi = P.get("x_lo", -1e9), P.get("x_hi", 1e9)
    alle = [(i, p) for i, (_, p) in enumerate(linien)]
    def motiv_fuer(i0):
        andere = np.vstack([p for i, p in alle if i != i0]) if len(alle) > 1 else np.zeros((0, 2))
        def m(p):
            if p[0] <= x_lo + 12 or p[0] >= x_hi - 12: return True
            if any(math.dist(p, k) <= 14 for k in marken): return True
            return bool(len(andere)) and float(np.min(np.hypot(*(andere - p).T))) <= 6.0
        return m
    bef = []
    for i, (w, pts) in enumerate(linien):
        if w < 3.0: continue                       # Streckengleise (dick); Nebengleise folgen ihren Weichen
        bef += pruefe_linien([(w, pts)], motiv_fuer(i))
    return bef

def pruefe_region(svg):
    """Regionalplan: Linien ausserhalb der eingebetteten Spurpläne (Strecken, Nebengleis-Verbindungen)."""
    import xml.etree.ElementTree as ET
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree = ET.parse(svg); root = tree.getroot()
    def _weg(el):                                   # Spurpläne (g mit data-st) heraus, auch verschachtelt
        for ch in list(el):
            if ch.get("data-st") is not None: el.remove(ch)
            else: _weg(ch)
    _weg(root)
    tmp = svg + ".ruhe.svg"; tree.write(tmp)
    linien, kreise = _polys(tmp); os.remove(tmp)
    linien = [(w, p) for w, p in linien if w >= 1.0 and len(p) >= 2]
    alle = [(i, p) for i, (_, p) in enumerate(linien)]
    def motiv_fuer(i0):
        andere = np.vstack([p for i, p in alle if i != i0]) if len(alle) > 1 else np.zeros((0, 2))
        def m(p):
            if any(math.dist(p, k) <= 8 for k in kreise): return True
            return bool(len(andere)) and float(np.min(np.hypot(*(andere - p).T))) <= 2.5
        return m
    bef = []
    for i, (w, pts) in enumerate(linien):
        for x in pruefe_linien([(w, pts)], motiv_fuer(i)):
            x["neben"] = w < 2.0; bef.append(x)
    return bef

if __name__ == "__main__":
    if "--region" in sys.argv:
        out = pruefe_region(sys.argv[sys.argv.index("--region") + 1])
        for x in out: x["plan"] = "Regionalplan"; x["text"] = f"Regionalplan: {x['art']} bei x={x['x']}, y={x['y']}" + (" (Nebengleis)" if x["neben"] else "")
        for x in out: print("T7", x["text"])
        print(f"T7 Regionalplan: {len(out)} Befunde ({sum(1 for x in out if x['art'] == 'Treppe')} Treppen)")
        if "--json" in sys.argv: json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), ensure_ascii=False, indent=1)
        sys.exit(0)
    ordner = sys.argv[1]; out = []
    for f in sorted(glob.glob(os.path.join(ordner, "*_spurplan.svg"))):
        b = os.path.basename(f)[:-len("_spurplan.svg")]
        for x in pruefe_plan(f, os.path.join(ordner, f"{b}_ports.json")):
            x["plan"] = b; x["text"] = f"{b}: {x['art']} bei x={x['x']}, y={x['y']}"; out.append(x)
    for x in out: print("T7", x["text"])
    print(f"T7: {len(out)} Befunde ({sum(1 for x in out if x['art'] == 'Treppe')} Treppen, {sum(1 for x in out if x['art'] == 'Ecke')} Ecken)")
    if "--json" in sys.argv: json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), ensure_ascii=False, indent=1)
