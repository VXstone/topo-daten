"""Prüfungen auf dem Netzmodell (D. Eckenstein 25.10.2026: «Gleise als Netz mit Koordinaten»).

  python3 netz_pruefung.py <bahnhof>          liest <bahnhof>_netz.json (spurplan_schema) und <bahnhof>.json (OSM)

Jeder Befund nennt die Regel-ID aus dem Regelkatalog (Doc «Regelwerk Spurpläne», Tab Regelkatalog), Plankoordinaten
und die OSM-Elemente. Ausgabe: <bahnhof>_netz_befunde.json und eine Zusammenfassung auf stdout.

Regeln (v1):
  T10  Durchfahrgleis grün: Gleis, das an beiden Enden über Weichen ohne Richtungswechsel ins Streckengleis führt,
       ist im Personenverkehr befahrbar (Ausnahme service=yard), sofern zwischen den Anschlüssen mindestens
       200 m Nebengleis liegen und das Gleis selbst mindestens 100 m lang ist oder eine Gleisnummer hat (sonst
       Verbindungsstück/Spurwechsel, schwarz nach E1) und es an beiden Enden direkt am Hauptgleis hängt (höchstens
       2 Weichen bis zum Hauptgleis, sonst Abstellgruppe); gezeichnet schwarz = Befund
  A5   Perron neben seinem Gleis: kein Gleis läuft durch das Perron
  D11  Gleisnummer nur an Perrongleisen: jede gezeichnete Nummer hat ein Perron daneben
  D12  Perrons vollständig: jede Gleisnummer mit Perron in OSM/SBB ist gezeichnet (Zählung)
  S1   Weichen sichtbar: jede OSM-Weiche im Planfenster liegt auf einem gezeichneten Gleis
  D6   Stillgelegtes nicht zeichnen
  Z2   Abgang mit Linie und Richtungsort; Pfeil der Beschriftung zeigt in die Richtung des Abgangs
  aus der gezeichneten Geometrie (<bahnhof>_spurplan.svg, Gleislinien 3.6/1.6 px):
  W2   jedes Gleisstück ab 10 px waagrecht oder 60°
  F2   Knick um mehr als 60° ohne Weiche (Haken, Spitzkehre)
  A1   zwei parallele Gleise enger als 20 px (Hauptgleise) bzw. 9.6 px (40 %, mit Nebengleis) über mind. 12 px
"""
import json, math, sys, collections

B = sys.argv[1]
N = json.load(open(f"{B}_netz.json"))
_raw = json.load(open(f"{B}.json"))
if isinstance(_raw, dict) and "elements" not in _raw:
    _raw = _raw.get(B) or next(iter(_raw.values()))
OSM = _raw["elements"] if isinstance(_raw, dict) else _raw

BEF = []
def bef(regel, x, y, text, **osm):
    BEF.append(dict(regel=regel, x=round(x, 1) if x is not None else None, y=round(y, 1) if y is not None else None,
                    text=text, **osm))

KN = N["knoten"]
LAT0 = sum(v["lat"] for v in KN.values()) / max(1, len(KN))
KX, KY = 111320 * math.cos(math.radians(LAT0)), 110540
m_xy = lambda lat, lon: (lon * KX, lat * KY)

# ---- OSM-Graph (Normalspur und Schmalspur, ohne Stillgelegtes)
WAYS = {e["id"]: e for e in OSM if e["type"] == "way" and e.get("tags", {}).get("railway") in ("rail", "narrow_gauge")
        and not e["tags"].get("disused")}
P = {}
NB = collections.defaultdict(set)
WAY_OF_EDGE = {}
for w in WAYS.values():
    for n, g in zip(w["nodes"], w["geometry"]): P[n] = m_xy(g["lat"], g["lon"])
    for a, b in zip(w["nodes"], w["nodes"][1:]):
        NB[a].add(b); NB[b].add(a); WAY_OF_EDGE[(a, b)] = WAY_OF_EDGE[(b, a)] = w["id"]
haupt = lambda wid: WAYS[wid]["tags"].get("service") is None

def winkel(a, b, c):
    """Richtungsänderung in Grad beim Weg a→b→c"""
    v1 = (P[b][0] - P[a][0], P[b][1] - P[a][1]); v2 = (P[c][0] - P[b][0], P[c][1] - P[b][1])
    l1, l2 = math.hypot(*v1), math.hypot(*v2)
    if l1 < 1e-6 or l2 < 1e-6: return 0.0
    return math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))))

