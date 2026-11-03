"""Prüfung T5 «Gleis endet im Leeren» je Bahnhofsplan (3.11.2026, D. Eckenstein: oberste Regel Topologie; Saanen: Lücke
im Streckengleis mitten im Plan wurde von keiner Prüfung gemeldet).

  python3 gleisenden.py <ordner> [--json befunde.json]

Liest jeden <b>_spurplan.svg (und <b>_ports.json) im Ordner. Ein Ende eines dicken Gleises (Streckengleis) ist in Ordnung,
wenn dort ein anderes Gleis anschliesst (≤ 2.5 px), ein Anschluss/Abgang/Pfeil liegt (≤ 14 px), ein Prellbock (Kreis)
liegt oder es am Planrand (x_lo/x_hi ± 14 px) endet. Sonst: Befund T5 mit Lage.
"""
import re, sys, os, glob, json
import numpy as np
from svgpathtools import parse_path

def enden(svg):
    s = open(svg).read()
    paths = []
    for d, w in re.findall(r'<path d="([^"]+)" stroke="[^"]+" stroke-width="([\d.]+)"', s):
        try: p = parse_path(d)
        except Exception: continue
        for sub in p.continuous_subpaths():
            if sub.length() < 1: continue
            pts = [sub.point(t) for t in np.linspace(0, 1, max(2, int(sub.length() / 2)))]
            paths.append((float(w), np.array([[z.real, z.imag] for z in pts])))
    kreise = [(float(x), float(y)) for x, y in re.findall(r'<circle cx="([-\d.]+)" cy="([-\d.]+)"', s)]
    # seitliche Abgänge enden an ihrer Beschriftung («Linie 914 / Susch →»), nicht am Anschlusspunkt
    texte = [(float(x), float(y)) for x, y, t in re.findall(r'<text x="([-\d.]+)" y="([-\d.]+)"[^>]*>([^<]*)</text>', s) if t.startswith("Linie") or "→" in t or "←" in t]
    return paths, kreise, texte

def pruefe(svg, ports):
    paths, kreise, texte = enden(svg)
    alle = np.vstack([p for _, p in paths]) if paths else np.zeros((0, 2))
    P = json.load(open(ports)) if os.path.exists(ports) else {}
    marken = [(q["x"], q["y"]) for q in P.get("ports", [])] + [(q["x"], q["y"]) for q in P.get("pfeile", [])] + kreise
    x_lo, x_hi = P.get("x_lo", -1e9), P.get("x_hi", 1e9)
    bef = []
    for i, (w, pts) in enumerate(paths):
        if w < 3.0: continue                      # nur Streckengleise (dick)
        for e in (pts[0], pts[-1]):
            if any(np.hypot(*(np.array(m) - e)) <= 14 for m in marken): continue
            # seitlicher Abgang: Ende liegt auf dem 60°-Strahl ab dem Anschlusspunkt (Sasslatsch, Sagliains Sasslatsch)
            _seit = False
            for q in P.get("ports", []):
                if q.get("kind") != "side": continue
                o_ = np.array([q["x"], q["y"]]); u_ = np.array([q["dx"] * 0.5, q["dy"] * 0.866]); u_ = u_ / (np.linalg.norm(u_) or 1)
                t_ = float((e - o_) @ u_)
                if 0 < t_ < 250 and np.linalg.norm(e - o_ - u_ * t_) < 8: _seit = True
                if 0 < t_ < 250 and np.linalg.norm(e - o_ - np.array([u_[0], -u_[1]]) * t_) < 8: _seit = True
            if _seit: continue
            if e[0] <= x_lo + 14 or e[0] >= x_hi - 14: continue
            andere = np.vstack([p for j, (_, p) in enumerate(paths) if j != i]) if len(paths) > 1 else np.zeros((0, 2))
            # eigenes Gleis: Punkte weiter als 6 px vom Ende zählen auch (Bogen zurück auf sich selbst)
            weit = pts[np.hypot(*(pts - e).T) > 6]
            kand = np.vstack([andere, weit]) if len(weit) else andere
            if len(kand) and np.min(np.hypot(*(kand - e).T)) <= 2.5: continue
            bef.append(dict(regel="T5", x=round(float(e[0]), 1), y=round(float(e[1]), 1)))
    return bef

if __name__ == "__main__":
    ordner = sys.argv[1]; out = []
    for f in sorted(glob.glob(os.path.join(ordner, "*_spurplan.svg"))):
        b = os.path.basename(f)[:-len("_spurplan.svg")]
        for x in pruefe(f, os.path.join(ordner, f"{b}_ports.json")):
            x["plan"] = b; x["text"] = f"{b}: Streckengleis endet im Leeren bei x={x['x']}, y={x['y']}"; out.append(x)
    for x in out: print("T5", x["text"])
    print(f"T5: {len(out)} Befunde")
    if "--json" in sys.argv: json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), ensure_ascii=False, indent=1)
