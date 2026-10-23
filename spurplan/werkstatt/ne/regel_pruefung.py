"""Regelprüfung Regionalplan (D. Eckenstein 19.10.: "Regeln, die Du über die Regionalpläne lässt").

python3 regel_pruefung.py <plan.svg> [--osm <region.json>] [--rand <rand.json>] [--topo <topologie.json>] [--json out.json]

Regeln (je Befund: Regel, x, y im Plan, Bahnhof, Text):
  G1  Bahnhof mit Spurplan hat Gleisnummern
  G2  Weichen ausgerundet: Linienende trifft ein anderes Gleis unter > 12° ohne Bogen
  G3  keine Ecke ohne Ausrundung in einer Linie (Knick > 12° zwischen zwei Geraden)
  G4  keine 90°: Gleisstück steiler als 75° zur Linie, an die es anschliesst (Portale/Brückenflügel ausgenommen)
  G5  Spurwechsel kreuzen sich nicht (sähe aus wie DKW)
  G6  Knubbel: zwei Linien enden im selben Punkt mit Knick, ohne Fortsetzung oder tangentialen Abzweig (Onnens 20.10.)
  G7  Gleis nicht angebunden: Linienende frei, aber ein anderes Gleis endet/läuft 1–20 px daneben (Toleranz 1 px, D.E. 20.10.) (Auvernier 20.10.)
  G8  Gleise doppelt aufeinander: zwei Linien laufen > 10 px deckungsgleich (Neuchâtel 20.10.)
  O1  jeder Bahnhof/Halt aus OSM ist im Plan (Stationsknoten oder Perron ohne Stationsknoten)
Die Prüfung 4 (Gleiszahl freie Strecke gegen OSM) läuft weiter in netz_lage.py --pruefen.
"""
import re, sys, json, math, argparse, collections
import numpy as np
import xml.etree.ElementTree as ET
from svgpathtools import parse_path, Line, QuadraticBezier, CubicBezier
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

ap = argparse.ArgumentParser()
ap.add_argument("svg"); ap.add_argument("--osm"); ap.add_argument("--rand"); ap.add_argument("--topo")
ap.add_argument("--json"); ap.add_argument("--versatz", default="0,0")
A = ap.parse_args()

GREEN = {"#00862f", "#00862F"}; BLACK = {"#111", "#111111", "#000"}

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
        else: continue
        M = M @ T
    return M

svg = open(A.svg).read()
root = ET.fromstring(svg)
ns = "{http://www.w3.org/2000/svg}"
paths = []          # (pts-Liste je Teilpfad mit Typ, farbe, breite, bahnhof, oberste_ebene)
texts = collections.defaultdict(list)
groups = {}
dots = []; masken = []
def walk(el, M, st, col, w):
    tag = el.tag.replace(ns, "")
    M = M @ mat(el.get("transform"))
    if el.get("data-st"): st = el.get("data-name"); groups[st] = M
    col = el.get("stroke", col); w = el.get("stroke-width", w)
    if tag == "circle": v_ = M @ np.array([float(el.get("cx", 0)), float(el.get("cy", 0)), 1.0]); dots.append((float(v_[0]), float(v_[1])))
    if tag == "path" and el.get("stroke-opacity"): return          # DKW-Klammern
    if tag == "path" and el.get("d") and (el.get("stroke") or "").lower() in ("#fff", "#ffffff"):
        try:
            for sg_ in parse_path(el.get("d")):
                a_ = M @ np.array([sg_.start.real, sg_.start.imag, 1.0]); b_ = M @ np.array([sg_.end.real, sg_.end.imag, 1.0])
                masken.append((LineString([(a_[0], a_[1]), (b_[0], b_[1])]), float(el.get("stroke-width") or 1) / 2))
        except Exception: pass
    if tag == "path" and el.get("d") and col not in (None, "none", "#fff", "#ffffff"):
        paths.append((el.get("d"), M, col, float(w or 1), st))
    if tag == "text" and st: texts[st].append(("".join(el.itertext())).strip())
    for ch in el: walk(ch, M, st, col, w)
walk(root, np.eye(3), None, None, None)