def weg_zum_haupt(prev, cur, max_m=1500, max_dreh=40):
    """Fährt ab (prev→cur) ohne Richtungswechsel weiter; Länge auf Nebengleisen bis zum ersten Hauptgleis (ohne
    service), None wenn keines erreichbar"""
    import heapq
    seen = set(); hq = [(0.0, prev, cur)]
    while hq:
        d, a, b = heapq.heappop(hq)
        if (a, b) in seen or d > max_m: continue
        seen.add((a, b))
        if haupt(WAY_OF_EDGE[(a, b)]): return d
        for c in NB[b]:
            if c != a and winkel(a, b, c) < max_dreh:
                heapq.heappush(hq, (d + math.dist(P[b], P[c]), b, c))
    return None
def weichen_bis_haupt(prev, cur, max_m=1500, max_dreh=40):
    """wie weg_zum_haupt, aber Anzahl befahrener Weichen (Knoten mit 3 und mehr Nachbarn) bis zum ersten Hauptgleis"""
    import heapq
    seen = set(); hq = [(0, 0.0, prev, cur)]
    while hq:
        k, d, a, b = heapq.heappop(hq)
        if (a, b) in seen or d > max_m: continue
        seen.add((a, b))
        if haupt(WAY_OF_EDGE[(a, b)]): return k
        for c in NB[b]:
            if c != a and winkel(a, b, c) < max_dreh:
                heapq.heappush(hq, (k + (1 if len(NB[b]) >= 3 else 0), d + math.dist(P[b], P[c]), b, c))
    return None
laenge = lambda ns: sum(math.dist(P[a], P[b]) for a, b in zip(ns, ns[1:]))
MAX_WEICHEN = 2             # je Ende höchstens 2 Weichen bis zum Hauptgleis: Kreuzungsgleis, nicht Abstellgruppe (Thun 3–9, 25.10.)
MIN_DURCHFAHRT_M = 200      # Nebengleis zwischen den beiden Hauptgleis-Anschlüssen: Platz für einen Zug (sonst Spurwechsel, E1)

# ---- T10 Durchfahrgleis
gl_way = collections.defaultdict(list)
for g in N["gleise"]: gl_way[g["way"]].append(g)
def plan_mitte(way):
    pts = [(KN[str(n)]["x"], KN[str(n)]["y"]) for g in gl_way.get(way, []) for n in g["knoten"]
           if str(n) in KN and KN[str(n)]["y"] is not None]
    if not pts: return None, None
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

durchfahr = set()
for wid, w in WAYS.items():
    sv = w["tags"].get("service")
    if sv not in ("siding", "spur", "crossover") or len(w["nodes"]) < 2: continue
    ns = w["nodes"]
    if laenge(ns) < 100 and not w["tags"].get("railway:track_ref"): continue   # kurzes Verbindungsstück ohne Gleisnummer = Spurwechsel
    # Gleis als Ganzes: von beiden Enden aus, jeweils vom Gleis weg, muss ein Hauptgleis erreichbar sein
    da = weg_zum_haupt(ns[1], ns[0]); db = weg_zum_haupt(ns[-2], ns[-1])
    if da is not None and db is not None and sv != "crossover" and da + db + laenge(ns) >= MIN_DURCHFAHRT_M \
            and (weichen_bis_haupt(ns[1], ns[0]) or 0) <= MAX_WEICHEN and (weichen_bis_haupt(ns[-2], ns[-1]) or 0) <= MAX_WEICHEN:
        durchfahr.add(wid)
        if wid in gl_way and not any(g["pax"] for g in gl_way[wid]):
            x, y = plan_mitte(wid)
            bef("T10", x, y, f"Durchfahrgleis (beidseitig ans Streckengleis angeschlossen, {da + db + laenge(ns):.0f} m Nebengleis, service={sv}) schwarz gezeichnet",
                way=wid, gleis=w["tags"].get("railway:track_ref"))

# ---- D6 Stillgelegtes
for g in N["gleise"]:
    if g.get("stillgelegt"):
        x, y = plan_mitte(g["way"]); bef("D6", x, y, "stillgelegtes Gleis gezeichnet", way=g["way"])

# ---- Perrons, Nummern (A5, D11, D12)
lanes = sorted({g["y"] for g in N["gleise"] if g["y"] is not None})
def gleis_an(y_, x0, x1, tol):
    """gezeichnete Gleise (Ebenen), die im x-Bereich auf Höhe y_ ± tol liegen"""
    r = []
    for g in N["gleise"]:
        if g["y"] is None: continue
        xs = [KN[str(n)]["x"] for n in g["knoten"] if str(n) in KN]
        if not xs or max(xs) < x0 or min(xs) > x1: continue
        if abs(g["y"] - y_) <= tol: r.append(g)
    return r
