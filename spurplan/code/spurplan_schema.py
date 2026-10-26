"""
Schematischer Spurplan aus OSM-Gleisdaten (Stil: Uppsala-Vorlage).

Ablauf
1. Referenzachse entlang der Stammlinie, alle Gleisknoten -> (s, d)
   (s = Kilometrierung entlang Achse, d = seitlicher Versatz)
2. Gleise an Weichen/Knoten in Segmente teilen
3. Flache Segmente = Gleisspuren, steile = Verbindungen (Weichenstrassen)
4. Durchgehende Spuren zu Ketten verbinden, Ketten per Kompaktierung
   auf ganzzahlige Spuren (y-Ebenen) legen (Reihenfolge bleibt erhalten)
5. SVG zeichnen: horizontale Gleise, S-Kurven an Weichen
"""
import json, math, collections, heapq, sys, re
import numpy as np

import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--src", default="kim.json")
ap.add_argument("--station", default=None, help="Schlüssel, falls die Datei mehrere Bahnhöfe enthält")
ap.add_argument("--out", default=None)
ap.add_argument("--warp", default=None)
ap.add_argument("--nowarp", action="store_true")
ap.add_argument("--dbg", action="store_true")
ap.add_argument("--bare", action="store_true", help="nur Gleise/Perrons, Anschlusspunkte nach <bahnhof>_ports.json")
ap.add_argument("--axis-ref", default=None, help="Achse entlang dieser Strecke (OSM ref) erzwingen")
ARGS, _ = ap.parse_known_args()

CFG = dict(
    s_pad=110,
    min_half_window_m=350,      # Fenster mindestens ±350 m um den Bahnhof                  # Rand vor erster / nach letzter Weiche [m]
    sw_search_m=900,            # Weichen in diesem Umkreis um den Bahnhof bestimmen den Ausschnitt
    d_lim=60,                   # max. seitlicher Abstand [m], darüber abgeschnitten
    flat_slope=0.06,            # |dd/ds| darunter = Gleisspur
    # Weichen-Standard (alle Verbindungen werden daraus gebaut)
    sw_angle=60,       # Neigung der Diagonale [Grad], wie Uppsala-Vorlage
    sw_radius=7,       # Ausrundung Gleis -> Diagonale [px]
    sw_min_run=10,     # kürzeste Diagonale [px] (auch bei kleinem Lane-Sprung)
    lane_gap_m=30,     # min. Längsabstand zweier Gleise auf derselben Ebene [m]
    long_track_m=1e9,
    rules=dict(r12=True, r13=True, r14a=True, r14b=True, r15=True),   # Regeln einzeln schaltbar
    side_lane_factor=0.55,   # Ebenenabstand Neben-/Abstell-/Gütergleise relativ zu lane_px
    px_per_m=0.92, lane_px=24, margin_x=230, margin_y=110,
    green="#00862f", black="#111",
    # Orte für die Richtungsangabe an Streckenabgängen (Lage der Bahnhöfe)
    towns={"Bern": (46.9490, 7.4391), "Neuchâtel": (46.9967, 6.9358), "Lyss": (47.0742, 7.3063),
           "Murten": (46.9254, 7.1153), "Kerzers": (46.9751, 7.1929), "Ins": (46.9999, 7.0996),
           "Fribourg": (46.8032, 7.1513), "Payerne": (46.8197, 6.9405), "Avenches": (46.8803, 7.0438), "Gümmenen": (46.9446, 7.2393),
           "Spiez": (46.6863, 7.6800), "Olten": (47.3519, 7.9075), "Basel": (47.5476, 7.5897),
           "Aarau": (47.3913, 8.0512), "Solothurn": (47.2035, 7.5422), "Luzern": (47.0502, 8.3102),
           "Zofingen": (47.2880, 7.9429), "Rothrist": (47.3064, 7.8795), "Langenthal": (47.2172, 7.7834),
           "Läufelfingen": (47.3921, 7.8562), "Sissach": (47.4644, 7.8121), "Tecknau": (47.4458, 7.8877),
           "Däniken": (47.3563, 7.9786), "Aarburg": (47.3202, 7.9082), "Wangen b. O.": (47.3414, 7.8682),
           "Oensingen": (47.2868, 7.7206), "Suhr": (47.3727, 8.0798), "Gelterkinden": (47.4652, 7.8559),
           "Trimbach": (47.3661, 7.9043), "Hägendorf": (47.3303, 7.8437), "Schönenwerd": (47.3713, 8.0002),
           "Dulliken": (47.3541, 7.9464), "Safenwil": (47.3217, 7.9835), "Sursee": (47.1716, 8.1055),
           "Lenzburg": (47.3915, 8.1717), "Bern": (46.9490, 7.4391), "Konolfingen": (46.8790, 7.6200), "Steffisburg": (46.7780, 7.6320)},
)

# ---------------------------------------------------------------- Daten
RAW = json.load(open(ARGS.src))
if "elements" not in RAW:
    key = ARGS.station or next(iter(RAW))
    RAW = RAW[key]
else:
    key = ARGS.station or ARGS.src.split(".")[0]
D = RAW["elements"]
STN = [e for e in D if e["type"] == "node" and e.get("tags", {}).get("railway") == "station"
       and e["tags"].get("public_transport") in (None, "station")]
CFG["out"] = ARGS.out or f"{key}_spurplan.svg"
import os
OVR = json.load(open(f"{key}_override.json")) if os.path.exists(f"{key}_override.json") else {}
for k_, v_ in OVR.get("cfg", {}).items():
    if k_ == "rules": CFG["rules"].update(v_)
    else: CFG[k_] = v_
RU = CFG["rules"]
LINE_TOWNS = {k: v for k, v in (json.load(open("region_lines.json")).items() if os.path.exists("region_lines.json") else []) if not k.startswith("_")}
CFG["warp_file"] = ARGS.warp or f"{key}_warp.json"
CFG["req_file"] = f"{key}_req.json"
ap.add_argument("--hauptgleise", action="store_true", help="nur Strecken-, Perron- und Überholgleise (ohne yard/spur)")
ARGS, _ = ap.parse_known_args()
_DROP = set(CFG.get("drop_service", [])) | ({"yard", "spur"} if ARGS.hauptgleise else set())
ways = {e["id"]: e for e in D if e["type"] == "way" and e["tags"].get("railway") == "rail"
        and e["tags"].get("gauge", "1435") == "1435" and (e["tags"].get("service") not in _DROP
            or e["tags"].get("railway:track_ref") in OVR.get("pax", []) or e["id"] in OVR.get("behalten", []))}   # Personengleise bleiben (Neuchâtel 19.10.)
ntag = {e["id"]: e["tags"] for e in D if e["type"] == "node"}
# Bahnhof: Stationsknoten, der dem Normalspurnetz am nächsten liegt
allpts = [(g["lat"], g["lon"]) for w in ways.values() for g in w["geometry"]]
def nearest_rail(e):
    return min((e["lat"] - la) ** 2 + ((e["lon"] - lo) * 0.68) ** 2 for la, lo in allpts)
ST = min(STN, key=nearest_rail) if STN else None
CFG["title"] = ST["tags"].get("name", key).split("/")[0].strip() if ST else key
lat0, lon0 = (ST["lat"], ST["lon"]) if ST else np.mean(allpts, axis=0)
kx = 111320 * math.cos(math.radians(lat0)); ky = 110540
xy = lambda p: ((p["lon"] - lon0) * kx, (p["lat"] - lat0) * ky)
P = {}
for w in ways.values():
    for n, g in zip(w["nodes"], w["geometry"]):
        P[n] = xy(g)
LL = {n: (g["lat"], g["lon"]) for w in ways.values() for n, g in zip(w["nodes"], w["geometry"])}
PLAT = [e for e in D if e["type"] == "way" and (e["tags"].get("railway") == "platform"
        or e["tags"].get("public_transport") == "platform")
        and not (e["tags"].get("disused") == "yes" or "disused:public_transport" in e["tags"] or "abandoned:railway" in e["tags"])]   # stillgelegt nicht zeichnen (20.10.)

# Regel 27: OSM-Lücken schliessen - offenes Gleisende ohne Prellbock, das < 6 m neben einem Knoten
# eines anderen Gleises liegt, wird mit diesem verbunden (Rothrist Gl. 1 endete 4,6 m vor der Weiche)
_deg = collections.Counter(n for w in ways.values() for n in w["nodes"])
_own = collections.defaultdict(set)
for w in ways.values():
    for n in w["nodes"]: _own[n].add(w["id"])
_ends = [(w, k) for w in ways.values() for k in (0, -1)
         if _deg[w["nodes"][k]] == 1 and ntag.get(w["nodes"][k], {}).get("railway") != "buffer_stop"]
if _ends and CFG["rules"].get("r27", True):
    from scipy.spatial import cKDTree as _KD
    _ids = list(P); _kd = _KD(np.array([P[n] for n in _ids]))
    for w, k in _ends:
        n = w["nodes"][k]
        for dist_, j in zip(*_kd.query(P[n], k=6)):
            m = _ids[j]
            if m == n or dist_ > 6 or _own[m] & _own[n] or m in w["nodes"]: continue
            # nur in Verlängerung des Gleises (nicht seitlich auf ein Nachbargleis)
            _pv = w["nodes"][k - 1] if k == -1 else w["nodes"][1]
            _u = np.subtract(P[n], P[_pv]); _v = np.subtract(P[m], P[n])
            if np.linalg.norm(_u) < 1e-6 or np.dot(_u, _v) < 0.9 * np.linalg.norm(_u) * np.linalg.norm(_v): continue
            w["nodes"][k] = m; _deg[m] += 1; break
_bx = [p[0] for p in P.values()]; _by = [p[1] for p in P.values()]
_Rdata = max(math.hypot(*p) for p in P.values())
_circ = sum(math.hypot(*p) > 0.93 * _Rdata for p in P.values()) > 6     # Daten kreisförmig ausgeschnitten (cut.py)
def at_data_edge(n, tol=60):
    x_, y_ = P[n]
    if _circ and math.hypot(x_, y_) > _Rdata - 2 * tol: return True
    return min(x_ - min(_bx), max(_bx) - x_, y_ - min(_by), max(_by) - y_) < tol

# ------------------------------------------------------ 1. Referenzachse
G = collections.defaultdict(list)
for w in ways.values():
    t = w["tags"]
    f = 1 if t.get("usage") == "main" else 2 if not t.get("service") else 6
    for a, b in zip(w["nodes"], w["nodes"][1:]):
        L = math.dist(P[a], P[b]) * f
        G[a].append((b, L)); G[b].append((a, L))
deg = collections.Counter()
for w in ways.values():
    for a_, b_ in zip(w["nodes"], w["nodes"][1:]): deg[a_] += 1; deg[b_] += 1