def tp(M, z): v = M @ np.array([z.real, z.imag, 1.0]); return (float(v[0]), float(v[1]))
# Zerlegen in Stücke: ("L", p0, p1) gerade, ("C", p0, p1, t0, t1) Bogen mit Endrichtungen
pieces = []
for d, M, col, w, st in paths:
    try: P = parse_path(d)
    except Exception: continue
    for sub in P.continuous_subpaths():
        seq = []
        for sg in sub:
            p0, p1 = tp(M, sg.start), tp(M, sg.end)
            if math.dist(p0, p1) < 0.05: continue
            if isinstance(sg, Line): seq.append(("L", p0, p1))
            else:
                a = tp(M, sg.point(0.02)); b = tp(M, sg.point(0.98))
                seq.append(("C", p0, p1, (a[0] - p0[0], a[1] - p0[1]), (p1[0] - b[0], p1[1] - b[1])))
        if seq: pieces.append(dict(seq=seq, col=col, w=w, st=st))
def ang(u, v):
    nu, nv = math.hypot(*u), math.hypot(*v)
    if nu < 1e-9 or nv < 1e-9: return 0.0
    return math.degrees(math.acos(max(-1, min(1, (u[0] * v[0] + u[1] * v[1]) / (nu * nv)))))
def dirv(s, end):
    if s[0] == "L": return (s[2][0] - s[1][0], s[2][1] - s[1][1])
    return s[4] if end else s[3]

B = []
def bef(r, x, y, st, t): B.append(dict(regel=r, x=round(x, 1), y=round(y, 1), bahnhof=st, text=t))

# G1 Gleisnummern (Regeln 20.10.): nötig, sobald mindestens zwei Gleise an einem Perron liegen; Gleise ohne Perron und
# Halte mit einem Gleis ohne Nummer; fehlt die Nummer in allen Quellen, steht ein "?" (zählt als erledigt, Liste G1?)
for g_el in root.iter(ns + "g"):
    st = g_el.get("data-name")
    if not st: continue
    rects = [(float(r.get("x")), float(r.get("y")) + 4, float(r.get("width"))) for r in g_el.iter(ns + "rect")
             if r.get("height") == "8" and (r.get("fill") or "").lower() in GREEN]
    hz = []
    for p in g_el.iter(ns + "path"):
        if (p.get("stroke") or "").lower() not in GREEN: continue
        try:
            for sg in parse_path(p.get("d")):
                if isinstance(sg, Line) and abs(sg.start.imag - sg.end.imag) < 0.2 and abs(sg.end.real - sg.start.real) > 5:
                    hz.append((min(sg.start.real, sg.end.real), max(sg.start.real, sg.end.real), round(sg.start.imag, 1)))
        except Exception: pass
    gleise = {y for x0, x1, y in hz for rx, ry, rw in rects if abs(y - ry) <= 13 and x0 < rx + rw and x1 > rx}
    t_ = texts.get(st, [])
    nums = [t for t in t_ if re.fullmatch(r"\d{1,2}[a-z]?", t)]; frag = [t for t in t_ if t == "?"]
    M = groups[st]; x, y = float(M[0, 2]), float(M[1, 2])
    if len(gleise) >= 2 and not nums and not frag:
        bef("G1", x, y, st, f"{len(gleise)} Perrongleise ohne Gleisnummer")
    elif frag:
        bef("G1?", x, y, st, f"{len(frag)} Gleisnummer(n) offen (?) – von Hand eintragen")

# Linien für Berührungen (nur Gleise: grün breit, schwarz dünn; Klammern/Portale = kurze schwarze Stücke mit 3 Ecken)
lines = []
for i, pc in enumerate(pieces):
    pts = [pc["seq"][0][1]] + [s[2] for s in pc["seq"]]
    if len(pts) > 1: lines.append((i, LineString(pts)))
tree = STRtree([l for _, l in lines]); owner = [i for i, _ in lines]

# G3 Ecke ohne Ausrundung innerhalb eines Pfads
for pc in pieces:
    s = pc["seq"]
    for a, b in zip(s, s[1:]):
        if a[0] == "L" and b[0] == "L":
            t = ang(dirv(a, 1), dirv(b, 0))
            if 12 < t < 170 and math.dist(a[1], a[2]) > 2 and math.dist(b[1], b[2]) > 2:
                bef("G3", *a[2], pc["st"], f"Knick {t:.0f}° ohne Ausrundung")