for p in N["perrons"]:
    durch = gleis_an(p["y"], p["x0"] + 5, p["x1"] - 5, 3.5)
    if durch:
        bef("A5", (p["x0"] + p["x1"]) / 2, p["y"], "Gleis läuft durch das Perron", way=durch[0]["way"])
for t in N["nummern"]:
    ok = any(p["x0"] - 40 <= t["x"] <= p["x1"] + 40 and 6 <= abs(p["y"] - t["y"]) <= 26 for p in N["perrons"])
    if not ok:
        bef("D11", t["x"], t["y"], f"Gleisnummer {t['text']} ohne Perron daneben (Perron fehlt oder Nummer zu viel)")
_osm_refs = sorted({r for p in N["perrons_osm"] for r in str(p.get("ref") or "").replace(",", ";").split(";") if r})
_num = sorted({t["text"] for t in N["nummern"]})
if len(N["perrons"]) < len(_num) / 2:
    bef("D12", None, None, f"{len(N['perrons'])} Perron(s) gezeichnet für {len(_num)} Gleisnummern {_num}; "
        f"OSM-Perrons: {len(N['perrons_osm'])} (ref {_osm_refs or '–'}) – SBB-Perrondaten nachladen (B13)")
for r in _osm_refs:
    if r not in _num: bef("D11", None, None, f"OSM-Perron ref {r} hat keine gleichnamige Gleisnummer im Plan")

# ---- S1 Weichen sichtbar
_auf_haupt = {n for w in WAYS.values() if w["tags"].get("service") is None for n in w["nodes"]}
fehl = [w for w in N["weichen_osm"] if not w["im_plan"] and w["id"] in _auf_haupt]     # Grundsatz 3: Weichen ab Hauptgleis
for w in fehl:
    bef("S1", None, None, "OSM-Weiche an einem Hauptgleis im Planfenster liegt auf keinem gezeichneten Gleis", node=w["id"],
        lat=round(w["lat"], 6), lon=round(w["lon"], 6))

# ---- Z2 Abgänge
for a in N["abgaenge"]:
    if a.get("pax") and not a.get("town"):
        bef("Z2", a.get("x"), a.get("y"), f"Abgang Linie {a.get('ref') or '?'} ohne Richtungsort", way=a.get("way"))

