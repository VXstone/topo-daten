"""
Verbindungsprüfung Spurplan gegen OSM (Personenverkehrsgleise).

Für jedes Perrongleis (beide Richtungen) und jeden Abgang wird bestimmt, welche Abgänge ein Zug ohne
Richtungswechsel erreicht – einmal im OSM-Netz (Ways mit pax=1 laut Schema), einmal in den grünen Linien
des gezeichneten Plans. Verglichen werden die beiden Mengen.

  python3 verbindungen_pruefen.py olten [--gleisx 693]
"""
import json, math, re, sys, collections, subprocess, os
import numpy as np
from svgpathtools import parse_path

st = sys.argv[1]
GX = float(sys.argv[sys.argv.index("--gleisx") + 1]) if "--gleisx" in sys.argv else 693.0
extra = [a for a in sys.argv[2:] if a.startswith("--") and a != "--gleisx"]
HERE = os.path.dirname(os.path.abspath(__file__))

ports = json.load(open(f"{st}_ports.json"))["ports"]
svg = open(f"{st}_spurplan.svg").read()
_lab = [(float(m[1]), float(m[2]) - 6.5, m[3]) for m in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)" font-size="19"[^>]*>(\d+)</text>', svg)]
labels = {y_: g_ for x_, y_, g_ in _lab}
if "--gleisx" not in sys.argv and _lab: GX = float(np.median([x_ for x_, _, _ in _lab]))       # Lage der Gleisnummern = Perronbereich

# ------------------------------------------------------------------ OSM-Seite
seg = subprocess.run(["python3", "spurplan_schema.py", "--src", f"{st}.json", "--out", "/tmp/_vp.svg"] + extra,
                     env=dict(os.environ, SEGDUMP="1"), capture_output=True, text=True).stdout
SEG = []
for l in seg.splitlines():
    if l.startswith("SEG "):
        f = l.split(); SEG.append(dict(way=int(f[2]), pax=f[3] == "1", a=int(f[4]), b=int(f[5]),
                                       xa=float(f[6]), ya=float(f[7]), xb=float(f[8]), yb=float(f[9])))
D = json.load(open(f"{st}.json"))
if isinstance(D, dict) and "elements" not in D and len(D) == 1: D = next(iter(D.values()))     # {bahnhof: {elements}} (Vauseyon 28.10.)
E = D["elements"] if "elements" in D else D
WAY = {e["id"]: e for e in E if e["type"] == "way"}
ND = {}
for e in E:
    if e["type"] == "node" and "lat" in e: ND[e["id"]] = e
    if e["type"] == "way" and "geometry" in e:
        for n, g in zip(e["nodes"], e["geometry"]): ND.setdefault(n, {"lat": g["lat"], "lon": g["lon"], "tags": {}})
lat0 = np.mean([ND[s["a"]]["lat"] for s in SEG if s["a"] in ND])
def P(n): return np.array([(ND[n]["lon"]) * 111320 * math.cos(math.radians(lat0)), ND[n]["lat"] * 110540])
CROSS = {n for n, v in ND.items() if (v.get("tags") or {}).get("railway") == "railway_crossing"}

def osm_graph(alle=False):
    adj = collections.defaultdict(list)          # node -> [(nachbar, way)]
    for s in SEG:
        if not s["pax"] and not (alle and WAY[s["way"]]["tags"].get("service") in ("siding", "crossover")): continue
        ns = WAY[s["way"]]["nodes"]; i, j = ns.index(s["a"]), ns.index(s["b"])
        part = ns[min(i, j):max(i, j) + 1]
        for u, v in zip(part, part[1:]):
            adj[u].append((v, s["way"])); adj[v].append((u, s["way"]))
    return adj
OADJ = osm_graph(); OADJ_N = osm_graph(True)

def walk(adj, pos, start, first, same_line, maxturn):
    """alle Knoten, die von start in Richtung first ohne Richtungswechsel erreichbar sind"""
    seen = set(); out = set(); stack = [(start, first)]
    while stack:
        u, (v, ln) = stack.pop()
        if (u, v) in seen: continue
        seen.add((u, v)); out.add(v)
        d0 = pos(v) - pos(u); n0 = np.linalg.norm(d0)
        if n0 == 0: continue
        for w, ln2 in adj[v]:
            if w == u: continue
            d1 = pos(w) - pos(v); n1 = np.linalg.norm(d1)
            if n1 == 0: continue
            ang = math.degrees(math.acos(max(-1, min(1, float(d0 @ d1) / n0 / n1))))
            if ang > maxturn: continue
            if not same_line(v, ln, ln2) and ang > 12: continue
            stack.append((v, (w, ln2)))
    return out

