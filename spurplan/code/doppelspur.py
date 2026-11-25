"""Mass «Doppelspur-Abstand» (REGELN 1.4, Präzisierung Daniel 25.11.2026): eine durchgehende Doppelspur liegt im Plan
1 Ebene auseinander; mehr nur, wo ein Mittelperron zwischen den beiden Gleisen liegt.

  python3 doppelspur.py <netz.json> [...]            einzelne Netzmodelle (Bahnhofpläne, aus Workflow plaene/regionen)
  python3 doppelspur.py --alle <netz_dir> [--json out.json] [--md out.md]

Gemessen auf dem Netzmodell des Plans (gleise mit Ebene, knoten mit lat/lon und Planlage):
  Doppelspur-Paar = zwei Hauptgleise (kein service, nicht stillgelegt, gleiche Spur, gleiche Linie, wenn beide eine
  ref tragen), die in OSM über ≥ 40 m parallel (< 12°) im Abstand 3,0–6,5 m nebeneinander laufen.
  Befund **HD** = das Paar liegt im Plan nicht auf benachbarten Ebenen (|Δ Ebene| ≠ 1) und zwischen ihnen liegt kein
  Perron (Plan: Perron-y zwischen den beiden Gleisen, x überlappt). Gezählt je Paar (Way-Paar).
  **HDz** = dito, aber im Plan liegt ein anderes Gleis auf einer Ebene dazwischen (x überlappt): meist ein Neben- oder
  Überholgleis, das die Doppelspur auseinanderschiebt (REGELN 1.4: soll ausserhalb liegen) – getrennt gezählt.
Nur Messung (Leitplanke), keine Sperre. Gleise ohne Ebene (Schrägen) zählen nicht.
"""
import argparse, glob, json, math, os, sys

R = 6371000.0


def _xy(k, lat0):
    return (math.radians(k["lon"]) * R * math.cos(math.radians(lat0)), math.radians(k["lat"]) * R)


def _poly(g, K, lat0):
    return [_xy(K[str(n)], lat0) for n in g["knoten"] if str(n) in K and "lat" in K[str(n)]]


def _proj(p, P):
    """kürzester Abstand von p zur Polylinie P und Richtung des getroffenen Stücks"""
    best = (1e9, None)
    for (ax, ay), (bx, by) in zip(P, P[1:]):
        dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        if L2 < 1e-6: continue
        t = ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2
        if t < -0.02 or t > 1.02: continue
        t = min(1, max(0, t)); qx, qy = ax + t * dx, ay + t * dy
        d = math.hypot(p[0] - qx, p[1] - qy)
        if d < best[0]: best = (d, (dx, dy))
    return best


def _winkel(u, v):
    nu, nv = math.hypot(*u), math.hypot(*v)
    if nu < 1e-9 or nv < 1e-9: return 90
    c = abs(u[0] * v[0] + u[1] * v[1]) / nu / nv
    return math.degrees(math.acos(min(1.0, c)))