ends_ = [n for n, k in deg.items() if k == 1 and any(not w["tags"].get("service") for w in ways.values() if n in (w["nodes"][0], w["nodes"][-1]))]
ends_ = sorted(ends_, key=lambda n: -math.hypot(*P[n]))[:10]     # äussere Enden
def shortest(A, B):
    dist = {A: 0}; prev = {}; pq = [(0, A)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == B: break
        if d > dist[u]: continue
        for v, L in G[u]:
            if d + L < dist.get(v, 1e18):
                dist[v] = d + L; prev[v] = u; heapq.heappush(pq, (d + L, v))
    if B not in prev: return None
    p = [B]
    while p[-1] != A: p.append(prev[p[-1]])
    return p[::-1]
plat_pts = np.array([xy(g) for e in PLAT for g in e["geometry"]]).reshape(-1, 2)
# Perronlänge entlang der Achse: Achse soll den Perrons folgen
def plat_score(pts):
    if not len(plat_pts): return 0
    from scipy.spatial import cKDTree
    d_, _ = cKDTree(pts).query(plat_pts)
    return int((d_ < 30).sum())
best = None
# Achswahl: Endpaar, dessen Weg nahe am Bahnhof vorbeiführt; findet sich keines < 150 m, Grenze lockern (Bern/Basel)
for _lim in (150, 450, 1350):
  if best is not None: break
  for i, A in enumerate(ends_):
    for B in ends_[i + 1:]:
        p = shortest(A, B)
        if not p: continue
        pts = np.array([P[n] for n in p])
        near_st = np.min(np.hypot(pts[:, 0], pts[:, 1]))
        if near_st > _lim: continue
        pset = set(p)
        dense = np.vstack([np.linspace(pts[i], pts[i + 1], 6) for i in range(len(pts) - 1)])
        score = plat_score(dense)
        length = math.dist(P[A], P[B])
        refshare = 0
        axis_refs = ([ARGS.axis_ref] if ARGS.axis_ref else []) + list(CFG.get("axis_refs", []))
        if axis_refs:
            refs_ = [w["tags"].get("ref") for w in ways.values() if w["nodes"][0] in p or w["nodes"][-1] in p]
            refshare = sum(r in axis_refs for r in refs_) / max(len(refs_), 1)
            ends_refs = {w["tags"].get("ref") for w in ways.values() for e_ in (A, B) if e_ in (w["nodes"][0], w["nodes"][-1])}
            refshare += len(ends_refs & set(axis_refs))          # beide Enden auf den gewünschten Strecken
        mainlen = sum(math.dist(P[a_], P[b_]) for w in ways.values() if w["tags"].get("usage") == "main"
                      for a_, b_ in zip(w["nodes"], w["nodes"][1:]) if a_ in pset and b_ in pset)
        totlen = sum(math.dist(P[a_], P[b_]) for a_, b_ in zip(p, p[1:]))
        key_ = (round(refshare, 1), round(mainlen / max(totlen, 1), 1), score, length)
        if best is None or key_ > best[0]: best = (key_, A, B, p)
if best is None:      # Kopfbahnhof mit nur einem Streckenende (Lenk 21.10.): vom Gleisknoten am Bahnhof zum fernsten erreichbaren Knoten
    _n0 = min(P, key=lambda n: math.hypot(*P[n]))
    _far = sorted(ends_ or list(P), key=lambda n: -math.dist(P[n], P[_n0]))
    _p = next((p for p in (shortest(_n0, f) for f in _far) if p), [_n0, _far[0]])
    best = (None, _p[0], _p[-1], _p)
_, A, B, path = best
if CFG.get("axis_mode") == "main_extremes":
    # Achse zwischen den äussersten Knoten der Stammlinie (usage=main), quer zur Hauptrichtung
    mainn = [n for w in ways.values() if w["tags"].get("usage") == "main" for n in w["nodes"]]
    pts_ = np.array([P[n] for n in mainn]); c_ = pts_.mean(0)
    u_, sv_, vt_ = np.linalg.svd(pts_ - c_); dirv = vt_[0]
    proj_ = (pts_ - c_) @ dirv
    A, B = mainn[int(proj_.argmin())], mainn[int(proj_.argmax())]
    path = shortest(A, B)
if P[A][0] > P[B][0]: A, B, path = B, A, path[::-1]        # Achse von West nach Ost
path = path[::-1]
R = np.array([P[n] for n in path[::-1]])
# Regel 25: Achse aus der Netz-Topologie (Streckenachse durch den Bahnhof), falls vorhanden
if os.path.exists(f"{key}_axis.json") and not CFG.get("axis_auto"):
    _ax = json.load(open(f"{key}_axis.json"))["coords"]
    R = np.array([xy({"lat": la, "lon": lo}) for la, lo in _ax])
    if R[0, 0] > R[-1, 0]: R = R[::-1]
    for _ in range(2):                                   # Enden um 1.5 km verlängern (Projektion ausserhalb)
        v0 = R[0] - R[min(5, len(R) - 1)]; v0 = v0 / (np.linalg.norm(v0) or 1)
        v1 = R[-1] - R[max(-6, -len(R))]; v1 = v1 / (np.linalg.norm(v1) or 1)
        R = np.vstack([R[0] + v0 * 1500, R, R[-1] + v1 * 1500])
        break
cum = np.r_[0, np.cumsum(np.linalg.norm(np.diff(R, axis=0), axis=1))]
SS = np.arange(0, cum[-1], 5.0)
Rx = np.interp(SS, cum, R[:, 0]); Ry = np.interp(SS, cum, R[:, 1])
k = np.ones(9) / 9
R = np.c_[np.convolve(np.pad(Rx, 4, "edge"), k, "valid"), np.convolve(np.pad(Ry, 4, "edge"), k, "valid")]
A0, AB = R[:-1], R[1:] - R[:-1]; AB2 = (AB ** 2).sum(1)

def _proj_all(Q):
    """(s, d) für viele Punkte gegen die aktuelle Achse R."""
    out = []
    for p in Q:
        t = np.clip(((p - A0) * AB).sum(1) / AB2, 0, 1); QQ = A0 + t[:, None] * AB
        dd = np.linalg.norm(p - QQ, axis=1); i = dd.argmin()
        cr = AB[i, 0] * (p - A0[i])[1] - AB[i, 1] * (p - A0[i])[0]
        out.append((SS[i] + t[i] * 5.0, math.copysign(dd[i], cr)))
    return np.array(out)
# Regel 26: Topologie-Achse an das Gleisbündel anschmiegen (grobe Achse lag in Kurven bis 50 m daneben)
if os.path.exists(f"{key}_axis.json") and not CFG.get("axis_auto") and CFG.get("axis_snap", True):
    _mn = list({n for w in ways.values() if not w["tags"].get("service") and (not CFG.get("snap_main_only") or w["tags"].get("usage") == "main")
                for n in w["nodes"] if n in P})
    _Q = np.array([P[n] for n in _mn])
    for _it in range(3):
        _sd = _proj_all(_Q); lim = (90, 60, 40)[_it]
        _sd = _sd[np.abs(_sd[:, 1]) < lim]
        if len(_sd) < 10: break
        shift = np.zeros(len(SS)); have = np.zeros(len(SS), bool)
        for j, s_ in enumerate(SS):
            m = np.abs(_sd[:, 0] - s_) < CFG.get("snap_win_m", 80)
            if m.sum() >= 3: shift[j] = np.median(_sd[m, 1]); have[j] = True
        if not have.any(): break
        idx = np.arange(len(SS)); shift = np.interp(idx, idx[have], shift[have])   # ausserhalb: konstant fortsetzen
        _kw = int(CFG.get("snap_smooth_m", 155) / 5) // 2 * 2 + 1
        kk = np.ones(_kw) / _kw; shift = np.convolve(np.pad(shift, _kw // 2, "edge"), kk, "valid")
        T_ = np.gradient(R, axis=0); T_ = T_ / np.linalg.norm(T_, axis=1)[:, None]; Nl = np.c_[-T_[:, 1], T_[:, 0]]
        R = R + Nl * shift[:, None]
        cum = np.r_[0, np.cumsum(np.linalg.norm(np.diff(R, axis=0), axis=1))]
        SS = np.arange(0, cum[-1], 5.0)
        R = np.c_[np.interp(SS, cum, R[:, 0]), np.interp(SS, cum, R[:, 1])]
        A0, AB = R[:-1], R[1:] - R[:-1]; AB2 = (AB ** 2).sum(1)

def project(p):
    p = np.asarray(p)
    t = np.clip(((p - A0) * AB).sum(1) / AB2, 0, 1)
    Q = A0 + t[:, None] * AB
    dd = np.linalg.norm(p - Q, axis=1); i = dd.argmin()
    cr = AB[i, 0] * (p - A0[i])[1] - AB[i, 1] * (p - A0[i])[0]
    return SS[i] + t[i] * 5.0, math.copysign(dd[i], cr)

SD = {n: project(p) for n, p in P.items()}
if os.environ.get("SPUR_SD"): json.dump({str(n): [SD[n][0], SD[n][1], LL[n][0], LL[n][1]] for n in SD if n in LL}, open(os.environ["SPUR_SD"], "w"))
sw_s = [SD[n][0] for n, t in ntag.items() if t.get("railway") == "switch" and n in SD
        and math.hypot(*P[n]) < CFG["sw_search_m"] and abs(SD[n][1]) < CFG["d_lim"]]
pl_s = [project(xy(g))[0] for e in PLAT for g in e["geometry"] if math.hypot(*xy(g)) < CFG["sw_search_m"]]
_s_st = project((0.0, 0.0))[0]                      # Bahnhofsknoten liegt im Ursprung
CFG["s_min"] = max(min(sw_s + pl_s + [_s_st - CFG["min_half_window_m"]]) - CFG["s_pad"], SS[0] + 1)
CFG["s_max"] = min(max(sw_s + pl_s + [_s_st + CFG["min_half_window_m"]]) + CFG["s_pad"], SS[-1] - 1)
if CFG.get("s_min_fix") is not None: CFG["s_min"] = CFG["s_min_fix"]
if CFG.get("s_max_fix") is not None: CFG["s_max"] = CFG["s_max_fix"]
# Regel 20: Seitenausschnitt so breit, dass alle Personengleise (Override) im Bahnhof hineinpassen
_pd = [abs(SD[n][1]) for w in ways.values() if w["tags"].get("railway:track_ref") in OVR.get("pax", [])
       and w["tags"].get("service") not in ("yard",) for n in w["nodes"]
       if CFG["s_min"] <= SD[n][0] <= CFG["s_max"] and abs(SD[n][1]) < 250]
D_BASE = CFG["d_lim"]; PZ = None
if _pd and max(_pd) + 25 > D_BASE:
    _ps = [SD[n][0] for w in ways.values() if w["tags"].get("railway:track_ref") in OVR.get("pax", [])
           and w["tags"].get("service") not in ("yard",) for n in w["nodes"]
           if CFG["s_min"] <= SD[n][0] <= CFG["s_max"] and abs(SD[n][1]) < 250]
    PZ = (min(_ps) - 20, max(_ps) + 20, max(_pd) + 25)      # Perronzone: (s von, s bis, d_lim)
def d_lim_at(s_):
    if PZ and PZ[0] <= s_ <= PZ[1]: return PZ[2]
    return D_BASE
print(f"Bahnhof {CFG['title']}: Achse {SS[-1]:.0f} m, Ausschnitt s={CFG['s_min']:.0f}…{CFG['s_max']:.0f}, {len(sw_s)} Weichen, {len(PLAT)} Perrons")
if os.environ.get("SPUR_FENSTER"):          # nur Planfenster ausgeben (Prüfung 4 im Regionalplan, 17.10.)
    _k = (SS >= CFG["s_min"]) & (SS <= CFG["s_max"])
    json.dump(dict(achse=[[lat0 + float(y_) / ky, lon0 + float(x_) / kx] for x_, y_ in R[:len(SS)][_k][::4]], d_lim=float(D_BASE),
                   s=[float(v) for v in SS[_k][::4]], s_min=float(CFG["s_min"]), s_max=float(CFG["s_max"])), open(f"{key}_fenster.json", "w"))
    sys.exit(0)

# ------------------------------------------------------ 2. Segmente
use = collections.Counter(n for w in ways.values() for n in w["nodes"])
ends = collections.Counter()
for w in ways.values():
    ends[w["nodes"][0]] += 1; ends[w["nodes"][-1]] += 1
def is_break(n):
    return use[n] > 1 or ntag.get(n, {}).get("railway") == "switch"

def passenger(t):
    r = t.get("railway:track_ref")
    if t.get("service"): return False
    return True

segs = []
for w in ways.values():
    ns = w["nodes"]; cur = [ns[0]]
    for n in ns[1:]:
        cur.append(n)
        if is_break(n) or n == ns[-1]:
            if len(cur) > 1: segs.append(dict(nodes=cur, way=w["id"], tags=w["tags"]))
            cur = [n]

if ARGS.dbg:
    for _w in (195100338, 195100333, 43482320):
        if _w in ways: print("WAY", _w, [(n, [round(v) for v in SD[n]] if n in SD else None) for n in ways[_w]["nodes"]])
# Clipping auf Zeichenbereich
def inside(n):
    s, d = SD[n]; return CFG["s_min"] <= s <= CFG["s_max"] and abs(d) <= d_lim_at(s)
clipped = []
LAT_CUT = set()
EDGE_NODES = set()          # innere Knoten, an denen ein Gleis den Ausschnitt verlässt
EDGE_OUT = {}
EDGE_OUTS = collections.defaultdict(set)
for sg in segs:
    ins = [inside(n) for n in sg["nodes"]]
    for k_ in range(len(ins) - 1):
        if ins[k_] != ins[k_ + 1]:
            n_in, n_out = (sg["nodes"][k_], sg["nodes"][k_ + 1]) if ins[k_] else (sg["nodes"][k_ + 1], sg["nodes"][k_])
            if not (CFG["s_min"] <= SD[n_out][0] <= CFG["s_max"]):
                EDGE_NODES.add(n_in); EDGE_OUT.setdefault(n_in, n_out); EDGE_OUTS[n_in].add(n_out)   # nur am Längsende
for sg in segs:
    ins = [inside(n) for n in sg["nodes"]]
    if not any(ins): continue
    # nur den zusammenhängenden inneren Teil behalten
    i0 = ins.index(True); i1 = len(ins) - 1 - ins[::-1].index(True)
    sg["cut0"] = i0 > 0; sg["cut1"] = i1 < len(ins) - 1
    # Regel 16: offenes Ende eines Streckengleises (kein Prellbock, Rand der Daten) = Abgang
    if not sg["tags"].get("service"):
        for e_, n_ in ((0, sg["nodes"][i0]), (1, sg["nodes"][i1])):
            if use[n_] == 1 and ntag.get(n_, {}).get("railway") != "buffer_stop" and at_data_edge(n_):
                sg["cut%d" % e_] = True
    # Regel 42: eine Weichenverbindung (crossover), die an einem Randknoten auf das Streckengleis trifft, läuft nicht
    # aus dem Plan - sie endet dort an der Weiche (Olten Hammer West: zweiter Spurwechsel fehlte)
    _xo42 = RU.get("r42", True) and sg["tags"].get("service") == "crossover"
    if sg["nodes"][i0] in EDGE_NODES and not (_xo42 and i0 == 0): sg["cut0"] = True
    if sg["nodes"][i1] in EDGE_NODES and not (_xo42 and i1 == len(ins) - 1): sg["cut1"] = True
    sg["nodes"] = sg["nodes"][i0:i1 + 1]
    if len(sg["nodes"]) < 2:
        # Gleis verlässt den Ausschnitt seitlich direkt am Knoten (Olten Ost, Linie 531): Nachbarsegment dort als Abgang
        if passenger(sg["tags"]): LAT_CUT.add(sg["nodes"][0])
        continue
    clipped.append(sg)
for sg in clipped:
    if sg["tags"].get("service"): continue
    if sg["nodes"][0] in LAT_CUT and use[sg["nodes"][0]] <= 2: sg["cut0"] = True
    if sg["nodes"][-1] in LAT_CUT and use[sg["nodes"][-1]] <= 2: sg["cut1"] = True
# Regel 36: verlässt ein Gleis den Plan an einem Knoten, an dem mehrere Gleisstücke enden (Weiche direkt vor dem
# Planrand, Zofingen Süd), läuft nur das Stück weiter, das in der Flucht der Strecke liegt - die anderen enden an der Weiche
if RU.get("r36", True):
    for n_ in EDGE_NODES:
        at_ = [(sg, e_) for sg in clipped for e_, m_ in ((0, sg["nodes"][0]), (1, sg["nodes"][-1])) if m_ == n_ and sg["cut%d" % e_]]
        if len(at_) < 2 or len(EDGE_OUTS[n_]) >= len(at_) or not all(passenger(t[0]["tags"]) for t in at_): continue
        vo = np.subtract(P[EDGE_OUT[n_]], P[n_]); vo = vo / (np.linalg.norm(vo) or 1)
        def _al(t):
            sg, e_ = t; m_ = sg["nodes"][1] if e_ == 0 else sg["nodes"][-2]
            vi = np.subtract(P[n_], P[m_]); return float(vi @ vo) / (np.linalg.norm(vi) or 1)
        best = max(at_, key=_al)
        if ARGS.dbg: print("R36", n_, [(t[0]["way"], t[0]["tags"].get("service"), round(_al(t), 2)) for t in at_], len(EDGE_OUTS[n_]))
        for t in at_:
            if t is not best: t[0]["cut%d" % t[1]] = False
# Gleisstücke, die an beiden Enden aus dem Plan laufen und dazwischen nirgends
# anschliessen (z.B. Hafengleise, die den Ausschnitt nur kurz streifen), weglassen
_u = collections.Counter(n for sg in clipped for n in (sg["nodes"][0], sg["nodes"][-1]))
# Regel 23: Abstellgleise, die seitlich (nicht am Längsende) aus dem Ausschnitt laufen, weglassen
def _side_cut(sg):          # abgeschnittenes Ende irgendwo zwischen den Längsenden des Ausschnitts
    return any(sg["cut%d" % e_] and CFG["s_min"] + 15 < SD[n_][0] < CFG["s_max"] - 15
               for e_, n_ in ((0, sg["nodes"][0]), (1, sg["nodes"][-1])))
def _lateral_cut(sg):
    for e_, n_ in ((0, sg["nodes"][0]), (1, sg["nodes"][-1])):
        if sg["cut%d" % e_] and n_ not in EDGE_NODES and CFG["s_min"] + 15 < SD[n_][0] < CFG["s_max"] - 15:
            return True
    return False
# Regel 35 (nur --hauptgleise): auch übrige Nebengleise, die seitlich aus dem Ausschnitt laufen, weglassen -
# im Hauptgleis-Plan sind sie Stummel mit Abgangspfeilen ins Nichts (Rothrist West: Zufahrt Rangieranlage)
clipped = [sg for sg in clipped if not ((sg["tags"].get("service") == "yard" or (ARGS.hauptgleise and RU.get("r35", True)
           and not passenger(sg["tags"]) and sg["tags"].get("railway:track_ref") not in OVR.get("pax", []) and _side_cut(sg))) and _lateral_cut(sg))
           and not (ARGS.hauptgleise and RU.get("r35", True) and not passenger(sg["tags"])
                    and sg["tags"].get("railway:track_ref") not in OVR.get("pax", []) and _side_cut(sg))]
segs = [sg for sg in clipped if not (sg["cut0"] and sg["cut1"] and not passenger(sg["tags"])
        and _u[sg["nodes"][0]] == 1 and _u[sg["nodes"][-1]] == 1)]
# Knoten, durch den ein anderer Way durchläuft (nicht dort endet) -> dort liegt eine Weiche auf einem durchgehenden Gleis
_thru_n = collections.defaultdict(set)
for _w, _wd in ways.items():
    for _n in _wd["nodes"][1:-1]: _thru_n[_n].add(_w)
def _thru(n, w): return bool(_thru_n.get(n, set()) - {w})
def _par_run(p):          # längster Abschnitt parallel zur Achse [m] (Gleis statt Verbindung)
    L_ = max(p[-1, 0] - p[0, 0], 1e-6); ss_ = np.linspace(p[0, 0], p[-1, 0], max(int(L_ / 5), 3))
    par_ = np.abs(np.diff(np.interp(ss_, p[:, 0], p[:, 1]))) / np.diff(ss_) < 0.012
    run_, best_ = 0, 0
    for v in par_:
        run_ = run_ + 1 if v else 0; best_ = max(best_, run_)
    return best_ * (ss_[1] - ss_[0])
# Override "kreuzung": Nebengleise, die an den beiden kreuzenden Strecken hängen, fallen weg (die Kreuzung wird schematisch gezeichnet)
WEG_SEGS = [sg for sg in segs if sg["way"] in OVR.get("weglassen", [])]
segs = [sg for sg in segs if sg["way"] not in OVR.get("weglassen", [])]     # Override "weglassen": Ways nicht zeichnen
if OVR.get("kreuzung") and OVR["kreuzung"].get("ohne_nebengleise", True):
    _kxn = set(ways[OVR["kreuzung"]["a"]["way"]]["nodes"]) | set(ways[OVR["kreuzung"]["b"]["way"]]["nodes"])
    _pax_ = lambda sg: passenger(sg["tags"]) or sg["tags"].get("railway:track_ref") in OVR.get("pax", [])
    for _ in range(5):
        _rm = [sg for sg in segs if not _pax_(sg) and (_kxn & {sg["nodes"][0], sg["nodes"][-1]})]
        if not _rm: break
        for sg in _rm: _kxn |= {sg["nodes"][0], sg["nodes"][-1]}
        segs = [sg for sg in segs if sg not in _rm]
for i, sg in enumerate(segs):
    sg["id"] = i
    p = np.array([SD[n] for n in sg["nodes"]])
    if p[0, 0] > p[-1, 0]:
        sg["nodes"] = sg["nodes"][::-1]; p = p[::-1]
        sg["cut0"], sg["cut1"] = sg["cut1"], sg["cut0"]
    sg["p"] = p
    sg["s0"], sg["s1"] = p[0, 0], p[-1, 0]
    L = max(sg["s1"] - sg["s0"], 1e-6)
    sg["slope"] = abs(p[-1, 1] - p[0, 1]) / L
    sg["flat"] = (sg["slope"] < CFG["flat_slope"] and (L > 15 or (RU["r14b"] and abs(p[-1, 1] - p[0, 1]) < 1.0))) or L > CFG["long_track_m"]
    # Lange, flache Gleisverbindungen (Schnellfahrweichen): wechseln die Seite um mindestens
    # einen Gleisabstand ohne geraden Abschnitt dazwischen -> Verbindung, nicht Gleis
    if not RU["r13"]: pass
    elif sg["tags"].get("service") == "crossover" and (abs(p[-1, 1] - p[0, 1]) > 2.5
                                                       or (RU.get("r34n", False) and abs(p[-1, 1] - p[0, 1]) > 0.8 and L < 100)
                                                       or (RU.get("r34", True) and abs(p[-1, 1] - p[0, 1]) > 1.0 and 100 <= L < 300)):
        if ARGS.dbg and sg["flat"] and abs(p[-1, 1] - p[0, 1]) <= 2.5: print("R34x", sg["way"], round(L), round(p[-1, 1] - p[0, 1], 1))
        sg["flat"] = False
    # Regel 34: kurzes Stück zwischen zwei Weichen, das die Seite um einen Gleisabstand wechselt = Verbindung (Wangen b. O.)
    elif (RU.get("r34", True) and 1.5 < abs(p[-1, 1] - p[0, 1]) < 5.0 and L < 120 and not sg["tags"].get("railway:track_ref")
          and _par_run(p) < 0.35 * L
          and ((not passenger(sg["tags"]) and all(_thru(n_, sg["way"]) or (RU.get("r34n", False) and use[n_] >= 2) for n_ in (sg["nodes"][0], sg["nodes"][-1])))
               or (passenger(sg["tags"]) and RU.get("r34p", True) and L < 90 and all(_thru(n_, sg["way"]) or use[n_] >= 3 for n_ in (sg["nodes"][0], sg["nodes"][-1]))))):
        if ARGS.dbg and sg["flat"]: print("R34", sg["way"], sg["tags"].get("service"), round(L), round(p[-1, 1] - p[0, 1], 1))
        sg["flat"] = False
    elif abs(p[-1, 1] - p[0, 1]) > 2.5 and 120 <= L < 250:
        sg_s = np.linspace(p[0, 0], p[-1, 0], max(int(L / 5), 3))
        sg_d = np.interp(sg_s, p[:, 0], p[:, 1])
        par = np.abs(np.diff(sg_d)) / np.diff(sg_s) < 0.012
        run_, best_ = 0, 0
        for v in par:
            run_ = run_ + 1 if v else 0; best_ = max(best_, run_)
        if best_ * (sg_s[1] - sg_s[0]) < 15:
            if sg["flat"] and ARGS.dbg: print("R13", sg["way"], sg["tags"].get("service"), sg["tags"].get("railway:track_ref"), "L %.0f dd %.1f run %.0f" % (L, p[-1, 1] - p[0, 1], best_ * (sg_s[1] - sg_s[0])))
            sg["flat"] = False
    # Override "schraeg": diese Ways sind Verbindungen (Diagonale), nicht Gleise (Tecknau Gl. 1 -> 2)
    if sg["way"] in OVR.get("schraeg", []):
        sg["flat"] = False
    for _g in OVR.get("gerade", []):           # Override "gerade": Gleis, auch wenn es leicht schräg liegt (Wangen Gl. 1)
        if (sg["way"] == _g) or (isinstance(_g, list) and sg["way"] == _g[0] and sg["s1"] <= _g[1] + 1):
            sg["flat"] = True                  # [way, s_bis]: nur das Stück dieses Ways bis s_bis
    # Nummerierte Gleise (railway:track_ref) sind immer Gleise, auch wenn sie schräg zulaufen
    tr = sg["tags"].get("railway:track_ref", "")
    if RU["r12"] and tr.isdigit() and int(tr) < 30 and (sg["s1"] - sg["s0"]) > 60 and sg["way"] not in OVR.get("schraeg", []):
        sg["flat"] = True
    # Gleisende (Prellbock/Stumpfgleis): immer als eigenes Gleis, nie als Diagonale
    if (use[sg["nodes"][0]] == 1 and not sg["cut0"]) or (use[sg["nodes"][-1]] == 1 and not sg["cut1"]):
        sg["flat"] = True
    sg["schmal"] = sg["tags"].get("spur") in ("1000", "800")       # Schmalspur (region_vorbereiten.py, Region MOB 21.10.)
    sg["pax"] = passenger(sg["tags"]) or sg["tags"].get("railway:track_ref") in OVR.get("pax", []) or sg["way"] in OVR.get("pax_ways", [])
    if sg["way"] in OVR.get("kein_pax", []): sg["pax"] = False      # Override "kein_pax": Way schwarz (Twann Bauphasen, 15.10.)
    if ARGS.dbg and sg["way"] == 263977262: print("FLATDBG", _thru(sg["nodes"][0], sg["way"]), _thru(sg["nodes"][-1], sg["way"]), round(_par_run(p)), sg["flat"], round(sg["slope"], 4), round(L), sg["nodes"][0], sg["nodes"][-1], use[sg["nodes"][0]], use[sg["nodes"][-1]])
    sg["ref"] = sg["tags"].get("railway:track_ref")
    # Gleisnummern laut Override (OSM ohne/abweichende railway:track_ref), {"2": [way, ...]}
    for _r, _ws in OVR.get("gleise", {}).items():
        if sg["way"] in _ws: sg["ref"] = _r

# Regel 43 (opt-in r43): Verbindungen zwischen zwei Personengleisen sind Fahrwege des Personenverkehrs (dunkelgrün),
# auch wenn OSM sie als service=crossover führt (D. Eckenstein: Perrongleise müssen in Dunkelgrün erreichbar sein)
if RU.get("r43", False):
    _dg = [sg for sg in segs if not sg["flat"] and not sg["pax"] and sg["tags"].get("service") in (None, "crossover", "siding")
           and sg["way"] not in OVR.get("kein_pax", [])]      # expliziter Override «kein_pax» gewinnt (Neuchâtel Ost 26.10.)
    _par = {id(x): id(x) for x in _dg}
    def _f43(a):
        while _par[a] != a: a = _par[a]
        return a
    _byn = collections.defaultdict(list)
    for x in _dg: _byn[x["nodes"][0]].append(x); _byn[x["nodes"][-1]].append(x)
    for n_, xs_ in _byn.items():
        for x in xs_[1:]: _par[_f43(id(x))] = _f43(id(xs_[0]))
    _flat_at = collections.defaultdict(list)
    for x in segs:
        if x["flat"]: _flat_at[x["nodes"][0]].append(x); _flat_at[x["nodes"][-1]].append(x)
    _comp = collections.defaultdict(list)
    for x in _dg: _comp[_f43(id(x))].append(x)
    for xs_ in _comp.values():
        ends = [n_ for x in xs_ for n_ in (x["nodes"][0], x["nodes"][-1]) if _flat_at[n_]]
        if len(set(ends)) >= 2 and all(any(f["pax"] for f in _flat_at[n_]) for n_ in ends):
            for x in xs_: x["pax"] = True
# Kurzes gerades Mittelstück einer Verbindung (beidseitig nur Verbindungsstücke, keine Abzweige)
_inc = collections.defaultdict(list)
for sg in segs:
    _inc[sg["nodes"][0]].append(sg); _inc[sg["nodes"][-1]].append(sg)
for sg in segs:
    if not RU["r14a"] or not sg["flat"] or sg["s1"] - sg["s0"] > CFG.get("r14a_m", 50) or sg["ref"]: continue     # r14a_m: weniger Zwischengeraden (Neuchâtel 17.10.)
    nb = [x for n in (sg["nodes"][0], sg["nodes"][-1]) for x in _inc[n] if x is not sg]
    if len(nb) == 2 and all(not x["flat"] for x in nb) and all(len(_inc[n]) == 2 for n in (sg["nodes"][0], sg["nodes"][-1])):
        sg["flat"] = False

# ------------------------------------------------------ 3. Ketten
parent = list(range(len(segs)))
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
at = collections.defaultdict(lambda: ([], []))   # node -> (segs links endend, segs rechts beginnend)
for sg in segs:
    at[sg["nodes"][-1]][0].append(sg); at[sg["nodes"][0]][1].append(sg)
def dir_at(sg, end):
    p = sg["p"]
    q = p[-min(len(p), 3):] if end else p[:min(len(p), 3)]
    return (q[-1, 1] - q[0, 1]) / max(q[-1, 0] - q[0, 0], 1e-3)
for n, (L, Rr) in at.items():
    fl = [a for a in L if a["flat"]]; fr = [b for b in Rr if b["flat"]]
    # Weiterlauf: gleiche Richtung, gleicher Way bevorzugt; Weichenverbindungen (service=crossover) nur, wenn nichts anderes
    _xo = lambda x: 0.05 if x["tags"].get("service") == "crossover" else 0
    pairs = sorted(((abs(dir_at(a, 1) - dir_at(b, 0)) + (0 if a["way"] == b["way"] else CFG.get("way_pen", 0.06)) + _xo(a) + _xo(b), a["id"], b["id"])
                    for a in fl for b in fr))
    usedl, usedr = set(), set()
    for c, a, b in pairs:
        if a in usedl or b in usedr: continue
        usedl.add(a); usedr.add(b); parent[find(a)] = find(b)
chains = collections.defaultdict(list)
for sg in segs:
    if sg["flat"]: chains[find(sg["id"])].append(sg)
C = []
for cid, ss in chains.items():
    s0 = min(x["s0"] for x in ss); s1 = max(x["s1"] for x in ss)
    pts = np.vstack([x["p"] for x in ss]); pts = pts[pts[:, 0].argsort()]
    C.append(dict(id=cid, segs=ss, s0=s0, s1=s1, pts=pts))
cidx = {c["id"]: i for i, c in enumerate(C)}
def d_at(c, s): return float(np.interp(s, c["pts"][:, 0], c["pts"][:, 1]))

# ------------------------------------------------------ 4. Kompaktierung
below = collections.defaultdict(set)
for i, a in enumerate(C):
    for j, b in enumerate(C):
        if i >= j: continue
        lo, hi = max(a["s0"], b["s0"]), min(a["s1"], b["s1"])
        # Gleise auf derselben Ebene brauchen Längsabstand, sonst wirken sie wie ein Gleis
        if hi - lo < -CFG["lane_gap_m"]: continue
        if hi - lo < 8:
            sm = np.array([(lo + hi) / 2])
        else:
            sm = np.linspace(lo, hi, 7)
        diff = np.mean([d_at(a, s) - d_at(b, s) for s in sm])
        if diff > 0: below[i].add(j)
        else: below[j].add(i)
lane = {}
sys.setrecursionlimit(10000)
def L_(i, stack=()):
    if i in lane: return lane[i]
    if i in stack: return 0
    lane[i] = 1 + max((L_(j, stack + (i,)) for j in below[i]), default=-1)
    return lane[i]
for i in range(len(C)): L_(i)
# Stammgleis (d≈0) als Referenz, Lanes relativ dazu
for i, c in enumerate(C): c["lane"] = lane[i]
# Regel 21: Überlappung auf derselben Ebene auflösen (entsteht bei kreuzenden Gleisen / Überwerfungen,
# wo die Reihenfolge quer zur Achse wechselt): Ebene einfügen und das rechts liegende Gleis hochschieben
for _it in range(200):
    clash = None
    for i, a in enumerate(C):
        for b in C[i + 1:]:
            if a["lane"] != b["lane"]: continue
            if min(a["s1"], b["s1"]) - max(a["s0"], b["s0"]) > -CFG["lane_gap_m"]:
                clash = (a, b); break
        if clash: break
    if not clash: break
    a, b = clash
    lo, hi = max(a["s0"], b["s0"]), min(a["s1"], b["s1"])
    sm = (lo + hi) / 2 if hi > lo else lo
    up = a if d_at(a, sm) > d_at(b, sm) else b
    L0 = up["lane"]
    for c in C:
        if c["lane"] > L0: c["lane"] += 1
    up["lane"] = L0 + 1

# Regel 30: Gleisstücke, die nahtlos aneinander anschliessen (gleicher Knoten, gleiche Querlage), auf dieselbe
# Ebene legen - sonst springt ein durchgehendes Gleis an jeder Weiche auf eine andere Ebene (Wangen b. O.)
if RU.get("r30", True):
    _end_nodes = lambda c: ({sg["nodes"][0] for sg in c["segs"]} | {sg["nodes"][-1] for sg in c["segs"]})
    for _it in range(6):
        moved = False
        for a in C:
            for b in C:
                if a is b or b["lane"] == a["lane"]: continue
                if not (-5 <= b["s0"] - a["s1"] <= CFG.get("r30_gap_m", 40)): continue
                if abs(d_at(a, a["s1"]) - d_at(b, b["s0"])) > CFG.get("r30_dd_m", 3.0): continue
                nl = a["lane"]; ok = True
                for x in C:
                    if x is b: continue
                    lo, hi = max(x["s0"], b["s0"]), min(x["s1"], b["s1"])
                    if x["lane"] == nl and hi - lo > -CFG["lane_gap_m"] and x is not a: ok = False; break
                    if hi - lo > 5:
                        sm = (lo + hi) / 2; dd_ = d_at(x, sm) - d_at(b, sm)
                        if abs(dd_) > 2.5 and (x["lane"] - nl) * dd_ < 0: ok = False; break
                if ok: b["lane"] = nl; moved = True
        if not moved: break
    _used = sorted({c["lane"] for c in C}); _rk = {l: i for i, l in enumerate(_used)}
    for c in C: c["lane"] = _rk[c["lane"]]

# Regel 33: Streckengleise laufen gerade aus dem Plan. Ein Abgang (Kette mit abgeschnittenem Ende), der über eine
# reine Fortsetzung (Knoten ohne Weiche) in ein Bahnhofsgleis übergeht, liegt auf dessen Ebene - sonst entsteht am
# Planrand eine S-Kurve, nur weil die Strecke ausserhalb des Bahnhofs leicht schräg liegt (Wangen b. O., Zofingen)
if RU.get("r33", True):
    _inc = collections.Counter(n for sg in segs for n in (sg["nodes"][0], sg["nodes"][-1]))
    _cof = {sg["id"]: c for c in C for sg in c["segs"]}
    def _end_seg(c, side):        # Segment am linken (0) / rechten (1) Ende der Kette
        return (min if side == 0 else max)(c["segs"], key=lambda x: x["s0"] if side == 0 else x["s1"])
    def _is_exit(c, side):
        e = _end_seg(c, side); return e["cut0"] if side == 0 else e["cut1"]
    if ARGS.dbg:
        for c in sorted(C, key=lambda c: (c["lane"], c["s0"])): print("CH", c["lane"], round(c["s0"]), round(c["s1"]), [round(d_at(c, q), 1) for q in np.linspace(c["s0"], c["s1"], 4)], any(x["pax"] for x in c["segs"]), _is_exit(c, 0), _is_exit(c, 1), [(x["way"], x["nodes"][0], x["nodes"][-1]) for x in c["segs"]])
        for sg in segs:
            if True: print("DG" if not sg["flat"] else "FL", round(sg["p"][0,1],1), round(sg["p"][-1,1],1), sg["pax"], sg["way"], sg["nodes"][0], sg["nodes"][-1], round(sg["s0"]), round(sg["s1"]))
    for _it in range(8):
        moved = False
        for sg in segs:
            if sg["flat"] or not sg["pax"]: continue
            n0, n1 = sg["nodes"][0], sg["nodes"][-1]
            A = [c for c in C if _end_seg(c, 1)["nodes"][-1] == n0]      # Kette endet links der Diagonale
            B = [c for c in C if _end_seg(c, 0)["nodes"][0] == n1]       # Kette beginnt rechts davon
            if ARGS.dbg and _it == 0: print("R33?", sg["way"], len(A), len(B), [(c["lane"], _is_exit(c, 1), _inc[n0]) for c in A], [(c["lane"], _is_exit(c, 0), _inc[n1]) for c in B])
            if len(A) != 1 or len(B) != 1: continue
            A, B = A[0], B[0]
            if A["lane"] == B["lane"]: continue
            for E, T, nE, side in ((A, B, n0, 0), (B, A, n1, 1)):
                if not _is_exit(E, side): continue
                # reine Fortsetzung: kein weiterer Abzweig am Übergang - oder die Diagonale ist selbst ein Streckengleis
                if _inc[nE] != 2 and (sg["tags"].get("service") or sg["tags"].get("usage") not in ("main", "branch")): continue
                if not any(x["pax"] for x in E["segs"]): continue
                nl = T["lane"]; ok = True
                for x in C:
                    if x is E or x is T: continue
                    lo, hi = max(x["s0"], E["s0"]), min(x["s1"], E["s1"])
                    if x["lane"] == nl and hi - lo > -CFG["lane_gap_m"]: ok = False; break
                    if hi - lo > 5:
                        sm = (lo + hi) / 2; dd_ = d_at(x, sm) - d_at(T, min(max(sm, T["s0"]), T["s1"]))
                        if abs(dd_) > 2.5 and (x["lane"] - nl) * dd_ < 0: ok = False; break
                if ok:
                    if ARGS.dbg: print("R33", E["lane"], "->", nl)
                    E["lane"] = nl; moved = True; break
        if not moved:      # direkt aneinanderstossende Ketten (kein Diagonalstück dazwischen)
            for A in C:
                nA = _end_seg(A, 1)["nodes"][-1]
                for B in C:
                    if B is A or B["lane"] == A["lane"] or _end_seg(B, 0)["nodes"][0] != nA: continue
                    for E, T, side in ((A, B, 0), (B, A, 1)):
                        if not _is_exit(E, side) or not any(x["pax"] for x in E["segs"]) or not any(x["pax"] for x in T["segs"]): continue
                        nl = T["lane"]; ok = True
                        for x in C:
                            if x is E or x is T: continue
                            lo, hi = max(x["s0"], E["s0"]), min(x["s1"], E["s1"])
                            if x["lane"] == nl and hi - lo > -CFG["lane_gap_m"]: ok = False; break
                            if hi - lo > 5:
                                sm = (lo + hi) / 2; dd_ = d_at(x, sm) - d_at(T, min(max(sm, T["s0"]), T["s1"]))
                                if abs(dd_) > 2.5 and (x["lane"] - nl) * dd_ < 0: ok = False; break
                        if ok:
                            if ARGS.dbg: print("R33b", E["lane"], "->", nl)
                            E["lane"] = nl; moved = True; break
                    if moved: break
                if moved: break
        if not moved: break
    _used = sorted({c["lane"] for c in C}); _rk = {l: i for i, l in enumerate(_used)}
    for c in C: c["lane"] = _rk[c["lane"]]

# Regel 40 (Schritt 2): Ebenen aller Ketten gemeinsam optimieren (MILP) statt Kette für Kette.
#   hart: überlappende Ketten auf verschiedenen Ebenen, Reihenfolge quer zur Achse wie in der Wirklichkeit
#         (wo sie wechselt - Kreuzung/Überwerfung - entscheidet der Löser); Weichenverbindungen behalten ihre Richtung
#   Ziel (Rangfolge über Gewichte): Fortsetzungen auf gleicher Ebene (gerade, R30/R33) > kurze Weichenverbindungen
#         (Weiche sichtbar, keine Treppen) > wenige Ebenen; Abstand zum bisherigen Ergebnis als Gleichstand-Brecher
def _r40():
    global C
    from scipy.optimize import milp, LinearConstraint, Bounds
    nC = len(C); gap = CFG["lane_gap_m"]
    _ends = {}
    for i, c in enumerate(C):
        for sg in c["segs"]:
            for n in (sg["nodes"][0], sg["nodes"][-1]): _ends.setdefault(n, set()).add(i)
    order = []                                    # (i, j, Bevorzugung): +1 i über j, -1 j über i, 0 offen (Kreuzung)
    for i in range(nC):
        for j in range(i + 1, nC):
            a, b = C[i], C[j]
            lo, hi = max(a["s0"], b["s0"]), min(a["s1"], b["s1"])
            if hi - lo < -gap: continue
            sm = np.array([(lo + hi) / 2]) if hi - lo < 8 else np.linspace(lo, hi, 9)
            df = np.array([d_at(a, s) - d_at(b, s) for s in sm])
            pos, neg = (df > 1.5).any(), (df < -1.5).any()
            pref = 0 if (pos and neg) else (1 if df.mean() > 0 else -1)
            stark = 1.0 if (abs(df) > 1.5).all() else 0.3
            order.append((i, j, pref * stark))
    pairs = collections.Counter()                 # (i, j, art) -> Gewicht
    for sg in segs:
        if sg["flat"]: continue
        n0, n1 = sg["nodes"][0], sg["nodes"][-1]
        dd = sg["p"][-1, 1] - sg["p"][0, 1]
        for i in _ends.get(n0, ()):
            for j in _ends.get(n1, ()):
                if i != j: pairs[(i, j, "w", int(np.sign(dd)) if abs(dd) > 1.0 else 0)] += 1
    for i, a in enumerate(C):                     # Fortsetzung: Ende von a stösst an Anfang von b, gleiche Querlage
        for j, b in enumerate(C):
            if i == j or not (-5 <= b["s0"] - a["s1"] <= CFG.get("r30_gap_m", 40)): continue
            if abs(d_at(a, a["s1"]) - d_at(b, b["s0"])) > CFG.get("r30_dd_m", 3.0): continue
            pairs[(i, j, "f", 0)] += 1
    P = list(pairs)
    # Variablen: l_i, t_k = |l_i - l_j|, z_k (1: i über j), H, u_i Abweichung vom bisherigen Stand, e_k Weiche gegen Richtung
    nP, nF = len(P), len(order)
    o_t, o_z, o_H, o_u = nC, nC + nP, nC + nP + nF, nC + nP + nF + 1
    o_e = o_u + nC
    nV = o_e + nP
    M = nC + 2
    cobj = np.zeros(nV)
    W = dict(f=CFG.get("r40_wf", 20.0), w=CFG.get("r40_ww", 2.0), H=CFG.get("r40_wh", 1.0), u=float(os.environ.get("SPUR_WU", CFG.get("r40_wu", 0.05))))
    for k, (i, j, art, sgn) in enumerate(P): cobj[o_t + k] = W[art] * pairs[P[k]]
    cobj[o_H] = W["H"]; cobj[o_u:o_u + nC] = W["u"]; cobj[o_e:o_e + nP] = CFG.get("r40_wr", 30.0)
    WO = CFG.get("r40_wo", 100.0)                 # Grundsatz 1/2: echte Reihenfolge quer zur Achse
    for k, (i, j, pr) in enumerate(order): cobj[o_z + k] = -WO * pr
    rows, lb, ub = [], [], []
    def R(coef, lo_, hi_):
        r = np.zeros(nV)
        for ix, v in coef: r[ix] += v
        rows.append(r); lb.append(lo_); ub.append(hi_)
    for k, (i, j, pr) in enumerate(order):                                  # entweder i über j oder j über i
        R([(i, 1), (j, -1), (o_z + k, -M)], 1 - M, np.inf)
        R([(j, 1), (i, -1), (o_z + k, M)], 1, np.inf)
    for k, (i, j, art, sgn) in enumerate(P):
        R([(o_t + k, 1), (i, -1), (j, 1)], 0, np.inf); R([(o_t + k, 1), (i, 1), (j, -1)], 0, np.inf)
        if art == "w" and sgn: R([(j, sgn), (i, -sgn), (o_e + k, 1)], 0, np.inf)   # Weiche zeigt in die echte Richtung
    for i in range(nC):
        R([(o_H, 1), (i, -1)], 0, np.inf)
        R([(o_u + i, 1), (i, -1)], -C[i]["lane"], np.inf); R([(o_u + i, 1), (i, 1)], C[i]["lane"], np.inf)
    integ = np.zeros(nV); integ[:nC] = 1; integ[o_z:o_z + nF] = 1
    lo_b = np.zeros(nV); hi_b = np.full(nV, np.inf); hi_b[:nC] = nC; hi_b[o_z:o_z + nF] = 1
    res = milp(cobj, constraints=LinearConstraint(np.array(rows), lb, ub), integrality=integ, bounds=Bounds(lo_b, hi_b),
               options=dict(time_limit=CFG.get("r40_zeit_s", 30)))
    if res.x is not None:
        new = [int(round(v)) for v in res.x[:nC]]
        if ARGS.dbg: print("R40", res.status, round(res.fun, 2), "Ketten", nC, "Paare quer", nF, "gegen Lage", sum(1 for k, (i, j, pr) in enumerate(order) if pr * (res.x[o_z + k] - 0.5) < 0), "Paare", nP,
                           "geändert", sum(1 for i in range(nC) if new[i] != C[i]["lane"]))
        for i, c in enumerate(C): c["lane"] = new[i]
        _used = sorted({c["lane"] for c in C}); _rk = {l: i for i, l in enumerate(_used)}
        for c in C: c["lane"] = _rk[c["lane"]]
    elif ARGS.dbg: print("R40 keine Lösung", res.status, res.message)

if RU.get("r40", os.environ.get("SPUR_OPT") == "1"): _r40()

# Override "ebene_wie": [[way, gleisnummer], ...] - die Kette dieses Ways liegt auf der Ebene des Gleises
# (Kerzers: Streckengleis Bern in der Flucht von Gleis 1). Nur wenn es dort keine Überlappung gibt.
for _w, _r in OVR.get("ebene_wie", []):
    _cw = [c for c in C if any(sg["way"] == _w for sg in c["segs"])]
    if isinstance(_r, int):          # direkt eine Ebene (Thun: Abstellgleis eine Ebene tiefer)
        if not _cw: continue
        _cw, _l = _cw[0], _r
    else:
        _cr = [c for c in C if any(sg["tags"].get("railway:track_ref") == _r for sg in c["segs"])]
        if not _cw or not _cr: continue
        _cw, _l = _cw[0], _cr[0]["lane"]
    if all(c is _cw or c["lane"] != _l or min(c["s1"], _cw["s1"]) - max(c["s0"], _cw["s0"]) < 0 for c in C):
        _cw["lane"] = _l

# Override "ebene_tausch": [[wayA, wayB], ...] - die Ketten der beiden Ways tauschen ihre Ebenen (Thun: Gl. 5 näher an 4)
for _wa, _wb in OVR.get("ebene_tausch", []):
    _ca = [c for c in C if any(sg["way"] == _wa for sg in c["segs"])]; _cb = [c for c in C if any(sg["way"] == _wb for sg in c["segs"])]
    if _ca and _cb: _ca[0]["lane"], _cb[0]["lane"] = _cb[0]["lane"], _ca[0]["lane"]

# x-Abbildung: linear oder entzerrt (warp.json aus spurplan_warp.py)
import os
WARP = None
if os.path.exists(CFG["warp_file"]) and not ARGS.nowarp:
    WARP = json.load(open(CFG["warp_file"]))
def Xm(s):
    if WARP: return float(np.interp(s, WARP["s"], WARP["x"]))
    return (s - CFG["s_min"]) * CFG["px_per_m"]
def Xm_inv(x):
    if WARP: return float(np.interp(x, WARP["x"], WARP["s"]))
    return CFG["s_min"] + x / CFG["px_per_m"]
def ppm(sa, sb):   # lokaler Massstab px/m
    return (Xm(sb) - Xm(sa)) / (sb - sa) if sb - sa > 1e-6 else CFG["px_per_m"]

# Ebenenabstände: Personengleise voller Abstand, reine Neben-/Abstell-/Güterebenen enger (Regel 24)
def build_ly():
    global LY_L, LY_Y
    pax_l = {c["lane"] for c in C if any(sg["pax"] for sg in c["segs"])}
    # Regel 31: Ebenen, die ein Personen-/Hauptgleis über eine Weichenverbindung berührt, bekommen vollen Abstand -
    # sonst klebt ein Nebengleis an der Fahrstrasse und die Weiche ist nicht erkennbar
    if RU.get("r31", True):
        for sg in segs:
            if not sg["pax"] or sg["flat"]: continue
            for n in (sg["nodes"][0], sg["nodes"][-1]):
                s_, d_ = SD[n]
                cc = [(abs(d_at(c, s_) - d_), c["lane"]) for c in C if c["s0"] - 1 <= s_ <= c["s1"] + 1]
                if cc and min(cc)[0] < 2.0: pax_l.add(min(cc)[1])
    top = max(c["lane"] for c in C)
    LY_L, LY_Y = [top], [0.0]
    for l in range(top - 1, min(c["lane"] for c in C) - 1, -1):
        g_ = CFG["lane_px"] if ((l in pax_l or l + 1 in pax_l) and l not in OVR.get("enge_ebenen", [])) else CFG["lane_px"] * CFG["side_lane_factor"]
        g_ += OVR.get("ebenen_luecke", {}).get(str(l), 0)    # Override: zusätzlicher Abstand über Ebene l (Kerzers: 3 und 4 gespreizt)
        LY_L.append(l); LY_Y.append(LY_Y[-1] + g_)
    LY_L, LY_Y = LY_L[::-1], LY_Y[::-1]
def LY(l):
    if l > LY_L[-1]: return LY_Y[-1] - (l - LY_L[-1]) * CFG["lane_px"]
    if l < LY_L[0]: return LY_Y[0] + (LY_L[0] - l) * CFG["lane_px"]
    return float(np.interp(l, LY_L, LY_Y))
build_ly()

# Knoten -> Heimat-Lane (Gleis, auf dem die Weiche liegt)
seglane = {}
for c in C:
    for sg in c["segs"]: seglane[sg["id"]] = c["lane"]
home = {}
cand = collections.defaultdict(list)
for c in C:
    nodes_c = collections.Counter()
    for sg in c["segs"]:
        nodes_c[sg["nodes"][0]] += 1; nodes_c[sg["nodes"][-1]] += 1
    for n, k in nodes_c.items():
        cand[n].append((k, c["s1"] - c["s0"], c["lane"]))
for n, cs in cand.items():
    home[n] = max(cs)[2]          # durchgehende Kette bevorzugt, sonst längste
# Vorrang: läuft ein OSM-Way durch den Knoten, liegt die Weiche auf dessen Gleis
_wl = collections.defaultdict(dict)
for c in C:
    for sg in c["segs"]:
        _wl[sg["nodes"][-1]].setdefault(sg["way"], c["lane"])
        _wl[sg["nodes"][0]].setdefault(sg["way"], c["lane"])
_thru = collections.defaultdict(set)
thru_fixed = set()
for sg in segs:
    _thru[sg["nodes"][0]].add(("R", sg["way"])); _thru[sg["nodes"][-1]].add(("L", sg["way"]))
for n in list(home):
    ways_thru = {w for side, w in _thru[n] if ("L", w) in _thru[n] and ("R", w) in _thru[n]}
    # Vorrang: durchgehendes Gleis vor Way-Regel - ausser ein Personengleis läuft
    # durch und das durchgehende Gleis ist nur ein Neben-/Abstellgleis
    thr_chains = [c for c in C if c["lane"] in {l for k, _, l in cand[n] if k == 2}
                  and any(n in (x["nodes"][0], x["nodes"][-1]) for x in c["segs"])]
    thr_pax = any(any(x["pax"] for x in c["segs"]) for c in thr_chains)
    way_pax = any(passenger(ways[w]["tags"]) for w in ways_thru)
    if thr_chains and (thr_pax or not way_pax): continue
    for w in ways_thru:
        if w in _wl[n]:
            home[n] = _wl[n][w]; thru_fixed.add(n); break
def lane_guess(s, d):
    cc = [(d_at(c, s), c["lane"]) for c in C if c["s0"] - 1 <= s <= c["s1"] + 1]
    if not cc: return 0
    cc.sort()
    # Regel 22: ausserhalb der vorhandenen Gleise mit Gleisabstand weiterzählen statt am Rand kleben
    _mx = CFG.get("extrap_max_lanes", 1e9)
    if d > cc[-1][0] + 2.5: return cc[-1][1] + min((d - cc[-1][0]) / 4.5, _mx)
    if d < cc[0][0] - 2.5: return cc[0][1] - min((cc[0][0] - d) / 4.5, _mx)
    return float(np.interp(d, [x[0] for x in cc], [x[1] for x in cc]))
# Weichenstrassen bilden: Diagonalen verketten. Am Knoten läuft die Diagonale
# mit dem Abzweig weiter, der am weitesten (in Lanes) in dieselbe Richtung führt;
# näher liegende Gleise zweigen von der Diagonale ab.
def lane_of(n):
    return home[n] if n in home else lane_guess(*SD[n])
diag = [sg for sg in segs if not sg["flat"]]
start_at = collections.defaultdict(list)
for sg in diag: start_at[sg["nodes"][0]].append(sg)
succ, has_pred = {}, set()
for sg in diag:
    n = sg["nodes"][-1]
    def dlane(p, q):   # Richtung/Weite aus dem echten Seitenversatz [m]
        return SD[q][1] - SD[p][1]
    dl = dlane(sg["nodes"][0], n)
    opts = [o for o in start_at[n] if dlane(n, o["nodes"][-1]) * dl > 0]
    opts = [o for o in opts if o["pax"] == sg["pax"]]   # gleiche Gleisklasse
    same = [o for o in opts if o["way"] == sg["way"]]
    if sg["pax"] and same: opts = same                   # Personengleis: eigener Weiterlauf
    if n in cand:   # Knoten auf einem Gleis: nur als Kreuzung durchlaufen (gleicher Way)
        opts = [o for o in opts if o["way"] == sg["way"]]
    if not opts: continue
    best = max(opts, key=lambda o: abs(dlane(n, o["nodes"][-1])))
    if best["id"] in has_pred: continue
    succ[sg["id"]] = best; has_pred.add(best["id"])
groups = []
for sg in diag:
    if sg["id"] in has_pred: continue
    g = [sg]
    while g[-1]["id"] in succ: g.append(succ[g[-1]["id"]])
    groups.append(g)
for g in groups:
    a, b = g[0]["nodes"][0], g[-1]["nodes"][-1]
    for n in (a, b):
        if n not in home: home[n] = int(round(lane_guess(*SD[n])))
    if len(g) > 1:
        sa, sb = g[0]["s0"], g[-1]["s1"]
        la, lb = home[a], home[b]
        run_m = (abs(LY(lb) - LY(la)) / math.tan(math.radians(CFG['sw_angle'])) + 2 * CFG["sw_radius"]) / ppm(sa, sb)
        run_m = min(run_m, sb - sa)
        # Diagonale dort, wo die echte Linie die halbe Seitenverschiebung erreicht
        pts = np.vstack([x["p"] for x in g])
        dm = (pts[0, 1] + pts[-1, 1]) / 2
        k = np.argmin(np.abs(pts[:, 1] - dm)); sm = pts[k, 0]
        d0 = min(max(sm - run_m / 2, sa), sb - run_m)
        thr = lambda n: any(k == 2 for k, _, _ in cand.get(n, []))
        g[0]["anchor"] = None
        if thr(b) and not thr(a): d0 = sb - run_m; g[0]["anchor"] = "b"     # Ziel-Weiche auf Hauptgleis: dort ankern
        elif thr(a) and not thr(b): d0 = sa; g[0]["anchor"] = "a"
        # Kreuzt die Diagonale unterwegs ein durchgehendes Gleis an einer Weiche,
        # muss sie genau dort durch -> Polygonzug durch die echten Weichenpunkte
        anchors = [(sa, la)] + [(sg_["s0"], home[sg_["nodes"][0]]) for sg_ in g[1:]
                                if thr(sg_["nodes"][0])] + [(sb, lb)]
        if len(anchors) > 2:
            for sg_ in g: sg_["anchors"] = anchors
            A_s = [x[0] for x in anchors]; A_l = [x[1] for x in anchors]
            for sg_ in g[1:]:
                m = sg_["nodes"][0]
                if not thr(m): home[m] = float(np.interp(Xm(sg_["s0"]), [Xm(v) for v in A_s], A_l))
            for sg_ in g: sg_["diag"] = (sa, sb)
        for sg in g:
            if "anchors" not in sg:
                # Breite in Pixeln exakt nach Standardfigur (Entzerrung ist nicht linear)
                need_px = abs(LY(lb) - LY(la)) / math.tan(math.radians(CFG["sw_angle"])) + 2 * CFG["sw_radius"]
                d1_ = Xm_inv(Xm(d0) + need_px)
                if d1_ > sb:
                    d1_ = sb; d0 = Xm_inv(Xm(sb) - need_px)
                sg["diag"] = (max(d0, sa), d1_)
        for sg in ([] if "anchors" in g[0] else g[1:]):
            n = sg["nodes"][0]
            if n not in cand:
                f = np.clip((sg["s0"] - d0) / max(run_m, 1e-6), 0, 1)
                home[n] = la + (lb - la) * f
    for sg in g: sg["group"] = g
for sg in segs:
    for n in (sg["nodes"][0], sg["nodes"][-1]):
        if n not in home: home[n] = int(round(lane_guess(*SD[n])))
# Abgeschnittene Enden (Strecke/Gleis läuft aus dem Plan): auf der Ebene des
# inneren Endes bleiben, statt per Schätzung auf einem fremden Gleis zu landen
LAT_CUT = {}
LAT_CUR = {}
LAT_OWN = {}
EDGE_LONG = set()   # Regel 28c
PAX_SIDE = set()    # Regel 15b: Hauptgleis läuft seitlich aus -> Abgang am Gleisende        # Regel 28: nur das auslaufende Gleis wird an den Rand gezogen, nicht andere Gleise am selben Knoten
for sg in segs:
    if sg["cut0"]: home[sg["nodes"][0]] = home[sg["nodes"][-1]]
    if sg["cut1"]: home[sg["nodes"][-1]] = home[sg["nodes"][0]]
    # seitlich aus dem Plan laufend: Abgang direkt am inneren Ende, nicht entlang eines fremden Gleises
    for end in (0, 1):
        if not sg["cut%d" % end]: continue
        nc = sg["nodes"][-1 if end else 0]; ni = sg["nodes"][0 if end else -1]
        # Regel 28: läuft das Gleis längs aus dem Ausschnitt (nächster Punkt jenseits s_min/s_max),
        # wird es bis an den Planrand gezogen statt als seitlicher Abgang behandelt
        _w = ways[sg["way"]]["nodes"]; _i = _w.index(nc) if nc in _w else -1
        _nb = [_w[j] for j in (_i - 1, _i + 1) if _i >= 0 and 0 <= j < len(_w) and _w[j] not in sg["nodes"]]
        if not _nb and RU.get("r28b", True):     # Gleis läuft in einem anderen Way weiter (Aarburg Gl. 2/3 Richtung Olten)
            for _w2 in ways.values():
                _ww = _w2["nodes"]
                if nc in _ww and _w2["id"] != sg["way"]:
                    _k = _ww.index(nc); _nb += [_ww[j] for j in (_k - 1, _k + 1) if 0 <= j < len(_ww) and _ww[j] not in sg["nodes"] and _ww[j] in SD]
        # Regel 28c: Nebengleis, das nahe am Planende seitlich ausläuft (Strecke im Bogen), läuft längs weiter
        _ez = CFG.get("edge_zone_m", 150)
        _near_end = SD[nc][0] - CFG["s_min"] < _ez or CFG["s_max"] - SD[nc][0] < _ez
        if RU.get("r28c", False) and not sg["pax"] and _nb and _near_end and (CFG["s_min"] <= SD[_nb[0]][0] <= CFG["s_max"]):
            LAT_CUT[nc] = CFG["s_min"] if SD[nc][0] - CFG["s_min"] < CFG["s_max"] - SD[nc][0] else CFG["s_max"]
            LAT_OWN[nc] = sg["id"]; EDGE_LONG.add(nc)
            continue
        # Regel 28d: bei mehreren Nachbarn (Weiche am Wayende, Tecknau Süd) zählt der Nachbar ausserhalb des Ausschnitts
        if RU.get("r28d", False):
            _nb = sorted(_nb, key=lambda m: CFG["s_min"] <= SD[m][0] <= CFG["s_max"] if m in SD else True)
        if RU.get("r28", True) and _nb and not (CFG["s_min"] <= SD[_nb[0]][0] <= CFG["s_max"]):
            LAT_CUT[nc] = CFG["s_min"] if SD[_nb[0]][0] < CFG["s_min"] else CFG["s_max"]
            LAT_OWN[nc] = sg["id"]
            continue
        if RU.get("r15b", True) and sg["flat"] and sg["pax"] and CFG["s_min"] + 15 < SD[nc][0] < CFG["s_max"] - 15:
            PAX_SIDE.add(nc)
            continue        # Regel 15b: flaches Hauptgleis bleibt bis zu seinem Endpunkt gezeichnet (Däniken Gl. 4 verschwand)
        if RU["r15"] and CFG["s_min"] + 15 < SD[nc][0] < CFG["s_max"] - 15:
            # nach innen laufen, bis ein Gleis (Kette) erreicht ist: dort beginnt der Abgang
            chainnodes, cur, seg_ = [nc], ni, sg
            while cur not in cand:
                nxt = [x for x in segs if x is not seg_ and cur in (x["nodes"][0], x["nodes"][-1]) and not x["flat"]]
                if len(nxt) != 1: break
                chainnodes.append(cur); seg_ = nxt[0]
                cur = seg_["nodes"][-1] if seg_["nodes"][0] == cur else seg_["nodes"][0]
            for m in chainnodes:
                LAT_CUT[m] = SD[cur][0]; home[m] = home[cur]; LAT_CUR[m] = cur

# Weichenregel (Weichenstrasse): kommt der Zulauf schräg und gehen auf der
# anderen Seite mehrere Gleise ab, liegt die Weiche auf dem Abzweig, der dem
# Zulauf am nächsten ist. Die übrigen Gleise schwenken von dort aus ab.
# -> keine V-Formen, Weichenstrassen werden zu sauberen Fächern.
ends_L = collections.defaultdict(list); ends_R = collections.defaultdict(list)
for sg in segs:
    ends_L[sg["nodes"][-1]].append(sg); ends_R[sg["nodes"][0]].append(sg)
def far_lane(sg, n):
    m = sg["nodes"][-1] if sg["nodes"][0] == n else sg["nodes"][0]
    return seglane[sg["id"]] if sg["flat"] else home[m]
for n in list(home):
    if n in thru_fixed: continue
    for one, many in ((ends_L[n], ends_R[n]), (ends_R[n], ends_L[n])):
        if len(one) == 1 and not one[0]["flat"] and len(many) >= 2:
            y_in = far_lane(one[0], n)
            opts = [far_lane(sg, n) for sg in many]
            home[n] = min(opts, key=lambda l: abs(l - y_in))

# Abgeschnittene Enden flacher Gleise bleiben auf der Ebene ihres Gleises (Vorrang vor Weichenregeln)
for sg in segs:
    if sg["flat"] and sg["id"] in seglane:
        if sg["cut0"]: home[sg["nodes"][0]] = seglane[sg["id"]]
        if sg["cut1"]: home[sg["nodes"][-1]] = seglane[sg["id"]]

# Weichen auf einer Weichenstrassen-Diagonale: x so setzen, dass der Punkt
# exakt auf der gezeichneten Diagonale liegt.
# Override "kreuzung": Anschlussknoten der kreuzenden Strecken auf das Gleis legen, durch das die Achse läuft
# (Kerzers: Murten-Lyss durch Gleis 1, Ins-Bern durch Gleis 6)
if OVR.get("kreuzung"):
    for _k, _end in (("a", 0), ("b", -1)):
        _cf = OVR["kreuzung"][_k]; _g = _cf.get("gleis")
        _ss = [sg for sg in segs if sg["way"] == _cf["way"]]
        if not _g or not _ss: continue
        _sg = (min(_ss, key=lambda x: x["s0"]) if _end == 0 else max(_ss, key=lambda x: x["s1"]))
        _ln = [seglane[x["id"]] for x in segs if x["ref"] == _g and x["id"] in seglane]
        if _ln: home[_sg["nodes"][_end]] = max(set(_ln), key=_ln.count)
# Override "knoten": {"<node>": "<gleisnummer>"} - Weichenknoten auf die Ebene dieses Gleises legen (Zofingen West)
for _n, _g in OVR.get("knoten", {}).items():
    _ln = [seglane[x["id"]] for x in segs if x["ref"] == _g and x["id"] in seglane]
    if _ln and int(_n) in home: home[int(_n)] = max(set(_ln), key=_ln.count)
for _n, _l in OVR.get("knoten_lane", {}).items():   # Override: Knoten auf eine bestimmte Ebene (Olten Nord, Gleis 314)
    home[int(_n)] = _l
xs_over = dict(LAT_CUT)
for _n, _ds in OVR.get("knoten_versatz_m", {}).items():   # Override: Weichenknoten längs verschieben (m), Platz für Schrägen
    if int(_n) in SD: xs_over[int(_n)] = SD[int(_n)][0] + _ds
if ARGS.dbg: print("LY", [(l, round(LY(l), 1)) for l in range(min(c["lane"] for c in C), max(c["lane"] for c in C) + 1)])
if ARGS.dbg: print("LATCUT", {k: round(v) for k, v in LAT_CUT.items()})
diag_dir = {}
for g in groups:
    if len(g) < 2: continue
    a, b = g[0]["nodes"][0], g[-1]["nodes"][-1]
    la, lb = home[a], home[b]
    if "anchors" in g[0]:
        A_s = [x[0] for x in g[0]["anchors"]]; A_l = [x[1] for x in g[0]["anchors"]]
        for sg in g[1:]:
            n = sg["nodes"][0]
            if any(k == 2 for k, _, _ in cand.get(n, [])): continue
            if n in cand: home[n] = float(np.interp(Xm(sg["s0"]), [Xm(v) for v in A_s], A_l))
            xs_over[n] = sg["s0"]
            i = max(1, min(len(A_s) - 1, int(np.searchsorted(A_s, sg["s0"]))))
            ddx = Xm(A_s[i]) - Xm(A_s[i - 1]); ddy = LY(A_l[i]) - LY(A_l[i - 1])
            L_ = math.hypot(ddx, ddy) or 1; diag_dir[n] = (ddx / L_, ddy / L_)
        continue
    d0, d1 = g[0]["diag"]
    # mit den endgültigen Ebenen neu bemessen (Standardfigur in Pixeln, Lage um die Mitte)
    need_px = abs(LY(lb) - LY(la)) / math.tan(math.radians(CFG["sw_angle"])) + 2 * CFG["sw_radius"]
    lo_px, hi_px = Xm(g[0]["s0"]), Xm(g[-1]["s1"])
    c_px = (Xm(d0) + Xm(d1)) / 2
    q0p = min(max(c_px - need_px / 2, lo_px), max(hi_px - need_px, lo_px))
    if g[0].get("anchor") == "b": q0p = max(hi_px - need_px, lo_px)
    elif g[0].get("anchor") == "a": q0p = lo_px
    d0, d1 = Xm_inv(q0p), Xm_inv(min(q0p + need_px, hi_px))
    for x_ in g: x_["diag"] = (d0, d1)
    for sg in g[1:]:
        n = sg["nodes"][0]
        if la == lb: continue
        if n in cand:
            if any(k == 2 for k, _, _ in cand[n]): continue      # Kreuzung: Gleis läuft durch
            home[n] = min((l for _, _, l in cand[n]), key=lambda l: abs(l - home[n]))  # Abzweig
        home[n] = min(max(home[n], min(la, lb)), max(la, lb))   # Weiche liegt auf der Diagonale
        f = min(max((LY(home[n]) - LY(la)) / (LY(lb) - LY(la)), 0), 1)
        # Lage auf der gezeichneten Diagonale in px rechnen (Entzerrung ist nicht linear)
        q0p, q1p = Xm(d0), Xm(d1)
        runp = abs(LY(lb) - LY(la)) / math.tan(math.radians(CFG["sw_angle"]))
        xa_p = q0p + max(q1p - q0p - runp, 0) / 2; xb_p = xa_p + min(runp, q1p - q0p)
        if f <= 1e-6 or f >= 1 - 1e-6:
            # Weiche auf dem Start-/Zielgleis: vor bzw. hinter der Ausrundung, auf dem geraden Gleis
            xs_over[n] = Xm_inv(q0p - 1 if f <= 1e-6 else xb_p + CFG["sw_radius"] + 1)
            continue
        xs_over[n] = Xm_inv(xa_p + f * (xb_p - xa_p))
        e0, e1 = Xm_inv(xa_p), Xm_inv(xb_p)
        ddx = Xm(e1) - Xm(e0); ddy = LY(lb) - LY(la)
        L_ = math.hypot(ddx, ddy); diag_dir[n] = (ddx / L_, ddy / L_)

# ------------------------------------------------------ 5. Zeichnen
s_lo = min(c["s0"] for c in C); s_hi = max(c["s1"] for c in C)
maxlane = max(c["lane"] for c in C)
W = CFG["margin_x"] * 2 + Xm(s_hi) - Xm(s_lo)
build_ly()
H = CFG["margin_y"] + LY(min(c["lane"] for c in C)) + 105
X = lambda s: CFG["margin_x"] + Xm(s) - Xm(s_lo)
Y = lambda l: CFG["margin_y"] + LY(l)

def ypos(n): return Y(home[n])
def xpos(n, s_default): return X(xs_over.get(n, s_default))

def exit_ref(sg):
    # Override "abgang": {"<way>": {"ref": "...", "ort": "..."}} - eigene Linie am Planrand (Thun: Gürbetal); "~Text" ohne "Linie"
    if str(sg["way"]) in OVR.get("abgang", {}) and "ref" in OVR["abgang"][str(sg["way"])]: return OVR["abgang"][str(sg["way"])]["ref"]
    r = sg["tags"].get("ref")
    if r: return r
    for n in sg["nodes"]:
        for w in ways.values():
            if n in w["nodes"] and w["tags"].get("ref") and not w["tags"].get("service"): return w["tags"]["ref"]
    return None
def exit_town(sg, n_cut):
    """Richtung des Abgangs: Ort, der in Fortsetzung der Strecke liegt (Peilung)."""
    if str(sg["way"]) in OVR.get("abgang", {}) and "ort" in OVR["abgang"][str(sg["way"])]: return OVR["abgang"][str(sg["way"])]["ort"]
    w = ways[sg["way"]]; i = w["nodes"].index(n_cut)
    inner = [m for m in sg["nodes"] if m != n_cut]
    # Punkt weiter aussen auf demselben Way (oder Way-Ende)
    j_out = 0 if w["nodes"].index(inner[0]) > i else len(w["nodes"]) - 1
    p0, p1 = LL[n_cut], LL[w["nodes"][j_out]]
    if p0 == p1: p0 = LL[inner[0]]
    br = math.atan2((p1[0] - p0[0]), (p1[1] - p0[1]) * math.cos(math.radians(lat0)))
    bestt = None
    cands = CFG["towns"].items()
    lt = LINE_TOWNS.get(sg["tags"].get("ref") or exit_ref(sg) or "")
    if lt:     # Linientabelle: nur Zielorte dieser Linie, reine Peilung entscheidet
        sc_ = []
        for name in lt:
            la, lo = CFG["towns"][name]
            if math.hypot(la - lat0, (lo - lon0) * math.cos(math.radians(lat0))) < 0.004: continue
            bt = math.atan2(la - p0[0], (lo - p0[1]) * math.cos(math.radians(lat0)))
            _dd = math.hypot(la - lat0, (lo - lon0) * math.cos(math.radians(lat0)))
            sc_.append((abs((bt - br + math.pi) % (2 * math.pi) - math.pi) + CFG.get("lt_dist_w", 0) * _dd, name))   # cfg.lt_dist_w: näherer Zielort bevorzugt (Region Neuchâtel)
        if sc_: return min(sc_)[1]
    for name, (la, lo) in cands:
        dd = math.hypot(la - lat0, (lo - lon0) * math.cos(math.radians(lat0)))
        if dd < 0.004 or dd > 0.25: continue
        bt = math.atan2(la - p0[0], (lo - p0[1]) * math.cos(math.radians(lat0)))
        dang = abs((bt - br + math.pi) % (2 * math.pi) - math.pi)
        if dang < math.radians(70):
            sc = dang + dd * 8          # nächstgelegener Ort in Fahrtrichtung bevorzugt
            if bestt is None or sc < bestt[0]: bestt = (sc, name)
    return bestt[1] if bestt else None

def port_bearing(sg, n_cut):
    """Geografische Richtung, in die das Gleis den Ausschnitt verlässt (Grad, Osten = 0, Gegenuhrzeigersinn)."""
    w = ways[sg["way"]]; i = w["nodes"].index(n_cut)
    inner = sg["nodes"][1] if sg["nodes"][0] == n_cut else sg["nodes"][-2]
    j_in = w["nodes"].index(inner) if inner in w["nodes"] else i
    j_out = min(len(w["nodes"]) - 1, i + 6) if j_in < i else max(0, i - 6)
    p0, p1 = P[n_cut], P[w["nodes"][j_out]]
    if j_out == i: p0, p1 = P[inner], P[n_cut]
    return math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])) % 360