def osm_same(v, l1, l2): return not (v in CROSS and l1 != l2)

# Terminals OSM: Abgänge (Port-Way, Endknoten weg vom Bahnhof) und Perrongleise (Way an Gleis-x)
def port_node_osm(p):
    cand = {n for sg in SEG if sg["way"] == p["way"] for n in (sg["a"], sg["b"])}
    ns = WAY[p["way"]]["nodes"]
    cand |= {n for n in ns if n in OADJ}
    if not cand: return None
    return min(cand, key=lambda n: (ND[n]["lon"] - p["lon"]) ** 2 + (ND[n]["lat"] - p["lat"]) ** 2)
EXIT_O = {}
for k, p in enumerate(ports):
    if not p.get("pax"): continue
    EXIT_O[k] = port_node_osm(p)
GLEIS_O = {}
for s in SEG:
    _gx = {y_: x_ for x_, y_, g_ in _lab}.get(s["ya"], GX)
    if s["pax"] and min(s["xa"], s["xb"]) < _gx < max(s["xa"], s["xb"]) and abs(s["ya"] - s["yb"]) < 0.5:
        g = labels.get(s["ya"])
        if g:
            ns = WAY[s["way"]]["nodes"]; i, j = ns.index(s["a"]), ns.index(s["b"]); st_ = 1 if j > i else -1
            # (Knoten, Nachbar) Richtung West bzw. Ost
            ab = (s["a"], ns[i + st_]); ba = (s["b"], ns[j - st_])
            GLEIS_O[g] = (ba, ab) if s["xa"] < s["xb"] else (ab, ba)
def reach_osm(start, nxt, neben=False):
    G_ = XADJ_N if neben else XADJ
    for ln in [l for w_, l in G_[start] if w_ == nxt][:1]:
        return walk(G_, P, start, (nxt, ln), osm_same, 40) | {start}
    return set()
# Abgang = Port-Knoten + alles, was von dort nach aussen (weg vom Bahnhof) innert 600 m folgt
# (Spurwechsel knapp am Planrand, z. B. Olten Nord vor dem Hauenstein-Basistunnel)
# Zusatzgraph knapp ausserhalb des Plans: alle Hauptgleise (ohne service) innert 400 m der Port-Knoten
_main = [w for w in WAY.values() if w.get("tags", {}).get("railway") == "rail" and not w["tags"].get("service")]
_pn = [P(n) for n in EXIT_O.values() if n]
XADJ = collections.defaultdict(list)
for u, l in OADJ.items(): XADJ[u] = list(l)
for w in _main:
    for u, v in zip(w["nodes"], w["nodes"][1:]):
        if u in ND and v in ND and min(np.linalg.norm(P(u) - q) for q in _pn) < 400:
            if (v, w["id"]) not in XADJ[u]: XADJ[u].append((v, w["id"])); XADJ[v].append((u, w["id"]))
# Regel 43 auch knapp ausserhalb des Plans: Verbindungen (siding/crossover) zwischen zwei Hauptgleisen sind Fahrwege
# des Personenverkehrs (Olten West 15.10.: Spurwechsel Bern/Luzern westlich des Planrands)
_ovr_ = json.load(open(f"{st}_override.json")) if os.path.exists(f"{st}_override.json") else {}
if _ovr_.get("cfg", {}).get("rules", {}).get("r43"):
    _mainn = {n for w in _main for n in w["nodes"]}; _segw = {s_["way"] for s_ in SEG}   # nur ausserhalb des Plans
    for w in WAY.values():
        t_ = w.get("tags", {})
        if t_.get("railway") != "rail" or t_.get("service") not in ("siding", "crossover") or w["id"] in _segw: continue
        ch_ = [w]; a_, b_ = w["nodes"][0], w["nodes"][-1]
        if not all(n in ND for n in w["nodes"]) or min(np.linalg.norm(P(a_) - q) for q in _pn) > 400: continue
        if a_ in _mainn and b_ in _mainn or any(a_ in o["nodes"] or b_ in o["nodes"] for o in WAY.values()
                                                if o is not w and o.get("tags", {}).get("service") in ("siding", "crossover")):
            for u, v in zip(w["nodes"], w["nodes"][1:]):
                if (v, w["id"]) not in XADJ[u]: XADJ[u].append((v, w["id"])); XADJ[v].append((u, w["id"]))