# G2 Weichen ausgerundet / G4 90°: Linienenden auf fremden Linien
for i, pc in enumerate(pieces):
    s = pc["seq"]
    if len(s) == 1 and s[0][0] == "L" and math.dist(s[0][1], s[0][2]) < 4: continue       # Kleinststücke
    for end, sg in ((0, s[0]), (1, s[-1])):
        p = sg[2] if end else sg[1]; v = dirv(sg, end)
        if end == 0: v = (-v[0], -v[1])
        P_ = Point(p)
        for k in tree.query(P_.buffer(1.2)):
            j = owner[k]
            if j == i: continue
            L_ = lines[k][1]
            if L_.distance(P_) > 1.2: continue
            # Richtung der anderen Linie an der Stelle
            t_ = L_.project(P_); q0 = L_.interpolate(max(0, t_ - 3)); q1 = L_.interpolate(min(L_.length, t_ + 3))
            u = (q1.x - q0.x, q1.y - q0.y)
            if math.hypot(*u) < 1: continue
            a_ = ang(v, u); a_ = min(a_, 180 - a_)
            if t_ < 1.5 or t_ > L_.length - 1.5: continue           # Enden treffen sich: Fortsetzung, keine Weiche
            if a_ > 75 and pc["col"] in BLACK and pieces[j]["col"] in BLACK: continue    # Klammer an Klammer
            if a_ > 75:
                if pc["w"] <= 1.4 and len(s) == 3: continue           # Portal/Brückenflügel
                bef("G4", *p, pc["st"], f"Gleisstück {a_:.0f}° zur Linie")
            elif a_ > 12 and sg[0] == "L":
                bef("G2", *p, pc["st"], f"Weiche ohne Ausrundung ({a_:.0f}°)")
            break

# G6 Knubbel / G7 nicht angebunden / G8 doppelt
_ends = []
for i, pc in enumerate(pieces):
    s_ = pc["seq"]
    if len(s_) == 1 and s_[0][0] == "L" and math.dist(s_[0][1], s_[0][2]) < 4: continue
    if pc["w"] <= 1.4 and len(s_) == 3 and all(x[0] == "L" for x in s_): continue      # Portal/Brückenflügel
    for end, sg in ((0, s_[0]), (1, s_[-1])):
        p = sg[2] if end else sg[1]; v = dirv(sg, end)
        if end == 0: v = (-v[0], -v[1])                     # Richtung aus der Linie hinaus
        _ends.append((i, p, v))
from scipy.spatial import cKDTree as _KDe
_ek = _KDe([e[1] for e in _ends]) if _ends else None
_g6 = set()
for a, (i, p, v) in enumerate(_ends):
    nb = [b for b in _ek.query_ball_point(p, 1.2) if b != a and _ends[b][0] != i]
    if not nb: continue
    ok = any(ang(v, _ends[b][2]) > 168 or ang(v, _ends[b][2]) < 12 for b in nb)
    on_line = any(lines[k][1].distance(Point(p)) < 1.2 and 1.5 < lines[k][1].project(Point(p)) < lines[k][1].length - 1.5
                  for k in tree.query(Point(p).buffer(1.2)) if owner[k] != i)
    if not ok and not on_line:
        key = (round(p[0]), round(p[1]))
        if key not in _g6:
            _g6.add(key); bef("G6", *p, pieces[i]["st"], f"Linien stossen mit Knick {min(ang(v, _ends[b][2]) for b in nb):.0f}° zusammen (Knubbel)")
_dk = _KDe(dots) if dots else None
for a, (i, p, v) in enumerate(_ends):
    if pieces[i]["col"] not in GREEN: continue
    if _ek.query_ball_point(p, 1.0) != [a]: continue
    if any(lines[k][1].distance(Point(p)) < 1.0 for k in tree.query(Point(p).buffer(1.2)) if owner[k] != i): continue
    if _dk is not None and _dk.query(p)[0] < 5: continue              # Prellbock
    if any(L_.distance(Point(p)) < r_ for L_, r_ in masken): continue    # Gleisende unter einer weissen Abdeckung (Port-Bogen)
    def _am_ende(L_):      # nächster Punkt ist das Ende der anderen Linie: parallele Gleisenden (Abgang am Planrand)
        t_ = L_.project(Point(p)); return t_ < 1.5 or t_ > L_.length - 1.5
    near = [(lines[k][1].distance(Point(p)), owner[k]) for k in tree.query(Point(p).buffer(20)) if owner[k] != i and pieces[owner[k]]["col"] in GREEN
            and not (_am_ende(lines[k][1]) and lines[k][1].distance(Point(p)) > 5)]
    def _parallel(k_):
        L_ = lines[k_][1]; t_ = L_.project(Point(p)); q0 = L_.interpolate(max(0, t_ - 3)); q1 = L_.interpolate(min(L_.length, t_ + 3))
        a_ = ang(v, (q1.x - q0.x, q1.y - q0.y)); return min(a_, 180 - a_) < 8
    near = [d_ for d_ in near if d_[0] <= 20]
    near = [(d_, o_) for d_, o_ in near if d_ < 4.5 or not any(owner[k] == o_ and _parallel(k) for k in tree.query(Point(p).buffer(20)))]
    if near:
        d_ = min(near)[0]
        bef("G7", *p, pieces[i]["st"], f"Gleisende nicht angebunden, nächstes Gleis {d_:.1f} px")