def scurve(x0, y0, x1, y1, xc=None):
    """Standard-Weichenverbindung zwischen zwei Gleispunkten.
    Gerade - Ausrundung r - Diagonale (sw_angle) - Ausrundung r - Gerade.
    Die Figur bleibt immer im Intervall [x0, x1]: reicht der Platz nicht,
    wird erst der Radius, dann der Winkel reduziert (nie über den Weichenpunkt hinaus)."""
    dy = y1 - y0; dx = x1 - x0
    if abs(dy) < 0.5 or dx <= 0.5: return f"M{x0:.1f},{y0:.1f}L{x1:.1f},{y1:.1f}"
    run = max(abs(dy) / math.tan(math.radians(CFG["sw_angle"])), CFG["sw_min_run"])
    r = CFG["sw_radius"]
    if run + 2 * r > dx:                      # zu eng: Radius verkleinern
        r = max(0.0, (dx - run) / 2)
    if run > dx:                              # immer noch zu eng: als S-Bogen
        if os.environ.get("CTRACE"): import traceback; print("CBOGEN", x0, y0, x1, y1); traceback.print_stack(limit=3)
        return f"M{x0:.1f},{y0:.1f}C{x0 + dx/2:.1f},{y0:.1f} {x1 - dx/2:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
    xa = x0 + (dx - run) / 2                  # Knickpunkte der Diagonale
    if xc is not None: xa = min(max(xc - run / 2, x0 + r), x1 - r - run)
    xb = xa + run
    L = math.hypot(run, dy); ux, uy = run / L, dy / L
    return (f"M{x0:.1f},{y0:.1f}H{xa - r:.1f}Q{xa:.1f},{y0:.1f} {xa + ux * r:.1f},{y0 + uy * r:.1f}"
            f"L{xb - ux * r:.1f},{y1 - uy * r:.1f}Q{xb:.1f},{y1:.1f} {xb + r:.1f},{y1:.1f}H{x1:.1f}")

def from_diag(xn, yn, u, xt, yt):
    """Abzweig aus einer Weiche, die auf einer Diagonale liegt.
    u = Richtung der Diagonale in Fahrtrichtung zum Ziel (xt, yt).
    Gerader Abzweig: Ausrundung von der Diagonale ins waagrechte Gleis.
    Schräger Abzweig: läuft in Diagonalrichtung weiter und rundet am Zielgleis aus."""
    ux, uy = u; sx = 1 if xt >= xn else -1
    if ux * sx < 0: ux, uy = -ux, -uy
    r = CFG["sw_radius"]
    if abs(yt - yn) < 0.5:          # waagrechter Abzweig
        return (f"M{xn - ux * r:.1f},{yn - uy * r:.1f}Q{xn:.1f},{yn:.1f} {xn + sx * r:.1f},{yn:.1f}H{xt:.1f}")
    if uy * (yt - yn) <= 0:          # Ziel auf der anderen Seite: Standardfigur direkt an der Weiche
        return scurve(min(xn, xt), yn if xn < xt else yt, max(xn, xt), yt if xn < xt else yn,
                      -1e9 if xn < xt else 1e9)
    t = (yt - yn) / uy; xr = xn + ux * t
    if (xr - xn) * sx + r <= (xt - xn) * sx:
        return (f"M{xn:.1f},{yn:.1f}L{xr - ux * r:.1f},{yt - uy * r:.1f}"
                f"Q{xr:.1f},{yt:.1f} {xr + sx * r:.1f},{yt:.1f}H{xt:.1f}")
    if RU.get("r49", False):       # zu eng: in Richtung der Schrägen weiter, auf dem Zielgleis ausrunden (kein Bogen, Neuchâtel 19.10.)
        xe_ = xr + sx * r
        return (f"M{xn:.1f},{yn:.1f}L{xr - ux * r:.1f},{yt - uy * r:.1f}"
                f"Q{xr:.1f},{yt:.1f} {xe_:.1f},{yt:.1f}H{(max if sx > 0 else min)(xt, xe_):.1f}")
    k = abs(xt - xn) / 2
    return (f"M{xn:.1f},{yn:.1f}C{xn + ux * k:.1f},{yn + uy * k:.1f} {xt - sx * k:.1f},{yt:.1f} {xt:.1f},{yt:.1f}")