XADJ_N = collections.defaultdict(list)
for u, l in XADJ.items(): XADJ_N[u] = list(l)
for u, l in OADJ_N.items():
    for x in l:
        if x not in XADJ_N[u]: XADJ_N[u].append(x)
for w in WAY.values():
    if w.get("tags", {}).get("railway") == "rail" and w["tags"].get("service") == "siding":
        for u, v in zip(w["nodes"], w["nodes"][1:]):
            if u in ND and v in ND and min(np.linalg.norm(P(u) - q) for q in _pn) < 400 and (v, w["id"]) not in XADJ_N[u]:
                XADJ_N[u].append((v, w["id"])); XADJ_N[v].append((u, w["id"]))
# --rand_m N: Abgangskette weiter hinaus verfolgen (Olten West 15.10.: Spurwechsel knapp ausserhalb des Plans)
RAND_M = float(sys.argv[sys.argv.index('--rand_m') + 1]) if '--rand_m' in sys.argv else 250
EXIT_SET = {}; EXIT_FAR = {}
for k, n in EXIT_O.items():
    b_ = math.radians(ports[k]["bearing"]); out_ = np.array([math.cos(b_), math.sin(b_)])      # bearing: Winkel ab Ost, Gegenuhrzeiger
    S_ = {n}
    _cands = sorted(XADJ[n], key=lambda t: -float((P(t[0]) - P(n)) @ out_) / (np.linalg.norm(P(t[0]) - P(n)) or 1))[:1]
    for w_, l_ in _cands:
        d_ = P(w_) - P(n)
        if float(d_ @ out_) > 0.5 * np.linalg.norm(d_):
            # nur geradeaus weiter (kein Abzweigen), bis 400 m
            u_, v_ = n, w_
            while v_ not in S_ and np.linalg.norm(P(v_) - P(n)) < RAND_M:
                S_.add(v_); d0_ = P(v_) - P(u_); best_ = None
                pass
                for x_, _l in XADJ[v_]:
                    if x_ == u_ or WAY.get(_l, {}).get("tags", {}).get("service") in ("siding", "crossover"): continue   # Abgangskette bleibt auf dem Streckengleis
                    d1_ = P(x_) - P(v_); a_ = math.degrees(math.acos(max(-1, min(1, float(d0_ @ d1_) / (np.linalg.norm(d0_) * np.linalg.norm(d1_) or 1)))))
                    if a_ < 40 and (best_ is None or a_ < best_[0]): best_ = (a_, x_)
                EXIT_FAR[k] = (v_, u_)              # äusserster Knoten, Blick nach innen
                if not best_: break
                u_, v_ = v_, best_[1]
    EXIT_SET[k] = S_
def exits_from_osm(nodes):
    return {k for k, S_ in EXIT_SET.items() if S_ & nodes}

# ------------------------------------------------------------------ Plan-Seite (grüne Linien)
pts_all = []
for tag in re.findall(r"<path[^>]*>", svg):
    at = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
    if at.get("stroke") != "#00862f" or float(at.get("stroke-width", 0)) < 3 or "d" not in at: continue
    for sub in re.split(r"(?=M)", at["d"]):
        if not sub.strip(): continue
        try: pp = parse_path(sub)
        except Exception: continue
        L = pp.length()
        if L < 0.5: continue
        k = max(2, int(L / 1.0) + 1)
        pts_all.append([pp.point(pp.ilength(t * L)) for t in np.linspace(0, 1, k)])
# Plan-Graph: Teilpfade mit 1-px-Stützpunkten; Übergang auf einen anderen Teilpfad, wo dieser näher als 1.6 px
# liegt und in dieselbe Richtung läuft (< 35°). Kreuzungen unter 60° verbinden damit nicht.
from scipy.spatial import cKDTree
LN = [np.array([[z.real, z.imag] for z in l]) for l in pts_all]
TG = []
for A in LN:
    t = np.gradient(A, axis=0); n = np.linalg.norm(t, axis=1, keepdims=True); n[n == 0] = 1; TG.append(t / n)