for i, pc in enumerate(pieces):
    Li = LineString([pc["seq"][0][1]] + [x[2] for x in pc["seq"]])
    if Li.length < 10: continue
    for k in tree.query(Li.buffer(0.8)):
        j = owner[k]
        if j <= i or pieces[j]["col"] != pc["col"]: continue
        ov = Li.intersection(lines[k][1].buffer(0.8))
        Lk = lines[k][1]; short_ = min((Li, pc), (Lk, pieces[j]), key=lambda t: t[0].length)
        if len(short_[1]["seq"]) == 1 and short_[0].length <= 30 and ov.length >= 0.9 * short_[0].length: continue   # Randstück Abgang
        if ov.length > 10:
            c_ = ov.centroid; bef("G8", c_.x, c_.y, pc["st"], f"Gleise {ov.length:.0f} px deckungsgleich")

# G5 sich kreuzende schwarze Spurwechsel ausserhalb der Spurpläne
xo = [LineString([pc["seq"][0][1]] + [s[2] for s in pc["seq"]]) for pc in pieces if pc["st"] is None and pc["col"] in BLACK and pc["w"] <= 1.4]
for i in range(len(xo)):
    for j in range(i + 1, len(xo)):
        if xo[i].crosses(xo[j]):
            q = xo[i].intersection(xo[j])
            if q.geom_type == "Point": bef("G5", q.x, q.y, None, "Spurwechsel kreuzen sich")

# O1 Bahnhöfe aus OSM
if A.osm:
    d = json.load(open(A.osm)); el = d["elements"] if isinstance(d, dict) else d
    rand = Polygon([(lo, la) for la, lo in json.load(open(A.rand))]) if A.rand else None
    inn = lambda la, lo: rand is None or rand.contains(Point(lo, la))
    known = []
    if A.topo:
        for n in json.load(open(A.topo))["nodes"]:
            if n.get("kind") in ("station", "halt") and n.get("lat"): known.append((n["name"], n["lat"], n["lon"]))
    # nur Normalspur (railway=rail, Spurweite 1435): Tram/Littorail, Standseilbahnen und Meterspur (BTI) zählen nicht
    from scipy.spatial import cKDTree
    _np = np.array([(g["lat"] * 111000, g["lon"] * 76000) for e in el if e.get("type") == "way" and "geometry" in e
                    and e.get("tags", {}).get("railway") == "rail" and e["tags"].get("gauge", "1435") == "1435"
                    and e["tags"].get("usage") != "tourism" for g in e["geometry"]])
    _kd = cKDTree(_np)
    normal = lambda la, lo, r=40: _kd.query((la * 111000, lo * 76000))[0] < r
    stn = [(e["tags"].get("name"), e["lat"], e["lon"]) for e in el if e.get("type") == "node"
           and e.get("tags", {}).get("railway") in ("station", "halt") and e["tags"].get("station") not in ("funicular", "subway", "light_rail")
           and inn(e["lat"], e["lon"]) and normal(e["lat"], e["lon"])]
    names_plan = set(groups) | {t for st in texts for t in texts[st]} | set(re.findall(r">([^<>]{3,60})</text>", svg))
    def im_plan(nm): return nm and any(re.split(r"[ /]", nm)[0].lower() in p.lower() for p in names_plan)
    for nm, la, lo in stn:
        if not im_plan(nm): bef("O1", 0, 0, nm, f"OSM-Bahnhof/Halt {nm} ({la:.4f},{lo:.4f}) fehlt im Plan")
    # Perrons ohne Stationsknoten in 600 m (Onnens-Bonvillars: in OSM ohne railway=station)
    # Lage der Spurpläne im Plan aus ihren Abgängen (<bahnhof>_ports.json: lat/lon), z. B. Ligerz ohne Stationsknoten
    import os
    for k_ in {re.search(r'data-st="([^"]+)"', m_).group(1) for m_ in re.findall(r'<g data-st="[^"]+"', svg)}:
        f_ = f"{k_}_ports.json"
        if os.path.exists(f_):
            pp_ = [(p["lat"], p["lon"]) for p in json.load(open(f_))["ports"] if p.get("lat")]
            if pp_: known.append((k_, float(np.mean([a for a, b in pp_])), float(np.mean([b for a, b in pp_]))))
    allst = [(la, lo) for _, la, lo in stn] + [(la, lo) for _, la, lo in known]
    seen = []
    for e in el:
        if e.get("type") != "way" or "geometry" not in e: continue
        t = e.get("tags", {})
        if t.get("railway") != "platform" and t.get("public_transport") != "platform": continue
        if t.get("disused") == "yes" or "disused:public_transport" in t: continue     # stillgelegter Perron: siehe O2
        la = float(np.mean([g["lat"] for g in e["geometry"]])); lo = float(np.mean([g["lon"] for g in e["geometry"]]))
        if not inn(la, lo) or not normal(la, lo, 25): continue
        dmin = min((math.hypot((la - a) * 111000, (lo - b) * 76000) for a, b in allst), default=1e9)
        if dmin < 600 or any(math.hypot((la - a) * 111000, (lo - b) * 76000) < 600 for a, b in seen): continue
        seen.append((la, lo))
        bef("O1", 0, 0, t.get("name"), f"Perron ohne Bahnhof im Plan bei {la:.4f},{lo:.4f} (Way {e['id']}, nächster Bahnhof {dmin:.0f} m)")