MS_BRAUN = "#9a5b1e"
SCHMAL_ALLE = bool(segs) and all(x.get("schmal") for x in segs)
SCHMAL_GEMISCHT = any(x.get("schmal") for x in segs) and not SCHMAL_ALLE
if SCHMAL_ALLE: CFG["green"] = CFG["black"] = MS_BRAUN        # reiner Schmalspurbahnhof: alles braun (dick = Hauptgleis, dünn = Nebengleis)
green, black = CFG["green"], CFG["black"]
# Regel 29: zweigen zwei Gleise derselben Richtung seitlich ab (Doppelspur, z. B. 451 in Aarburg), dürfen die
# Abgänge nicht auf einer Linie liegen: der äussere Abgang wird stromaufwärts gelegt, so dass der innere
# parallel daneben (stromabwärts) abzweigt und dazwischenliegende Kleinanlagen auf der richtigen Seite bleiben
def _xinv(x_):
    lo_, hi_ = CFG["s_min"] - 500, CFG["s_max"] + 500
    for _ in range(60):
        m_ = (lo_ + hi_) / 2
        if X(m_) < x_: lo_ = m_
        else: hi_ = m_
    return (lo_ + hi_) / 2
_sd29 = []
for sg in segs:
    if not sg["pax"] or sg["flat"]: continue
    for end in (0, 1):
        if not sg.get("cut%d" % end): continue
        n = sg["nodes"][-1 if end else 0]; s_, d_ = SD[n]
        if abs(d_) > d_lim_at(s_) - 25:
            _sd29.append([xpos(n, sg["s1"] if end else sg["s0"]), ypos(n), end, -1 if d_ > 0 else 1, n])
for A_ in _sd29:
    for B_ in _sd29:
        if A_ is B_ or A_[2] != B_[2] or A_[3] != B_[3] or (B_[1] - A_[1]) * A_[3] <= 0: continue
        dxv = -(1 - 2 * A_[2])
        x_at = A_[0] + dxv * abs(B_[1] - A_[1]) * 0.5 / 0.866
        need = x_at - dxv * CFG["lane_px"] / 0.866
        if (B_[0] - need) * dxv > 0:
            s_new = _xinv(need); n_ = B_[4]
            # nicht hinter den vorherigen Knoten des Stammgleises zurück (sonst bleibt ein rückläufiger Stummel, Aarburg Gl. 1)
            _cur = LAT_CUR.get(n_)
            if _cur is not None:
                _prev = [SD[x["nodes"][0 if x["nodes"][-1] == _cur else -1]][0] for x in segs if x["flat"] and _cur in (x["nodes"][0], x["nodes"][-1])]
                if _prev:
                    _pp_ = [p_ for p_ in _prev if (p_ - SD[_cur][0]) * dxv < 0]
                    if _pp_:
                        _bound = (max if dxv > 0 else min)(_pp_) + dxv * 3
                        if (s_new - _bound) * dxv < 0:
                            _def = (X(_bound) - need) * dxv      # fehlender Abstand: den anderen Abgang stromabwärts legen
                            s_new = _bound; need = X(s_new)
                            sA_ = _xinv(A_[0] + dxv * _def); nA_ = A_[4]
                            xs_over[nA_] = sA_
                            if nA_ in LAT_CUR:
                                for m_, c_ in LAT_CUR.items():
                                    if c_ == LAT_CUR[nA_]: xs_over[m_] = sA_
                                xs_over[LAT_CUR[nA_]] = sA_
                            A_[0] = A_[0] + dxv * _def
            xs_over[n_] = s_new
            if n_ in LAT_CUR: xs_over[LAT_CUR[n_]] = s_new
            for m_, c_ in LAT_CUR.items():
                if c_ == LAT_CUR.get(n_): xs_over[m_] = s_new
            B_[0] = need

_nbr0 = collections.defaultdict(set)
for _w in ways.values():
    for _a, _b in zip(_w["nodes"], _w["nodes"][1:]): _nbr0[_a].add(_b); _nbr0[_b].add(_a)
_pax_set = {n for w in ways.values() if passenger(w["tags"]) for n in w["nodes"] if n in P}
_pax_nodes = list(_pax_set)
# Konvention prüfen: Kreuzprodukt (Achsrichtung x Punkt) > 0 entspricht d > 0 ?
_votes = []
for _m in [n for n in SD if n in P and n not in _pax_set and inside(n)][:300]:
    _q = min(_pax_nodes, key=lambda q: (P[q][0] - P[_m][0]) ** 2 + (P[q][1] - P[_m][1]) ** 2, default=None)
    if _q is None or abs(SD[_m][1] - SD[_q][1]) < 3: continue
    _nq = [r for r in _nbr0.get(_q, ()) if r in _pax_set and r in SD]
    if not _nq: continue
    _r = max(_nq, key=lambda r: SD[r][0]); _t = np.subtract(P[_r], P[_q]); _v = np.subtract(P[_m], P[_q])
    if SD[_r][0] < SD[_q][0]: _t = -_t
    _votes.append(np.sign(_t[0] * _v[1] - _t[1] * _v[0]) * np.sign(SD[_m][1] - SD[_q][1]))
_d_sign_check = 1.0 if sum(_votes) >= 0 else -1.0
_nbr = collections.defaultdict(set)
for _w in ways.values():
    for _a, _b in zip(_w["nodes"], _w["nodes"][1:]): _nbr[_a].add(_b); _nbr[_b].add(_a)
# Override "knoten_x": {knoten: x_px} - Knoten (z. B. Prellbock) auf eine feste x-Position legen (Thun Ost: Gleisende
# lag genau unter einer Schrägen)
for _n, _xp in OVR.get("knoten_x", {}).items():
    if int(_n) in SD: xs_over[int(_n)] = Xm_inv(_xp - CFG["margin_x"] + Xm(s_lo))
# Regel 44, Vorlauf: die Weichen am Fuss einer DKW-Schrägen so legen, dass die Schräge gerade (60°) durch den DKW-Knoten läuft
if RU.get("r44", False) and RU.get("r44v", True):
    _t60_ = math.tan(math.radians(60))
    _Xinv = lambda x_: Xm_inv(x_ - CFG["margin_x"] + Xm(s_lo))
    for n, t in ntag.items():
        if t.get("railway:switch") != "double_slip" or n not in home or n not in SD: continue
        _dg = [x for x in segs if not x["flat"] and n in (x["nodes"][0], x["nodes"][-1])]
        if len(_dg) != 2: continue
        xn, yn = xpos(n, SD[n][0]), ypos(n)
        for x in _dg:
            o = x["nodes"][-1] if x["nodes"][0] == n else x["nodes"][0]
            if o not in SD: continue
            xo, yo = xpos(o, SD[o][0]), ypos(o)
            if abs(yo - yn) < 3: continue
            xt = xn + (1 if xo > xn else -1) * abs(yo - yn) / _t60_
            if 0 < abs(xt - xo) < 25 and not (o in EDGE_NODES if "EDGE_NODES" in globals() else False):
                xs_over[o] = _Xinv(xt)
svg_paths = {True: [], False: []}
STUB_SRC = []
DBG = []
STUBS = []
arrows = []
def _xpos_sg(n, s_def, sg):
    if n in LAT_OWN and LAT_OWN[n] != sg["id"] and xs_over.get(n) == LAT_CUT.get(n): return X(SD[n][0])
    return xpos(n, s_def)
for sg in segs:
    n0, n1 = sg["nodes"][0], sg["nodes"][-1]
    x0, x1 = _xpos_sg(n0, sg["s0"], sg), _xpos_sg(n1, sg["s1"], sg)
    y0, y1 = ypos(n0), ypos(n1)
    on0 = n0 in diag_dir and sg not in sg.get("group", [])
    on1 = n1 in diag_dir and sg not in sg.get("group", [])
    if (on0 or on1) and not (on0 and on1):
        n, other = (n0, n1) if on0 else (n1, n0)
        xn, yn = (x0, y0) if on0 else (x1, y1)
        xt, yt = (x1, y1) if on0 else (x0, y0)
        if sg["flat"]: yt = Y(seglane[sg["id"]])
        d = from_diag(xn, yn, diag_dir[n], xt, yt)
        if sg["flat"] and abs(yt - (y1 if on0 else y0)) > 0.5:
            d += scurve(*( (xt - 1, yt, xt, y1) if on0 else (x0, y0, x0 + 1, yt)))
    elif sg["flat"] and RU.get("r49", False) and min(y0, y1) + 0.5 < Y(seglane[sg["id"]]) < max(y0, y1) - 0.5 \
            and sum(len(c_["segs"]) for c_ in C if any(x_ is sg for x_ in c_["segs"])) == 1:
        # Regel 49 (Neuchâtel 19.10., "Zwischengerade"): ein einzelnes flaches Stück, dessen Ebene zwischen seinen beiden
        # Endknoten liegt, ist eine Verbindung - eine Schräge statt Schräge-Gerade-Schräge
        p = sg["p"]; dm = (p[0, 1] + p[-1, 1]) / 2; sm = p[np.argmin(np.abs(p[:, 1] - dm)), 0]
        _need = abs(y1 - y0) / math.tan(math.radians(CFG["sw_angle"])) + 2 * CFG["sw_radius"] + 2
        if abs(x1 - x0) < _need:      # zu eng: Schräge mit voller Länge, das Ende läuft auf dem Zielgleis aus
            d = scurve(x0, y0, x0 + _need, y1) if x1 >= x0 else scurve(x1 - _need, y1, x1, y0)
        else:
            d = scurve(x0, y0, x1, y1, X(sm)) if x1 >= x0 else scurve(x1, y1, x0, y0, X(sm))
    elif sg["flat"]:
        y = Y(seglane[sg["id"]])
        d = ""
        xa, xb = x0, x1
        if abs(y0 - y) > 0.5:
            _cap = (x1 - x0) / 2 if not (RU.get("r49", False) and abs(y1 - y) <= 0.5) else (x1 - x0) - 2   # r49: ganze Länge nutzen, wenn das andere Ende gerade ist
            run = min(max(abs(y0 - y) / math.tan(math.radians(CFG['sw_angle'])), 14) + 6, _cap)
            d += scurve(x0, y0, x0 + run, y); xa = x0 + run
        if abs(y1 - y) > 0.5:
            _cap = (x1 - x0) / 2 if not (RU.get("r49", False) and abs(y0 - y) <= 0.5) else (x1 - x0) - 2
            run = min(max(abs(y1 - y) / math.tan(math.radians(CFG['sw_angle'])), 14) + 6, _cap)
            xb = x1 - run
        d += f"M{xa:.1f},{y:.1f}H{xb:.1f}"
        if xb < x1: d += scurve(xb, y, x1, y1)
    else:
        g = sg["group"]
        if len(g) == 1:
            p = sg["p"]; dm = (p[0, 1] + p[-1, 1]) / 2
            sm = p[np.argmin(np.abs(p[:, 1] - dm)), 0]   # dort wechselt das echte Gleis die Seite
            _need = abs(y1 - y0) / math.tan(math.radians(CFG["sw_angle"])) + 2 * CFG["sw_radius"] + 2
            if RU.get("r49", False) and abs(y1 - y0) > 0.5 and x1 - x0 < _need:
                # zu eng für 60° (sonst Bogen/90°, Neuchâtel 19.10.): Schräge in voller Länge, läuft auf dem anschliessenden Gleis aus
                if any(o["flat"] and o["nodes"][0] == n1 for o in segs): d = scurve(x0, y0, x0 + _need, y1)
                elif any(o["flat"] and o["nodes"][-1] == n0 for o in segs): d = scurve(x1 - _need, y0, x1, y1)
                else: d = scurve(x0, y0, x1, y1, X(sm))
            else: d = scurve(x0, y0, x1, y1, X(sm))
        elif sg is g[0]:
            ga, gb = g[0]["nodes"][0], g[-1]["nodes"][-1]
            xa, xb, ya, yb = X(g[0]["s0"]), X(g[-1]["s1"]), ypos(ga), ypos(gb)
            # Override knoten_x gilt auch für Enden einer Weichenstrasse (Olten Ostknoten 14.10.)
            if str(ga) in OVR.get("knoten_x", {}): xa = xpos(ga, g[0]["s0"])
            if str(gb) in OVR.get("knoten_x", {}): xb = xpos(gb, g[-1]["s1"])
            if "anchors" in sg:
                P_ = [(X(s_), Y(l_)) for s_, l_ in sg["anchors"]]
                r = CFG["sw_radius"]
                (ax, ay), (bx, by) = P_[0], P_[1]
                L1 = math.hypot(bx - ax, by - ay); u1 = ((bx - ax) / L1, (by - ay) / L1)
                (cx, cy), (ex, ey) = P_[-2], P_[-1]
                L2 = math.hypot(ex - cx, ey - cy); u2 = ((ex - cx) / L2, (ey - cy) / L2)
                # alle Knicke der Weichenstrasse ausrunden (Hinweis Thun 14.10.: "runder")
                _pp_ = [(ax - r, ay)] + P_ + [(ex + r, ey)]
                d = f"M{_pp_[0][0]:.1f},{_pp_[0][1]:.1f}"
                for i_ in range(1, len(_pp_) - 1):
                    (qa, qb), (qx, qy), (qc, qd) = _pp_[i_ - 1], _pp_[i_], _pp_[i_ + 1]
                    l1_, l2_ = math.hypot(qx - qa, qy - qb), math.hypot(qc - qx, qd - qy)
                    if l1_ < 1e-6 or l2_ < 1e-6: continue
                    rr_ = min(r, l1_ / 2, l2_ / 2)
                    d += (f"L{qx + (qa - qx) * rr_ / l1_:.1f},{qy + (qb - qy) * rr_ / l1_:.1f}"
                          f"Q{qx:.1f},{qy:.1f} {qx + (qc - qx) * rr_ / l2_:.1f},{qy + (qd - qy) * rr_ / l2_:.1f}")
                d += f"L{_pp_[-1][0]:.1f},{_pp_[-1][1]:.1f}"
            else:
                q0, q1 = X(sg["diag"][0]), X(sg["diag"][1])
                _need = abs(yb - ya) / math.tan(math.radians(CFG["sw_angle"])) + 2 * CFG["sw_radius"] + 2
                if RU.get("r49", False) and q1 - q0 < _need and abs(yb - ya) > 0.5:     # zu eng: volle 60°-Schräge statt Bogen
                    if xb - q0 >= _need: q1 = q0 + _need
                    elif q1 - xa >= _need: q0 = q1 - _need
                d = f"M{xa:.1f},{ya:.1f}H{q0:.1f}" + scurve(q0, ya, q1, yb) + f"M{q1:.1f},{yb:.1f}H{max(xb, q1):.1f}"
        else:
            d = ""
    if d: svg_paths[sg["pax"]].append(d); DBG.append((sg["id"], d))
    if ARGS.dbg and d and "200.2" in d: print("DRAW", sg["way"], sg["tags"].get("service"), sg["flat"], d[:120])
    edge0 = SD[sg["nodes"][0]][0] <= CFG["s_min"] + 15
    edge1 = SD[sg["nodes"][-1]][0] >= CFG["s_max"] - 15
    for end, (xe, ye, dr) in ((0, (x0, y0, -1)), (1, (x1, y1, 1))):
        if not sg.get("cut%d" % end): continue
        n_out = sg["nodes"][-1 if end else 0]
        if sg["pax"] and n_out not in PAX_SIDE: continue
        if (SD[n_out][0] <= CFG["s_min"] + 15 and not end) or (SD[n_out][0] >= CFG["s_max"] - 15 and end) or n_out in EDGE_LONG:
            arrows.append((xe, ye, dr))                       # läuft am Planrand weiter
        else:                                                 # läuft seitlich aus dem Plan
            # Richtung des Abgangs aus der echten Lage des ersten Punkts ausserhalb
            w = ways[sg["way"]]; i = w["nodes"].index(n_out)
            nb = [w["nodes"][j] for j in (i - 1, i + 1) if 0 <= j < len(w["nodes"]) and w["nodes"][j] not in sg["nodes"]]
            out_d = SD[nb[0]][1] if nb else SD[n_out][1]
            # Regel 37: Richtung nach dem weiteren Verlauf (alle Gleise ausserhalb bis 400 m), nicht nach dem ersten Punkt -
            # sonst zeigen Zufahrten zur selben Anlage in verschiedene Richtungen (Rothrist West)
            _nb37 = nb or [q for q in _nbr.get(n_out, ()) if q not in sg["nodes"]]
            if RU.get("r37", True) and _nb37:
                seen, todo, far = {n_out}, [(q, 0.0, n_out) for q in _nb37], []
                while todo:
                    m_, dist_, prev_ = todo.pop()
                    if m_ in seen or m_ not in SD: continue
                    seen.add(m_); dist_ += math.dist(P[m_], P[prev_]) if m_ in P and prev_ in P else 0
                    if dist_ > 400: continue
                    if not inside(m_): far.append(m_)
                    for q_ in _nbr.get(m_, ()):
                        if q_ not in seen: todo.append((q_, dist_, m_))
                if far:
                    # Seite relativ zum nächsten Streckengleis an derselben Stelle (Strecke im Bogen)
                    sides = []
                    for m_ in far[:40]:
                        if m_ not in P: continue
                        q_ = min(_pax_nodes, key=lambda q: (P[q][0] - P[m_][0]) ** 2 + (P[q][1] - P[m_][1]) ** 2, default=None)
                        if q_ is None: continue
                        nq = [r for r in _nbr.get(q_, ()) if r in _pax_set and r in SD]
                        if not nq: continue
                        r_ = max(nq, key=lambda r: SD[r][0])            # Nachbar in Richtung wachsender s
                        t_ = np.subtract(P[r_], P[q_]); v_ = np.subtract(P[m_], P[q_])
                        if SD[r_][0] < SD[q_][0]: t_ = -t_
                        sides.append(np.sign(t_[0] * v_[1] - t_[1] * v_[0]))
                    if sides and abs(sum(sides)) > 0:
                        # Vorzeichen so, dass es zur d-Konvention passt: links der Achsrichtung = d positiv
                        _ref = np.sign(_d_sign_check)
                        out_d = SD[n_out][1] + (1 if np.sign(sum(sides)) == _ref else -1)
                    else:
                        out_d = float(np.mean([SD[m_][1] for m_ in far]))
            up = -1 if out_d > SD[n_out][1] else 1
            if ARGS.dbg: print("R37", sg["way"], len(far) if RU.get("r37", True) and _nb37 else None, _d_sign_check, round(out_d - SD[n_out][1], 2))
            L = 26; ex, ey = xe + dr * L * 0.5, ye + up * L * 0.866
            svg_paths[False].append(f"M{xe:.1f},{ye:.1f}L{ex:.1f},{ey:.1f}")
            ang = math.atan2(ey - ye, ex - xe)
            STUBS.append((ex, ey, ang)); STUB_SRC.append((sg["way"], f"M{xe:.1f},{ye:.1f}L{ex:.1f},{ey:.1f}", (ex, ey, ang)))
            if ARGS.dbg: print("STUB", sg["way"], sg["tags"].get("service"), sg["tags"].get("usage"), sg["tags"].get("name"), round(xe), round(ye), up)

# Regel 38 (nur --hauptgleise): Weichen in weggelassene Anlagen (Rangier-/Güter-/Anschlussgleise) als Abgang andeuten -
# "eine Weiche ab Hauptgleis muss mindestens angedeutet werden"
CONT38 = {}
R38_ST = {}
R47_P = []
_done38 = set()
if ARGS.hauptgleise and RU.get("r38", True):
    _kept_end = {}
    for sg in segs:
        for e_, n_ in ((0, sg["nodes"][0]), (1, sg["nodes"][-1])): _kept_end.setdefault(n_, sg)
        if RU.get("r38m", False):          # auch Weichen mitten im gezeichneten Stück (Neuchâtel 19.10.: Grundsatz 3 nach drop_service)
            for n_ in sg["nodes"][1:-1]: _kept_end.setdefault(n_, sg)
    for e in D:
        if e["type"] != "way" or e["tags"].get("railway") != "rail" or e["id"] in ways: continue
        if e["tags"].get("gauge", "1435") != "1435": continue
        nn_ = e["nodes"]
        for k_, n_ in enumerate(nn_):
            if n_ not in _kept_end or n_ in _done38 or not inside(n_): continue
            # Richtung: Mittel der Anlagenpunkte bis 300 m entlang des weggelassenen Ways
            pts_ = [xy(g) for g in e["geometry"]]
            here_ = np.array(P[n_]); acc_ = []
            for j_ in (range(k_ + 1, len(nn_)) if k_ < len(nn_) - 1 else range(k_ - 1, -1, -1)):
                if np.hypot(*(np.array(pts_[j_]) - here_)) > 300: break
                acc_.append(project(pts_[j_]))
            if RU.get("r38m", False):
                # kurzer Weichen-Way: über weggelassene Folge-Ways weiter bis 300 m (Neuchâtel 19.10.)
                _nb = {}
                for e2 in D:
                    if e2["type"] == "way" and e2["tags"].get("railway") == "rail" and e2["id"] not in ways and "geometry" in e2:
                        for k2, n2 in enumerate(e2["nodes"]): _nb.setdefault(n2, []).append((e2, k2))
                cur_, ci_ = e, k_; seen_ = {e["id"]}; last_ = here_
                while True:
                    end_ = cur_["nodes"][-1] if ci_ < len(cur_["nodes"]) - 1 else cur_["nodes"][0]
                    if np.hypot(*(np.array(xy(cur_["geometry"][-1 if end_ == cur_["nodes"][-1] else 0])) - here_)) > 300: break
                    nxt_ = [(e2, k2) for e2, k2 in _nb.get(end_, []) if e2["id"] not in seen_]
                    if not nxt_: break
                    cur_, ci_ = nxt_[0]; seen_.add(cur_["id"])
                    rng_ = range(ci_ + 1, len(cur_["nodes"])) if ci_ < len(cur_["nodes"]) - 1 else range(ci_ - 1, -1, -1)
                    for j_ in rng_:
                        p_ = xy(cur_["geometry"][j_])
                        if np.hypot(*(np.array(p_) - here_)) > 300: break
                        acc_.append(project(p_))
            if not acc_: continue
            s_m, d_m = np.mean([a_[0] for a_ in acc_]), np.mean([a_[1] for a_ in acc_])
            if RU.get("r38m", False) and abs(d_m - SD[n_][1]) < 1.0 and abs(acc_[-1][1] - SD[n_][1]) >= 2.5:
                d_m = acc_[-1][1]               # parallel abgehendes Nebengleis: Seite aus dem fernsten Punkt (Neuchâtel 19.10.)
            if abs(d_m - SD[n_][1]) < 1.0:
                # Anlage läuft geradeaus weiter: kein Prellbock, sondern Pfeil "läuft weiter" (Olten Hammer Gl. 4)
                if sum(1 for sg in segs if n_ in (sg["nodes"][0], sg["nodes"][-1])) == 1:
                    _done38.add(n_); CONT38[n_] = 1 if s_m >= SD[n_][0] else -1
                continue
            _done38.add(n_)
            dr_ = 1 if s_m >= SD[n_][0] else -1
            up_ = -1 if d_m > SD[n_][1] else 1
            # Override "r38_seite" {way: "oben"|"unten"}: Seite des Pfeils von Hand (Neuchâtel 20.10.: Pfeile zeigten aufs Nachbargleis)
            # "gerade": die Anlage ist der gerade Strang der Weiche -> Pfeil "läuft weiter" am Gleisende (nur wo das topologisch stimmt,
            # Regel D. Eckenstein 20.10. abends: Pfeil nur drehen, wenn die Verzweigung so liegt)
            if OVR.get("r38_seite", {}).get(str(e["id"])) == "gerade": CONT38[n_] = dr_; continue
            if str(e["id"]) in OVR.get("r38_seite", {}): up_ = -1 if OVR["r38_seite"][str(e["id"])] == "oben" else 1
            if n_ in home: xe_, ye_ = xpos(n_, SD[n_][0]), ypos(n_)
            else:                              # r38m: Weiche mitten im Stück, nur auf geraden Gleisen
                sg_ = _kept_end[n_]; ha_, hb_ = home.get(sg_["nodes"][0]), home.get(sg_["nodes"][-1])
                if ha_ is None or ha_ != hb_: continue
                xe_, ye_ = X(SD[n_][0]), Y(ha_)
            L_ = 22; ex_, ey_ = xe_ + dr_ * L_ * 0.5, ye_ + up_ * L_ * 0.866
            svg_paths[False].append(f"M{xe_:.1f},{ye_:.1f}L{ex_:.1f},{ey_:.1f}")
            STUBS.append((ex_, ey_, math.atan2(ey_ - ye_, ex_ - xe_)))
            R38_ST.setdefault(e["id"], []).append((n_, f"M{xe_:.1f},{ye_:.1f}L{ex_:.1f},{ey_:.1f}", STUBS[-1]))
# Override "zusatz_spurwechsel": Spurwechsel nach Ortskenntnis, der in den OSM-Daten fehlt (liegt z. B. ausserhalb
# des Datenausschnitts): [{"von": "1", "nach": "2", "s": 5440}] -> 60°-Schräge ab s auf Gleis "von" nach Gleis "nach"
for _zs in OVR.get("zusatz_spurwechsel", []):
    _la = [seglane[x["id"]] for x in segs if x["ref"] == _zs["von"] and x["id"] in seglane]
    _lb = [seglane[x["id"]] for x in segs if x["ref"] == _zs["nach"] and x["id"] in seglane]
    if not _la or not _lb: continue
    _ya, _yb = Y(max(set(_la), key=_la.count)), Y(max(set(_lb), key=_lb.count))
    _x0 = X(_zs["s"]); _x1 = _x0 + abs(_yb - _ya) / math.tan(math.radians(60))
    svg_paths[bool(_zs.get("pax"))].append(scurve(_x0 - 8, _ya, _x1 + 8, _yb) if RU.get("r48", False) else f"M{_x0:.1f},{_ya:.1f}L{_x1:.1f},{_yb:.1f}")
PFEIL_N = set()
# Override "pfeile": Gleis läuft über das gezeichnete Ende hinaus weiter (z. B. Anschlussgleis, in OSM nicht erfasst)
for _pf in OVR.get("pfeile", []):
    _ss = [sg for sg in segs if sg["way"] == _pf["way"] and sg["flat"] and sg["id"] in seglane]
    if not _ss: continue
    _lk = _pf.get("seite", "links") == "links"
    _sg = min(_ss, key=lambda x: x["s0"]) if _lk else max(_ss, key=lambda x: x["s1"])
    _y = Y(seglane[_sg["id"]]); _L = _pf.get("laenge", 50)
    _x0 = _xpos_sg(_sg["nodes"][0], _sg["s0"], _sg) if _lk else _xpos_sg(_sg["nodes"][-1], _sg["s1"], _sg)
    # Anfang des geraden Teils auf der Ebene (nach der S-Kurve vom Abzweig), aus der gezeichneten Linie
    _xs = [float(a) for d_ in (d for i_, d in DBG if i_ == _sg["id"]) for a, b in re.findall(r"(-?[\d.]+),(-?[\d.]+)", d_) if abs(float(b) - _y) < 0.6]
    if _xs: _x0 = min(_xs) if _lk else max(_xs)
    _x1 = _x0 - _L if _lk else _x0 + _L
    svg_paths[_sg["pax"]].append(f"M{_x0:.1f},{_y:.1f}H{_x1:.1f}")
    arrows.append((_x1, _y, -1 if _lk else 1)); PFEIL_N.add(_sg["nodes"][0] if _lk else _sg["nodes"][-1])

# Prellböcke
deg = collections.Counter()
for sg in segs: deg[sg["nodes"][0]] += 1; deg[sg["nodes"][-1]] += 1
cutn = {sg["nodes"][0] for sg in segs if sg["cut0"]} | {sg["nodes"][-1] for sg in segs if sg["cut1"]}
stops = [n for n, k in deg.items() if k == 1 and n not in cutn and use[n] == 1 and n not in CONT38 and n not in _done38 and n not in PFEIL_N]   # Gleisende mit Abgang in weggelassene Anlage: kein Prellbock
# Pfeil «läuft weiter» (E2) nicht direkt auf die Weiche setzen, wo der gezeichnete Ast abbiegt (Neuchâtel 25.10.:
# «Pfeil auf Gleis drauf»): kurzer gerader Stummel über die Weiche hinaus, Pfeil an dessen Ende
_PST = CFG.get("pfeil_stummel_px", 14)
for n_, dr_ in CONT38.items():
    _xa, _ya = xpos(n_, SD[n_][0]), ypos(n_)
    if _PST: svg_paths[False].append(f"M{_xa:.1f},{_ya:.1f}L{_xa + dr_ * _PST:.1f},{_ya:.1f}")
    arrows.append((_xa + dr_ * _PST, _ya, dr_))
dots = [(xpos(n, SD[n][0]), ypos(n), any(sg["pax"] for sg in segs if n in sg["nodes"])) for n in stops]

_pl_s = [x for pl in OVR.get("platforms", []) if "s" in pl for x in pl["s"]] or \
        [project(xy(g))[0] for e in PLAT for g in e["geometry"]]
S_PERRON = float(np.mean(_pl_s)) if _pl_s else (CFG["s_min"] + CFG["s_max"]) / 2
# Gleisnummern (Personenverkehr: kleine Nummern)
labels = {}
for c in C:
    refs = [sg["ref"] for sg in c["segs"] if sg["ref"] and sg["ref"].isdigit() and int(sg["ref"]) < 30
            and (sg["pax"] or sg["ref"] in OVR.get("nummern", [])) and sg["ref"] not in OVR.get("nummern_weg", [])]      # "nummern": auch Nebengleise beschriften; "nummern_weg": Nummer weglassen (Kerzers 16, 15.10.)
    if not refs: continue
    r = collections.Counter(refs).most_common(1)[0][0]
    # Nummer, die im Perronbereich gilt, hat Vorrang (Dulliken: 2/3 statt 12/13 der Streckengleise)
    _at = [sg["ref"] for sg in c["segs"] if sg["ref"] in refs and sg["s0"] <= S_PERRON <= sg["s1"]]
    if _at: r = _at[0]
    segs_r = [sg for sg in c["segs"] if sg["ref"] == r]
    a = min(x["s0"] for x in segs_r); b = max(x["s1"] for x in segs_r)
    if r not in labels or (b - a) > labels[r][3]:
        labels[r] = (c["lane"], a, b, b - a)