IDX = np.array([(i, j) for i, A in enumerate(LN) for j in range(len(A))])
ALL = np.vstack(LN); TREE = cKDTree(ALL)
COS = math.cos(math.radians(35)); COS62 = math.cos(math.radians(62))
KNICK = []
def plan_walk(i, j, d):
    seen = set(); pts = []; stack = [(i, j, d)]
    while stack:
        i, j, d = stack.pop()
        if (i, j, d) in seen: continue
        seen.add((i, j, d)); pts.append(LN[i][j])
        vdir = TG[i][j] * d
        # Übergänge
        for q in TREE.query_ball_point(LN[i][j], 1.6):
            i2, j2 = IDX[q]
            if i2 == i: continue
            if float((LN[i2][j2] - LN[i][j]) @ vdir) < 0.05: continue      # nicht rückwärts springen
            c = float(TG[i2][j2] @ vdir)
            # an Linienenden (Weiche ohne Ausrundung) bis 62° zulassen, auf freier Linie nur 35° (Kreuzung ≠ Weiche)
            cc = COS62 if (j2 in (0, len(LN[i2]) - 1) or j in (0, len(LN[i]) - 1)) else COS
            if c > cc: stack.append((i2, j2, 1))
            elif c < -cc: stack.append((i2, j2, -1))
        j2 = j + d
        if 0 <= j2 < len(LN[i]): stack.append((i, j2, d))
    return np.array(pts)
def start_at(x, y, dx):
    q = TREE.query_ball_point((x, y), 2.0)
    out = []
    for k in q:
        i, j = IDX[k]
        c = TG[i][j][0] * dx
        if c > COS: out.append((i, j, 1))
        elif c < -COS: out.append((i, j, -1))
    return out
def exits_plan_set(P_):
    S = set()
    if not len(P_): return S
    T_ = cKDTree(P_)
    for k, p in enumerate(ports):
        if p.get("pax") and T_.query_ball_point((p["x"], p["y"]), 3.0): S.add(k)
    return S
def plan_from(x, y, dx):
    P_ = [plan_walk(*s_) for s_ in start_at(x, y, dx)]
    return np.vstack(P_) if P_ else np.zeros((0, 2))
def name(k):
    p = ports[k]; return f"{p['ref']} {p['town']} ({p['kind']} y{p['y']:.0f} x{p['x']:.0f})"

# ------------------------------------------------------------------ Vergleich
probleme = 0
print(f"Verbindungsprüfung {st}: {len(GLEIS_O)} Perrongleise, {len(EXIT_O)} Abgänge (Personenverkehr)")
for g in sorted(GLEIS_O, key=lambda s: int(s)):
    wst, ost = GLEIS_O[g]
    y = [yy for yy, gg in labels.items() if gg == g][0]
    for richt, (s0, s1), dx in (("West", wst, -1), ("Ost", ost, 1)):
        eo = exits_from_osm(reach_osm(s0, s1) | {s1})
        _gx = {y_: x_ for x_, y_, g_ in _lab if g_ == g}.get(y, GX)
        ep = exits_plan_set(plan_from(_gx + dx * 30, y, dx))
        eon = exits_from_osm(reach_osm(s0, s1, True) | {s1})
        miss = eo - ep; extra_ = ep - eon; neben_ = (ep - eo) & eon
        flag = "ok" if not miss and not extra_ else "ABWEICHUNG"
        for k in sorted(neben_): print(f"  Gleis {g:>2} {richt:<4} Hinweis: Plan grün nach {name(k)}, in OSM nur über Nebengleis (siding)")
        if flag != "ok": probleme += 1
        print(f"  Gleis {g:>2} {richt:<4} OSM {len(eo)} / Plan {len(ep)}  {flag}")
        for k in sorted(miss): print(f"        fehlt im Plan: {name(k)}")
        for k in sorted(extra_): print(f"        zu viel im Plan: {name(k)}")