# O2 Betriebspunkte: Weichenhäufung (>= 3 Weichen in 500 m) ohne Bahnhof/Spurplan in 900 m (Onnens-Bonvillars 19.10.)
if A.osm:
    sw = [(e["lat"], e["lon"]) for e in el if e.get("type") == "node" and e.get("tags", {}).get("railway") == "switch"
          and inn(e["lat"], e["lon"]) and normal(e["lat"], e["lon"], 15)]
    # durch ein Planfenster abgedeckt (<bahnhof>_fenster.json: Achse + d_lim) zählt als gezeichnet
    import os, glob
    from shapely.geometry import LineString as _LSf
    _fen = []
    for k_ in {re.search(r'data-st="([^"]+)"', m_).group(1) for m_ in re.findall(r'<g data-st="[^"]+"', svg)}:
        for f_ in (f"{k_}_fenster.json", f"{k_.replace('_regional', '')}_fenster.json"):
            if os.path.exists(f_):
                F_ = json.load(open(f_))
                if len(F_["achse"]) > 1:
                    _fen.append(_LSf([(lo * 76000, la * 111000) for la, lo in F_["achse"]]).buffer(F_["d_lim"]))
                break
    sw = [p for p in sw if not any(f_.contains(Point(p[1] * 76000, p[0] * 111000)) for f_ in _fen)]
    far = [p for p in sw if min((math.hypot((p[0] - a) * 111000, (p[1] - b) * 76000) for a, b in allst), default=1e9) > 900]
    used = set()
    for i, p in enumerate(far):
        if i in used: continue
        cl = [j for j, q in enumerate(far) if math.hypot((p[0] - q[0]) * 111000, (p[1] - q[1]) * 76000) < 500]
        used |= set(cl)
        if len(cl) >= 3:
            la = float(np.mean([far[j][0] for j in cl])); lo = float(np.mean([far[j][1] for j in cl]))
            nm = min(((math.hypot((la - e["lat"]) * 111000, (lo - e["lon"]) * 76000), e["tags"].get("name")) for e in el
                      if e.get("type") == "way" and "geometry" in e and e.get("tags", {}).get("railway") == "platform" and e["tags"].get("name")
                      for e in [dict(e, lat=e["geometry"][0]["lat"], lon=e["geometry"][0]["lon"])]), default=(0, None))
            bef("O2", 0, 0, None, f"{len(cl)} Weichen bei {la:.4f},{lo:.4f} ohne Spurplan (Betriebspunkt?)")
cnt = collections.Counter(b["regel"] for b in B)
for b in B: print(f'{b["regel"]}\t{b["x"]},{b["y"]}\t{b["bahnhof"] or "-"}\t{b["text"]}')
print("Regelprüfung:", dict(sorted(cnt.items())) or "0 Befunde", file=sys.stderr)
if A.json: json.dump(B, open(A.json, "w"), ensure_ascii=False, indent=1)