# gemeinsame x-Position im Perronbereich
pax_mid = np.median([(v[1] + v[2]) / 2 for v in labels.values()]) if labels else S_PERRON   # Halte ohne Gleisnummern: Titel unter den Perrons


def _rund(pts, r=7.0):
    """Polylinie mit gerundeten Ecken (quadratische Bézier), wie die übrigen Weichenübergänge"""
    pts = [p for i, p in enumerate(pts) if i == 0 or math.dist(p, pts[i - 1]) > 0.1]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1):
        (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[i + 1]
        l1, l2 = math.dist(pts[i - 1], pts[i]), math.dist(pts[i], pts[i + 1])
        rr = min(r, l1 / 2, l2 / 2)
        p_ = (bx + (ax - bx) * rr / l1, by + (ay - by) * rr / l1); q_ = (bx + (cx - bx) * rr / l2, by + (cy - by) * rr / l2)
        d += f"L{p_[0]:.1f},{p_[1]:.1f}Q{bx:.1f},{by:.1f} {q_[0]:.1f},{q_[1]:.1f}"
    return d + f"L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
# Regel 47 (Olten 14.10.: "Pfeile sind doch ein Spurwechsel 11 12"): verbindet ein weggelassener Way zwei gezeichnete Gleise,
# wird er als Spurwechsel gezeichnet statt als zwei Pfeile
if RU.get("r47", True):
    for _eid, _l in R38_ST.items():
        if len(_l) != 2: continue
        (na_, da_, sa_), (nb_, db_, sb_) = _l
        xa_, ya_, xb_, yb_ = xpos(na_, SD[na_][0]), ypos(na_), xpos(nb_, SD[nb_][0]), ypos(nb_)
        if abs(ya_ - yb_) < 3 or abs(ya_ - yb_) > 2.5 * CFG["lane_px"] or abs(xa_ - xb_) > 200: continue
        if xa_ > xb_: xa_, ya_, xb_, yb_ = xb_, yb_, xa_, ya_
        dx_ = abs(yb_ - ya_) / math.tan(math.radians(60)); xm_ = (xa_ + xb_) / 2
        if xb_ - xa_ < dx_ + 8: continue
        for d_ in (da_, db_):
            if d_ in svg_paths[False]: svg_paths[False].remove(d_)
        STUBS = [t_ for t_ in STUBS if t_ not in (sa_, sb_)]
        _d47 = _rund([(xa_, ya_), (xm_ - dx_ / 2, ya_), (xm_ + dx_ / 2, yb_), (xb_, yb_)])
        if _eid in OVR.get("r47_pax", []): svg_paths[True].append(_d47)      # Spurwechsel zwischen Hauptgleisen, in OSM siding (Neuchâtel 19.10.)
        else: svg_paths[False].append(_d47)
        R47_P.append((_d47, na_, nb_, _eid))

# Override "kreuzung" (Keilbahnhof mit Kreuzung, Kerzers): zwei Strecken kreuzen ausserhalb der Perrongruppen.
# a: Way, der links an ein Gleis anschliesst und nach der Kreuzung unten rechts weiterläuft (z. B. 220 nach Bern)
# b: Way, der von unten links kommt und nach der Kreuzung rechts an ein Gleis anschliesst (z. B. 251 von Murten)
# DKW-Zeichengrösse (Standard, 14.10.): Die Bogenfahrwege einer Doppelkreuzungsweiche als zwei Klammern in den stumpfen
# Winkeln, parallel im Abstand OFF neben den Gleisen und tangential ausgerundet (Kontrollpunkt im Schnitt der Parallelen).
# Hauptgleis: Armlänge 12 px, Abstand 3 px, Strich 2.2, hellgrün. Nebengleis: 9 px, 2.2 px, Strich 1.4, grau.
DKW_STD = {True: dict(L=12.0, OFF=3.0, W=2.2), False: dict(L=9.0, OFF=2.2, W=1.4)}
DKW_FILLET = []          # Ausrundungen der DKW: unter den grünen Gleisen einfügen (schwarz hinter grün)
def _alle_pax(n):
    """Ausrundung einer DKW grün nur, wenn alle Gleise am Knoten Personengleise sind (sonst Nebengleis-Fahrweg, schwarz)"""
    xs_ = [x for x in segs if n in (x["nodes"][0], x["nodes"][-1])]
    return bool(xs_) and all(x["pax"] for x in xs_)
def _dkw_klammer(c0, a_, b_, hp, rp=None):
    a_, b_ = np.array(a_, float), np.array(b_, float)
    a_ = a_ / np.linalg.norm(a_); b_ = b_ / np.linalg.norm(b_)
    bis = a_ + b_; bis = bis / (np.linalg.norm(bis) or 1)
    st = DKW_STD[bool(hp)]; _c = green if hp else black
    half = math.acos(max(-1.0, min(1.0, float(a_ @ b_)))) / 2
    p0 = c0 + a_ * st["L"] + _perp(a_, bis) * st["OFF"]
    p1 = c0 + b_ * st["L"] + _perp(b_, bis) * st["OFF"]
    cq = c0 + bis * st["OFF"] / max(math.sin(half), 0.2)
    # Standard 14.10. (Blaupause E9): dazu eine kleine Ausrundung direkt auf den Gleisen, 10 % der Schrägen einer Weiche
    t_ = 0.10 * CFG["lane_px"] / math.sin(math.radians(60))
    f0 = c0 + a_ * t_; f1 = c0 + b_ * t_
    DKW_FILLET.append(f'<path d="M{f0[0]:.1f},{f0[1]:.1f}Q{c0[0]:.1f},{c0[1]:.1f} {f1[0]:.1f},{f1[1]:.1f}" fill="none" '
            f'stroke="{green if (hp if rp is None else rp) else black}" stroke-width="{3.6 if (hp if rp is None else rp) else 1.6}" stroke-linecap="round"/>')
    return (f'<path d="M{p0[0]:.1f},{p0[1]:.1f}Q{cq[0]:.1f},{cq[1]:.1f} {p1[0]:.1f},{p1[1]:.1f}" fill="none" '
            f'stroke="{_c}" stroke-opacity="0.55" stroke-width="{st["W"]}" stroke-linecap="round"/>')
def _perp(u, toward):
    """Normale zu u, auf die Seite von 'toward'"""
    n_ = np.array([-u[1], u[0]])
    return n_ if n_ @ toward > 0 else -n_
KX_EXITS = []
KX_WAYS = set()
_kx = OVR.get("kreuzung")
if _kx and not ARGS.bare:
    _A = [sg for sg in segs if sg["way"] == _kx["a"]["way"]]; _B = [sg for sg in segs if sg["way"] == _kx["b"]["way"]]
    if _A and _B:
        _ids = {sg["id"] for sg in _A + _B}
        _kw = {_kx[k]["way"] for k in ("a", "b", "c", "d") if k in _kx}; KX_WAYS = _kw
        for w_, d_, st_ in STUB_SRC:                 # seitliche Stummel dieser Ways entfallen (sie werden schematisch gezeichnet)
            if w_ in _kw:
                if d_ in svg_paths[False]: svg_paths[False].remove(d_)
                if st_ in STUBS: STUBS.remove(st_)
        _drop = {d_ for i_, d_ in DBG if i_ in _ids}
        for k_ in (True, False): svg_paths[k_] = [d_ for d_ in svg_paths[k_] if d_ not in _drop]
        DBG[:] = [(i_, d_) for i_, d_ in DBG if i_ not in _ids]
        sa = min(_A, key=lambda x: x["s0"]); sb = max(_B, key=lambda x: x["s1"])
        xa, ya = xpos(sa["nodes"][0], sa["s0"]), ypos(sa["nodes"][0])
        xb, yb = xpos(sb["nodes"][-1], sb["s1"]), ypos(sb["nodes"][-1])
        t60 = math.tan(math.radians(60)); lp = CFG["lane_px"]
        ycx = max(ya, yb) + lp * _kx.get("tiefe", 1.5); yband = ycx + lp
        xcx = (xa + xb) / 2
        _xx = [float(a) for d_ in svg_paths[True] for a in re.findall(r"[MLHQ ](-?[\d.]+)(?=[,HMLQ ]|$)", d_)]
        xL, xR = (min(_xx), max(_xx)) if _xx else (CFG["margin_x"], W - CFG["margin_x"])
        r_ = 6
        # a: waagrecht ab Gleis, 60° hinunter durch die Kreuzung bis aufs untere Band, waagrecht an den rechten Rand
        a0 = xcx - (ycx - ya) / t60; a1 = xcx + (yband - ycx) / t60
        da = f"M{xa:.1f},{ya:.1f}H{a0:.1f}L{a1:.1f},{yband:.1f}H{xR:.1f}"
        # b: vom linken Rand auf dem unteren Band, 60° hinauf durch die Kreuzung bis aufs Gleis
        b0 = xcx - (yband - ycx) / t60; b1 = xcx + (ycx - yb) / t60
        db = f"M{xL:.1f},{yband:.1f}H{b0:.1f}L{b1:.1f},{yb:.1f}H{xb:.1f}"
        svg_paths[True] += [da, db]; DBG += [(x["id"], da) for x in _A] + [(x["id"], db) for x in _B]
        # c: Verbindung vom unteren Band links hinauf an den Anfang von a (Kerzers 258: Murten -> Gl. 4-6)
        # d: Verbindung vom Ende von b hinunter aufs untere Band rechts (Kerzers 259: Gl. 1-3 -> Bern)
        for _k, _up in (("c", True), ("d", False)):
            if _k not in _kx: continue
            _ss = [sg for sg in segs if sg["way"] == _kx[_k]["way"]]
            _drop = {d_ for i_, d_ in DBG if i_ in {x["id"] for x in _ss}}
            for k_ in (True, False): svg_paths[k_] = [d_ for d_ in svg_paths[k_] if d_ not in _drop]
            DBG[:] = [(i_, d_) for i_, d_ in DBG if i_ not in {x["id"] for x in _ss}]
            if _up: dc = f"M{xa - (yband - ya) / t60 - lp * 0.6:.1f},{yband:.1f}L{xa - lp * 0.6:.1f},{ya:.1f}H{xa:.1f}"
            else:   dc = f"M{xb:.1f},{yb:.1f}H{xb + lp * 0.6:.1f}L{xb + lp * 0.6 + (yband - yb) / t60:.1f},{yband:.1f}"
            _pax_c = any(x["pax"] for x in _ss)
            svg_paths[_pax_c].append(dc)
            DBG += [(x["id"], dc) for x in _ss]
        KX_EXITS = [(xR, yband, _kx["a"].get("ref"), "start", _kx["a"].get("ort")),
                    (xL, yband, _kx["b"].get("ref"), "end", _kx["b"].get("ort"))]
        H = max(H, yband + 120)

# Override "x_kreuzung": zwei Ways, die sich kreuzen (Kerzers 220 x 251), als gerade 60°-Schrägen durch einen
# gemeinsamen Kreuzungspunkt zeichnen (statt S-Kurven mit Zwischengeraden)
_xk = OVR.get("x_kreuzung")
if _xk:
    _ends = []
    for _w in _xk["ways"]:
        _ss = sorted([sg for sg in segs if sg["way"] == _w], key=lambda x: x["s0"])
        if not _ss: continue
        n0, n1 = _ss[0]["nodes"][0], _ss[-1]["nodes"][-1]
        _ends.append((_ss, xpos(n0, _ss[0]["s0"]), ypos(n0), xpos(n1, _ss[-1]["s1"]), ypos(n1)))
    if len(_ends) == 2:
        t60 = math.tan(math.radians(60))
        (_, ax0, ay0, ax1, ay1), (_, bx0, by0, bx1, by1) = _ends
        lo = max(min(ay0, ay1), min(by0, by1)); hi = min(max(ay0, ay1), max(by0, by1)); yc = (lo + hi) / 2
        xlo = max(e[1] + abs(yc - e[2]) / t60 for e in _ends); xhi = min(e[3] - abs(e[4] - yc) / t60 for e in _ends)
        xc = (xlo + xhi) / 2
        for _ss, x0, y0, x1, y1 in _ends:
            _ids = {x["id"] for x in _ss}
            _drop = {d_ for i_, d_ in DBG if i_ in _ids}
            for k_ in (True, False): svg_paths[k_] = [d_ for d_ in svg_paths[k_] if d_ not in _drop]
            DBG[:] = [(i_, d_) for i_, d_ in DBG if i_ not in _ids]
            d_ = _rund([(x0, y0), (xc - abs(yc - y0) / t60, y0), (xc + abs(y1 - yc) / t60, y1), (x1, y1)])
            svg_paths[any(x["pax"] for x in _ss)].append(d_); DBG += [(i, d_) for i in _ids]
        KX_WAYS = set(_xk["ways"]) | set(_xk.get("extra", []))
        if ARGS.dbg: print("XK", round(xlo), round(xhi), round(yc))

# Override "direkt": Way als gerade 60°-Schräge zwischen seinen beiden Endknoten zeichnen (Zofingen West: Gleis von
# der Suhrer Linie über 2 und 3 hinunter zum Weichenknoten bei Gleis 4)
DKW_EXTRA = []
if OVR.get("direkt"):
    t60 = math.tan(math.radians(60))
    for _w in OVR["direkt"]:
        _ss = sorted([sg for sg in segs if sg["way"] == _w], key=lambda x: x["s0"])
        if not _ss: continue
        _ids = {x["id"] for x in _ss}
        _e = [(xpos(n, SD[n][0]), ypos(n)) for n in (_ss[0]["nodes"][0], _ss[-1]["nodes"][-1])]
        (x0, y0), (x1, y1) = sorted(_e)
        _drop = {d_ for i_, d_ in DBG if i_ in _ids}
        for k_ in (True, False): svg_paths[k_] = [d_ for d_ in svg_paths[k_] if d_ not in _drop]
        DBG[:] = [(i_, d_) for i_, d_ in DBG if i_ not in _ids]
        xm = max(x0, x1 - abs(y1 - y0) / t60)
        # Kreuzungsknoten (DKW) auf dem Weg: Schräge durch den ersten solchen Knoten legen, dort DKW-Symbol zeichnen
        _outer = {_ss[0]["nodes"][0], _ss[-1]["nodes"][-1]}
        _cand = [n for x in _ss for n in x["nodes"] if n not in _outer]
        _mid = [n for n in dict.fromkeys(_cand) if any(n in o["nodes"] for o in segs if o["way"] != _w and o["flat"])]
        _mid.sort(key=lambda n: ypos(n))
        _sg_ = 1 if (x1 - x0) * (y1 - y0) > 0 else -1
        if _mid:
            nk = _mid[0]; xk, yk = xpos(nk, SD[nk][0]), ypos(nk)
            xm = xk - abs(yk - y0) / t60; xb = xk + abs(y1 - yk) / t60
            if ARGS.dbg: print("DIREKT", _w, "Versatz Fuss px", round(xb - x1, 1))
            x1 = xb
            for nn in dict.fromkeys(_mid):
                if ntag.get(nn, {}).get("railway:switch") != "double_slip" and not OVR.get("direkt_alle_dkw"): continue   # nur echte DKW
                yy = ypos(nn); xx = xm + abs(yy - y0) / t60
                c0 = np.array([xx, yy]); _hp_ = any(o["pax"] for o in segs if nn in (o["nodes"][0], o["nodes"][-1])) or any(x["pax"] for x in _ss)
                for a_, b_ in (((-1, 0), (0.5, 0.866 * _sg_)), ((1, 0), (-0.5, -0.866 * _sg_))):
                    DKW_EXTRA.append(_dkw_klammer(c0, a_, b_, _hp_, _alle_pax(nn)))
        d_ = _rund([(x0, y0), (xm, y0), (x1, y1), (x1 + 8, y1)])
        svg_paths[any(x["pax"] for x in _ss)].append(d_); DBG += [(i, d_) for i in _ids]
        KX_WAYS = set(KX_WAYS) | {_w}

# Override "stummel_versatz": {"<way>": meter} - kurzes Nebengleis an einer Weichenhäufung weiter hinten abzweigen
# lassen (Aarburg Süd: Stummel lag direkt neben der Schrägen nach Rothrist)
for _w, _dm in OVR.get("stummel_versatz", {}).items():
    _ss = [sg for sg in segs if sg["way"] == int(_w)]
    if not _ss: continue
    _ids = {x["id"] for x in _ss}
    _drop = {d_ for i_, d_ in DBG if i_ in _ids}
    for k_ in (True, False): svg_paths[k_] = [d_ for d_ in svg_paths[k_] if d_ not in _drop]
    DBG[:] = [(i_, d_) for i_, d_ in DBG if i_ not in _ids]
    _ends = [n for x in _ss for n in (x["nodes"][0], x["nodes"][-1])]
    _sw = max(_ends, key=lambda n: sum(1 for x in segs if n in (x["nodes"][0], x["nodes"][-1])))   # Weichenknoten
    _fr = [n for n in _ends if n != _sw][0]
    _x0 = X(SD[_sw][0] + _dm); _y0 = ypos(_sw); _dy = ypos(_fr) - _y0 or CFG["lane_px"]
    _x1 = _x0 + abs(_dy) / math.tan(math.radians(60))
    d_ = _rund([(_x0 - 8, _y0), (_x0, _y0), (_x1, _y0 + _dy), (_x1 + 25, _y0 + _dy)])   # ausgerundet (Hinweis Aarburg)
    svg_paths[False].append(d_); DBG += [(i, d_) for i in _ids]; KX_WAYS = set(KX_WAYS) | {int(_w)}

# Override "abzweig_diagonale": Gleis zweigt direkt aus einer Schrägen ab (dort, wo die Schräge seine Ebene kreuzt),
# statt aus dem Gleis am Ende der Schrägen (Kerzers: 2 und 3 auf derselben 60°-Linie)
for _ad in OVR.get("abzweig_diagonale", []):
    _dg = [d_ for i_, d_ in DBG if any(sg["id"] == i_ and sg["way"] == _ad["diag_way"] for sg in segs)]
    _gs = [sg for sg in segs if sg["way"] == _ad["way"] and sg["id"] in seglane]
    if not _dg or not _gs: continue
    _nums = [tuple(map(float, p)) for p in re.findall(r"(-?[\d.]+),(-?[\d.]+)", _dg[0])]
    _g = min(_gs, key=lambda x: x["s0"]); yg = Y(seglane[_g["id"]])
    xc = None
    for (xa, ya), (xb, yb) in zip(_nums, _nums[1:]):
        if min(ya, yb) < yg < max(ya, yb) and abs(yb - ya) > 1:
            xc = xa + (xb - xa) * (yg - ya) / (yb - ya); break
    if xc is None: continue
    for k_ in (True, False):
        for j_, d_ in enumerate(svg_paths[k_]):
            if (_g["id"], d_) in DBG:
                m_ = re.search(r"M(-?[\d.]+),%s(H-?[\d.]+.*)$" % re.escape(f"{yg:.1f}"), d_)
                if m_:
                    nd_ = f"M{xc:.1f},{yg:.1f}" + m_.group(2)
                    svg_paths[k_][j_] = nd_; DBG[DBG.index((_g["id"], d_))] = (_g["id"], nd_)
    KX_WAYS = set(KX_WAYS) | {_ad["way"]}

# Override "kuerzen": {"<way>": x_px} - Nebengleis, das seitlich aus dem Plan läuft, schon bei x enden lassen
# (Pfeil dort), damit es nicht bis an den Planrand gezogen wird (Safenwil 13/14)
for _w, _xc in OVR.get("kuerzen", {}).items():
    _ids = {sg["id"] for sg in segs if sg["way"] == int(_w)}
    if not _ids: continue
    for i_, (sid, d_) in enumerate(list(DBG)):
        if sid not in _ids: continue
        nd_ = re.sub(r"M(-?[\d.]+),(-?[\d.]+)H(-?[\d.]+)", lambda m_: (f"M{max(float(m_.group(1)), _xc):.1f},{m_.group(2)}H{m_.group(3)}"
                     if float(m_.group(3)) > _xc else ""), d_)
        for k_ in (True, False):
            if d_ in svg_paths[k_]: svg_paths[k_][svg_paths[k_].index(d_)] = nd_
        DBG[i_] = (sid, nd_)
    for w_, d_, st_ in STUB_SRC:
        if w_ == int(_w):
            if d_ in svg_paths[False]: svg_paths[False].remove(d_)
            if st_ in STUBS: STUBS.remove(st_)
            _y0 = float(re.findall(r"(-?[\d.]+)", d_)[1]); _dx = -1 if st_[0] < _xc else 1
            ex_, ey_ = _xc + _dx * 6.5, _y0 + (st_[1] - _y0) / max(abs(st_[1] - _y0), 1) * 11.3
            svg_paths[False].append(f"M{_xc:.1f},{_y0:.1f}L{ex_:.1f},{ey_:.1f}"); STUBS.append((ex_, ey_, math.atan2(ey_ - _y0, ex_ - _xc)))

# Regel 44 (DKW-Standard, D. Eckenstein 14.10.): An einer Doppelkreuzungsweiche läuft die kreuzende Schräge als eine
# gerade 60°-Linie durch den Knoten (keine kurze Gerade auf dem gekreuzten Gleis, sonst sieht es aus wie zwei Weichen).
# Ausgerundet wird erst dort, wo die Schräge auf ihre Gleise oben und unten trifft.
R44_DKW = {}
if RU.get("r44", False):
    _t60 = math.tan(math.radians(60))
    _segd = {x["id"]: x for x in segs}
    for n, t in ntag.items():
        if t.get("railway:switch") != "double_slip" or n not in home or n not in SD: continue
        _dg = [x for x in segs if not x["flat"] and n in (x["nodes"][0], x["nodes"][-1]) and x["id"] in dict(DBG)]
        if len(_dg) != 2: continue
        xn, yn = xpos(n, SD[n][0]), ypos(n)
        ends = []
        for x in _dg:
            o = x["nodes"][-1] if x["nodes"][0] == n else x["nodes"][0]
            ends.append((xpos(o, SD[o][0]), ypos(o), x))
        ends.sort()
        (xa, ya, A), (xb, yb, B) = ends
        if any(len(x.get("group") or []) > 1 for x in (A, B)): continue     # Teil einer längeren Weichenstrasse: nicht anfassen
        if not (xa < xn < xb) or (ya - yn) * (yb - yn) >= 0 or abs(ya - yn) < 3 or abs(yb - yn) < 3: continue
        # nur, wenn die beiden Schrägen eigene Pfade haben (nicht Teil einer längeren Weichenstrasse)
        _pa = [d_ for i_, d_ in DBG if i_ == A["id"]]; _pb = [d_ for i_, d_ in DBG if i_ == B["id"]]
        if not _pa or not _pb or any(i_ not in (A["id"], B["id"]) for i_, d_ in DBG if d_ in _pa + _pb): continue
        xa2 = xn - abs(yn - ya) / _t60; xb2 = xn + abs(yb - yn) / _t60
        xa0 = xa if 0 <= xa2 - xa < 25 else xa2 - 7; xb0 = xb if 0 <= xb - xb2 < 25 else xb2 + 7
        # Schwanz nur, wo die Schräge in ein Gleis einmündet (nicht, wenn sie als Schräge weiterläuft)
        _oa = A["nodes"][-1] if A["nodes"][0] == n else A["nodes"][0]; _ob = B["nodes"][-1] if B["nodes"][0] == n else B["nodes"][0]
        _flat_at_ = lambda m_: (any(x["flat"] and m_ in (x["nodes"][0], x["nodes"][-1]) for x in segs)
                                and not any(not x["flat"] and x["id"] not in (A["id"], B["id"]) and m_ in (x["nodes"][0], x["nodes"][-1]) for x in segs))
        _ta = 7 if _flat_at_(_oa) else 0.01; _tb = 7 if _flat_at_(_ob) else 0.01
        if ARGS.dbg: print("R44a", n, round(xa), round(xa2), round(xb), round(xb2))
        d_ = _rund([(min(xa0, xa2 - _ta), ya), (xa2, ya), (xb2, yb), (max(xb0, xb2 + _tb), yb)])
        _k = A["pax"] or B["pax"]
        for k_ in (True, False): svg_paths[k_] = [q for q in svg_paths[k_] if q not in _pa + _pb]
        if A["pax"] == B["pax"]:
            svg_paths[_k].append(d_)
        else:   # gemischt: Personen-Teil grün, Rest schwarz (selbe Linie)
            svg_paths[A["pax"]].append(_rund([(min(xa0, xa2 - _ta), ya), (xa2, ya), (xn, yn)]))
            svg_paths[B["pax"]].append(_rund([(xn, yn), (xb2, yb), (max(xb0, xb2 + _tb), yb)]))
        DBG[:] = [(i_, q) for i_, q in DBG if i_ not in (A["id"], B["id"])] + [(A["id"], d_), (B["id"], d_)]
        KX_WAYS = set(KX_WAYS) | {A["way"], B["way"]}      # eigene Zeichnung, Prüfung B/C dort aussetzen
        R44_DKW[n] = (np.sign(ya - yn), np.sign(yb - yn), A["pax"] or B["pax"] or any(o["pax"] for o in segs if n in (o["nodes"][0], o["nodes"][-1]) and o["flat"]))
        if ARGS.dbg: print("R44", n, round(xn), round(yn), round(xa2), round(xb2))

# Regel 45 (DKW-Standard für Weichenstrassen, Hinweise Thun/Rothrist 14.10.): Läuft eine Kette von Schrägen über mehrere
# Ebenen durch eine oder mehrere DKW, wird die ganze Kette eine gerade 60°-Linie durch die mittlere DKW. Die DKW-Symbole
# sitzen dort, wo die Linie die Ebene der DKW schneidet. Keine kurzen Geraden mehr auf den gekreuzten Gleisen.
R45_DKW = {}
_GABEL = []
ALS_DKW = {int(n) for n in OVR.get("als_dkw", [])}   # Override: Knoten wie DKW zeichnen (Rothrist: zwei Weichen = DKW nach Ortskenntnis)
if RU.get("r45", True):
    _t60_ = math.tan(math.radians(60))
    _isdkw = lambda n: (ntag.get(n, {}).get("railway:switch") == "double_slip" or n in ALS_DKW) and n in home and n in SD
    _G = {}
    for sg in segs:
        g = sg.get("group") or ([sg] if not sg["flat"] else None)
        if sg["flat"] or not g: continue
        _G[id(g)] = g
    _ch = lambda g: [g[0]["nodes"][0]] + [x["nodes"][-1] for x in g]
    _start = collections.defaultdict(list)
    for g in _G.values(): _start[_ch(g)[0]].append(g)
    _r45w = {int(n) for n in OVR.get("r45_weiter", [])}     # Kette auch durch diese Weichen gerade weiterziehen (Thun Gl. 5)
    _ends_at_dkw = {_ch(g)[-1] for g in _G.values() if _isdkw(_ch(g)[-1])}
    _ketten = []
    for g in _G.values():
        c0 = _ch(g)[0]
        if c0 in _ends_at_dkw and _start.get(c0) and any(_ch(h)[-1] == c0 for h in _G.values()): continue   # nicht Anfang einer Kette
        kette = list(g); cur = g
        while True:
            e_ = _ch(cur)[-1]
            if not (_isdkw(e_) or e_ in _r45w): break
            dy0 = ypos(_ch(cur)[-1]) - ypos(_ch(cur)[0])
            nx_ = [h for h in _start.get(e_, []) if h is not cur and (ypos(_ch(h)[-1]) - ypos(_ch(h)[0])) * dy0 > 0]
            if not nx_: break
            cur = nx_[0]; kette += list(cur)
        _ketten.append(kette)
    _ketten.sort(key=lambda g: -sum(1 for x in g if _isdkw(x["nodes"][-1])))   # Ketten mit echten DKW zuerst
    _R45X = {}
    for g in _ketten:
        chain = [g[0]["nodes"][0]] + [x["nodes"][-1] for x in g]
        if os.environ.get("R45DBG"): print("K45", [x["way"] for x in g], chain, [_isdkw(n) for n in chain])
        dk = [n for n in chain[1:-1] if _isdkw(n) or n in _r45w]
        if not dk: continue
        A_, B_ = chain[0], chain[-1]
        if A_ not in SD or B_ not in SD: continue
        xa, ya, xb, yb = xpos(A_, SD[A_][0]), ypos(A_), xpos(B_, SD[B_][0]), ypos(B_)
        if xa > xb: xa, ya, xb, yb = xb, yb, xa, ya
        if abs(yb - ya) < 3 or not all(min(ya, yb) + 2 < ypos(n) < max(ya, yb) - 2 for n in dk): continue
        K = min(dk, key=lambda n: (n not in _R45X, abs(ypos(n) - (ya + yb) / 2))); xk, yk = _R45X.get(K, xpos(K, SD[K][0])), ypos(K)
        xline = lambda y_: xk + (y_ - yk) / (yb - ya) * abs(yb - ya) / _t60_
        xa2, xb2 = xline(ya), xline(yb)
        _ids = {x["id"] for x in g}
        _drop = {d_ for i_, d_ in DBG if i_ in _ids}
        if not _drop: continue
        for k_ in (True, False): svg_paths[k_] = [q for q in svg_paths[k_] if q not in _drop]
        # Teilstücke in ihrer eigenen Farbe (grün = Personenverkehr), Ausrundung nur an den Enden
        _ys = [ypos(n) for n in chain]
        if xpos(chain[0], SD[chain[0]][0]) > xpos(chain[-1], SD[chain[-1]][0]): pass
        _parts = []
        for i_, x in enumerate(g):
            y0_, y1_ = _ys[i_], _ys[i_ + 1]
            if _parts and _parts[-1][0] == x["pax"]: _parts[-1][1].append((xline(y1_), y1_))
            else: _parts.append([x["pax"], [(xline(y0_), y0_), (xline(y1_), y1_)]])
        _first = min(range(len(_parts)), key=lambda k: min(p_[0] for p_ in _parts[k][1]))
        _last = max(range(len(_parts)), key=lambda k: max(p_[0] for p_ in _parts[k][1]))
        _newd = []
        for k_, (px_, pts_) in enumerate(_parts):
            pts_ = sorted(pts_); pts_ = [pts_[0], pts_[-1]]     # Zwischenknoten liegen auf der Geraden: nicht runden
            if k_ == _first: pts_ = [(min(xa, xa2 - 7), ya)] + pts_
            if k_ == _last: pts_ = pts_ + [(max(xb, xb2 + 7), yb)]
            dd_ = _rund(pts_); svg_paths[px_].append(dd_); _newd.append(dd_)
        d_ = " ".join(_newd)
        DBG[:] = [(i_, q) for i_, q in DBG if i_ not in _ids] + [(i_, d_) for i_ in _ids]
        KX_WAYS = set(KX_WAYS) | {x["way"] for x in g}
        # Abzweige an Zwischenknoten der Kette (Weiche in der Schrägen, Thun Ost 14.10.): Ansatz auf die neue Gerade legen;
        # liegt die Weiche fast auf dem End-Gleis, wird der Abzweig dort als Gabel angesetzt
        for n in chain[1:-1]:
            if _isdkw(n) or n not in SD: continue
            x_old, y_n = xpos(n, SD[n][0]), ypos(n)
            for o in segs:
                if o["id"] in _ids or n not in (o["nodes"][0], o["nodes"][-1]): continue
                for i2, (j_, d0) in enumerate(DBG):
                    if j_ != o["id"]: continue
                    _d0h = re.sub(r"^M(-?[\d.]+),(-?[\d.]+)L(-?[\d.]+),\2$", r"M\1,\2H\3", d0)
                    m2_ = re.fullmatch(r"M(-?[\d.]+),(-?[\d.]+)H(-?[\d.]+)", _d0h)
                    if m2_ and abs(float(m2_[2]) - y_n) < 1.5:
                        # gerades Gleis endet an der Weiche in der Schrägen / beginnt dort: ausgerundet in die Schräge
                        # (Thun Gl. 5 "in Schräge aber auch runden", Olten "Schräge durchziehen")
                        xs_, xe_ = float(m2_[1]), float(m2_[3]); xl_ = xline(y_n); sl_ = 1 if yb > ya else -1; r_ = 6.0
                        nd = None
                        if abs(xe_ - x_old) < 1.5 and abs(xs_ - xl_) > r_ + 1:
                            dx_ = 1 if xs_ < xl_ else -1
                            nd = (f"M{xs_:.1f},{y_n:.1f}H{xl_ - dx_ * r_:.1f}Q{xl_:.1f},{y_n:.1f} "
                                  f"{xl_ + dx_ * 0.5 * r_:.1f},{y_n + dx_ * sl_ * 0.866 * r_:.1f}")
                        elif abs(xs_ - x_old) < 1.5 and abs(xe_ - xl_) > r_ + 1:
                            dx_ = 1 if xe_ > xl_ else -1
                            nd = (f"M{xl_ - dx_ * 0.5 * r_:.1f},{y_n - dx_ * sl_ * 0.866 * r_:.1f}Q{xl_:.1f},{y_n:.1f} "
                                  f"{xl_ + dx_ * r_:.1f},{y_n:.1f}H{xe_:.1f}")
                        if nd:
                            for k_ in (True, False): svg_paths[k_] = [nd if q == d0 else q for q in svg_paths[k_]]
                            DBG[i2] = (j_, nd)
                        continue
                    m_ = re.match(r"M(-?[\d.]+),(-?[\d.]+)H(-?[\d.]+)Q(-?[\d.]+),(-?[\d.]+) (-?[\d.]+),(-?[\d.]+)L(-?[\d.]+),(-?[\d.]+)", d0)
                    if not m_: continue
                    x0, y0, h1, cx, cy, ex, ey, lx, ly = map(float, m_.groups())
                    if abs(x0 - x_old) > 1.5 or abs(y0 - y_n) > 1.5: continue
                    _gab = n in {int(v) for v in OVR.get("r45_gabel", [])}
                    yt = min((ya, yb), key=lambda v: abs(v - y_n)) if not _gab else max((ya, yb), key=lambda v: (ly - y_n) * (v - y_n))
                    if abs(yt - y_n) < 0.25 * CFG["lane_px"] or _gab:
                        # Gabel am Ende der Schrägen: Ast läuft als Gerade vom End-Gleis weiter (Thun Ost: "als Gerade vom Gleis 4 her")
                        ux, uy = lx - ex, ly - ey; Lu = math.hypot(ux, uy); ux, uy = ux / Lu, uy / Lu
                        xc = ex + (yt - ey) * ux / uy; r_ = 7.0; x0_ = min(xline(yt), xc - r_)
                        rest_ = d0[m_.end(7):]
                        _dup = [g_ for g_ in _GABEL if abs(g_[1] - yt) < 1 and abs(g_[0] - xc) < 10 and g_[2] == (uy > 0)]
                        if _dup:     # zwei Äste aus derselben Gabel (Thun Ost): zweiten Ast parallel versetzt ansetzen
                            dx_ = max(g_[0] for g_ in _dup) + 16 - xc; xc += dx_; x0_ = xc - r_ - 1
                            def _sh(mm): return f"{float(mm[1]) + dx_:.1f},{mm[2]}"
                            mq_ = re.match(r"L(-?[\d.]+),(-?[\d.]+)Q(-?[\d.]+),(-?[\d.]+) (-?[\d.]+),(-?[\d.]+)", rest_)
                            if mq_:
                                rest_ = re.sub(r"(-?[\d.]+),(-?[\d.]+)", _sh, rest_[:mq_.end()]) + rest_[mq_.end():]
                        _GABEL.append((xc, yt, uy > 0))
                        nd = (f"M{x0_:.1f},{yt:.1f}H{xc - r_:.1f}Q{xc:.1f},{yt:.1f} {xc + ux * r_:.1f},{yt + uy * r_:.1f}" + rest_)
                    else:
                        # Mindestabstand zur DKW auf dem Hauptgleis (Thun Ost 14.10.: "Weiche geht sehr nahe an der DKW raus")
                        _yd = [ypos(d2) for d2 in dk if _isdkw(d2)]
                        _dmin = 0.4 * CFG["lane_px"]
                        y_s = y_n
                        for yd_ in _yd:
                            if abs(y_s - yd_) < _dmin: y_s = yd_ + (1 if y_s >= yd_ else -1) * _dmin
                        ux, uy = lx - ex, ly - ey; Lu = math.hypot(ux, uy); ux, uy = ux / Lu, uy / Lu
                        xn_ = xline(y_s); xd_ = ex + (y_s - ey) * ux / uy if abs(uy) > 0.1 else ex
                        dxs_ = 1 if xd_ >= xn_ else -1
                        r_ = max(1.0, min(5.0, abs(xd_ - xn_)))
                        if (xd_ - xn_) * ux < 3:      # Ecke läge hinter dem Ansatz (Haken)
                            rest_ = d0[m_.end(9):]
                            mh_ = re.match(r"Q(-?[\d.]+),(-?[\d.]+) (-?[\d.]+),(-?[\d.]+)H(-?[\d.]+)", rest_)
                            if mh_ and min(ya, yb) < float(mh_[2]) < max(ya, yb):
                                # Gleis zweigt dort aus der Schrägen ab, wo die Schräge seine Ebene kreuzt (Blaupause C7)
                                yh_ = float(mh_[2]); xh_ = xline(yh_)
                                nd = f"M{xh_:.1f},{yh_:.1f}H{float(mh_[5]):.1f}" + rest_[mh_.end():]
                            else:
                                nd = f"M{xn_:.1f},{y_s:.1f}L{lx:.1f},{ly:.1f}" + rest_
                        else: nd = (f"M{xn_:.1f},{y_s:.1f}H{xd_ - dxs_ * r_:.1f}Q{xd_:.1f},{y_s:.1f} {xd_ + ux * r_:.1f},{y_s + uy * r_:.1f}"
                              f"L{lx:.1f},{ly:.1f}" + d0[m_.end(9):])
                    for k_ in (True, False): svg_paths[k_] = [nd if q == d0 else q for q in svg_paths[k_]]
                    DBG[i2] = (j_, nd)
        for n in chain: _R45X.setdefault(n, xline(ypos(n)))
        for n in dk:
            if not _isdkw(n): continue          # Kreuzung (r45_weiter): kein DKW-Symbol
            yn = ypos(n)
            R45_DKW[n] = (xline(yn), yn, np.sign(ya - yn), np.sign(yb - yn), any(o["pax"] for o in segs if n in (o["nodes"][0], o["nodes"][-1])))
        if ARGS.dbg: print("R45", [x["way"] for x in g], len(dk), round(xa2), round(xb2))

# Override "dkw_gerade" {node: [sa, sb]}: DKW-Symbol für eine von Hand (zeichnen) gerade durchgezogene Schräge
for n_, (sa_, sb_) in OVR.get("dkw_gerade", {}).items():
    n_ = int(n_)
    if n_ in SD: R45_DKW[n_] = (xpos(n_, SD[n_][0]), ypos(n_), sa_, sb_, any(o["pax"] for o in segs if n_ in (o["nodes"][0], o["nodes"][-1])))
# Override "weglassen_pfeil": weggelassene Gleise, die an einem Hauptgleis abzweigen, als kurzen Stummel mit Pfeil andeuten
# (D. Eckenstein, Kerzers: "Weichen weg von einem Hauptgleis zeichnen, mindestens als Pfeil andeuten")
if OVR.get("weglassen_pfeil"):
    _pax_n = {n for sg in segs if sg["pax"] for n in sg["nodes"]}
    _seen = set()
    _ohne = {int(w) for w in OVR.get("weglassen_ohne_pfeil", [])}
    for sg in WEG_SEGS:
        if sg["way"] in _ohne: continue
        for e_ in (0, -1):
            n = sg["nodes"][e_]; o_ = sg["nodes"][-1 if e_ == 0 else 0]
            if n not in _pax_n or n not in home or n not in SD or o_ not in SD: continue
            if not (CFG["s_min"] <= SD[n][0] <= CFG["s_max"]): continue
            # Richtung: einige Meter in den weggelassenen Way hinein
            _ns = sg["nodes"] if e_ == 0 else sg["nodes"][::-1]
            _q = next((m for m in _ns[1:] if m in SD and math.hypot(SD[m][0] - SD[n][0], SD[m][1] - SD[n][1]) > 15), o_)
            dx_ = 1 if SD[_q][0] >= SD[n][0] else -1; dy_ = -1 if SD[_q][1] > SD[n][1] else 1
            k_ = (n, dx_, dy_)
            if k_ in _seen: continue
            _seen.add(k_)
            x_, y_ = xpos(n, SD[n][0]), ypos(n)
            ex_, ey_ = x_ + dx_ * 6.5, y_ + dy_ * 11.3
            svg_paths[False].append(f"M{x_:.1f},{y_:.1f}L{ex_:.1f},{ey_:.1f}"); STUBS.append((ex_, ey_, math.atan2(ey_ - y_, ex_ - x_)))

if os.environ.get("SEGDUMP"):
    for sg in segs:
        a_, b_ = sg["nodes"][0], sg["nodes"][-1]
        if a_ in SD and b_ in SD:
            print("SEG", sg["id"], sg["way"], int(sg["pax"]), a_, b_, round(xpos(a_, SD[a_][0])), round(ypos(a_)), round(xpos(b_, SD[b_][0])), round(ypos(b_)), round(sg["s0"]), round(sg["s1"]), seglane.get(sg["id"]) if "seglane" in globals() else None)
# Override "zeichnen" (Olten Nord, Fächer der Aarauer Gleise): Ways aus der Zeichnung nehmen und als eigene Linien
# in Ebenen-Koordinaten neu zeichnen. Punkte: [s, lane] oder ["x:<px>", lane] oder ["d60", lane] (unter 60° bis zur Ebene);
# "port_way": der Ast endet als seitlicher Abgang dieses Ways (Stummel + Anschluss für den Regionalplan wie bisher).
ZEICHNEN_PORT = {}; ZEICHNEN_PORT_AB = {}; ZEICHNEN_LINIEN = []; ZEICHNEN_UEBER = []
_zn = OVR.get("zeichnen")
if _zn:
    _wg = {int(w) for w in _zn.get("weg", [])}
    _ids = {sg["id"] for sg in segs if sg["way"] in _wg}
    _wn = {n_ for sg in segs if sg["way"] in _wg for n_ in sg["nodes"]}
    for _d, _a, _b, _e in R47_P:        # Regel-47-Spurwechsel an weggenommenen Gleisen ebenfalls weg (auch der weggelassene Way selbst, 21.10.)
        if _a in _wn or _b in _wn or _e in _wg:
            for k_ in (True, False):
                if _d in svg_paths[k_]: svg_paths[k_].remove(_d)
    _wpos = {(f"{xpos(n_, SD[n_][0]):.1f}", f"{ypos(n_):.1f}") for n_ in _wn if n_ in SD and n_ in home}
    for k_ in (True, False):
        _keep_ = []
        for d_ in svg_paths[k_]:
            m_ = re.fullmatch(r"M(-?[\d.]+),(-?[\d.]+)L(-?[\d.]+),(-?[\d.]+)", d_)
            if m_ and (m_[1], m_[2]) in _wpos and abs(float(m_[4]) - float(m_[2])) > 2 and math.hypot(float(m_[3]) - float(m_[1]), float(m_[4]) - float(m_[2])) < 30:
                STUBS = [t_ for t_ in STUBS if not (abs(t_[0] - float(m_[3])) < 0.2 and abs(t_[1] - float(m_[4])) < 0.2)]
                continue
            _keep_.append(d_)
        svg_paths[k_] = _keep_
    # Randpfeile der weggenommenen Ways ebenfalls weglassen
    _wp = [(xpos(n_, SD[n_][0]), ypos(n_)) for sg in segs if sg["way"] in _wg for n_ in (sg["nodes"][0], sg["nodes"][-1]) if n_ in SD]
    arrows = [a for a in arrows if not any(abs(a[0] - px) < 12 and abs(a[1] - py) < 2 for px, py in _wp)]
    # Endpunkte (Prellbock) weggenommener Ways ebenfalls weglassen (Rothrist 15.10.), wenn kein anderes Gleis dort endet
    _keepn = {n_ for sg in segs if sg["way"] not in _wg for n_ in (sg["nodes"][0], sg["nodes"][-1]) if n_ in SD}
    _kp = [(xpos(n_, SD[n_][0]), ypos(n_)) for n_ in _keepn]
    dots = [d_ for d_ in dots if not (any(abs(d_[0] - px) < 0.5 and abs(d_[1] - py) < 0.5 for px, py in _wp)
                                      and not any(abs(d_[0] - px) < 0.5 and abs(d_[1] - py) < 0.5 for px, py in _kp))]
    _drop = {d_ for i_, d_ in DBG if i_ in _ids}
    for k_ in (True, False): svg_paths[k_] = [d_ for d_ in svg_paths[k_] if d_ not in _drop]
    DBG = [(i_, d_) for i_, d_ in DBG if i_ not in _ids]
    STUBS = [st_ for st_ in STUBS if not any(w_ in _wg and st_ == t_ for w_, _d, t_ in STUB_SRC)]
    for _eid, _l in R38_ST.items():          # Regel-38-Pfeile weggenommener Ways (Olten West, Gleis 480)
        if _eid not in _wg: continue
        for _n, _d, _t in _l:
            for k_ in (True, False):
                if _d in svg_paths[k_]: svg_paths[k_].remove(_d)
            if _t in STUBS: STUBS.remove(_t)
    for li in _zn.get("linien", []):
        # "nur_plan": nur im Spurplan, "nur_regional": nur im Regionalplan (--bare), z. B. Auvernier 219 (18.10.)
        if (li.get("nur_plan") and ARGS.bare) or (li.get("nur_regional") and not ARGS.bare): continue
        pts = []
        def _nref(t_):      # "n:<knoten>[+-px][@+-py]" -> (x, y) des Knotens, verschoben
            m_ = re.fullmatch(r"n:(\d+)([+-][\d.]+)?(?:@([+-][\d.]+))?", t_); n_ = int(m_[1])
            return xpos(n_, SD[n_][0]) + float(m_[2] or 0), ypos(n_) + float(m_[3] or 0)
        for a_, l_ in li["pts"]:
            y_ = float(l_[2:]) if isinstance(l_, str) and l_.startswith("y:") else (_nref(l_)[1] if isinstance(l_, str) and l_.startswith("n:") else Y(l_))
            if isinstance(a_, str) and a_.startswith("n:"): pts.append((_nref(a_)[0], y_))
            elif isinstance(a_, str) and (a_.startswith("c60:") or a_.startswith("c60-:")):     # auf der 60°-Linie durch einen Knoten (fallend nach rechts, "c60-:" steigend)
                m_ = re.fullmatch(r"c60-?:(\d+)([+-][\d.]+)?", a_); n_ = int(m_[1]); sg_ = -1 if a_.startswith("c60-") else 1
                pts.append((xpos(n_, SD[n_][0]) + sg_ * (y_ - ypos(n_)) / math.tan(math.radians(60)) + float(m_[2] or 0), y_))
            elif a_ == "d60":
                x0_, y0_ = pts[-1]; pts.append((x0_ + abs(y_ - y0_) / math.tan(math.radians(60)), y_))
            elif isinstance(a_, str) and a_.startswith("x:"): pts.append((float(a_[2:]), y_))
            elif isinstance(a_, str) and a_[:1] in "+-" and pts: pts.append((pts[-1][0] + float(a_), y_))   # relativ in px
            else: pts.append((X(float(a_)), y_))
        svg_paths[bool(li.get("pax", True))].append(_rund(pts, li.get("rund", 7.0)))
        ZEICHNEN_LINIEN.append(pts)
        if li.get("ueber"): ZEICHNEN_UEBER.append((pts, bool(li.get("pax", True)), li.get("rund", 7.0)))
        if li.get("punkt_anfang"): dots.append((pts[0][0], pts[0][1], bool(li.get("pax", True))))
        if li.get("punkt_ende"): dots.append((pts[-1][0], pts[-1][1], bool(li.get("pax", True))))       # Bôle 17.10.
        if li.get("port_way"):
            ZEICHNEN_PORT[int(li["port_way"])] = pts[0] if li.get("port_am_anfang") else pts[-1]
            ZEICHNEN_PORT_AB[int(li["port_way"])] = pts[-1] if li.get("port_am_anfang") else pts[0]   # Anfang der Linie (20.10.)
        if li.get("pfeil") and len(pts) > 1:      # Linie endet als Weichenpfeil (Gleis in weggelassene Anlage, Olten 480, 15.10.)
            (xa_, ya_), (xb_, yb_) = pts[-2], pts[-1]; STUBS.append((xb_, yb_, math.atan2(yb_ - ya_, xb_ - xa_)))

out = []
EXITS = list(KX_EXITS)
PORTS = []
out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif">')
out.append(f'<rect width="100%" height="100%" fill="#fff"/>')
out.append(f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">')
# Weichenpfeile (Stummel mit Pfeil) ausrunden wie Weichen (D. Eckenstein 14.10.: "auch Pfeile ausrunden, gilt überall")
_stub_end = {(round(x_, 1), round(y_, 1)) for x_, y_, _ in STUBS}
def _rund_stub(d_):
    m_ = re.fullmatch(r"M(-?[\d.]+),(-?[\d.]+)L(-?[\d.]+),(-?[\d.]+)", d_)
    if not m_: return d_
    x0_, y0_, x1_, y1_ = map(float, m_.groups())
    if (round(x1_, 1), round(y1_, 1)) not in _stub_end or abs(y1_ - y0_) < 2 or (round(x1_, 1), round(y1_, 1)) in _no_round: return d_
    L_ = math.hypot(x1_ - x0_, y1_ - y0_); r_ = min(6.0, L_ * 0.45); sx_ = 1 if x1_ >= x0_ else -1
    return (f"M{x0_ - sx_ * r_:.1f},{y0_:.1f}Q{x0_:.1f},{y0_:.1f} {x0_ + (x1_ - x0_) * r_ / L_:.1f},{y0_ + (y1_ - y0_) * r_ / L_:.1f}"
            f"L{x1_:.1f},{y1_:.1f}")
# Pfeil in der Luft (Thun 14.10.): liegt der Ansatzpunkt eines Stummels auf keinem gezeichneten Gleis (das Gleis läuft dort
# schon in der Schrägen), den Stummel samt Pfeil auf den nächsten Gleispunkt verschieben
from svgpathtools import parse_path as _pp2
_samp = []
for k_ in (True, False):
    for d_ in svg_paths[k_]:
        if re.fullmatch(r"M(-?[\d.]+),(-?[\d.]+)L(-?[\d.]+),(-?[\d.]+)", d_) and (lambda m_: (round(float(m_[2]), 1), round(float(m_[3]), 1)) in _stub_end)(re.findall(r"-?[\d.]+", d_)): continue
        try:
            for sub in _pp2(d_).continuous_subpaths():
                L_ = sub.length()
                for t_ in np.linspace(0, 1, max(2, int(L_ / 2))):
                    z_ = sub.point(sub.ilength(t_ * L_)) if L_ > 0 else sub.point(0)
                    _samp.append((z_.real, z_.imag))
        except Exception: pass
_samp = np.array(_samp) if _samp else np.zeros((0, 2)); _no_round = set()
def _snap_stub(d_):
    m_ = re.fullmatch(r"M(-?[\d.]+),(-?[\d.]+)L(-?[\d.]+),(-?[\d.]+)", d_)
    if not m_ or not len(_samp): return d_
    x0_, y0_, x1_, y1_ = map(float, m_.groups())
    k_ = (round(x1_, 1), round(y1_, 1))
    if k_ not in _stub_end: return d_
    dd_ = np.hypot(_samp[:, 0] - x0_, _samp[:, 1] - y0_); i_ = int(dd_.argmin())
    # Stummel liegt auf einem anderen Gleis (gleiche Richtung wie eine Schräge daneben): ein Stück weiter ansetzen
    xm_, ym_ = (x0_ + x1_) / 2, (y0_ + y1_) / 2
    if dd_[i_] < 2.5 and np.hypot(_samp[:, 0] - xm_, _samp[:, 1] - ym_).min() < 2.0:
        sh_ = 12.0 * (1 if x1_ < x0_ else -1)
        for j_, st_ in enumerate(STUBS):
            if (round(st_[0], 1), round(st_[1], 1)) == k_: STUBS[j_] = (st_[0] + sh_, st_[1], st_[2])
        _stub_end.add((round(x1_ + sh_, 1), round(y1_, 1)))
        return f"M{x0_ + sh_:.1f},{y0_:.1f}L{x1_ + sh_:.1f},{y1_:.1f}"
    # Pfeilspitze trifft ein anderes Gleis (Thun: Überlappung mit Stumpengleis): Stummel kürzen
    de_ = np.hypot(_samp[:, 0] - x1_, _samp[:, 1] - y1_)
    if de_.min() < 6 and dd_[i_] < 2.5:
        f_ = 0.55; nx1_, ny1_ = x0_ + (x1_ - x0_) * f_, y0_ + (y1_ - y0_) * f_
        for j_, st_ in enumerate(STUBS):
            if (round(st_[0], 1), round(st_[1], 1)) == k_: STUBS[j_] = (nx1_, ny1_, st_[2])
        _stub_end.add((round(nx1_, 1), round(ny1_, 1)))
        return f"M{x0_:.1f},{y0_:.1f}L{nx1_:.1f},{ny1_:.1f}"
    if dd_[i_] < 2.5 or dd_[i_] > 40: return d_
    sx_, sy_ = _samp[i_] - (x0_, y0_)
    for j_, st_ in enumerate(STUBS):
        if (round(st_[0], 1), round(st_[1], 1)) == k_: STUBS[j_] = (st_[0] + sx_, st_[1] + sy_, st_[2])
    _stub_end.add((round(x1_ + sx_, 1), round(y1_ + sy_, 1))); _no_round.add((round(x1_ + sx_, 1), round(y1_ + sy_, 1)))
    return f"M{x0_ + sx_:.1f},{y0_ + sy_:.1f}L{x1_ + sx_:.1f},{y1_ + sy_:.1f}"
svg_paths = {k_: [_snap_stub(d_) for d_ in v_] for k_, v_ in svg_paths.items()}
# Pfeile, deren Spitzen fast aufeinander liegen (Olten Nord 14.10.: "Überlappungen"): nur einen zeichnen
_keep = []
for st_ in STUBS:
    if any(math.hypot(st_[0] - k_[0], st_[1] - k_[1]) < 12 for k_ in _keep): continue
    _keep.append(st_)
if len(_keep) < len(STUBS):
    _drop_tips = {(round(x_, 1), round(y_, 1)) for x_, y_, _ in STUBS if (x_, y_, _) not in _keep}
    def _is_drop(d_):
        m_ = re.fullmatch(r"M(-?[\d.]+),(-?[\d.]+)L(-?[\d.]+),(-?[\d.]+)", d_)
        return bool(m_) and (round(float(m_[3]), 1), round(float(m_[4]), 1)) in _drop_tips
    svg_paths = {k_: [d_ for d_ in v_ if not _is_drop(d_)] for k_, v_ in svg_paths.items()}
    STUBS = _keep
    _stub_end = {(round(x_, 1), round(y_, 1)) for x_, y_, _ in STUBS}
_RS = []
def _rund_stub2(d_):
    n_ = _rund_stub(d_)
    if n_ != d_:
        m_ = re.match(r"M(-?[\d.]+),(-?[\d.]+)Q(-?[\d.]+),", n_); _RS.append((float(m_[1]), float(m_[3]), m_[2]))
    return n_
svg_paths = {k_: [_rund_stub2(d_) for d_ in v_] for k_, v_ in svg_paths.items()}
# Weiche mit Mini-Radius (Ast beginnt genau im Weichenknoten, Thun 14.10. "Weiche nach oben runden"): Ausrundung mit vollem
# Radius, das gerade Stück davor liegt auf dem durchgehenden Gleis
_N = r"(-?[\d.]+)"
_pat_s = re.compile(r"M%s,%sH\1Q%s,\2 %s,%sL%s,%s" % (_N, _N, _N, _N, _N, _N, _N))
def _vollrad(m_):
    x0, y0, cx, ex, ey, lx, ly = map(float, m_.groups())
    if abs(cx - x0) > 2.5: return m_[0]
    ux, uy = lx - cx, ly - y0; L_ = math.hypot(ux, uy)
    if L_ < 14 or abs(uy) < 1: return m_[0]
    ux, uy = ux / L_, uy / L_; r_ = 6.0; sx_ = 1 if ux > 0 else -1
    return f"M{cx - sx_ * r_:.1f},{y0:.1f}Q{cx:.1f},{y0:.1f} {cx + ux * r_:.1f},{y0 + uy * r_:.1f}L{lx:.1f},{ly:.1f}"
_pat_e = re.compile(r"L%s,%sQ%s,%s %s,\4H\5(?=[\sM]|$)" % (_N, _N, _N, _N, _N))
def _vollrad_e(m_):
    lx, ly, cx, cy, ex = map(float, m_.groups())
    if abs(ex - cx) > 2.5: return m_[0]
    ux, uy = lx - cx, ly - cy; L_ = math.hypot(ux, uy)
    if L_ < 14 or abs(uy) < 1: return m_[0]
    ux, uy = ux / L_, uy / L_; r_ = 6.0; sx_ = 1 if ux > 0 else -1
    return f"L{cx + ux * r_:.1f},{cy + uy * r_:.1f}Q{cx:.1f},{cy:.1f} {cx - sx_ * r_:.1f},{cy:.1f}"
if RU.get("r46", True):
    svg_paths = {k_: [_pat_e.sub(_vollrad_e, _pat_s.sub(_vollrad, d_)) for d_ in v_] for k_, v_ in svg_paths.items()}
# Regel 48 (opt-in, Verbindungsprüfung 15.10.): Spurwechsel, der an der Weiche ohne Ausrundung beginnt ("M x,y L ..." schräg),
# bekommt am Anfang dieselbe Ausrundung wie am Ende (Rothrist, Zofingen)
_pat48 = re.compile(r"(?:^|(?<=\s))M%s,%sL%s,%s(?=Q)" % (_N, _N, _N, _N))
def _r48(m_):
    x0, y0, x1, y1 = map(float, m_.groups())
    L_ = math.hypot(x1 - x0, y1 - y0)
    if abs(y1 - y0) < 5 or L_ < 12: return m_[0]
    ux, uy = (x1 - x0) / L_, (y1 - y0) / L_; r_ = 6.0; sx_ = 1 if ux > 0 else -1
    return f"M{x0 - sx_ * r_:.1f},{y0:.1f}Q{x0:.1f},{y0:.1f} {x0 + ux * r_:.1f},{y0 + uy * r_:.1f}L{x1:.1f},{y1:.1f}"
if RU.get("r48", False):
    svg_paths = {k_: [_pat48.sub(_r48, d_) for d_ in v_] for k_, v_ in svg_paths.items()}
# Teilpfade der Länge 0 ("M x,y H x") zeichnen mit runden Enden einen Punkt: weglassen
_z0 = re.compile(r"M(-?[\d.]+),(-?[\d.]+)H\1(?=\s*M|\s*$)")
svg_paths = {k_: [z_ for z_ in (_z0.sub("", d_).strip() for d_ in v_) if z_] for k_, v_ in svg_paths.items()}
# Gerades Gleis, das genau am Knick eines ausgerundeten Pfeils endet: bis zum Beginn der Ausrundung kürzen (kein Überstand)
_all_d = " ".join(svg_paths[True] + svg_paths[False])
for xs_, xk_, ys_ in _RS:
    if re.search(r"M%s,%s[HQL]" % (re.escape(f"{xk_:.1f}"), re.escape(ys_)), _all_d) and not re.search(r"M%s,%sQ" % (re.escape(f"{xs_:.1f}"), re.escape(ys_)), "M" + _all_d.split("M%s,%s" % (f"{xk_:.1f}", ys_))[1][:0]):
        continue      # am Knick beginnt ein weiteres Gleis (Thun Ost: Lücke vor dem Abzweig): Gleis nicht kürzen
    pat_ = re.compile(r"M(-?[\d.]+),%s((?:H-?[\d.]+)*)H%s(?=[\sM]|$)" % (re.escape(ys_), re.escape(f"{xk_:.1f}")))
    def _tr(m_):
        x0_ = float(m_[1])
        if (xk_ - x0_) * (xk_ - xs_) <= 0 or abs(xk_ - x0_) <= abs(xk_ - xs_): return m_[0]
        return f"M{m_[1]},{ys_}{m_[2]}H{xs_:.1f}"
    svg_paths = {k_: [pat_.sub(_tr, d_) for d_ in v_] for k_, v_ in svg_paths.items()}
_BRAUN = {True: [], False: []}
if SCHMAL_GEMISCHT:
    # gemischter Bahnhof (Montreux, Zweisimmen): Teilpfade nach der nächstgelegenen Spur trennen, Schmalspur braun
    from svgpathtools import parse_path as _ppS
    def _samp_d(d_, step=3.0):
        out_ = []
        try:
            for sub in _ppS(d_).continuous_subpaths():
                L_ = sub.length()
                for t_ in np.linspace(0, 1, max(2, int(L_ / step))):
                    z_ = sub.point(sub.ilength(t_ * L_)) if L_ > 0 else sub.point(0); out_.append((z_.real, z_.imag))
        except Exception: pass
        return out_
    _sgS = {x["id"]: x for x in segs}
    _ps, _pn = [], []
    for i_, d_ in DBG:
        if i_ in _sgS: (_ps if _sgS[i_].get("schmal") else _pn).extend(_samp_d(d_))
    from scipy.spatial import cKDTree as _KDS
    _ks = _KDS(np.array(_ps)) if _ps else None; _kn = _KDS(np.array(_pn)) if _pn else None
    def _ist_schmal(sub_d):
        q_ = _samp_d(sub_d)
        if not q_ or _ks is None: return False
        if _kn is None: return True
        ds_, _ = _ks.query(q_); dn_, _ = _kn.query(q_)
        return float(np.mean(ds_)) < float(np.mean(dn_))
    for k_ in (True, False):
        keep_ = []
        for d_ in svg_paths[k_]:
            subs_ = [p_.strip() for p_ in re.split(r"(?=M)", d_) if p_.strip()]
            for x_ in subs_:
                (_BRAUN[k_] if _ist_schmal(x_) else keep_).append(x_)
        svg_paths[k_] = keep_
out.append(f'<path d="{" ".join(svg_paths[False])}" stroke="{black}" stroke-width="1.6"/>')
if _BRAUN[False]: out.append(f'<path d="{" ".join(_BRAUN[False])}" stroke="{MS_BRAUN}" stroke-width="1.6"/>')
_z = re.compile(r"M([-\d.]+),([-\d.]+)L\1,\2(?=[\s\"M]|$)")
svg_paths = {k_: [_z.sub("", d_) for d_ in v_] for k_, v_ in svg_paths.items()}
_GREEN_IDX = len(out)
out.append(f'<path d="{" ".join(svg_paths[True])}" stroke="{green}" stroke-width="3.6"/>')
if _BRAUN[True]: out.append(f'<path d="{" ".join(_BRAUN[True])}" stroke="{MS_BRAUN}" stroke-width="3.6"/>')
# Override "portale": [{"s": m, "y": [ebenen-ref...], "dir": +1}] - Tunnelportal nach Blaupause E7 (öffnet nach aussen)
for _pt in OVR.get("portale", []):        # auch im Regionalplan (bare) zeichnen (Hinweis Region Olten 15.10.)
    _xp = X(float(_pt["s"])); _dr = _pt.get("dir", 1)
    _yy = []
    for _r in _pt["y"]:
        m_ = re.fullmatch(r"n:(\d+)(?:@([+-][\d.]+))?", str(_r)); _yy.append(ypos(int(m_[1])) + float(m_[2] or 0))
    y0_, y1_ = min(_yy) - 7, max(_yy) + 7
    out.append(f'<path d="M{_xp + _dr * 5:.1f},{y0_ - 3:.1f}L{_xp:.1f},{y0_:.1f}L{_xp:.1f},{y1_:.1f}L{_xp + _dr * 5:.1f},{y1_ + 3:.1f}" fill="none" stroke="{black}" stroke-width="1.4"/>')
# Über-/Unterführung (Blaupause E6, Olten Nord: Aarauer Gleise über die Basler Gleise): das untere Gleis bekommt eine Lücke,
# das obere Gleis läuft durch und hat Brückenflügel
if ZEICHNEN_UEBER:                  # auch im Regionalplan (bare): "Unterführungssymbol?" (15.10.)
    _hz = []
    for k_ in (True, False):
        for d_ in svg_paths[k_]:
            for m_ in re.finditer(r"M(-?[\d.]+),(-?[\d.]+)((?:H-?[\d.]+)+)", d_):
                xs_ = [float(m_[1])] + [float(v) for v in re.findall(r"H(-?[\d.]+)", m_[3])]
                _hz.append((min(xs_), max(xs_), float(m_[2]), k_))
            # waagrechte Stücke irgendwo in einem Pfad (Zeichnen-Linien mit Ausrundungen, Olten 388 und 531, 15.10.)
            _cx = _cy = None
            for c_, a_ in re.findall(r"([MLHQ])([^MLHQ]*)", d_):
                v_ = [float(t_) for t_ in re.findall(r"-?[\d.]+", a_)]
                if c_ == "M" and len(v_) >= 2: _cx, _cy = v_[0], v_[1]
                elif c_ == "Q" and len(v_) >= 4: _cx, _cy = v_[2], v_[3]
                elif c_ in "LH" and _cx is not None and v_:
                    nx_, ny_ = (v_[0], _cy) if c_ == "H" else (v_[0], v_[1] if len(v_) > 1 else _cy)
                    if c_ == "L" and abs(ny_ - _cy) < 0.05 and abs(nx_ - _cx) > 30:
                        _hz.append((min(_cx, nx_), max(_cx, nx_), _cy, k_))
                    _cx, _cy = nx_, ny_
    _kr = []          # (linie, horizontale, xc, y, u)
    for li_, (pts_, pax_, rund_) in enumerate(ZEICHNEN_UEBER):
        for (x0, y0), (x1, y1) in zip(pts_, pts_[1:]):
            if abs(y1 - y0) < 1: continue
            L_ = math.hypot(x1 - x0, y1 - y0); u = ((x1 - x0) / L_, (y1 - y0) / L_)
            for hi_, (hx0, hx1, hy, hk) in enumerate(_hz):
                if not (min(y0, y1) + 4 < hy < max(y0, y1) - 4): continue
                xc_ = x0 + (hy - y0) * (x1 - x0) / (y1 - y0)
                if not (hx0 + 14 < xc_ < hx1 - 14): continue       # nur echte Kreuzungen (Gleis läuft auf beiden Seiten weiter)
                _kr.append((li_, hi_, xc_, hy, u))
    # Bündel: Kreuzungen, die nahe beieinander liegen (Olten 15.10.: Aarau 540 und 531 sind zwei getrennte Brücken)
    _bund = []
    for k in sorted(_kr, key=lambda k: k[2]):
        if _bund and k[2] - _bund[-1][-1][2] < 80 and k[4][0] * _bund[-1][-1][4][0] > 0: _bund[-1].append(k)
        else: _bund.append([k])
    for _kb in _bund:
        # Lücke im unteren Gleis: eine pro Gleis über das ganze Bündel
        for hy in {round(k[3], 1) for k in _kb}:
            xs_ = [k[2] for k in _kb if round(k[3], 1) == hy]
            out.append(f'<path d="M{min(xs_) - 12:.1f},{hy:.1f}H{max(xs_) + 12:.1f}" stroke="#fff" stroke-width="8"/>')
        # Brückenflügel: aussen am Bündel, über alle gekreuzten Gleise
        u = _kb[0][4]; n = (u[1], -u[0])
        _off = {li_: min(k[2] for k in _kb if k[0] == li_) for li_ in {k[0] for k in _kb}}
        for li_, sd_ in ((min(_off, key=_off.get), -1), (max(_off, key=_off.get), 1)):
            ks_ = sorted([k for k in _kb if k[0] == li_], key=lambda k: k[3])
            a_ = (ks_[0][2], ks_[0][3]); b_ = (ks_[-1][2], ks_[-1][3])
            sg_ = sd_ * (1 if n[0] > 0 else -1)             # Seite: links (-x) bzw. rechts (+x) des Bündels, Flügel nach aussen (Olten 15.10.)
            q0 = (a_[0] - u[0] * 11 + n[0] * sg_ * 6, a_[1] - u[1] * 11 + n[1] * sg_ * 6)
            q1 = (b_[0] + u[0] * 11 + n[0] * sg_ * 6, b_[1] + u[1] * 11 + n[1] * sg_ * 6)
            f0 = (q0[0] - u[0] * 3 + n[0] * sg_ * 3, q0[1] - u[1] * 3 + n[1] * sg_ * 3)
            f1 = (q1[0] + u[0] * 3 + n[0] * sg_ * 3, q1[1] + u[1] * 3 + n[1] * sg_ * 3)
            out.append(f'<path d="M{f0[0]:.1f},{f0[1]:.1f}L{q0[0]:.1f},{q0[1]:.1f}L{q1[0]:.1f},{q1[1]:.1f}L{f1[0]:.1f},{f1[1]:.1f}" fill="none" stroke="{black}" stroke-width="1.2"/>')
    for pts_, pax_, rund_ in ZEICHNEN_UEBER:
        out.append(f'<path d="{_rund(pts_, rund_)}" stroke="{green if pax_ else black}" stroke-width="{3.6 if pax_ else 1.6}" fill="none"/>')
# Meterspur (Override "meterspur": Overpass-Datei mit gauge=1000) als eigene, braune Schicht ohne Verbindung zur Normalspur
MS_COL = "#9a5b1e"; MS_LEG = False
if OVR.get("meterspur") and os.path.exists(OVR["meterspur"]) and (not ARGS.bare or OVR.get("meterspur_cfg", {}).get("regional", True)):   # auch im Regionalplan (Hinweis Region NE 20.10. "Wo ist die Meterspur?")
    _msd = []
    for e in json.load(open(OVR["meterspur"]))["elements"]:
        if e.get("type") != "way" or e["tags"].get("railway") != "narrow_gauge": continue
        _msd.append((e["id"], e["tags"], [project(xy(g)) for g in e["geometry"]], e.get("nodes", [None] * len(e["geometry"]))))
    if os.environ.get("MS_DBG"):
        for i_, t_, sd_, _ in _msd: print("MS", i_, t_.get("railway:track_ref"), [(round(a), round(b)) for a, b in sd_])
    _ms_cfg = OVR.get("meterspur_cfg", {})
    _lmin = min(c["lane"] for c in C); _lmax = max(c["lane"] for c in C)
    # Bezugsgleis (track_ref, z. B. 11) wird waagrecht eine Ebene ausserhalb der Normalspur gezeichnet,
    # alles andere relativ dazu, quer gestaucht (m_pro_lane), durch die Normalspur hindurch begrenzt
    _ref = [sd_ for i_, t_, sd_, _ in _msd if t_.get("railway:track_ref") == str(_ms_cfg.get("bezug", ""))]
    _ref = sorted(p_ for r_ in _ref for p_ in r_)
    _rs = np.array([p_[0] for p_ in _ref]) if _ref else np.array([0.0]); _rd = np.array([p_[1] for p_ in _ref]) if _ref else np.array([0.0])
    _oben = (np.median(_rd) > 0)
    _y0 = Y(_lmax) - CFG["lane_px"] * _ms_cfg.get("abstand_lanes", 1.0) if _oben else Y(_lmin) + CFG["lane_px"] * _ms_cfg.get("abstand_lanes", 1.0)
    def _ms_y(s_, d_):
        q_ = (d_ - float(np.interp(s_, _rs, _rd))) * (1 if _oben else -1) / _ms_cfg.get("m_pro_lane", 10.0)
        q_ = max(q_, -_ms_cfg.get("max_innen", 0.6))
        return _y0 - q_ * CFG["lane_px"]
    def _ms_ok(s_, d_): return abs(d_ - float(np.interp(s_, _rs, _rd))) <= _ms_cfg.get("d_max", 40)   # Regel E8 (20.10.): Meterspur bis ~40 m neben der Normalspur
    def _dp(pts, eps=1.5):            # Douglas-Peucker: Messrauschen weg, Knicke bleiben
        if len(pts) < 3: return pts
        (ax, ay), (bx, by) = pts[0], pts[-1]; L = math.hypot(bx - ax, by - ay) or 1e-9
        dd = [abs((bx - ax) * (ay - y) - (ax - x) * (by - ay)) / L for x, y in pts[1:-1]]
        i = int(np.argmax(dd)) + 1
        return _dp(pts[:i + 1], eps)[:-1] + _dp(pts[i:], eps) if dd[i - 1] > eps else [pts[0], pts[-1]]
    _mp = {True: [], False: []}; _aus = _ms_cfg.get("ausfahrt_lanes", 0.8); MS_TXT = []
    for i_, t_, sd_, nn_ in _msd:
        q_ = []; raus = None
        for (s_, d_), mn_ in zip(sd_, nn_):
            if mn_ in home and mn_ in SD:      # gemeinsamer Knoten mit der Normalspur (Rollbockanlage Ins): dort anschliessen
                q_.append((xpos(mn_, SD[mn_][0]), ypos(mn_))); continue
            if not (CFG["s_min"] - 1 <= s_ <= CFG["s_max"] + 1) or not _ms_ok(s_, d_):
                if q_: break
                continue
            y_ = _ms_y(s_, d_)
            if abs(y_ - _y0) > _aus * CFG["lane_px"] and (_y0 - y_) * (1 if _oben else -1) > 0:   # Strecke verlässt den Bahnhof quer: schematischer Abgang
                if q_: raus = q_[-1]
                if q_: break
                continue
            q_.append((X(s_), y_))
        # Rollbockanlage (Ins, Hinweis 14.10.): vom gemeinsamen Knoten in derselben 60°-Schrägen weiter bis auf die Meterspurebene
        if _ms_cfg.get("rollbock_diag") and q_ and nn_ and nn_[0] in home:
            mx_, my_ = q_[0]; tx_ = mx_ + abs(my_ - _y0) / math.tan(math.radians(60))
            q_ = [q_[0], (tx_, _y0)] + [p_ for p_ in q_[1:] if p_[0] > tx_ + 2]
        if os.environ.get("MS_DBG"): print("MSQ", i_, [(round(a), round(b)) for a, b in q_][:6], raus)
        q_ = _dp(q_)
        hpt = t_.get("service") is None
        if raus is not None and len(q_) >= 1:
            dx_ = 1 if len(q_) < 2 or q_[-1][0] >= q_[-2][0] else -1
            # Hinweis Ins 25.10. («fast 90 Grad und dann wieder schräg»): Abgang ab dem letzten Punkt auf der
            # Meterspurebene gerade unter 60° (W2), ohne das steile Zwischenstück, wo das Gleis die Ebene verlässt
            _qe = [p_ for p_ in q_ if abs(p_[1] - _y0) < 1.5]
            if _qe and _ms_cfg.get("abgang_60", True): q_ = q_[:q_.index(_qe[-1]) + 1]
            Lr = CFG["lane_px"] * _ms_cfg.get("ausfahrt_len", 1.2)
            _c, _s = (0.5, math.sqrt(3) / 2) if _ms_cfg.get("abgang_60", True) else (1 / math.sqrt(2), 1 / math.sqrt(2))
            x2, y2 = q_[-1][0] + dx_ * Lr * _c / _s, q_[-1][1] - (1 if _oben else -1) * Lr
            q_.append((x2, y2))
            ux, uy = dx_ * _c, -(1 if _oben else -1) * _s
            out.append(f'<path d="M{x2 + ux * 9:.1f},{y2 + uy * 9:.1f}L{x2 - uy * 4:.1f},{y2 + ux * 4:.1f}L{x2 + uy * 4:.1f},{y2 - ux * 4:.1f}Z" fill="{MS_COL}" stroke="none"/>')
            if _ms_cfg.get("ziel"):
                for k_, z_ in enumerate(_ms_cfg["ziel"].split("|")):
                    MS_TXT.append(f'<text x="{x2 + dx_ * 14:.1f}" y="{y2 - (8 if _oben else -22) + 24 * k_ - (24 * (len(_ms_cfg["ziel"].split("|")) - 1) if _oben else 0):.1f}" font-size="20" text-anchor="{"start" if dx_ > 0 else "end"}" fill="{MS_COL}">{z_}</text>')
        if len(q_) >= 2: _mp[hpt].append(_rund(q_, 6.0))
    if _mp[True] or _mp[False]:
        MS_LEG = True
        if _mp[False]: out.append(f'<path d="{" ".join(_mp[False])}" stroke="{MS_COL}" stroke-width="1.6"/>')
        if _mp[True]: out.append(f'<path d="{" ".join(_mp[True])}" stroke="{MS_COL}" stroke-width="3.6"/>')
    # Perron am Bezugsgleis (OSM-Perron, der höchstens 30 m neben dem Meterspurgleis liegt; Ins Gleis 11)
    if _ref and _ms_cfg.get("perron", True):
        for e in PLAT:
            pp_ = [project(xy(g)) for g in e["geometry"]]
            dd_ = [d_ - float(np.interp(s_, _rs, _rd)) for s_, d_ in pp_]
            a_, b_ = max(min(p_[0] for p_ in pp_), _rs.min()), min(max(p_[0] for p_ in pp_), _rs.max())
            if b_ - a_ < 20 or abs(np.mean(dd_)) > 30: continue
            yb_ = _y0 + (11 if (np.mean(dd_) < 0) == _oben else -11)
            MS_TXT.insert(0, f'<rect x="{X(a_):.1f}" y="{yb_ - 4:.1f}" width="{X(b_) - X(a_):.1f}" height="8" rx="1.5" fill="{MS_COL}"/>')      # Meterspur-Perron braun (Hinweis Region NE 22.10.)
    # Gleisnummer des Bezugsgleises
    if _ref and _ms_cfg.get("bezug"):
        _xm = X(float(np.median(_rs)))
        MS_TXT.append(f'<rect x="{_xm - 13:.1f}" y="{_y0 - 8:.1f}" width="26" height="16" fill="#fff" stroke="none"/>'
                      f'<text x="{_xm:.1f}" y="{_y0 + 6.5:.1f}" font-size="19" text-anchor="middle" fill="{MS_COL}">{_ms_cfg["bezug"]}</text>')
    out.append('</g>'); out.extend(MS_TXT); out.append('<g fill="none" stroke-linecap="round" stroke-linejoin="round">')
out.append('</g>')
# Perrons laut Override: zwischen zwei Gleisen oder aussen an einem Gleis
def ref_span(r):
    ss_ = [x for sg in segs if sg["ref"] == r for x in (sg["s0"], sg["s1"])]
    if CFG.get("perron_nur_gerade"):       # Perron nur, wo das Gleis gerade auf seiner Ebene liegt (Neuchâtel 6/7, 19.10.)
        _g = [x for sg in segs if sg["ref"] == r and sg["flat"] and sg["id"] in seglane
              and all(abs(ypos(n_) - Y(seglane[sg["id"]])) < 0.5 for n_ in (sg["nodes"][0], sg["nodes"][-1])) for x in (sg["s0"], sg["s1"])]
        if _g: ss_ = _g
    if not ss_: return None
    lanes_ = [seglane[sg["id"]] for sg in segs if sg["ref"] == r and sg["id"] in seglane]
    return min(ss_), max(ss_), (max(set(lanes_), key=lanes_.count) if lanes_ else None)
_PER = []
for pl in OVR.get("platforms", []):
    if "between" in pl:
        A_, B_ = ref_span(pl["between"][0]), ref_span(pl["between"][1])
        if not (A_ and B_) or A_[2] is None or B_[2] is None: continue
        a_, b_ = max(A_[0], B_[0]), min(A_[1], B_[1]); yb = (Y(A_[2]) + Y(B_[2])) / 2
        lo_, hi_ = sorted((A_[2], B_[2]))
        blocked = sorted((c["s0"] - 10, c["s1"] + 10) for c in C if lo_ < c["lane"] < hi_ and c["s1"] > a_ and c["s0"] < b_)
        free, cur = [], a_
        for u, v in blocked:
            if u > cur: free.append((cur, min(u, b_)))
            cur = max(cur, v)
        if cur < b_: free.append((cur, b_))
        if not free: continue
        a_, b_ = max(free, key=lambda f: f[1] - f[0])
        if "s" in pl: a_, b_ = max(a_, pl["s"][0]), min(b_, pl["s"][1])
    else:
        A_ = ref_span(pl["outer"])
        if not A_ or A_[2] is None: continue
        a_, b_ = A_[0], A_[1]
        if "s" in pl: a_, b_ = max(a_, pl["s"][0]), min(b_, pl["s"][1])
        others = [c["lane"] for c in C if c["s0"] < (a_ + b_) / 2 < c["s1"] and c["lane"] != A_[2]]
        below = not any(l < A_[2] for l in others) if pl.get("side") is None else pl["side"] == "below"
        yb = Y(A_[2]) + (11 if below else -11)
    m_ = 0.12 * (b_ - a_); a_, b_ = a_ + m_, b_ - m_
    _PER.append([a_, b_, yb])
# Override "perron_einheitlich" (Olten 14.10.: "Perrons alle etwa gleich lang"): gemeinsame Mitte und Länge, soweit Platz
_PE = OVR.get("perron_einheitlich")
if isinstance(_PE, dict) and _PER:      # {"mitte_px", "laenge_px"}: alle Perrons gleich lang an derselben Stelle (Olten 15.10.)
    _Xs = lambda px_: Xm_inv(px_ - CFG["margin_x"] + Xm(s_lo))
    for p_ in _PER: p_[0], p_[1] = _Xs(_PE["mitte_px"] - _PE["laenge_px"] / 2), _Xs(_PE["mitte_px"] + _PE["laenge_px"] / 2)
elif _PE and _PER:
    _L = float(np.median([b - a for a, b, _ in _PER])); _M = float(np.median([(a + b) / 2 for a, b, _ in _PER]))
    for p_ in _PER:
        lo_, hi_ = p_[0], p_[1]; L_ = min(_L, hi_ - lo_)
        c_ = min(max(_M, lo_ + L_ / 2), hi_ - L_ / 2); p_[0], p_[1] = c_ - L_ / 2, c_ + L_ / 2
for a_, b_, yb in _PER:
    out.append(f'<rect x="{X(a_):.1f}" y="{yb - 4:.1f}" width="{X(b_) - X(a_):.1f}" height="8" rx="1.5" fill="{green}"/>')
# Override "perrons_px" [[x0, x1, y], ...]: Perrons in Pixeln, für von Hand gezeichnete Pläne (Chambrelien 15.10.)
for x0_, x1_, y_ in OVR.get("perrons_px", []):
    out.append(f'<rect x="{x0_:.1f}" y="{y_ - 4:.1f}" width="{x1_ - x0_:.1f}" height="8" rx="1.5" fill="{green}"/>')
# Override "nummern_px" [[text, x, y], ...]: Gleisnummern in Pixeln (Chambrelien 15.10.)
for t_, x_, y_ in OVR.get("nummern_px", []):
    out.append(f'<rect x="{x_ - 13:.1f}" y="{y_ - 8:.1f}" width="26" height="16" fill="#fff" stroke="none"/>'
               f'<text x="{x_:.1f}" y="{y_ + 6.5:.1f}" font-size="19" text-anchor="middle" fill="{green}">{t_}</text>')
# Perrons aus OSM: Balken zwischen den beiden Gleisen, an denen der Perron real liegt
for e in ([] if OVR.get("platforms") is not None else PLAT):
    pts = [project(xy(g)) for g in e["geometry"]]
    ss_ = [p[0] for p in pts]; dd_ = [p[1] for p in pts]
    a_, b_ = max(min(ss_), CFG["s_min"]), min(max(ss_), CFG["s_max"])
    if b_ - a_ < 20 or abs(np.mean(dd_)) > CFG["d_lim"]: continue
    sm_, dm_ = (a_ + b_) / 2, float(np.mean(dd_))
    rows = sorted((d_at(c, sm_), c["lane"]) for c in C if c["s0"] <= sm_ <= c["s1"])
    up = [r for r in rows if r[0] > dm_]; dn = [r for r in rows if r[0] < dm_]
    if up and dn and up[0][1] != dn[-1][1]:
        yb = (Y(up[0][1]) + Y(dn[-1][1])) / 2
    elif up: yb = Y(up[0][1]) + 11
    elif dn: yb = Y(dn[-1][1]) - 11
    else: continue
    out.append(f'<rect x="{X(a_):.1f}" y="{yb - 4:.1f}" width="{X(b_) - X(a_):.1f}" height="8" rx="1.5" fill="{green}"/>')
# Doppelkreuzungsweichen (OSM railway:switch=double_slip): X mit den beiden Bogenverbindungen
from svgpathtools import parse_path as _pp
def _arm(d, nx_, ny_, reach=26):
    """Richtung eines gezeichneten Arms ab dem Knoten, gemessen in 'reach' px Abstand (hinter der Ausrundung)"""
    p = _pp(d); best = None
    for sub in p.continuous_subpaths():
        L_ = sub.length()
        if L_ < 1e-6: continue
        for t_ in (0.0, 1.0):
            z = sub.point(t_)
            if abs(z.real - nx_) < 1.5 and abs(z.imag - ny_) < 1.5:
                r_ = min(reach, L_)
                q = sub.point(sub.ilength(r_)) if t_ == 0 else sub.point(sub.ilength(L_ - r_))
                v = np.array([q.real - nx_, q.imag - ny_]); n_ = np.linalg.norm(v)
                if n_ > 1e-6: best = v / n_
    return best
def _dkw_fallback(n, nx_, ny_, hp_):
    """DKW ohne gerade Kreuzung im Plan: Standardsymbol nach der Lage der Schrägen (links/rechts, oben/unten)"""
    _dg = [x for x in segs if not x["flat"] and n in (x["nodes"][0], x["nodes"][-1])]
    _e = []
    for x in _dg:
        o = x["nodes"][-1] if x["nodes"][0] == n else x["nodes"][0]
        if o in SD: _e.append((xpos(o, SD[o][0]), ypos(o)))
    _l = [e for e in _e if e[0] < nx_ - 2]; _r = [e for e in _e if e[0] > nx_ + 2]
    if not (_l and _r): return False
    sa_ = np.sign(_l[0][1] - ny_); sb_ = np.sign(_r[0][1] - ny_)
    if not (sa_ and sb_ and sa_ != sb_): return False
    c0 = np.array([nx_, ny_])
    out.append(_dkw_klammer(c0, (-1, 0), (0.5, 0.866 * sb_), hp_)); out.append(_dkw_klammer(c0, (1, 0), (-0.5, 0.866 * sa_), hp_))
    return True
_dbg = dict(DBG)
for n, t in list(ntag.items()) + [(n_, {"railway:switch": "double_slip"}) for n_ in ALS_DKW if n_ not in ntag]:
    if (t.get("railway:switch") != "double_slip" and n not in ALS_DKW) or n not in home: continue
    if n in {int(a) for a, _ in OVR.get("dkw_symbol", [])}: continue      # Symbol per Override, nicht doppelt zeichnen
    if n in R45_DKW:      # Regel 45: Symbol am Schnittpunkt der geraden Kette mit der Ebene der DKW
        x45, y45, sa_, sb_, hp_ = R45_DKW[n]; c0 = np.array([x45, y45])
        out.append(_dkw_klammer(c0, (-1, 0), (0.5, 0.866 * sb_), hp_)); out.append(_dkw_klammer(c0, (1, 0), (-0.5, 0.866 * sa_), hp_))
        continue
    if n in R44_DKW:      # gerade durchlaufende Schräge (Regel 44): Klammern in den beiden stumpfen Winkeln
        sa_, sb_, hp_ = R44_DKW[n]; c0 = np.array([xpos(n, SD[n][0]), ypos(n)])
        out.append(_dkw_klammer(c0, (-1, 0), (0.5, 0.866 * sb_), hp_)); out.append(_dkw_klammer(c0, (1, 0), (-0.5, 0.866 * sa_), hp_))
        continue
    nx_, ny_ = xpos(n, SD[n][0]), ypos(n)
    arms = []
    for sg in segs:
        if n in (sg["nodes"][0], sg["nodes"][-1]) and sg["id"] in _dbg:
            a_ = _arm(_dbg[sg["id"]], nx_, ny_)
            if a_ is not None: arms.append((a_, sg["pax"]))
    if ARGS.dbg and len(arms) != 4: print("DKW?", n, len(arms))
    _hpn = any(x["pax"] for x in segs if n in (x["nodes"][0], x["nodes"][-1]))
    if len(arms) != 4:
        _dkw_fallback(n, nx_, ny_, _hpn); continue
    # nur echte Kreuzung (zwei Linien laufen durch): je zwei Arme entgegengesetzt
    opp = [(i_, j_) for i_ in range(4) for j_ in range(i_ + 1, 4) if arms[i_][0] @ arms[j_][0] < -0.85]
    if ARGS.dbg: print("DKW", n, len(arms), [round(float(arms[i_][0] @ arms[j_][0]), 2) for i_ in range(4) for j_ in range(i_ + 1, 4)])
    if len(opp) != 2 and not RU.get("dkw_alt", False):
        _dkw_fallback(n, nx_, ny_, any(a[1] for a in arms)); continue
    if len(opp) != 2 or RU.get("dkw_alt", False):
        for i_ in range(4):
            for j_ in range(i_ + 1, 4):
                ang_ = math.degrees(math.acos(max(-1, min(1, arms[i_][0] @ arms[j_][0]))))
                if 100 < ang_ < 170:
                    a_, b_ = arms[i_][0], arms[j_][0]; col = green if (arms[i_][1] and arms[j_][1]) else black
                    p0 = (nx_ + a_[0] * 14, ny_ + a_[1] * 14); p1 = (nx_ + b_[0] * 14, ny_ + b_[1] * 14)
                    out.append(f'<path d="M{p0[0]:.1f},{p0[1]:.1f}Q{nx_:.1f},{ny_:.1f} {p1[0]:.1f},{p1[1]:.1f}" fill="none" stroke="{col}" stroke-width="1.4"/>')
        continue
    # DKW-Symbol (D. Eckenstein, 13.10.): je eine Klammer in den beiden stumpfen Winkeln, frei neben den Gleisen
    for i_ in range(4):
        for j_ in range(i_ + 1, 4):
            if (i_, j_) in opp: continue
            a_, b_ = arms[i_][0], arms[j_][0]
            if a_ @ b_ > -0.05: continue                     # spitzer Winkel: keine Bogenverbindung
            # ein Standard je DKW: liegt sie an einem Hauptgleis, ganzes Symbol gross und hellgrün (Hinweis Ins 14.10.)
            out.append(_dkw_klammer(np.array([nx_, ny_]), a_, b_, any(a[1] for a in arms), all(a[1] for a in arms)))
# Override "dkw_symbol": [[knoten, richtung]] - DKW-Symbol an einem Knoten erzwingen (beide Klammern), richtung +1 = Schräge
# von oben links nach unten rechts, -1 = von unten links nach oben rechts (Aarburg Süd: nur eine Klammer sichtbar)
for _n, _sg_ in OVR.get("dkw_symbol", []):
    if _n not in SD: continue
    c0 = np.array([xpos(_n, SD[_n][0]), ypos(_n)]); _hp_ = any(o["pax"] for o in segs if _n in o["nodes"])
    for a_, b_ in (((-1, 0), (0.5, 0.866 * _sg_)), ((1, 0), (-0.5, -0.866 * _sg_))):
        DKW_EXTRA.append(_dkw_klammer(c0, a_, b_, _hp_, _alle_pax(_n)))
# Override "dkw_px": [{"x", "y", "pax", "arme": [[[ax, ay], [bx, by]], ...]}] - DKW-Symbol an einer Pixelstelle mit frei
# gewählten Armpaaren (stumpfe Winkel), für von Hand gezeichnete Kreuzungen zweier Schrägen (Onnens-Bonvillars 20.10.)
for _dp in OVR.get("dkw_px", []):
    c0 = np.array([float(_dp["x"]), float(_dp["y"])])
    for a_, b_ in _dp["arme"]:
        DKW_EXTRA.append(_dkw_klammer(c0, a_, b_, bool(_dp.get("pax")), bool(_dp.get("rund_pax", _dp.get("pax")))))
out.extend(DKW_EXTRA)
for x, y, pax in dots:
    out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.5 if pax else 3.2}" fill="{green if pax else black}"/>')
for x, y, a in STUBS:
    c, s_ = math.cos(a), math.sin(a)
    pts = [(x + 9 * c, y + 9 * s_), (x - 4 * s_, y + 4 * c), (x + 4 * s_, y - 4 * c)]
    out.append('<path d="M' + "L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + f'Z" fill="{black}"/>')
# Pfeile, die auf dem Ende eines Hauptgleises liegen (Nebengleis läuft im selben Punkt aus), weglassen
# (Hinweise Zofingen/Schönenwerd: "Pfeil direkt auf dem Streckengleis")
_pax_ends = []
for sg in segs:
    if sg["pax"] and sg["id"] in seglane:
        for n_ in (sg["nodes"][0], sg["nodes"][-1]): _pax_ends.append((xpos(n_, SD[n_][0]), Y(seglane[sg["id"]])))
    elif sg["pax"]:     # Gleis ohne eigene Ebene (Olten West, 410 Gl. 2): Knotenhöhe nehmen
        for n_ in (sg["nodes"][0], sg["nodes"][-1]):
            if n_ in SD: _pax_ends.append((xpos(n_, SD[n_][0]), ypos(n_)))
_pax_y = {round(Y(seglane[sg["id"]])) for sg in segs if sg["pax"] and sg["id"] in seglane} | {round(py) for px, py in _pax_ends}
arrows = [a for a in arrows if not (round(a[1]) in _pax_y and any(abs(a[0] - px) < 30 and abs(a[1] - py) < 1.5 for px, py in _pax_ends))]
for x, y, dr in arrows:
    out.append(f'<path d="M{x:.1f},{y - 4:.1f}L{x + 9 * dr:.1f},{y:.1f}L{x:.1f},{y + 4:.1f}Z" fill="{black}"/>')
for r, (l, a, b, _) in labels.items():
    xm = min(max(pax_mid, X(a) - X(s_lo) + CFG["margin_x"] + 30 and pax_mid), 1e9)
    xs = min(max(X(pax_mid if a <= pax_mid <= b else (a + b) / 2), X(a) + 20), X(b) - 20)
    y = Y(l)
    out.append(f'<rect x="{xs - 13:.1f}" y="{y - 8:.1f}" width="26" height="16" fill="#fff"/>')
    out.append(f'<text x="{xs:.1f}" y="{y + 6.5:.1f}" font-size="19" text-anchor="middle" fill="{green}">{r}</text>')
TITLE_X = X(pax_mid)

json.dump(dict(W=W, H=H, s_lo=s_lo, maxlane=maxlane,
               ends=[(sg["id"], X(sg["s0"]), X(sg["s1"]), ypos(sg["nodes"][0]), ypos(sg["nodes"][-1]), sg["cut0"], sg["cut1"], sg["pax"], sg["tags"].get("ref")) for sg in segs if sg["pax"] and (sg["cut0"] or sg["cut1"])]),
          open("meta.json", "w"))
SIDE = []
for sg in segs:
    if not sg["pax"]: continue
    if not (sg["cut0"] or sg["cut1"]): continue
    for end in (0, 1):
        if not sg["cut%d" % end]: continue
        n = sg["nodes"][-1 if end else 0]
        s_, d_ = SD[n]
        x, y = (xpos(n, sg["s1"]), ypos(n)) if end else (xpos(n, sg["s0"]), ypos(n))
        if ((abs(d_) > d_lim_at(s_) - 25 and not sg["flat"]) or sg["way"] in OVR.get("seitlich", [])) and sg["way"] not in OVR.get("als_rand", []):   # seitlich abzweigende Strecke; "als_rand": Abgang am Längsrand (Regionalvariante Olten Ost 20.10.)
            SIDE.append([x, y, end, -1 if d_ > 0 else 1, sg, n])
        else:
            if sg["way"] in ZEICHNEN_PORT: x, y = ZEICHNEN_PORT[sg["way"]]     # neu gezeichneter Abgang (Thun Gürbetal)
            _c, _w = (green, 3.6) if sg["pax"] else (black, 1.6)
            if sg.get("schmal"): _c = MS_BRAUN
            _xs = x - (1 if end else -1) * 22
            if sg["way"] in ZEICHNEN_PORT_AB and (ZEICHNEN_PORT_AB[sg["way"]][0] - _xs) * (1 if end else -1) > 0:
                _xs = ZEICHNEN_PORT_AB[sg["way"]][0]     # neu gezeichneter Abgang: Randstück nicht vor den Linienanfang (Chambrelien 224, grüner Stummel)
            # Gleis knickt vor dem Ende des Randstücks ab (Olten West, Rothrist): Randstück nur bis zum Beginn der Ausrundung
            for _i, _d in DBG:
                if _i != sg["id"]: continue
                _m = re.match(r"M%s,%s((?:H-?[\d.]+)+)" % (re.escape(f"{x:.1f}"), re.escape(f"{y:.1f}")), _d)
                _m2 = re.search(r"(?:^|\s|M)(-?[\d.]+),%sQ" % re.escape(f"{y:.1f}"), _d) if not _m else None
                if _m:
                    _hl = float(re.findall(r"H(-?[\d.]+)", _m[1])[-1])
                    if _d[_m.end():_m.end() + 1] in ("Q", "L", "M", " ") and (_xs - _hl) * (_xs - x) > 0 and abs(_hl - x) < abs(_xs - x):
                        _xs = _hl
            out.append(f'<path d="M{_xs:.1f},{y:.1f}H{x:.1f}" stroke="{_c}" stroke-width="{_w}" fill="none"/>')   # Abgang bis an den Rand
            PORTS.append(dict(kind="edge", x=x, y=y, dx=1 if end else -1, dy=0, ref=exit_ref(sg), town=exit_town(sg, n),
                              bearing=port_bearing(sg, n), lat=LL[n][0], lon=LL[n][1], pax=sg["pax"], way=sg["way"]))
            EXITS.append((x + (12 if end else -12), y + 6, exit_ref(sg), "start" if end else "end", exit_town(sg, n)))
for x, y, end, dy, sg, n in SIDE:
    _fil = False
    if sg["way"] in ZEICHNEN_PORT:
        x, y = ZEICHNEN_PORT[sg["way"]]; _fil = True
    # Regel 39: seitlicher Streckenabgang mit Ausrundung (kein harter Knick, Aarburg 451)
    if RU.get("r39", True) and not _fil:
        dx_ = -(1 - 2 * end); r_ = 9.0
        # alle geraden Stücke auf dieser Ebene, die (±1.5 px) am Abgangspunkt enden, bis zum Anfang der Ausrundung kürzen;
        # zu kurze Reststücke entfallen (sonst kurze Doppelung von Gleisen, Aarburg Gl. 1)
        pat_ = re.compile(r"M([-\d.]+),%s((?:H[-\d.]+)*)H([-\d.]+)(?=[\s\"MLQ]|$)" % re.escape(f"{y:.1f}"))
        _xe = x - dx_ * r_
        # Gerade, die am Abgangspunkt weiterläuft (durchgehendes Gleis), nicht kürzen (Ins: Lücke im Gleis nach Kerzers)
        _starts = [float(a) for a, b_ in re.findall(r"M(-?[\d.]+),%s(H-?[\d.]+)" % re.escape(f"{y:.1f}"), out[_GREEN_IDX])
                   if abs(float(a) - x) < 1.5 and (float(b_[1:]) - float(a)) * dx_ > 2]
        def _cut(m_):
            x0_, xe_ = float(m_.group(1)), float(m_.group(3))
            if abs(xe_ - x) > 1.5 or _starts: return m_.group(0)
            if m_.string[m_.end():m_.end() + 1] in ("L", "Q"): return m_.group(0)   # Gerade gehört zu einer Kurve: nicht anfassen
            if (_xe - x0_) * dx_ <= 0.5: return ""
            return f"M{x0_:.1f},{y:.1f}{m_.group(2)}H{_xe:.1f}"
        new_, k_ = pat_.subn(_cut, out[_GREEN_IDX])
        k_ = k_ if (new_ != out[_GREEN_IDX] or _starts) else 0
        if not k_:
            # reine Ecke: das Gleis beginnt am Abgangspunkt und läuft vom Abgang weg (Thun West, Linie 430): Anfang kürzen, ausrunden
            _ys = re.escape(f"{y:.1f}")
            pat2_ = re.compile(r"M(-?[\d.]+),%s((?:H-?[\d.]+|L-?[\d.]+,%s)+)" % (_ys, _ys))
            def _cut2(m_):
                x0_ = float(m_.group(1)); hs_ = [float(v) for v in re.findall(r"[HL](-?[\d.]+)", m_.group(2))]
                if abs(x0_ - x) > 1.5 or (hs_[-1] - x0_) * dx_ >= 0 or abs(hs_[-1] - x0_) < r_ + 2: return m_.group(0)
                return f"M{x0_ - dx_ * r_:.1f},{y:.1f}" + m_.group(2)
            new2_, k2_ = pat2_.subn(_cut2, out[_GREEN_IDX])
            if new2_ != out[_GREEN_IDX]: new_, k_ = new2_, 1
        if k_:
            out[_GREEN_IDX] = new_
            xf_, yf_ = x + dx_ * 0.5 * r_, y + dy * 0.866 * r_
            out.append(f'<path d="M{x - dx_ * r_:.1f},{y:.1f}Q{x:.1f},{y:.1f} {xf_:.1f},{yf_:.1f}" stroke="{green}" stroke-width="3.6" fill="none"/>')
            # Verbindung, die genau im Eckpunkt beginnt (Murten Gl. 4 -> 3): Anfang auf die Ausrundung legen, sonst hängt sie
            # 2 px neben dem Abgang (Regel D. Eckenstein 20.10.: Stoss > 1 px ist ein Befund)
            _mx, _my = 0.25 * (x - dx_ * r_) + 0.5 * x + 0.25 * xf_, 0.25 * y + 0.5 * y + 0.25 * yf_
            out[_GREEN_IDX] = re.sub(r"M%s,%s(?:H%s)?(?=Q)" % (re.escape(f"{x:.1f}"), re.escape(f"{y:.1f}"), re.escape(f"{x:.1f}")),
                                     f"M{_mx:.1f},{_my:.1f}", out[_GREEN_IDX])
            x, y = xf_, yf_; _fil = True
    L = 105; x2, y2 = x - (1 - 2 * end) * L * 0.5, y + dy * L * 0.866
    PORTS.append(dict(kind="side", x=x, y=y, dx=-(1 - 2 * end), dy=dy, ref=exit_ref(sg), town=exit_town(sg, n),
                      bearing=port_bearing(sg, n), lat=LL[n][0], lon=LL[n][1], pax=sg["pax"], way=sg["way"]))
    if not ARGS.bare:
        x0_ = x if _fil else xpos(n, sg["s1"] if end else sg["s0"])
        out.append(f'<path d="M{x0_:.1f},{y:.1f}L{x:.1f},{y:.1f}L{x2:.1f},{y2:.1f}" stroke="{green}" stroke-width="3.6" stroke-linecap="round" fill="none"/>')
    EXITS.append((x2, y2 + (-40 if dy < 0 else 44), exit_ref(sg), "middle", exit_town(sg, n)))
if ARGS.bare: EXITS = []
_town = {}
for e_ in EXITS:
    if e_[4]: _town.setdefault((e_[2], e_[3]), e_[4])
EXITS = [(x_, y_, r_, a_, t_ or _town.get((r_, a_))) for x_, y_, r_, a_, t_ in EXITS]
from shapely.geometry import LineString as _LS, box as _sbox
_LINES = [_LS(p_) for p_ in ZEICHNEN_LINIEN if len(p_) > 1]
for _sid, _d in DBG + [(None, d_) for d_ in svg_paths[False] if d_ not in dict(DBG).values()] + [(None, d_) for d_ in svg_paths[True]]:
    try:
        _p = _pp(_d); _pts = [(_p.point(t_).real, _p.point(t_).imag) for t_ in np.linspace(0, 1, max(3, int(_p.length() / 4)))]
        if len(_pts) > 1: _LINES.append(_LS(_pts))
    except Exception: pass
_LBOX = []
done = set()
# Gruppen: gleiche Linie/Richtung/Ziel, aber nur zusammenhängende Abgänge (kein fremder Abgang dazwischen)
_LGROUPS = []
for x, y, ref, anc, town in EXITS:
    gk = (ref, anc, town)
    if gk in done: continue
    done.add(gk)
    grp = sorted([e for e in EXITS if (e[2], e[3], e[4]) == gk], key=lambda e: e[1])
    sub = [grp[0]]
    for e in grp[1:]:
        if anc != "middle" and any(o[3] == anc and (o[2], o[4]) != (ref, town) and sub[-1][1] < o[1] < e[1] for o in EXITS):
            _LGROUPS.append((gk, sub)); sub = [e]
        else: sub.append(e)
    _LGROUPS.append((gk, sub))
for (ref, anc, town), grp in _LGROUPS:
    x = grp[0][0]; y = grp[0][1]
    ys = [e[1] for e in grp]
    if anc == "middle" and len(grp) > 1:      # Bündel seitlicher Abgänge (Olten, 4 Gleise Aarau): Beschriftung mittig unter allen
        x = sum(e[0] for e in grp) / len(grp); y = max(ys)
    yy = (min(ys) + max(ys)) / 2 if anc != "middle" else y
    arrow = "←" if anc == "end" or (anc == "middle" and x < W / 2) else "→"
    t2 = (f"{arrow} {town}" if arrow == "←" else f"{town} {arrow}") if town else ""
    lines2 = [l for l in ((ref[1:] if ref.startswith("~") else f"Linie {ref}") if ref else "", t2) if l]
    lines1 = [" ".join(lines2)] if len(lines2) > 1 else lines2
    xx = x if anc == "middle" else (min if anc == "end" else max)(e[0] for e in grp)
    def _box(x0, y0, lines):
        w_ = max(len(t) for t in lines) * 0.56 * 22; h_ = 26 * len(lines)
        xl = x0 - (w_ if anc == "end" else w_ / 2 if anc == "middle" else 0)
        top = y0 - 6 - 13 * (len(lines) - 1) - 17
        return _sbox(xl, top, xl + w_, top + h_)
    found = None
    for lines in (lines2, lines1):          # zweizeilig; wenn kein Platz: einzeilig (enge Abgänge)
        for dy_, dx_ in ((0, 0), (-28, 0), (28, 0), (-56, 0), (56, 0), (0, 40), (0, -40), (-28, 40), (-28, -40), (-84, 0), (84, 0)):
            if anc == "end" and dx_ > 0 or anc == "start" and dx_ < 0: continue
            if len(lines) == 1 and abs(dy_) > 28: continue
            bx_ = _box(xx + dx_, yy + dy_, lines)
            if not any(l.intersects(bx_) for l in _LINES) and not any(b.intersects(bx_) for b in _LBOX):
                found = (dy_, dx_, lines); break
        if found: break
    dy_, dx_, lines = found or (0, 0, lines1)
    _LBOX.append(_box(xx + dx_, yy + dy_, lines))
    for k, t in enumerate(lines):
        out.append(f'<text x="{xx + dx_:.1f}" y="{yy + dy_ - 6 + 26 * k - 13 * (len(lines) - 1):.1f}" font-size="22" text-anchor="{anc}" fill="{green}">{t}</text>')
# Titel unterhalb aller Gleise und Beschriftungen
_ys = [Y(0)] + [e[1] + 10 for e in EXITS] + [y_ for _, y_, _ in STUBS]
ty = max(_ys) + 60
if not ARGS.bare:
    out.append(f'<text x="{TITLE_X:.1f}" y="{ty:.1f}" font-size="38" font-weight="700" text-anchor="middle" fill="{green}">{CFG["title"]}</text>')
_seen = set(); _pp = []
for p_ in PORTS:                     # doppelte Abgänge (zwei Ways enden im selben Randpunkt) nur einmal
    k_ = (round(p_["x"]), round(p_["y"]), p_["dx"], p_["kind"])
    if k_ in _seen: continue
    _seen.add(k_); _pp.append(p_)
PORTS = _pp
# Anschlüsse nur aus dem Regionalplan-Lauf (--bare) oder dem Standardlauf schreiben: ein Prüflauf mit --out in eine Zwischendatei
# (spurplan_check aus ne_zusatz_update) überschrieb sonst die Anschlüsse der bare-Fassung (Auvernier 219, Hinweis 20.10.)
if ARGS.bare or ARGS.out in (None, f"{key}_spurplan.svg"):
    json.dump(dict(ports=PORTS, W=W, H=H, title=CFG["title"], x_lo=CFG["margin_x"], x_hi=W - CFG["margin_x"],
                   y_lo=CFG["margin_y"] - 40, y_hi=Y(0) + 20, ways=sorted({int(sg["way"]) for sg in segs})), open(f"{key}_ports.json", "w"))
H = max(H, ty + 30)
if DKW_FILLET:
    _gi = next((i_ for i_, o_ in enumerate(out) if f'stroke="{green}" stroke-width="3.6"/>' in o_ and o_.startswith('<path d="M')), None)
    if _gi is not None:
        _bl = [f_ for f_ in DKW_FILLET if f'stroke="{black}"' in f_]; _gr = [f_ for f_ in DKW_FILLET if f_ not in _bl]
        out[_gi:_gi] = _bl; _gi2 = _gi + len(_bl) + 1; out[_gi2:_gi2] = _gr
    else: out.extend(DKW_FILLET)
_ty = [float(v) for o_ in out if o_.startswith("<text") for v in re.findall(r' y="(-?[\d.]+)"', o_)]
_py = [float(v) for o_ in out if o_.startswith("<path") for v in re.findall(r"-?[\d.]+,(-?[\d.]+)", o_.split('d="', 1)[1].split('"', 1)[0])] if out else []
_Y0 = min(0.0, min(_ty, default=0.0) - 26, min(_py, default=0.0) - 10)   # Beschriftung/Linien oberhalb des Plans nicht abschneiden (Bern Westkopf)
if _Y0 < 0: out = [o_.replace('<rect width="100%" height="100%" fill="#fff"/>', f'<rect y="{_Y0:.0f}" width="100%" height="100%" fill="#fff"/>') for o_ in out]
out[0] = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {_Y0:.0f} {W:.0f} {H - _Y0:.0f}" width="{W:.0f}" height="{H - _Y0:.0f}" font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif">'
if os.environ.get("SPUR_IDS"):        # Fehlersuche: Way-Nummern an die Gleisstücke schreiben
    _sgw = {x["id"]: x for x in segs}
    for i_, d_ in DBG:
        _n = [float(a) for a in re.findall(r"-?[\d.]+", d_)]
        if len(_n) < 4 or i_ not in _sgw: continue
        _xy = list(zip(_n[0::2], _n[1::2])); mx_, my_ = _xy[len(_xy) // 2]
        out.append(f'<text x="{mx_:.1f}" y="{my_ - 2:.1f}" font-size="7" fill="#c00">{_sgw[i_]["way"]}{"/" + str(_sgw[i_]["ref"]) if _sgw[i_].get("ref") else ""}</text>')
out.append("</svg>")
open(CFG["out"], "w").write("\n".join(out))

# ---- Netzmodell (D. Eckenstein 25.10.: Gleise als Netz mit Koordinaten, Prüfungen rechnen darauf statt auf dem SVG)
# <bahnhof>_netz.json: Gleisstücke mit OSM-Knoten (Karte + Plan), Weichen, gezeichnete Perrons und Nummern, Abgänge,
# OSM-Perrons. Nur im Standardlauf (nicht --bare, nicht in eine Zwischendatei). Auswertung: netz_pruefung.py.
if not ARGS.bare and ARGS.out in (None, f"{key}_spurplan.svg"):
    _svg = "\n".join(out)
    _f = lambda v: round(float(v), 1)
    _kn = {}
    for sg in segs:
        for n_ in sg["nodes"]:
            if n_ in SD and n_ in LL and n_ not in _kn:
                _kn[n_] = dict(lat=LL[n_][0], lon=LL[n_][1], x=_f(xpos(n_, SD[n_][0])), y=_f(ypos(n_)) if n_ in home else None,
                               typ=ntag.get(n_, {}).get("railway"))
    _NETZ = dict(
        bahnhof=key, titel=CFG["title"], W=_f(W), H=_f(H),
        gleise=[dict(id=sg["id"], way=int(sg["way"]), knoten=[int(n_) for n_ in sg["nodes"] if n_ in _kn],
                     ebene=seglane.get(sg["id"]), y=_f(Y(seglane[sg["id"]])) if sg["id"] in seglane else None,
                     pax=bool(sg["pax"]), service=sg["tags"].get("service"), usage=sg["tags"].get("usage"),
                     ref=sg["tags"].get("ref"), gleis=sg["tags"].get("railway:track_ref"),
                     spur=sg["tags"].get("spur") or sg["tags"].get("gauge"), stillgelegt=bool(sg["tags"].get("disused")))
                for sg in segs],
        knoten={str(n_): v for n_, v in _kn.items()},
        weichen_osm=[dict(id=int(n_), lat=LL[n_][0], lon=LL[n_][1], im_plan=n_ in _kn)
                     for n_, t in ntag.items() if t.get("railway") == "switch" and n_ in LL and n_ in SD
                     and CFG["s_min"] <= SD[n_][0] <= CFG["s_max"] and abs(SD[n_][1]) <= CFG["d_lim"]],
        perrons=[dict(x0=_f(m.group(1)), y=_f(float(m.group(2)) + 4), x1=_f(float(m.group(1)) + float(m.group(3))))
                 for m in re.finditer(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="8" rx="1.5"', _svg)],
        nummern=[dict(text=m.group(3), x=_f(m.group(1)), y=_f(float(m.group(2)) - 6.5))
                 for m in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)" font-size="19" text-anchor="middle"[^>]*>([^<]+)</text>', _svg)],
        perrons_osm=[dict(way=int(e["id"]), name=e["tags"].get("name"), ref=e["tags"].get("ref"),
                          punkte=[[g["lat"], g["lon"]] for g in e["geometry"]]) for e in PLAT],
        abgaenge=[{k_: (v_ if not isinstance(v_, float) else round(v_, 5)) for k_, v_ in p_.items()} for p_ in PORTS])
    json.dump(_NETZ, open(f"{key}_netz.json", "w"), ensure_ascii=False, indent=0)
print("chains", len(C), "lanes", maxlane + 1, "segs", len(segs), "W", round(W), "H", round(H))

# ---- Anforderungen für die x-Entzerrung: Platz für jede Verbindung in Standardgeometrie
TAN = math.tan(math.radians(CFG["sw_angle"])); R2 = 2 * CFG["sw_radius"]
REQ = []
done_g = set()
for sg in segs:
    g = sg.get("group")
    if not sg["flat"] and g and id(g) not in done_g:
        done_g.add(id(g))
        if "anchors" in g[0]:
            A_ = g[0]["anchors"]
            for (s1_, l1_), (s2_, l2_) in zip(A_, A_[1:]):
                if s2_ - s1_ > 0.3: REQ.append((s1_, s2_, abs(LY(l2_) - LY(l1_)) / TAN, 1.0))
        else:
            a_, b_ = g[0]["nodes"][0], g[-1]["nodes"][-1]
            REQ.append((g[0]["s0"], g[-1]["s1"], abs(LY(home[b_]) - LY(home[a_])) / TAN + R2, 1.0))
    elif sg["flat"]:
        need = 0
        for n_ in (sg["nodes"][0], sg["nodes"][-1]):
            dl = abs(home[n_] - seglane[sg["id"]])
            if dl > 0.01 and n_ not in diag_dir: need += abs(LY(home[n_]) - LY(seglane[sg["id"]])) / TAN + R2
        if need: REQ.append((sg["s0"], sg["s1"], need + 4, 0.3))
# Regel 32: parallele Weichenverbindungen, die sich in der Höhe überschneiden, brauchen Längsabstand, damit sie
# mindestens einen Gleisabstand auseinander liegen (sonst wirken zwei Verbindungen wie eine)
if RU.get("r32", True):
    _G = []
    for g in {id(x["group"]): x["group"] for x in segs if not x["flat"] and x.get("group")}.values():
        if "anchors" in g[0] or "diag" not in g[0]: continue
        la_, lb_ = home[g[0]["nodes"][0]], home[g[-1]["nodes"][-1]]
        if abs(lb_ - la_) < 0.3: continue
        _G.append(((g[0]["diag"][0] + g[0]["diag"][1]) / 2, min(la_, lb_), max(la_, lb_), np.sign(lb_ - la_)))
    for i_, A_ in enumerate(_G):
        for B_ in _G[i_ + 1:]:
            if A_[3] != B_[3] or min(A_[2], B_[2]) - max(A_[1], B_[1]) < 0.3: continue
            if abs(A_[0] - B_[0]) > 80: continue
            a_, b_ = sorted((A_[0], B_[0]))
            if b_ - a_ > 0.3: REQ.append((a_, b_, CFG["lane_px"] / math.sin(math.radians(CFG["sw_angle"])) + 4, 0.5))
for e in PLAT:
    ps_ = [project(xy(g))[0] for g in e["geometry"]]
    a_, b_ = max(min(ps_), CFG["s_min"]), min(max(ps_), CFG["s_max"])
    if b_ - a_ > 20: REQ.append((a_, b_, 0.6 * (b_ - a_) * CFG["px_per_m"], 0.0))
for _a, _b, _px in OVR.get("platz", []):      # Override "platz": Mindestbreite zwischen zwei Knoten (Kerzers: Kreuzung)
    if _a in SD and _b in SD: REQ.append((min(SD[_a][0], SD[_b][0]), max(SD[_a][0], SD[_b][0]), _px, 2.0))
json.dump(dict(req=REQ, s_min=CFG["s_min"], s_max=CFG["s_max"], px_per_m=CFG["px_per_m"], warp_min=CFG.get("warp_min", 0.15),
               nodes=sorted({float(SD[n][0]) for sg in segs for n in sg["nodes"]})), open(CFG["req_file"], "w"))

# ---- Diagnose
if ARGS.dbg:
    for sg in segs:
        if sg["pax"] and (sg["cut0"] or sg["cut1"]):
            print("CUT", sg["way"], sg["tags"].get("ref"), sg["tags"].get("railway:track_ref"), "s %.0f-%.0f"%(sg["s0"],sg["s1"]), "d %.1f..%.1f"%(sg["p"][0,1],sg["p"][-1,1]), sg["cut0"], sg["cut1"], "x %.0f-%.0f"%(X(sg["s0"]),X(sg["s1"])), "y", ypos(sg["nodes"][0]), ypos(sg["nodes"][-1]))
    for sg in segs:
        if sg["pax"] and 1500<X(sg["s0"])*1.0<1700 or (sg["pax"] and 1500<X(sg["s1"])<1700):
            print("Z", sg["way"], sg["tags"].get("railway:track_ref"), sg["flat"], "x %.0f-%.0f"%(X(sg["s0"]),X(sg["s1"])), "d %.1f..%.1f"%(sg["p"][0,1],sg["p"][-1,1]), "y", ypos(sg["nodes"][0]), ypos(sg["nodes"][-1]), seglane.get(sg["id"]))