# Durchfahrten Abgang -> Abgang
for k, n in EXIT_O.items():
    first = [(n, w) for w, _ in OADJ[n]]
    if k in EXIT_FAR: first = [EXIT_FAR[k]]          # vom äussersten Knoten nach innen (Spurwechsel knapp ausserhalb)
    if not first: print(f"  Abgang {name(k)}: OSM-Knoten nicht im Netz"); continue
    eo = set(); eon = set()
    for n_, f_ in first: eo |= exits_from_osm(reach_osm(n_, f_)); eon |= exits_from_osm(reach_osm(n_, f_, True))
    eo -= {k}; eon -= {k}
    p = ports[k]
    st_ = []
    for q in TREE.query_ball_point((p["x"], p["y"]), 2.0):
        i, j = IDX[q]; st_ += [(i, j, 1), (i, j, -1)]
    PP = [plan_walk(*z) for z in st_]
    ep = exits_plan_set(np.vstack(PP) if PP else np.zeros((0, 2))) - {k}
    miss = eo - ep; extra_ = ep - eon
    for q in sorted((ep - eo) & eon): print(f"  Abgang {name(k)} Hinweis: Plan grün nach {name(q)}, in OSM nur über Nebengleis (siding)")
    if miss or extra_:
        probleme += 1
        print(f"  Abgang {name(k)}: ABWEICHUNG")
        for q in sorted(miss): print(f"        fehlt im Plan: {name(q)}")
        for q in sorted(extra_): print(f"        zu viel im Plan: {name(q)}")
    else:
        print(f"  Abgang {name(k)}: ok ({len(eo)} Ziele)")
print(f"→ {probleme} Abweichungen")

def osm_pfad(start, nxt, ziel):
    """Way-Folge eines OSM-Wegs von start (Richtung nxt) zum Knoten ziel"""
    G_ = XADJ_N
    ln0 = [l for w_, l in G_[start] if w_ == nxt][0]
    prev = {(start, nxt): None}; stack = [(start, nxt, ln0)]
    while stack:
        u, v, ln = stack.pop()
        if v == ziel:
            out = []; k = (u, v)
            while k: out.append(k); k = prev[k]
            ws = []
            for a_, b_ in reversed(out):
                l_ = [l for w_, l in OADJ[a_] if w_ == b_][0]
                if not ws or ws[-1] != l_: ws.append(l_)
            return ws
        d0 = P(v) - P(u)
        for w, ln2 in G_[v]:
            if w == u or (v, w) in prev: continue
            d1 = P(w) - P(v)
            ang = math.degrees(math.acos(max(-1, min(1, float(d0 @ d1) / (np.linalg.norm(d0) * np.linalg.norm(d1) or 1)))))
            if ang > 40: continue
            if not osm_same(v, ln, ln2) and ang > 12: continue
            prev[(v, w)] = (u, v); stack.append((v, w, ln2))
    return None
if "--pfad" in sys.argv:
    g, ri, ex = sys.argv[sys.argv.index("--pfad") + 1].split(",")
    s0, s1 = GLEIS_O[g][0 if ri == "W" else 1]
    for ex_ in (range(len(EXIT_O)) if ex == "*" else [int(ex)]): print("Pfad", ex_, osm_pfad(s0, s1, EXIT_O[ex_]))

# Weichen ohne Ausrundung: Linienende trifft eine andere Linie unter mehr als 35° (sichtbarer Knick)
_kn = []
for i, A in enumerate(LN):
    for j in (0, len(A) - 1):
        for q in TREE.query_ball_point(A[j], 1.2):
            i2, j2 = IDX[q]
            if i2 == i or j2 in (0, len(LN[i2]) - 1): continue
            a_ = math.degrees(math.acos(min(1, abs(float(TG[i][j] @ TG[i2][j2])))))
            if 35 < a_ < 75: _kn.append((round(A[j][0]), round(A[j][1]), round(a_)))
_kn = sorted(set(_kn))
_kk = []
for k_ in _kn:
    if not any(abs(k_[0] - m[0]) < 4 and abs(k_[1] - m[1]) < 4 for m in _kk): _kk.append(k_)
print(f"Weichen ohne Ausrundung (Linienende unter >35° auf Gleis): {len(_kk)}")
for x_, y_, a_ in _kk: print(f"   x{x_} y{y_}  {a_}°")