# ---- Gezeichnete Geometrie aus dem SVG (Konolfingen 25.10.: «Knicke, enge doppelte Gleise, Pfeil falsch rum»)
import os, re
_SVGF = f"{B}_spurplan.svg"
if os.path.exists(_SVGF):
    from svgpathtools import parse_path, Line
    _svg = open(_SVGF).read()
    # Abgang-Beschriftung: Pfeil im Text muss in die Richtung zeigen, in die der Abgang den Plan verlässt (Z2)
    for m in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)"[^>]*>([^<]*[→←][^<]*)</text>', _svg):
        t_ = m.group(3); pfeil = 1 if "→" in t_ else -1; ort = t_.replace("→", "").replace("←", "").strip()
        for a in N["abgaenge"]:
            if a.get("town") == ort and a.get("dx") and (a["dx"] > 0) != (pfeil > 0):
                bef("Z2", float(m.group(1)), float(m.group(2)) - 8, f"Pfeil «{t_}» zeigt {'rechts' if pfeil > 0 else 'links'}, "
                    f"der Abgang verlässt den Plan nach {'rechts' if a['dx'] > 0 else 'links'}", way=a.get("way"))
    # Gleislinien: Pfade ohne Füllung mit Gleis-Strichbreite (Haupt 3.6, Neben 1.6); Portale, Brückenflügel, Masken ausgenommen
    LIN = []
    for k_, m in enumerate(re.finditer(r'<path d="([^"]+)"([^>]*)>', _svg)):
        at = m.group(2)
        if re.search(r'fill="#', at) or 'stroke="#fff"' in at or "stroke-opacity" in at: continue
        sw = re.search(r'stroke-width="([\d.]+)"', at)
        if not sw or float(sw.group(1)) not in (3.6, 1.6): continue
        haupt_l = float(sw.group(1)) > 2
        try: P_ = parse_path(m.group(1))
        except Exception: continue
        for j_, sub in enumerate(P_.continuous_subpaths()):
            for seg in sub:
                if isinstance(seg, Line) and abs(seg.end - seg.start) >= 3:
                    LIN.append(dict(a=seg.start, b=seg.end, haupt=haupt_l, sub=(k_, j_)))
                elif not isinstance(seg, Line) and seg.length() >= 20:      # S-Kurve (Verbindung): steilste Stelle in der Mitte
                    t_ = seg.unit_tangent(0.5); r_ = math.degrees(math.atan2(t_.imag, t_.real)) % 180
                    dev = min(abs(r_ - z) for z in (0, 60, 120, 180))
                    if dev > 8:
                        mz = seg.point(0.5)
                        bef("W2", mz.real, mz.imag, f"S-Kurve in der Mitte unter {r_:.0f}° (steiler oder flacher als 60°)")
    _wpos = [complex(v["x"], v["y"]) for v in KN.values() if v.get("y") is not None and v.get("typ") in ("switch", "railway_crossing")]
    an_weiche = lambda z: any(abs(z - w_) < 16 for w_ in _wpos)
    def richt(l):
        d = l["b"] - l["a"]; return math.degrees(math.atan2(d.imag, d.real)) % 180
    # W2: jedes Stück waagrecht oder 60°; nur Stücke ab 10 px, ausserhalb der Weichenrundung
    for l in LIN:
        r_ = richt(l); dev = min(abs(r_ - z) for z in (0, 60, 120, 180))
        if abs(l["b"] - l["a"]) >= 10 and dev > 4:
            mz = (l["a"] + l["b"]) / 2
            bef("W2", mz.real, mz.imag, f"Gleisstück unter {r_:.0f}° (nur 0° und 60° erlaubt)")
    # Knick ohne Weiche: zwei aufeinanderfolgende Stücke derselben Linie drehen um mehr als 60° (Haken, Spitzkehre)
    by_sub = collections.defaultdict(list)
    for l in LIN: by_sub[l["sub"]].append(l)
    for ls in by_sub.values():
        for l1, l2 in zip(ls, ls[1:]):
            if abs(l2["a"] - l1["b"]) > 16: continue
            d1, d2 = l1["b"] - l1["a"], l2["b"] - l2["a"]
            dreh = abs(math.degrees(math.atan2((d2 / d1).imag, (d2 / d1).real)))
            if dreh > 65 and not an_weiche(l1["b"]):
                bef("F2", l1["b"].real, l1["b"].imag, f"Knick um {dreh:.0f}° ohne Weiche (mehr als 60°)")
    # A1: zwei parallele Linien enger als erlaubt (Hauptgleise 20 px, mit Nebengleis 40 % = 9.6 px), über mindestens 12 px
    _ab = set()
    for i, l1 in enumerate(LIN):
        d1 = l1["b"] - l1["a"]; L1 = abs(d1); u = d1 / L1
        for l2 in LIN[i + 1:]:
            if l2["sub"] == l1["sub"]: continue
            d2 = l2["b"] - l2["a"]
            if abs(math.sin(math.atan2((d2 / d1).imag, (d2 / d1).real))) > 0.09: continue      # nicht parallel (> 5°)
            pa, pb = (l2["a"] - l1["a"]) / u, (l2["b"] - l1["a"]) / u                           # l2 im System von l1
            dist = abs((pa.imag + pb.imag) / 2)
            lo, hi = max(0, min(pa.real, pb.real)), min(L1, max(pa.real, pb.real))
            grenze = 20 if (l1["haupt"] and l2["haupt"]) else 9.6
            if hi - lo >= 12 and 0.8 < dist < grenze:
                mz = l1["a"] + u * (lo + hi) / 2
                k_ = (round(mz.real / 20), round(mz.imag / 20))
                if k_ in _ab or an_weiche(mz): continue
                _ab.add(k_)
                bef("A1", mz.real, mz.imag, f"zwei Gleise nur {dist:.1f} px auseinander über {hi - lo:.0f} px (Grenze {grenze} px)")

json.dump(dict(bahnhof=B, befunde=BEF, durchfahrgleise=sorted(durchfahr)), open(f"{B}_netz_befunde.json", "w"),
          ensure_ascii=False, indent=1)
z = collections.Counter(b["regel"] for b in BEF)
print(f"Netzprüfung {B}: {dict(sorted(z.items())) or 'keine Befunde'}; Durchfahrgleise {len(durchfahr)}")
for b in BEF:
    print(f"  {b['regel']:4} x={b['x']} y={b['y']}  {b['text']}" + (f"  (way {b['way']})" if b.get("way") else "")
          + (f"  (node {b['node']})" if b.get("node") else ""))