def _ueberlappung(A, B, dmin=3.0, dmax=6.5, wmax=12):
    """Länge von A (m), die parallel im Abstand dmin..dmax neben B läuft (Stücke von A in 5-m-Schritten abgetastet)"""
    L = 0.0
    for (ax, ay), (bx, by) in zip(A, A[1:]):
        dx, dy = bx - ax, by - ay; l = math.hypot(dx, dy)
        if l < 0.5: continue
        n = max(1, int(l // 5))
        for i in range(n):
            t = (i + 0.5) / n; p = (ax + t * dx, ay + t * dy)
            d, r = _proj(p, B)
            if r is not None and dmin <= d <= dmax and _winkel((dx, dy), r) <= wmax: L += l / n
    return L


def messen(N):
    K = N["knoten"]; lats = [k["lat"] for k in K.values() if "lat" in k]
    if not lats: return []
    lat0 = sum(lats) / len(lats)
    H = [g for g in N["gleise"] if not g.get("service") and not g.get("stillgelegt") and g.get("ebene") is not None]
    P = {g["id"]: _poly(g, K, lat0) for g in H}
    xs = {g["id"]: [K[str(n)]["x"] for n in g["knoten"] if str(n) in K and K[str(n)].get("x") is not None] for g in H}
    B = []
    for i, a in enumerate(H):
        for b in H[i + 1:]:
            if a.get("spur") != b.get("spur"): continue
            if a.get("ref") and b.get("ref") and a["ref"] != b["ref"]: continue
            if len(P[a["id"]]) < 2 or len(P[b["id"]]) < 2: continue
            L = max(_ueberlappung(P[a["id"]], P[b["id"]]), _ueberlappung(P[b["id"]], P[a["id"]]))
            if L < 40: continue
            de = abs(a["ebene"] - b["ebene"])
            if de == 1: continue
            y0, y1 = sorted((a["y"], b["y"]))
            xa, xb = xs[a["id"]], xs[b["id"]]
            x0, x1 = (max(min(xa), min(xb)), min(max(xa), max(xb))) if xa and xb else (-1e9, 1e9)
            if any(y0 < pr["y"] < y1 and min(pr["x0"], pr["x1"]) < x1 and max(pr["x0"], pr["x1"]) > x0 for pr in N.get("perrons", [])):
                continue
            e0, e1 = sorted((a["ebene"], b["ebene"]))
            zw = [g["way"] for g in N["gleise"] if g.get("ebene") is not None and e0 < g["ebene"] < e1 and g["id"] not in (a["id"], b["id"])
                  and any(x0 < K[str(n)]["x"] < x1 for n in g["knoten"] if str(n) in K and K[str(n)].get("x") is not None)]
            B.append(dict(regel="HDz" if zw else "HD", zwischen=zw[:5], ways=[a["way"], b["way"]], ref=a.get("ref") or b.get("ref"), ebenen=[a["ebene"], b["ebene"]],
                          parallel_m=round(L), text=f"Doppelspur {a['way']}/{b['way']} ({a.get('ref') or b.get('ref') or '–'}): "
                          f"{de} Ebenen auseinander statt 1, kein Perron dazwischen ({round(L)} m parallel)" + (f", Gleis dazwischen {zw[:3]}" if zw else "")))
    return B


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("netz", nargs="*"); ap.add_argument("--alle")
    ap.add_argument("--json"); ap.add_argument("--md"); A = ap.parse_args()
    files = sorted(glob.glob(os.path.join(A.alle, "*.json"))) if A.alle else A.netz
    tab = {}
    for f in files:
        key = os.path.basename(f)[:-5]
        for s in ("_netz",): key = key[:-len(s)] if key.endswith(s) else key
        try: N = json.load(open(f))
        except Exception: continue
        if not isinstance(N, dict) or "gleise" not in N: continue
        tab[key] = messen(N)
    summe = sum(len(v) for v in tab.values()); hd = sum(1 for v in tab.values() for b in v if b["regel"] == "HD")
    print(f"Doppelspur-Abstand: HD {hd}, HDz {summe - hd} in {sum(1 for v in tab.values() if v)} von {len(tab)} Plänen")
    for k, v in sorted(tab.items()):
        for b in v: print(f"  {k}: {b['regel']} {b['text']}")
    if A.json: json.dump(dict(zaehlung={k: {r: sum(1 for b in v if b["regel"] == r) for r in ("HD", "HDz")} for k, v in tab.items()}, befunde=tab), open(A.json, "w"), ensure_ascii=False, indent=1, sort_keys=True)
    if A.md:
        L = ["# Mass «Doppelspur-Abstand» (REGELN 1.4) – HD", "", f"{summe} Befunde in {sum(1 for v in tab.values() if v)} von {len(tab)} Plänen "
             "(Doppelspur nicht auf benachbarten Ebenen, ohne Perron dazwischen). Nur Messung, keine Sperre.", ""]
        for k, v in sorted(tab.items()):
            if v: L += [f"- **{k}** ({len(v)})"] + [f"  - {b['regel']} {b['text']}" for b in v]
        open(A.md, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
