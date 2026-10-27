"""
Netzplan mit eingebetteten Spurplänen (Prinzip Dreieck Kerzers–Ins–Murten, vollautomatisch).

1. Topologie bereinigen (wie netz_layout.py); Bahnhöfe mit Spurplan = starre Kästen (waagrecht).
   Bahnhöfe, deren Gleise schon im Plan eines grösseren Nachbarn liegen, werden Halte.
2. Jede Netzkante an einem Bahnhof wird einer Anschlussgruppe im Spurplan zugeordnet
   (Peilung Strecke ↔ Peilung Anschluss, Linie als Zusatzkriterium). Daraus: Ankerpunkt im Kasten
   und Austrittsrichtung (rechts, links oder schräg).
3. Kantenrichtungen: 0/60/90/120° (+Gegenrichtungen); an Ankern nur Richtungen, die nicht in den
   Bahnhof zurückführen (±60° um die Austrittsrichtung).
4. Ausgleichsrechnung: Unbekannte = Kastenmittelpunkte und Punktknoten; Kantenendpunkte = Mittelpunkt
   + Anker. Richtung exakt, Länge ~ L_geo^0.75, schwacher Zug zur Geografie. Überlappen Kästen,
   wird der Massstab vergrössert.
5. Zeichnen: Spurpläne, je Strecke k parallele Gleise exakt an die Anschlüsse, Halte, Kreuzungsstellen,
   Abgänge.
Aufruf: python3 netz_plan.py olten_region "Region Olten" ausgabe.svg
"""
import json, math, sys, os, re, unicodedata, collections
import numpy as np
def _cr(a, b): return float(a[0] * b[1] - a[1] * b[0])

NAME, TITLE, OUTF = sys.argv[1], sys.argv[2], sys.argv[3]
GEO_W = float(os.environ.get("GEO_W", "0.03"))
CFG = dict(S=0.42, lane=24, scale=0.30, len_pow=0.75, merge_station_m=1250, merge_junction_m=420,
           drop_end_m=700, snap_end_m=150, cover_m=1300, stub=14, R=9, min_len=dict(inset=60, halt=55, junction=45, exit=60, via=40),
           box_gap=30)
G, BK = "#00862f", "#111"
TAN60 = math.tan(math.radians(60))
TG = CFG["lane"] * CFG["S"]                     # Gleisabstand Strecke = Ebenenabstand im Spurplan
T = json.load(open(f"{NAME}_topologie.json"))
def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")
nodes = {n["id"]: dict(n) for n in T["nodes"]}
# Lage "knoten_bahnhof": {"#<id>": "Name"} – ein Abzweig der Topologie ist ein Bahnhof mit eigenem Spurplan
# (27.10.2026: Abzweig #54 = Neuchâtel Vauseyon, Hinweis 2ayi)
_L00 = json.load(open(f"{NAME}_lage.json")) if os.path.exists(f"{NAME}_lage.json") else {}
for _k, _nm in _L00.get("knoten_bahnhof", {}).items():
    if int(_k.lstrip("#")) in nodes: nodes[int(_k.lstrip("#"))].update(name=_nm, kind="station")
edges = [dict(e) for e in T["edges"]]
def dist(a, b): return math.hypot(nodes[a]["x"] - nodes[b]["x"], nodes[a]["y"] - nodes[b]["y"])
def relabel(old, new):
    for e in edges:
        if e["a"] == old: e["a"] = new
        if e["b"] == old: e["b"] = new
    nodes.pop(old, None)
def drop_loops():
    global edges
    edges = [e for e in edges if e["a"] != e["b"]]
    uniq = {}
    for e in edges:
        k = tuple(sorted((e["a"], e["b"]))) + (e.get("_eigen"),)     # "_eigen": eigene Strecke, nicht mit paralleler zusammenlegen (531 Olten, 15.10.)
        if k in uniq:
            u = uniq[k]; u["tracks"] = max(u["tracks"], e["tracks"]); u["refs"] = sorted(set(u["refs"]) | set(e["refs"]))
            if e["length"] < u["length"]: u["geom"], u["length"] = (e["geom"] if e["a"] == u["a"] else e["geom"][::-1]), e["length"]
        else: uniq[k] = e
    edges = list(uniq.values())

# ------------------------------------------------------------------ 1. Bereinigen, Kästen
PORTS = {}
L0 = json.load(open(f"{NAME}_lage.json")) if os.path.exists(f"{NAME}_lage.json") else {}
CFG.update(L0.get("cfg", {}))       # Lage "cfg": Grundwerte je Region (Region MOB: dichte Betriebspunkte, cover_m/merge_station_m kleiner)
for i, n in nodes.items():
    n["inset"] = None
    if n["kind"] == "station" and os.path.exists(slug(n["name"]) + "_ports.json"):
        n["inset"] = slug(n["name"])
        # eigene Fassung für den Regionalplan (Detailplan mit grösserem Ausschnitt, z. B. Rothrist 14.10.)
        if os.path.exists(n["inset"] + "_regional_ports.json"): n["inset"] += "_regional"
        PORTS[i] = json.load(open(n["inset"] + "_ports.json"))
for a in [i for i in nodes if nodes[i]["inset"]]:
    for b in [i for i in nodes if nodes[i]["inset"]]:
        if a != b and dist(a, b) < CFG["cover_m"] and nodes[b]["name"] not in L0.get("als_halt", []) \
                and nodes[a]["name"] not in L0.get("eigenes_feld", []):
            ka = (PORTS[a]["W"] * PORTS[a]["H"], len(PORTS[a]["ports"])); kb = (PORTS[b]["W"] * PORTS[b]["H"], len(PORTS[b]["ports"]))
            if ka < kb: nodes[a]["covered"] = b
for i, n in nodes.items():
    if n.get("covered") is not None or (n["kind"] == "station" and not n["inset"]) or n["name"] in L0.get("als_halt", []):
        n["inset"] = None; n["kind"] = "halt"; PORTS.pop(i, None)
# Lose Enden, die nahe an einer anderen Strecke enden (Gleisdreieck/Schleife, deren Anfang beim
# Abziehen paralleler Achsen verloren ging): Strecke dort teilen und anschliessen
from shapely.geometry import LineString as _LSg, Point as _Pt
from shapely.ops import substring as _sub
for nid in [n for n in nodes if nodes[n]["kind"] == "end"]:
    own = [e for e in edges if nid in (e["a"], e["b"])]
    if len(own) != 1: continue
    p = _Pt(nodes[nid]["x"], nodes[nid]["y"]); best = None
    for e in edges:
        if e is own[0] or len(e["geom"]) < 2: continue
        gg = list(e["geom"])
        if math.dist(gg[0], (nodes[e["a"]]["x"], nodes[e["a"]]["y"])) > math.dist(gg[-1], (nodes[e["a"]]["x"], nodes[e["a"]]["y"])): gg = gg[::-1]
        L = _LSg(gg); d_ = L.distance(p)
        if d_ < CFG["snap_end_m"] and (best is None or d_ < best[0]): best = (d_, e, L)
    if not best: continue
    d_, e, L = best; t = L.project(p)
    if t < 30 or t > L.length - 30: continue
    jid = max(nodes) + 1; q = L.interpolate(t)
    nodes[jid] = dict(id=jid, name="Abzweig", kind="junction", x=q.x, y=q.y, inset=None)
    g1 = list(_sub(L, 0, t).coords); g2 = list(_sub(L, t, L.length).coords)
    edges.remove(e)
    edges.append(dict(e, b=jid, geom=g1, length=t)); edges.append(dict(e, a=jid, geom=g2, length=L.length - t))
    o = own[0]
    if o["a"] == nid: o["a"] = jid; o["geom"] = [(q.x, q.y)] + list(o["geom"])
    else: o["b"] = jid; o["geom"] = list(o["geom"]) + [(q.x, q.y)]
    o["length"] += d_; nodes.pop(nid)
    print(f"  loses Ende #{nid} an Strecke {e['refs']} angeschlossen (Abzweig #{jid}, {d_:.0f} m)")
for nid in [n for n in nodes if nodes[n]["kind"] == "end"]:
    edges = [e for e in edges if nid not in (e["a"], e["b"]) or e["length"] > CFG["drop_end_m"]]
    if not any(nid in (e["a"], e["b"]) for e in edges): nodes.pop(nid)
for j in [n for n in nodes if nodes[n]["kind"] == "junction"]:
    st = [s for s in nodes if nodes[s]["inset"] and dist(j, s) < L0.get("merge_radius", {}).get(nodes[s]["name"], CFG["merge_station_m"])]
    if st: relabel(j, min(st, key=lambda s: dist(j, s)))
drop_loops()
changed = True
while changed:
    changed = False
    J = [n for n in nodes if nodes[n]["kind"] == "junction"]
    for a in J:
        for b in J:
            if a != b and a in nodes and b in nodes and dist(a, b) < CFG["merge_junction_m"]:
                relabel(b, a); drop_loops(); changed = True
changed = True
while changed:
    changed = False
    for j in list(nodes):
        if nodes[j]["kind"] != "junction": continue
        inc = [e for e in edges if j in (e["a"], e["b"])]
        if len(inc) == 2:
            e1, e2 = inc
            o1 = e1["b"] if e1["a"] == j else e1["a"]; o2 = e2["b"] if e2["a"] == j else e2["a"]
            pj = (nodes[j]["x"], nodes[j]["y"])
            g1 = list(e1["geom"]); g2 = list(e2["geom"])
            if math.dist(g1[0], pj) < math.dist(g1[-1], pj): g1 = g1[::-1]      # g1 endet am Abzweig
            if math.dist(g2[-1], pj) < math.dist(g2[0], pj): g2 = g2[::-1]      # g2 beginnt am Abzweig
            edges.remove(e1); edges.remove(e2)
            edges.append(dict(a=o1, b=o2, tracks=e1["tracks"] if e1["length"] >= e2["length"] else e2["tracks"],
                              length=e1["length"] + e2["length"], refs=sorted(set(e1["refs"]) | set(e2["refs"])), geom=g1 + g2,
                              _eigen=e1.get("_eigen") or e2.get("_eigen")))
            nodes.pop(j); changed = True; break
drop_loops()
ids = sorted(nodes); idx = {n: k for k, n in enumerate(ids)}
inc = collections.defaultdict(list)
for e in edges: inc[e["a"]].append(e); inc[e["b"]].append(e)
print("Knoten:", collections.Counter("spurplan" if nodes[n]["inset"] else nodes[n]["kind"] for n in ids), "Kanten:", len(edges))

# ------------------------------------------------------------------ 2. Anschlüsse zuordnen
def adiff(a, b): return abs((a - b + 180) % 360 - 180)
def geo_bearing(e, at, reach=500):
    g = e["geom"] if e["a"] == at else e["geom"][::-1]
    if math.dist(g[0], (nodes[at]["x"], nodes[at]["y"])) > math.dist(g[-1], (nodes[at]["x"], nodes[at]["y"])): g = g[::-1]
    p0 = np.array(g[0]); L = 0; q = p0
    for p in g[1:]:
        L += math.dist(q, p); q = np.array(p)
        if L > reach: break
    return math.degrees(math.atan2(q[1] - p0[1], q[0] - p0[0])) % 360
S = CFG["S"]
def port_xy(P, p, cx, cy):
    x = p["x"]
    if p["kind"] == "edge" and not ("auto" in L0 and L0.get("port_am_gleisende", True)):     # automatische Lage: Port am Gleisende (Knick direkt am Bahnhof, 18.10.)
        x = max(P["x_hi"], x) if p["dx"] > 0 else min(P["x_lo"], x)
    return np.array([(x - cx) * S, (p["y"] - cy) * S]), np.array([(p["x"] - cx) * S, (p["y"] - cy) * S])
def port_vec(p):
    if p["kind"] == "side": return np.array([p["dx"] * 0.5, -p["dy"] * 0.866 * -1])   # SVG-y nach unten: dy=+1 -> unten
    return np.array([float(p["dx"]), 0.0])
anchor = {}        # (id(e), node) -> dict(off=np.array (px, rel. Kastenmitte, SVG-Koordinaten), v=Austritt, ports=[...])
for i in [i for i in ids if nodes[i]["inset"]]:
    P = PORTS[i]["ports"]; cx = (PORTS[i]["x_lo"] + PORTS[i]["x_hi"]) / 2; cy = (PORTS[i]["y_lo"] + PORTS[i]["y_hi"]) / 2
    es = [(e, geo_bearing(e, i)) for e in inc[i]]
    taken = set()
    for e, br in sorted(es, key=lambda t: min([adiff(t[1], p["bearing"]) for p in P] or [999])):
        cand = sorted((adiff(br, p["bearing"]) + (0 if p["ref"] in e["refs"] else (12 if p["ref"] is None else 45)), k) for k, p in enumerate(P) if k not in taken)
        cand = [c for c in cand if c[0] < 70]
        if cand:
            k0 = cand[0][1]; v0 = port_vec(P[k0])
            grp = [k for sc, k in cand if sc < cand[0][0] + 30 and np.allclose(port_vec(P[k]), v0)]
            g_ref = [k for k in grp if P[k]["ref"] in e["refs"]]; g_oth = [k for k in grp if k not in g_ref]
            nt = max(1, min(6, e["tracks"]))
            _dn = lambda k: min([abs(P[k]["y"] - P[j]["y"]) for j in g_ref] or [0])
            grp = g_ref[:6] if len(g_ref) >= nt else g_ref + [k for k in sorted(g_oth, key=_dn) if _dn(k) <= 30 or not g_ref][:nt - len(g_ref)]
            grp = sorted(grp, key=lambda k: P[k]["y"])
            for k in grp: taken.add(k)
            pp = [port_xy(PORTS[i], P[k], cx, cy) for k in grp]
            if len(pp) > 1:            # Abgänge eines Bündels auf eine gemeinsame Front (quer zur Austrittsrichtung) verlängern
                vn = v0 / np.linalg.norm(v0); fr = max(float(a @ vn) for a, b in pp)
                pp = [(a + vn * (fr - float(a @ vn)), b) for a, b in pp]
            pts = [a for a, b in pp]
            anchor[(id(e), i)] = dict(off=np.mean(pts, axis=0), v=v0, pts=pts, pax=all(P[k]["pax"] for k in grp), ext=pp, refs=[P[k]["ref"] for k in grp], side=all(P[k]["kind"] == "side" for k in grp))
        elif [k for k in range(len(P)) if k not in taken and P[k]["ref"] in e["refs"]]:
            # Fallback: freier Anschluss derselben Linie
            k0 = [k for k in range(len(P)) if k not in taken and P[k]["ref"] in e["refs"]][0]; v0 = port_vec(P[k0])
            grp = [k for k in range(len(P)) if k not in taken and P[k]["ref"] == P[k0]["ref"] and np.allclose(port_vec(P[k]), v0)][:4]
            for k in grp: taken.add(k)
            pp = [port_xy(PORTS[i], P[k], cx, cy) for k in grp]
            if len(pp) > 1:            # Abgänge eines Bündels auf eine gemeinsame Front (quer zur Austrittsrichtung) verlängern
                vn = v0 / np.linalg.norm(v0); fr = max(float(a @ vn) for a, b in pp)
                pp = [(a + vn * (fr - float(a @ vn)), b) for a, b in pp]
            pts = [a for a, b in pp]
            anchor[(id(e), i)] = dict(off=np.mean(pts, axis=0), v=v0, pts=pts, pax=all(P[k]["pax"] for k in grp), ext=pp, refs=[P[k]["ref"] for k in grp], side=all(P[k]["kind"] == "side" for k in grp))
        else:     # kein passender Anschluss: Kastenende in Streckenrichtung
            right = math.cos(math.radians(br)) >= 0
            off = np.array([((PORTS[i]["x_hi"] - cx) if right else (PORTS[i]["x_lo"] - cx)) * S, 0.0])
            anchor[(id(e), i)] = dict(off=off, v=np.array([1.0 if right else -1.0, 0.0]), pts=[off], pax=True)
            print(f"  {nodes[i]['name']}: Strecke Richtung {br:.0f}° ohne Anschluss")
    # Strecke mit mehreren Linien (z. B. 540 + 531 Olten Ost): freie Anschlüsse derselben Linien gehören ins selbe Bündel
    for e in inc[i]:
        a_ = anchor.get((id(e), i))
        _nm = {nodes[e["a"]]["name"], nodes[e["b"]]["name"]}
        if not any(set(x.split("|")) == _nm for x in L0.get("buendel_zusatz", [])): continue     # nur von Hand freigegeben
        if not a_ or len(a_["pts"]) >= 6 or len(set(e["refs"])) < 2: continue
        add = [k for k in range(len(P)) if k not in taken and P[k]["ref"] in e["refs"]][:6 - len(a_["pts"])]
        for k in add:
            taken.add(k); a_["pts"].append(port_xy(PORTS[i], P[k], cx, cy)[0]); a_["refs"].append(P[k]["ref"]); a_["ext"].append(port_xy(PORTS[i], P[k], cx, cy))
        if add: a_["off"] = np.mean(a_["pts"], axis=0)
    free = [k for k in range(len(P)) if k not in taken]
    if free: print(f"  {nodes[i]['name']}: freie Anschlüsse {[(P[k]['ref'], round(P[k]['bearing'])) for k in free]}")

# ------------------------------------------------------------------ Drehung (Nord-Süd-Bahnhöfe senkrecht)
ROT = {}
OVR_LAGE = json.load(open(f"{NAME}_lage.json")) if os.path.exists(f"{NAME}_lage.json") else {}
AUTO = OVR_LAGE.get("auto") if "auto" in OVR_LAGE else None
if AUTO is not None and not AUTO: AUTO = {"_": 1}
def rotv(v, a):
    if a == -90: return np.array([v[1], -v[0]])
    if a == 90: return np.array([-v[1], v[0]])
    if a in (180, -180): return -np.array(v, float)
    if a:          # auch 60°-Lagen (Daniel 16.10.: Bahnhöfe dürfen im Regionalplan schräg liegen); Drehsinn wie SVG rotate()
        c_, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
        return np.array([v[0] * c_ - v[1] * s_, v[0] * s_ + v[1] * c_])
    return np.array(v, float)
for i in [i for i in ids if nodes[i]["inset"]]:
    ROT[i] = 0
    ov = OVR_LAGE.get("drehung", {}).get(nodes[i]["name"]) if "OVR_LAGE" in globals() else None
    P = PORTS[i]["ports"]
    rb = [p["bearing"] for p in P if p["dx"] > 0 and p["kind"] == "edge"]
    lb = [p["bearing"] for p in P if p["dx"] < 0 and p["kind"] == "edge"]
    if rb:
        vx = np.mean([math.cos(math.radians(b)) for b in rb]); vy = np.mean([math.sin(math.radians(b)) for b in rb])
        if abs(vy) > abs(vx) * 1.1: ROT[i] = -90 if vy > 0 else 90      # rechtes Ende zeigt nach Norden -> oben
    if AUTO: ROT[i] = 0          # automatische Lage (16.10.): Drehung wird in lage_auto bestimmt
    if ov is not None: ROT[i] = ov
for (eid, i), a_ in anchor.items():
    r_ = ROT.get(i, 0)
    if r_:
        a_["off"] = rotv(a_["off"], r_); a_["v"] = rotv(a_["v"], r_); a_["pts"] = [rotv(p, r_) for p in a_["pts"]]
        a_["ext"] = [(rotv(p, r_), rotv(q, r_)) for p, q in a_.get("ext", [])]
print("senkrecht:", [nodes[i]["name"] for i in ROT if ROT[i]])

# ------------------------------------------------------------------ 3. Hauptknoten, Strecken, Lage
MAJOR = [n for n in ids if nodes[n]["inset"] or nodes[n]["kind"] in ("junction", "exit")]
routes, used = [], set()
for m in MAJOR:
    for e in inc[m]:
        if id(e) in used: continue
        chain, seq = [e], [m]; used.add(id(e))
        nxt = e["b"] if e["a"] == m else e["a"]
        while nxt not in MAJOR:
            seq.append(nxt)
            cand = [f for f in inc[nxt] if id(f) not in used]
            if not cand: break
            f = cand[0]; used.add(id(f)); chain.append(f); nxt = f["b"] if f["a"] == nxt else f["a"]
        seq.append(nxt)
        routes.append(dict(a=m, b=nxt, seq=seq, edges=chain, first=chain[0], last=chain[-1],
                           tracks=max(f["tracks"] for f in chain), length=sum(f["length"] for f in chain)))
_tot = [r for r in routes if r["b"] not in MAJOR]
if _tot: print("Stichstrecken ohne Endknoten weggelassen:", [nodes[r["a"]]["name"] + " -> " + nodes[r["b"]]["name"] for r in _tot])
routes = [r for r in routes if r["b"] in MAJOR]
LAGE_F = f"{NAME}_lage.json"
K0 = 0.16
if os.path.exists(LAGE_F):
    L_ = json.load(open(LAGE_F))
    pos = {n: np.array(L_.get(nodes[n]["name"] + ("" if nodes[n]["inset"] else f" #{n}"), [nodes[n]["x"] * K0, -nodes[n]["y"] * K0]), float) for n in MAJOR}   # neue Knoten: geografisch
else:
    pos = {n: np.array([nodes[n]["x"] * K0, -nodes[n]["y"] * K0]) for n in MAJOR}
    json.dump({nodes[n]["name"] + ("" if nodes[n]["inset"] else f" #{n}"): [round(float(pos[n][0])), round(float(pos[n][1]))] for n in MAJOR},
              open(LAGE_F, "w"), ensure_ascii=False, indent=1)
    print("Lagedatei angelegt:", LAGE_F)
def off(e, n): return anchor[(id(e), n)]["off"] if (id(e), n) in anchor else np.zeros(2)
if AUTO:
    import lage_auto
    _fix = {i: ROT[i] for i in ROT if nodes[i]["name"] in OVR_LAGE.get("drehung", {})}
    for (eid, i), a_ in anchor.items():          # Anker zurück in Kastenlage (ungedreht), lage_auto dreht selbst
        r_ = _fix.get(i, 0)
        if r_:
            a_["off"] = rotv(a_["off"], -r_); a_["v"] = rotv(a_["v"], -r_); a_["pts"] = [rotv(p, -r_) for p in a_["pts"]]
            a_["ext"] = [(rotv(p, -r_), rotv(q, -r_)) for p, q in a_.get("ext", [])]
    for (eid_, i_), a_ in anchor.items():       # Portrichtung von Hand (Lage port_richtung {"Bahnhof|Linie": Grad im Bahnhof}), Murten 255 (18.10.)
        for k_, wk_ in L0.get("port_richtung", {}).items():
            nm_, rf_ = k_.split("|")
            if nodes[i_]["name"] == nm_ and rf_ in a_.get("refs", []):
                a_["v"] = np.array([math.cos(math.radians(wk_)), -math.sin(math.radians(wk_))])
    if os.environ.get("REFDBG"): [print("REF", nodes[i_]["name"], a_.get("refs"), a_["v"], a_["off"], a_.get("ext")) for (e_, i_), a_ in anchor.items() if nodes[i_]["name"] == os.environ["REFDBG"]]
    pos, rot_ = lage_auto.ketten(nodes, MAJOR, routes, anchor, PORTS, S, AUTO, _fix, L0)
    for i in ROT: ROT[i] = rot_.get(i, 0)
    for (eid, i), a_ in anchor.items():
        r_ = ROT.get(i, 0)
        if r_:
            a_["off"] = rotv(a_["off"], r_); a_["v"] = rotv(a_["v"], r_); a_["pts"] = [rotv(p, r_) for p in a_["pts"]]
            a_["ext"] = [(rotv(p, r_), rotv(q, r_)) for p, q in a_.get("ext", [])]
    _L = json.load(open(LAGE_F)) if os.path.exists(LAGE_F) else {}
    for n in MAJOR: _L[nodes[n]["name"] + ("" if nodes[n]["inset"] else f" #{n}")] = [round(float(pos[n][0])), round(float(pos[n][1]))]
    _L["drehung_auto"] = {nodes[i]["name"]: round(ROT[i], 1) for i in ROT if ROT[i]}
    json.dump(_L, open(LAGE_F, "w"), ensure_ascii=False, indent=1)
# Regel S1 (27.10.2026, Hinweis c8i4 Region Olten: «solche S-Kurven vermeiden, da passiert ja nichts»): liegen die
# Anschlüsse zweier Bahnhöfe auf einer geraden Strecke fast auf einer Linie (Versatz unter einer halben Gleisachse),
# wird ein Bahnhof quer verschoben, damit die Gleise ohne Versatz durchlaufen. Verschoben wird der Bahnhof mit weniger
# Strecken (bei Gleichstand der zweite); jeder Bahnhof höchstens einmal. Abschalten: Lage "s1_aus": true
_S1 = {}; _S1_EXIT = set()
if not L0.get("s1_aus"):
    for _ in range(3):
        for _r in routes:
            _a, _b = _r["a"], _r["b"]
            if not (nodes[_a]["inset"] and nodes[_b]["inset"]) or _a not in pos or _b not in pos: continue
            _aa = anchor.get((id(_r["first"]), _a)); _ab = anchor.get((id(_r["last"]), _b))
            if not _aa or not _ab: continue
            _va = np.asarray(_aa["v"], float); _vb = np.asarray(_ab["v"], float)
            if float(_va @ _vb) > -0.995: continue                       # Anschlüsse nicht genau gegenüber
            _pa = pos[_a] + np.asarray(_aa["off"], float); _pb = pos[_b] + np.asarray(_ab["off"], float)
            _d = _pb - _pa
            if float(_d @ _va) <= 0: continue
            _nrm = np.array([-_va[1], _va[0]]); _q = float(_d @ _nrm)
            if not (0.3 < abs(_q) < 0.5 * TG): continue
            _deg = lambda n_: sum(1 for r_ in routes if n_ in (r_["a"], r_["b"]))
            _m, _sg = (_b, -1) if _deg(_b) <= _deg(_a) else (_a, 1)
            if _m in _S1: _m, _sg = (_a, 1) if _m == _b else (_b, -1)
            if _m in _S1: continue
            pos[_m] = pos[_m] + _sg * _q * _nrm; _S1[_m] = round(_q, 1)
    _S1_EXIT.update(n_ for n_ in MAJOR if nodes[n_]["kind"] == "exit" and any(n_ in (r_["a"], r_["b"]) and (r_["a"] in _S1 or r_["b"] in _S1) for r_ in routes))
    if _S1: print("S1 quer ausgerichtet:", {nodes[k]["name"]: v for k, v in _S1.items()})
# Abgänge mit kleinem Versatz zum Anschluss auf dessen Linie legen (Hinweis Region Olten 15.10.: "S Kurve" Safenwil–Suhr)
for _n in [n for n in MAJOR if nodes[n]["kind"] == "exit"]:
    for _r in [r for r in routes if _n in (r["a"], r["b"])]:
        _o = _r["b"] if _r["a"] == _n else _r["a"]
        _a = anchor.get((id(_r["first"] if _r["a"] == _o else _r["last"]), _o))
        if _o not in pos or not _a or not nodes[_o]["inset"]: continue
        _v = np.asarray(_a["v"], float); _pp = pos[_o] + np.asarray(_a["off"], float)
        for _ax in (0, 1):
            if abs(_v[_ax]) > 0.98 and 0.5 < abs(pos[_n][1 - _ax] - _pp[1 - _ax]) < 25 and (pos[_n][_ax] - _pp[_ax]) * _v[_ax] > 0:
                pos[_n][1 - _ax] = _pp[1 - _ax]
        # auch schräge Anschlüsse (27.10., nach S1-Ausrichtung): Abgang quer auf die Anschlusslinie
        if max(abs(_v[0]), abs(_v[1])) <= 0.98 and _n in _S1_EXIT:
            _vn = _v / (np.linalg.norm(_v) or 1); _nr = np.array([-_vn[1], _vn[0]]); _qq = float((pos[_n] - _pp) @ _nr)
            if 0.3 < abs(_qq) < 25 and float((pos[_n] - _pp) @ _vn) > 0: pos[_n] = pos[_n] - _qq * _nr
def boxes(Y=None):
    out = {}
    for n in MAJOR:
        if not nodes[n]["inset"]: continue
        P = PORTS[n]; w = (P["x_hi"] - P["x_lo"] + 40) * S; h = (P["y_hi"] - P["y_lo"] + 50) * S
        r_ = ROT.get(n, 0)
        if abs(r_) == 90: w, h = h, w
        elif r_ and abs(r_) != 180:
            c_, s_ = abs(math.cos(math.radians(r_))), abs(math.sin(math.radians(r_))); w, h = w * c_ + h * s_, w * s_ + h * c_
        c = pos[n]; out[n] = (c[0] - w / 2, c[1] - h / 2, c[0] + w / 2, c[1] + h / 2)
    return out
DIRS = [0, 60, 90, 120, 180, 240, 270, 300]
def uvec(dg): return np.array([math.cos(math.radians(dg)), -math.sin(math.radians(dg))])

# ------------------------------------------------------------------ 5. Zeichnen
out = []
POLYS = []
_CUR = [None]      # Strecke, die gerade gezeichnet wird (Farbe je Linie, Lage "linienfarbe")
def _spur_col(r):
    if r is None: return None
    _f = L0.get("linienfarbe", {}) if "L0" in globals() else {}
    refs = [f_.get("ref") for f_ in r.get("edges", [])] + [x for f_ in r.get("edges", []) for x in f_.get("refs", [])]
    return next((_f[x] for x in refs if x in _f), None)
PORTAL = "#8a8a8a"   # Tunnelportale grau und vor Grün (D. Eckenstein 26.10.2026: «Schwarz hinter Grün nur bei Weichen»)
def path(pts, color=G, w=2.4):
    _sc = _spur_col(_CUR[0])
    if _sc and color in (G, BK): color = _sc      # Schmalspur braun (Region MOB 21.10.)
    if os.environ.get("PDBG") and any(abs(float(p[0]) - float(os.environ["PDBG"].split(",")[0])) < 3 and abs(float(p[1]) - float(os.environ["PDBG"].split(",")[1])) < 3 for p in pts):
        import traceback; traceback.print_stack(limit=3)
    pts = [np.array(p, float) for p in pts]; cl = [pts[0]]
    for p in pts[1:]:
        if np.linalg.norm(p - cl[-1]) > 0.3: cl.append(p)
    pts = cl
    if len(pts) < 2: return
    # Regel W8 (27.10.2026, Hinweis x42t: «es kommt schräg, wieso muss es vertikal und dann 90° nach horizontal?»):
    # ein kurzes Zwischenstück (< 1.5 Gleisachsen) zwischen zwei Knicken entfällt, wenn die beiden Nachbarstücke sich
    # direkt unter höchstens 60° treffen; der Knick liegt dann im Schnittpunkt. Abschalten: Lage "w8_aus": true
    if not L0.get("w8_aus"):
        k = 1
        while k < len(pts) - 2:
            a0, a1, a2, a3 = pts[k - 1], pts[k], pts[k + 1], pts[k + 2]
            u1, u2, u3 = a1 - a0, a2 - a1, a3 - a2; l1, l2, l3 = (np.linalg.norm(u1), np.linalg.norm(u2), np.linalg.norm(u3))
            if l2 < 1.5 * TG and min(l1, l3) > l2 and l1 > 0 and l3 > 0:
                cr = _cr(u1, u3)
                ang = math.degrees(math.atan2(abs(cr), float(u1 @ u3)))
                if abs(cr) > 1e-6 and ang <= 61:
                    t = _cr(a2 - a0, u3) / cr; X = a0 + u1 * t
                    t3 = float((X - a2) @ u3) / (l3 * l3)
                    if t > 0.5 and t3 < 0.9 and np.linalg.norm(X - a1) < 2.5 * TG:
                        pts = pts[:k] + [X] + pts[k + 2:]; continue
            k += 1
    POLYS.append([tuple(p) for p in pts])
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for k in range(1, len(pts) - 1):
        p0, p1, p2 = pts[k - 1], pts[k], pts[k + 1]; l1, l2 = np.linalg.norm(p1 - p0), np.linalg.norm(p2 - p1)
        r = min(CFG["R"], l1 / 2, l2 / 2); a = p1 - (p1 - p0) / l1 * r; b = p1 + (p2 - p1) / l2 * r
        d += f"L{a[0]:.1f},{a[1]:.1f}Q{p1[0]:.1f},{p1[1]:.1f} {b[0]:.1f},{b[1]:.1f}"
    d += f"L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')
def text(x, y, t, size=14, anchor_="middle", weight=400, color=G):
    out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor_}" fill="{color}">{t}</text>')
DV = [uvec(a) for a in DIRS]
def turn(u, v): return math.degrees(math.acos(max(-1, min(1, float(u @ v)))))
def connector(A, a, B, b):
    st = CFG["stub"] * 2; A1 = A + a * st; B1 = B + b * st; d = B1 - A1; best = None
    def score(dirs, lens):
        sc_ = sum(turn(p, q) ** 1.5 for p, q in zip(dirs, dirs[1:])) * 0.1 + sum(lens) * 0.01
        if max(turn(p, q) for p, q in zip(dirs, dirs[1:])) > 90: sc_ += 1e4
        return sc_
    cands = []
    for u in DV:                                   # 2 Schenkel
        for v in DV:
            M = np.array([u, v]).T
            if abs(np.linalg.det(M)) < 1e-6: continue
            t, s_ = np.linalg.solve(M, d)
            if t < -0.5 or s_ < -0.5: continue
            cands.append((score([a, u, v, -b], [t, s_]), [A, A1, A1 + u * t, B1, B]))
    w = a - b                                      # 3 Schenkel: Port-Richtung / Schräge / Port-Richtung, gleich lang
    if np.linalg.norm(w) > 1e-6:
        for u in DV:
            M = np.array([w, u]).T
            if abs(np.linalg.det(M)) < 1e-6: continue
            t, m = np.linalg.solve(M, d)
            if t < -0.5 or m < -0.5: continue
            P1 = A1 + a * t; P2 = P1 + u * m
            cands.append((score([a, a, u, -b, -b], [t, m, t]) - 0.5, [A, A1, P1, P2, B1, B]))
    if np.linalg.norm(d) < 1e-6: return [A, B]
    for v in DV:                                   # gerade
        if abs(_cr(v, d)) < 1e-6 and v @ d > 0: cands.append((score([a, v, -b], [np.linalg.norm(d)]) - 1, [A, A1, B1, B]))
    if AUTO:                                       # automatische Lage: gerade Strecke in beliebiger Richtung (16.10.)
        dn = d / np.linalg.norm(d)
        if turn(a, dn) <= L0.get("auto_knick", 61) and turn(dn, -b) <= L0.get("auto_knick", 61): cands.append((score([a, dn, -b], [np.linalg.norm(d)]) - 3, [A, A1, B1, B]))
        # genau ein Knick am Schnittpunkt der beiden Portgeraden (Hinweis 18.10.: "mit den Ästen aus dem Bahnhof raus auf 60 Grad
        # gehen, dann braucht es den Knick nicht"): liegt ein Ende auf der Kettenachse, knickt die Strecke direkt am Port
        dAB = (B - A) / (np.linalg.norm(B - A) or 1)
        if turn(a, dAB) <= L0.get("auto_knick", 61) and turn(dAB, -b) <= 8:      # Knick direkt am Port (andere Ende liegt auf der Linie)
            cands.append((score([a, dAB, -b], [np.linalg.norm(B - A)]) - 8, [A, B]))
        M_ = np.array([a, -b]).T
        if abs(np.linalg.det(M_)) > 1e-6:
            t_, s_ = np.linalg.solve(M_, B - A)
            if t_ > -1 and s_ > -1:
                P_ = A + a * max(t_, 0.0)
                e1, e2 = P_ - A, B - P_
                dirs = [a] + ([e1 / np.linalg.norm(e1)] if np.linalg.norm(e1) > 1 else []) + ([e2 / np.linalg.norm(e2)] if np.linalg.norm(e2) > 1 else []) + [-b]
                if len(dirs) > 2 and max(turn(p, q) for p, q in zip(dirs, dirs[1:])) <= 91:
                    cands.append((score(dirs, [np.linalg.norm(e1), np.linalg.norm(e2)]) - 6, [A, P_, B]))
        # ein Knick: erst ein Stück in Portrichtung, dann gerade frei zum anderen Ende (keine Stufen an Knoten-Bahnhöfen)
        for t in np.arange(st / 2, 6 * st + 1, st / 2):
            for P1 in (A1 + a * t, B1 + b * t):
                pl = [A1, P1, B1]; segs = [q - p for p, q in zip(pl, pl[1:])]
                if min(np.linalg.norm(x) for x in segs) < 1: continue
                dirs = [a] + [x / np.linalg.norm(x) for x in segs] + [-b]
                if max(turn(p, q) for p, q in zip(dirs, dirs[1:])) > 91: continue
                if sum(1 for p, q in zip(dirs, dirs[1:]) if turn(p, q) > 3) > 1: continue
                cands.append((score(dirs, [np.linalg.norm(x) for x in segs]) - 2, [A, A1, P1, B1, B]))
    return min(cands, key=lambda c: c[0])[1] if cands else [A, B]
RAUS_S = False      # Versuch "kleine Versätze direkt verbinden": erzeugte mehr Stufen, deshalb aus
def track_line(core, ps, pe, o, defer_px=250, stub=6, defer_s=True, defer_e=True, late=False, late_f=None):
    """Ein Gleis entlang der Streckenachse: bleibt gerade auf seiner Spur und wechselt die Spur nur an einem
    Knick der Strecke (Seitenversatz geht im Knick auf) oder - wenn bis zum Knick zu weit - gleich am Anfang
    bzw. Ende mit einem 60°-Versatz."""
    C = [np.array(core[0], float)]
    for c in core[1:]:
        c = np.array(c, float)
        if np.linalg.norm(c - C[-1]) > 0.5: C.append(c)
    _ch = True                      # Mini-Schenkel (< 3 px) und fast gerade Knicke (< 4°) entfernen
    while _ch and len(C) > 2:
        _ch = False
        for i in range(1, len(C) - 1):
            u1 = C[i] - C[i - 1]; u2 = C[i + 1] - C[i]
            if np.linalg.norm(u1) < 3 or np.linalg.norm(u2) < 3 or turn(u1 / np.linalg.norm(u1), u2 / np.linalg.norm(u2)) < 4:
                if 0 < i < len(C) - 1 and not (i == 1 and np.linalg.norm(u1) >= 3 and np.linalg.norm(u2) < 3 and len(C) == 3):
                    C.pop(i); _ch = True; break
    if len(C) < 2: return [ps, pe]
    m = len(C) - 1
    U = [(C[i + 1] - C[i]) / np.linalg.norm(C[i + 1] - C[i]) for i in range(m)]
    N = [np.array([-u[1], u[0]]) for u in U]
    hs = float((ps - C[0]) @ N[0]); he = float((pe - C[-1]) @ N[-1])
    corners = [i for i in range(1, m) if turn(U[i - 1], U[i]) > 5]
    W = [o] * m; jog_s = jog_e = False
    if late:          # Spur bis kurz vor das Ende halten, erst dort mit einem 60°-Versatz wechseln (Rothrist Ost: 4 bleibt gerade)
        ps_, pe_ = np.array(ps, float), np.array(pe, float); u_ = U[0]; n_ = N[0]
        along, lat = float((pe_ - ps_) @ u_), float((pe_ - ps_) @ n_)
        if along > 0 and abs(lat) < 0.5 * along:
            run = abs(lat) / TAN60; p1 = ps_ + u_ * max(min(along * (late_f or L0.get("spaet_anteil", 0.72)), along - stub - 12 - run), 0)
            return [ps_, p1, p1 + u_ * run + n_ * lat, pe_] if abs(lat) > 0.5 else [ps_, pe_]
    # kleiner Seitenversatz (< 6 px) an beiden Enden auf gerader Strecke: direkt verbinden statt S-Kurve
    # (Hinweise Region: "alle Gleise eine S-Kurve")
    if RAUS_S and not corners and max(abs(hs - o), abs(he - o)) < 6 and (abs(hs - o) > 0.5 or abs(he - o) > 0.5):
        return [np.array(ps, float), np.array(pe, float)]
    if abs(hs - o) > 0.5:
        if defer_s and corners and np.linalg.norm(C[corners[0]] - C[0]) < defer_px:
            for i in range(corners[0]): W[i] = hs
        else: jog_s = True
    if abs(he - o) > 0.5:
        if defer_e and corners and np.linalg.norm(C[-1] - C[corners[-1]]) < defer_px and (not corners or corners[-1] >= (corners[0] if not jog_s and abs(hs - o) > 0.5 else 0)) \
                and all(W[i] == o for i in range(corners[-1], m)):
            for i in range(corners[-1], m): W[i] = he
        else: jog_e = True
    pts = [np.array(ps, float)]
    if jog_s:
        q1 = ps + U[0] * stub; pts += [q1, q1 + U[0] * abs(o - hs) / TAN60 + N[0] * (o - hs)]
    for i in range(1, m):
        a0 = C[i] + N[i - 1] * W[i - 1]; b0 = C[i] + N[i] * W[i]
        M_ = np.array([U[i - 1], -U[i]]).T
        if turn(U[i - 1], U[i]) > 25:
            t_ = np.linalg.solve(M_, b0 - a0)[0]; pts.append(a0 + U[i - 1] * t_)
        elif abs(W[i] - W[i - 1]) > 0.5:
            run = abs(W[i] - W[i - 1]) / TAN60
            run = min(run, 0.9 * np.linalg.norm(C[i] - C[i - 1]), 0.9 * np.linalg.norm(C[i + 1] - C[i]))
            pts += [a0 - U[i - 1] * run / 2, b0 + U[i] * run / 2]
    if jog_e:
        r2 = pe - U[-1] * stub; pts += [r2 - U[-1] * abs(o - he) / TAN60 + N[-1] * (o - he), r2]
    pts.append(np.array(pe, float))
    return pts
def offset_poly(pts, o):
    pts = [p for k_, p in enumerate(pts) if k_ == 0 or np.linalg.norm(p - pts[k_ - 1]) > 0.3]
    if len(pts) < 2 or abs(o) < 1e-9: return pts
    nrm = []
    for p, q in zip(pts, pts[1:]):
        u = (q - p) / np.linalg.norm(q - p); nrm.append(np.array([-u[1], u[0]]))
    res = [pts[0] + nrm[0] * o]
    for k_ in range(1, len(pts) - 1):
        m = nrm[k_ - 1] + nrm[k_]; m = m / (np.linalg.norm(m) or 1); res.append(pts[k_] + m * o / max(m @ nrm[k_], 0.3))
    res.append(pts[-1] + nrm[-1] * o)
    return res
# Spurpläne
for n in [n for n in ids if nodes[n]["inset"]]:
    P = PORTS[n]; cx = (P["x_lo"] + P["x_hi"]) / 2; cy = (P["y_lo"] + P["y_hi"]) / 2
    svg = open(nodes[n]["inset"] + "_bare.svg").read()
    a_ = ROT.get(n, 0)
    body = re.sub(r"^.*?<svg[^>]*>", "", svg, flags=re.S).replace("</svg>", "").replace('<rect width="100%" height="100%" fill="#fff"/>', "")
    body = re.sub(r'<rect[^>]*width="100%"[^>]*/>', "", body)   # Blatt-Hintergrund jeder Form (auch mit x/y): deckt sonst Nachbarpläne ab
    body = re.sub(r'stroke-width="([\d.]+)"', lambda m: f'stroke-width="{float(m.group(1)) * 0.72 / S:.2f}"', body)
    body = re.sub(r'font-size="([\d.]+)"', lambda m: f'font-size="{float(m.group(1)) * 0.6 / S:.1f}"', body)
    if a_:      # Schrift aufrecht halten
        body = re.sub(r'<text x="([-\d.]+)" y="([-\d.]+)"', lambda m: f'<text transform="rotate({-a_} {m.group(1)} {float(m.group(2)) - 4:.1f})" x="{m.group(1)}" y="{m.group(2)}"', body)
    out.append(f'<g data-st="{nodes[n]["inset"].replace("_regional", "")}" data-name="{nodes[n]["name"]}" transform="translate({pos[n][0]:.1f},{pos[n][1]:.1f}) rotate({a_}) translate({-cx * S:.1f},{-cy * S:.1f}) scale({S})">{body}</g>')
    bx_ = boxes()[n]
    if abs(a_) == 90: text(bx_[2] + 8, pos[n][1] + 6, nodes[n]["name"], 16, "start", 700)
    elif a_ and abs(a_) != 180 and 40 < abs(a_) % 180 < 140: text(pos[n][0] + 34, pos[n][1] + 6, nodes[n]["name"], 16, "start", 700)   # steil: rechts neben der Mitte
    elif a_ and abs(a_) != 180:       # leicht schräg: über dem Kasten, quer zur Achse versetzt
        _h = (P["y_hi"] - P["y_lo"] + 50) * S / 2 + 10; _aa = a_ if abs(a_) < 90 else a_ - math.copysign(180, a_)
        _o = rotv(np.array([0.0, -_h]), _aa); text(pos[n][0] + _o[0], pos[n][1] + _o[1], nodes[n]["name"], 16, weight=700)
    else: text(pos[n][0], bx_[1] + 4, nodes[n]["name"], 16, weight=700)
# Strecken
def track_ends(e, n, k):
    """k Anschlusspunkte (SVG) am Knoten n, quer sortiert."""
    a = anchor.get((id(e), n))
    if a:
        pts = [pos[n] + p for p in a["pts"]]
        if len(pts) >= k: return pts[:k], a["v"]
        base = pos[n] + a["off"]; return [base] * k, a["v"]
    return [pos[n]] * k, None
def VERT(n): return f"#{n}" in L0.get("senkrecht", [])
def far_y(r, n):
    """Querlage des anderen Endes: y bei waagrechtem Abzweig, x bei senkrechtem."""
    o = r["b"] if r["a"] == n else r["a"]; e = r["last"] if r["a"] == n else r["first"]
    q = 0 if VERT(n) else 1
    a_ = anchor.get((id(e), o)); return float(pos[o][q] + (a_["off"][q] if a_ else 0)), o
def rtracks(r):
    _gs = L0.get("gleise_strecke", {})          # {"A|B": n}: Gleiszahl von Hand (Einspur durch Ligerz, 15.10.)
    for _k in (nodes[r["a"]]["name"] + "|" + nodes[r["b"]]["name"], nodes[r["b"]]["name"] + "|" + nodes[r["a"]]["name"]):
        if _k in _gs: return _gs[_k]
    k = max(1, min(6, r["tracks"])); kk = []
    for n, e in ((r["a"], r["first"]), (r["b"], r["last"])):
        a_ = anchor.get((id(e), n))
        if a_: kk.append(max(1, min(6, len(a_["pts"]))))
    return max(kk) if kk else k
JLANE = {}
JMERGE = {}     # (Abzweig, Strecke) -> (halbe Breite der Gegenseite, Seite): überzählige Gleise münden ein
for n in [n for n in MAJOR if nodes[n]["kind"] in ("junction", "exit")]:
    rs = [r for r in routes if n in (r["a"], r["b"])]
    K = max(rtracks(r) for r in rs); sides = {}
    for r in rs:
        y_, o = far_y(r, n); ax_ = 1 if VERT(n) else 0
        sides.setdefault(pos[o][ax_] > pos[n][ax_], []).append((y_, id(r), rtracks(r)))
    for sd, lst in sides.items():
        lst.sort()
        _Ko = max([k_ for k_ in [rtracks(r_) for r_ in rs] ] or [K])
        _oth = [t for s2, l2 in sides.items() if s2 != sd for t in l2]
        _Kother = max([k_ for _, _, k_ in _oth] or [0])
        if sum(k_ for _, _, k_ in lst) > _Kother and _Kother and sum(k_ for _, _, k_ in lst) > 4:
            # mehr Gleise als auf der Gegenseite: Bündel nebeneinander, überzählige Gleise münden am Abzweig ein
            # (keine überlagerten Achsen, Olten Nordost 531/540, 15.10.)
            m_ = max(range(len(lst)), key=lambda q: lst[q][2]); Kc = _Kother
            lo_ = -(Kc - 1) / 2; cur_lo, cur_hi = lo_, lo_ + lst[m_][2] - 1
            JLANE[(n, lst[m_][1])] = [lo_ + j for j in range(lst[m_][2])]
            for q in range(m_ - 1, -1, -1):
                k_ = lst[q][2]; JLANE[(n, lst[q][1])] = [cur_lo - k_ + j for j in range(k_)]; cur_lo -= k_
            for q in range(m_ + 1, len(lst)):
                k_ = lst[q][2]; JLANE[(n, lst[q][1])] = [cur_hi + 1 + j for j in range(k_)]; cur_hi += k_
            for _, rid, _ in lst: JMERGE[(n, rid)] = ((Kc - 1) / 2, sd)
            continue
        for q, (y_, rid, k) in enumerate(lst):
            st0 = 0 if q == 0 else (K - k if q == len(lst) - 1 else (K - k) // 2)
            if len(lst) == 1 and k < K: st0 = 0
            JLANE[(n, rid)] = [(st0 + j) - (K - 1) / 2 for j in range(k)]
# Bündel je Spurplanseite stapeln: verlassen mehrere Strecken eine Spurplanseite in dieselbe Richtung, liegen
# ihre Gleisbündel nebeneinander in der Reihenfolge ihrer Ziele (keine verschränkten Bündel; ein Gleis, das
# in ein anderes Bündel wechselt, kreuzt gleich am Kastenrand = Über-/Unterwerfung)
STACK = {}
_grp = collections.defaultdict(list)
for r in routes:
    for n, e, o in ((r["a"], r["first"], r["b"]), (r["b"], r["last"], r["a"])):
        a_ = anchor.get((id(e), n))
        if a_ is None: continue
        _grp[(n, tuple(np.round(a_["v"], 2)))].append(((id(e), n), r, o, a_))
for (n, vk), lst in _grp.items():
    if len(lst) < 2: continue
    if nodes[n]["name"] in L0.get("stack_aus", []): continue     # Bündel nicht stapeln: Gleise laufen gerade weiter und kreuzen später
    v = np.array(vk, float); nrm = np.array([-v[1], v[0]])
    allp = [p for _, _, _, a_ in lst for p in a_["pts"]]
    c = float(np.mean([p @ nrm for p in allp])); al = float(np.mean([p @ v for p in allp]))
    spans = [(min(p @ nrm for p in a_["pts"]), max(p @ nrm for p in a_["pts"])) for _, _, _, a_ in lst]
    if not any(spans[i][0] < spans[j][1] and spans[j][0] < spans[i][1] for i in range(len(spans)) for j in range(i + 1, len(spans))):
        continue                                             # Bündel liegen schon getrennt nebeneinander
    lst = sorted(lst, key=lambda t: float((pos[t[2]] - pos[n]) @ nrm))
    ks = [rtracks(r) for _, r, _, _ in lst]; Kt = sum(ks); i0 = 0
    for (key, r, o, a_), k_ in zip(lst, ks):
        mid = c + ((i0 + (k_ - 1) / 2) - (Kt - 1) / 2) * TG
        STACK[key] = v * al + nrm * mid; i0 += k_
HALT_AT = {}
ROUTE_X = {}
LANE_REFS = collections.defaultdict(list)
def route_geom(r):
    na, nb = r["a"], r["b"]; ea, eb = r["first"], r["last"]
    k = max(1, min(6, r["tracks"])); kk = []
    for n, e in ((na, ea), (nb, eb)):
        a_ = anchor.get((id(e), n))
        if a_: kk.append(max(1, min(6, len(a_["pts"]))))
    if kk: k = max(kk)
    _gs = L0.get("gleise_strecke", {})
    if f'{nodes[na]["name"]}|{nodes[nb]["name"]}' in _gs or f'{nodes[nb]["name"]}|{nodes[na]["name"]}' in _gs: k = rtracks(r)
    def endinfo(n, e, other):
        a_ = anchor.get((id(e), n))
        if a_:
            pts = [pos[n] + p for p in a_["pts"]]
            if len(pts) < k:      # weniger Abgänge im Spurplan als Streckengleise: quer zur Austrittsrichtung auffächern
                nrm_ = np.array([-a_["v"][1], a_["v"][0]])
                pts = [pos[n] + a_["off"] + nrm_ * (j - (k - 1) / 2) * TG for j in range(k)]
            return pos[n] + STACK.get((id(e), n), a_["off"]), a_["v"], pts[:k], a_["pax"]
        v = pos[other] - pos[n]; v = v / (np.linalg.norm(v) or 1)
        u = max([uvec(0), uvec(180)] if not VERT(n) or nodes[n]["kind"] == "exit" and False else [uvec(90), uvec(270)], key=lambda q: q @ v) \
            if nodes[n]["kind"] == "junction" else max([uvec(0), uvec(90), uvec(180), uvec(270)], key=lambda q: q @ v - (0.35 if abs(q[1]) > 0.5 else 0))
        ov_ = L0.get("richtung", {}).get(f"#{n}", {}).get(f"#{other}")
        if ov_ is not None: u = uvec(ov_)
        if AUTO:          # automatische Lage: Abzweig/Abgang zeigt gerade auf das andere Ende (keine Haken)
            u = v / (np.linalg.norm(v) or 1)
        nv_ = np.array([1.0, 0.0]) if VERT(n) or (nodes[n]["kind"] != "junction" and abs(u[0]) <= 0.5) else np.array([0.0, 1.0])
        lanes = JLANE.get((n, id(r)))
        if lanes is None: lanes = [j - (k - 1) / 2 for j in range(k)]
        pp_ = [pos[n] + nv_ * o * TG for o in lanes[:k]]
        return np.mean(pp_, axis=0), u, pp_ + [pos[n] + nv_ * lanes[-1] * TG] * max(0, k - len(lanes)), True
    A, va, pa, xa = endinfo(na, ea, nb); B, vb, pb, xb = endinfo(nb, eb, na)
    core = connector(A, va, B, vb)
    if os.environ.get("CDBG") and os.environ["CDBG"] in (nodes[na]["name"], nodes[nb]["name"]): print("CORE", nodes[na]["name"], nodes[nb]["name"], A.round(1), va.round(2), B.round(1), vb.round(2), [np.round(c_, 1).tolist() for c_ in core])
    col, w = (G, 2.4) if (xa and xb) else (BK, 1.3)
    offs = [(j - (k - 1) / 2) * TG for j in range(k)]
    # Querreihenfolge an beiden Enden relativ zur ersten/letzten Teilstrecke
    d0 = core[1] - core[0]; d0 = d0 / (np.linalg.norm(d0) or 1); n0 = np.array([-d0[1], d0[0]])
    d1 = core[-1] - core[-2]; d1 = d1 / (np.linalg.norm(d1) or 1); n1 = np.array([-d1[1], d1[0]])
    pa = sorted(pa, key=lambda p: float((p - A) @ n0)); pb = sorted(pb, key=lambda p: float((p - B) @ n1))
    from shapely.geometry import LineString as _LSx
    def _lines(pa_, pb_):
        _late = nodes[na]["name"] in L0.get("stack_aus", []) and not any({nodes[na]["name"], nodes[nb]["name"]} == set(x.split("|")) for x in L0.get("frueh", []))
        _fr = any({nodes[na]["name"], nodes[nb]["name"]} == set(x.split("|")) for x in L0.get("frueh", []))
        # "spaet_anteil_strecke": {"Rothrist|#43": 0.8} - Anteil je Strecke (Platz für Spurwechsel danach, Rothrist Ost 15.10.)
        _lf = L0.get("spaet_anteil_strecke", {}).get(f'{nodes[na]["name"]}|#{nb}') or L0.get("spaet_anteil_strecke", {}).get(f'{nodes[nb]["name"]}|#{na}')
        return [track_line(core, pa_[j], pb_[j], o, defer_s=(id(ea), na) not in STACK and not _fr, defer_e=(id(eb), nb) not in STACK and not _fr, late=_late, late_f=_lf) for j, o in enumerate(offs)]
    def _cross(ls):
        G_ = [_LSx([tuple(p) for p in l]) for l in ls]
        return sum(1 for i in range(len(G_)) for j in range(i + 1, len(G_)) if G_[i].crosses(G_[j]))
    best_ = None
    for pa_ in (pa, pa[::-1]):
        for pb_ in (pb, pb[::-1]):
            ls = _lines(pa_, pb_); sc = (_cross(ls), sum(_LSx([tuple(p) for p in l]).length for l in ls))
            if best_ is None or sc < best_[0]: best_ = (sc, ls)
    def _refs(n, e):
        a_ = anchor.get((id(e), n))
        if not a_ or not a_.get("refs"): return {}
        return {tuple(np.round(pos[n] + p, 3)): rf for p, rf in zip(a_["pts"], a_["refs"])}
    ra, rb = _refs(na, ea), _refs(nb, eb)
    ref_of = [ra.get(tuple(np.round(l[0], 3))) or rb.get(tuple(np.round(l[-1], 3))) for l in best_[1]]
    return dict(lines=best_[1], nx=best_[0][0], core=core, k=k, col=col, w=w, ref_of=ref_of)

# Spurfolge an Abzweigen: Stammstrecke mit bekannten Gleis-Linien (aus dem Spurplan) auf die Äste verteilen,
# z. B. Rothrist West: 450 / 400 / 400 / 450 -> 450 nimmt die äusseren, 400 (NBS) die mittleren Spuren
for n in [n for n in MAJOR if nodes[n]["kind"] == "junction"]:
    rs = [r for r in routes if n in (r["a"], r["b"])]; ax_ = 1 if VERT(n) else 0
    side = collections.defaultdict(list)
    for r in rs:
        o = r["b"] if r["a"] == n else r["a"]; side[pos[o][ax_] > pos[n][ax_]].append(r)
    for sd, lst in side.items():
        if len(lst) != 1 or len(side.get(not sd, [])) < 2: continue
        tr = lst[0]; g_ = route_geom(tr)
        if not any(g_["ref_of"]): continue
        endpts = [l[-1] if tr["b"] == n else l[0] for l in g_["lines"]]
        q_ = 0 if VERT(n) else 1
        order = sorted(range(len(endpts)), key=lambda j: endpts[j][q_])
        K = len(order); lane_ref = [g_["ref_of"][j] for j in order]
        ok, assign = True, {}
        for br in side[not sd]:
            refs_br = set(f for e in br["edges"] for f in e["refs"])
            ln = [i for i, rf in enumerate(lane_ref) if rf in refs_br and rf is not None]
            if len(ln) != rtracks(br): ok = False; break
            assign[id(br)] = [i - (K - 1) / 2 for i in ln]
        if ok and len({tuple(v) for v in assign.values()}) == len(assign) and not set(sum(assign.values(), [])) ^ set(i - (K - 1) / 2 for i in range(K)):
            JLANE.update({(n, rid): v for rid, v in assign.items()})
            JLANE[(n, id(tr))] = [i - (K - 1) / 2 for i in range(K)]
            print(f"  Spurfolge {nodes[n]['name']} #{n}: " + " | ".join(str(x) for x in lane_ref))
# Spurwechsel auf freier Strecke (D. Eckenstein 13.10.: "reine Spurwechsel auf der Strecke zeichnen, sind wichtig"):
# OSM-Verbindungen zwischen zwei Streckengleisen, die in keinem Spurplan liegen, als Diagonale im Streckenbündel
XO = collections.defaultdict(list)
_OSM_F = L0.get("osm", "region.json")          # OSM-Daten der Region (NE: ne_region.json, 17.10.)
if os.path.exists(_OSM_F):
    _D = json.load(open(_OSM_F))["elements"]
    _lat = [g["lat"] for e in _D if e["type"] == "way" for g in e["geometry"]]; _lon = [g["lon"] for e in _D if e["type"] == "way" for g in e["geometry"]]
    _LAT0, _LON0 = (min(_lat) + max(_lat)) / 2, (min(_lon) + max(_lon)) / 2
    _KX = 111320 * math.cos(math.radians(_LAT0))
    _OV = L0.get("osm_versatz", [0, 0])          # Bezugspunkt der Topologie weicht vom OSM-Ausschnitt ab (NE: Topologie aus kleinerem Ausschnitt)
    _xy = lambda la, lo: ((lo - _LON0) * _KX - _OV[0], (la - _LAT0) * 110540 - _OV[1])
    _R = [e for e in _D if e["type"] == "way" and e["tags"].get("railway") == "rail" and e["tags"].get("gauge", "1435") == "1435"]
    _P = {n: _xy(g["lat"], g["lon"]) for w_ in _R for n, g in zip(w_["nodes"], w_["geometry"])}
    _main = [w_ for w_ in _R if not w_["tags"].get("service")]
    _thru = collections.defaultdict(set)
    for w_ in _main:
        for n_ in w_["nodes"]: _thru[n_].add(w_["id"])
    _drawn = set()
    for n_ in nodes:
        if nodes[n_].get("inset"): _drawn |= set(PORTS[n_].get("ways", []))
    _mainpts = np.array([_P[n_] for w_ in _main for n_ in w_["nodes"]])
    def _route_poly(r):
        pts = []
        for i_, e in enumerate(r["edges"]):
            g = [tuple(p) for p in e["geom"]]
            n0 = r["seq"][i_]
            if math.dist(g[-1], (nodes[n0]["x"], nodes[n0]["y"])) < math.dist(g[0], (nodes[n0]["x"], nodes[n0]["y"])): g = g[::-1]
            pts += g if not pts else g[1:]
        return np.array(pts, float)
    _RP = {id(r): _route_poly(r) for r in routes if r["tracks"] >= 2}
    _RPT = {id(r): _route_poly(r) for r in routes}
    from shapely.geometry import LineString as _LSg, Point as _Ptg
    _RL = {k_: _LSg(v_) for k_, v_ in _RP.items() if len(v_) > 1}
    for w_ in _R:
        t_ = w_["tags"]
        if w_["id"] in _drawn or (t_.get("usage") == "main" and not t_.get("service")): continue
        a_, b_ = w_["nodes"][0], w_["nodes"][-1]
        if not (_thru.get(a_) and _thru.get(b_)) or not (_thru[a_] ^ _thru[b_] or len(_thru[a_] | _thru[b_]) >= 2): continue
        if _thru[a_] == _thru[b_]: continue
        L_ = sum(math.dist(_P[u], _P[v]) for u, v in zip(w_["nodes"], w_["nodes"][1:]))
        if L_ > 300 or L_ < 20: continue
        m_ = _Ptg(((_P[a_][0] + _P[b_][0]) / 2, (_P[a_][1] + _P[b_][1]) / 2))
        best = min(((ln.distance(m_), rid) for rid, ln in _RL.items()), default=None)
        if not best or best[0] > 40: continue
        ln = _RL[best[1]]; sa, sb = ln.project(_Ptg(_P[a_])), ln.project(_Ptg(_P[b_]))
        sm = (sa + sb) / 2
        p0, p1 = ln.interpolate(max(sm - 10, 0)), ln.interpolate(min(sm + 10, ln.length))
        dv = np.array([p1.x - p0.x, p1.y - p0.y]); dv = dv / (np.linalg.norm(dv) or 1); cpt = np.array(ln.interpolate(sm).coords[0])
        lat_ = lambda q: float(dv[0] * (q[1] - cpt[1]) - dv[1] * (q[0] - cpt[0]))       # links der Richtung positiv
        near = _mainpts[np.hypot(*(_mainpts - cpt).T) < 120]
        offs_ = sorted(lat_(q) for q in near)
        cl = []
        for o_ in offs_:
            if cl and o_ - cl[-1][-1] < 2.2: cl[-1].append(o_)
            else: cl.append([o_])
        lanes_ = [float(np.mean(c_)) for c_ in cl if len(c_) >= 2]
        if len(lanes_) < 2: continue
        la_ = min(range(len(lanes_)), key=lambda i_: abs(lanes_[i_] - lat_(_P[a_])))
        lb_ = min(range(len(lanes_)), key=lambda i_: abs(lanes_[i_] - lat_(_P[b_])))
        if la_ == lb_: continue
        XO[best[1]].append(dict(t=sm / ln.length, sa=sa, sb=sb, la=la_, lb=lb_, n=len(lanes_), way=w_["id"]))
    print(f"  Spurwechsel auf freier Strecke: {sum(len(v) for v in XO.values())}")
    # Tunnel auf freier Strecke (Hinweis Hauenstein 15.10.: "Tunnelportal mitnehmen"): Anteile der Strecke im Tunnel
    TUN = collections.defaultdict(list)
    _RLT = {k_: _LSg(v_) for k_, v_ in _RPT.items() if len(v_) > 1}
    for rid, ln in _RLT.items():
        iv = []
        for w_ in _R:
            if w_["tags"].get("tunnel") not in ("yes", "building_passage") or w_["tags"].get("service"): continue
            ps_ = [_P[n_] for n_ in w_["nodes"]]
            if len(ps_) < 2 or max(ln.distance(_Ptg(q)) for q in (ps_[0], ps_[-1])) > 60: continue
            a_, b_ = sorted((ln.project(_Ptg(ps_[0])), ln.project(_Ptg(ps_[-1]))))
            iv.append([a_, b_, w_["id"], w_["id"]])
            if os.environ.get("TUNDBG"): print("  tw", w_["id"], w_["tags"].get("name"), w_["tags"].get("tunnel:name"), round(b_ - a_), round(a_))
        iv.sort(); mg = []
        for a_, b_, wa_, wb_ in iv:
            if mg and a_ < mg[-1][1] + 80:
                if b_ > mg[-1][1]: mg[-1][1] = b_; mg[-1][3] = wb_
            else: mg.append([a_, b_, wa_, wb_])
        TUN[rid] = [(a_ / ln.length, b_ / ln.length, wa_, wb_) for a_, b_, wa_, wb_ in mg if b_ - a_ > 400]
        if os.environ.get("TUNDBG") and TUN[rid]: print("TUN", rid, [(round(a_), round(b_), round(ln.length), wa_, wb_) for a_, b_, wa_, wb_ in mg if b_ - a_ > 400])
    print(f"  Tunnel auf freier Strecke: {sum(len(v) for v in TUN.values())}")
    if os.environ.get("TUNDBG"):
        for r_ in routes:
            if TUN.get(id(r_)): print("TUN", nodes[r_["a"]]["name"], nodes[r_["b"]]["name"], [(round(a,3),round(b,3)) for a,b,*_ in TUN[id(r_)]], round(_RLT[id(r_)].length))
XO_N = [0]
XO_T = {}
def _at(l, t_):
    """Punkt auf Polylinie l bei Anteil t_ der Länge"""
    l = np.asarray(l, float); seg_ = np.hypot(*np.diff(l, axis=0).T); cum = np.concatenate([[0], np.cumsum(seg_)])
    s_ = t_ * cum[-1]; i_ = min(max(int(np.searchsorted(cum, s_) - 1), 0), len(seg_) - 1)
    f_ = (s_ - cum[i_]) / (seg_[i_] or 1); return l[i_] + (l[i_ + 1] - l[i_]) * f_, (l[i_ + 1] - l[i_]) / (seg_[i_] or 1)
_STW = {}
def ST_WAYS(n):
    if not nodes[n].get("inset"): return set()
    k_ = nodes[n]["inset"]
    if k_ not in _STW:
        f_ = k_.replace("_regional", "") + ".json"
        try: _STW[k_] = {e["id"] for e in json.load(open(f_))["elements"] if e.get("type") == "way"}
        except Exception: _STW[k_] = set()
    return _STW[k_]
def _hat_portale(n):
    k_ = nodes[n].get("inset")
    if not k_: return False
    for f_ in (f"{k_}_override.json", f"{k_.replace('_regional', '')}_override.json", f"regional_rothrist/{k_.replace('_regional', '')}_override.json"):
        try: return bool(json.load(open(f_)).get("portale"))
        except Exception: pass
    return False
RLINES = []
DEFER_L = []
_XOPTS = []   # bereits gesetzte Spurwechsel (nicht übereinander)
_XO_ORD = []  # (Strecke, Soll-Lage, gesetzte Lage) für die Reihenfolge
for r in routes:
    _CUR[0] = r
    na, nb = r["a"], r["b"]
    g_ = route_geom(r); core, k, col, w = g_["core"], g_["k"], g_["col"], g_["w"]
    ROUTE_X[(r["a"], r["b"])] = g_["nx"]
    for n_j in (na, nb):
        if (n_j, id(r)) not in JMERGE: continue
        hw_, _ = JMERGE[(n_j, id(r))]; VJ = np.array([1.0, 0.0]) if VERT(n_j) else np.array([0.0, 1.0])
        for li_, l in enumerate(g_["lines"]):
            at_end = math.dist(l[-1], pos[n_j]) < math.dist(l[0], pos[n_j])
            pe = np.array(l[-1] if at_end else l[0], float); o_ = float((pe - pos[n_j]) @ VJ) / TG
            if abs(o_) <= hw_ + 0.01: continue
            o2 = math.copysign(hw_, o_); q_ = np.array(l[-2] if at_end else l[1], float)
            d_ = pe - q_; d_ = d_ / (np.linalg.norm(d_) or 1)
            back = abs(o_ - o2) * TG / TAN60 + 6
            p1 = pe - d_ * back; p2 = pe + VJ * (o2 - o_) * TG
            nl = list(l[:-1]) + [p1, p2] if at_end else [p2, p1] + list(l[1:])
            g_["lines"][li_] = nl
    # Lage "strecke_hand" {"A|B": {"<Linie>": [[x, y], ...]}} (D. Eckenstein 26.10.2026, Skizzen Olten Nord): einzelne Linien
    # einer Strecke von Hand als Punktfolge im Regionalplan; Ausrundung und Bogen am Gleisende wie automatisch
    _shk = f'{nodes[na]["name"]}|{nodes[nb]["name"]}'
    for li_, pts_ in L0.get("strecke_hand", {}).get(_shk, {}).items():
        if not str(li_).startswith("_") and int(li_) < len(g_["lines"]): g_["lines"][int(li_)] = [np.asarray(p_, float) for p_ in pts_]
    if os.environ.get("LINDBG"):
        for li_, l in enumerate(g_["lines"]): print("LIN", _shk, li_, [[round(float(v), 1) for v in p_] for p_ in l])
    if AUTO and L0.get("port_bogen", True):
        # Knick am Gleisende als Bogen (Hinweis Region NE 19.10. Murten–Faoug "knick/Bogen"): Linie beginnt ein Stück
        # im Bahnhof, das Gleisende darunter wird weiss abgedeckt, damit die Ecke nicht übersteht
        for li_, l in enumerate(g_["lines"]):
            l = [np.asarray(p_, float) for p_ in l]
            for end_ in (0, -1):
                pe, q_ = l[end_], l[1 if end_ == 0 else -2]
                dl_ = q_ - pe; ln_ = np.linalg.norm(dl_)
                if ln_ < 8: continue
                dl_ = dl_ / ln_; v_ = None; _side = False
                for n_, e_ in ((na, r["first"]), (nb, r["last"])):
                    a_ = anchor.get((id(e_), n_))
                    if a_ and n_ in pos and any(np.linalg.norm(pos[n_] + p_ - pe) < 1.5 for p_ in a_["pts"] + [a_["off"]]):
                        v_ = np.asarray(a_["v"], float) / (np.linalg.norm(a_["v"]) or 1)
                        # seitlicher Abgang (Stummel im Spurplan): kein Bogen, sonst deckt die Maske den Stummel ab und das Gleis
                        # hängt in der Luft (Hinweise Region NE 20.10.: Ins, Murten, Auvernier "nicht mehr angebunden")
                        _side = bool(a_.get("side"))
                if os.environ.get("BOGDBG") and (nodes[na]["name"] == os.environ["BOGDBG"] or nodes[nb]["name"] == os.environ["BOGDBG"]): print("BOG", nodes[na]["name"], nodes[nb]["name"], np.round(pe, 1), None if v_ is None else round(turn(v_, dl_), 1), [np.round(pos[n_] + p_, 1) for n_, e_ in ((na, r["first"]), (nb, r["last"])) for a_ in [anchor.get((id(e_), n_))] if a_ for p_ in a_["pts"] + [a_["off"]]])
                if v_ is None or not 8 < turn(v_, dl_) < 125: continue
                inner = pe - v_ * (5 if _side else 9)
                if _side:          # seitlicher Abgang: erst ein Stück in Stummelrichtung weiter, dann abbiegen; keine Maske (sie deckte
                    # Stummel und Nachbargleise ab, Hinweise Region NE 20.10.: Ins, Murten "nicht mehr angebunden")
                    ext_ = pe + v_ * 10
                    l = [pe, ext_] + l[1:] if end_ == 0 else l[:-1] + [ext_, pe]; continue
                out.append(f'<path d="M{(pe - v_ * 9.5)[0]:.1f},{(pe - v_ * 9.5)[1]:.1f}L{(pe + v_ * 2.5)[0]:.1f},{(pe + v_ * 2.5)[1]:.1f}" stroke="#fff" stroke-width="{w + 2.4:.1f}" fill="none"/>')
                l = [inner] + l if end_ == 0 else l + [inner]
            g_["lines"][li_] = l
    for l in g_["lines"]: DEFER_L.append((r, l, col, w))      # gezeichnet nach der Schleife (Stösse glätten, 20.10.)
    RLINES.append((r, [np.asarray(l, float) for l in g_["lines"]], col, w))
    # Gleiszahl von Hand kleiner als Abgänge des Spurplans: überzählige Gleise laufen mit 60° in das durchgehende Gleis ein
    for n_, e_ in ((na, r["first"]), (nb, r["last"])):
        a_ = anchor.get((id(e_), n_))
        if not a_ or len(a_["pts"]) <= k or rtracks(r) != k: continue
        v_ = np.asarray(a_["v"], float); v_ = v_ / (np.linalg.norm(v_) or 1)
        _nv = np.array([-v_[1], v_[0]])
        _ex = sorted((pos[n_] + p_ for p_ in a_["pts"][k:]), key=lambda p_: min(abs(float(np.dot(p_ - (pos[n_] + q), _nv))) for q in a_["pts"][:k]))
        _ln = sorted(g_["lines"], key=lambda l: min(math.dist(l[0], _ex[0]), math.dist(l[-1], _ex[0])))
        for _j, pj in enumerate(_ex):
            q0 = min((pos[n_] + q for q in a_["pts"][:k]), key=lambda q: abs(float(np.dot(pj - q, np.array([-v_[1], v_[0]])))))   # nächstes durchgehendes Gleis
            dl = abs(float(np.dot(pj - q0, np.array([-v_[1], v_[0]]))))
            # ohne Vorlauf in Bündelrichtung: der Zusatz-Abgang kommt schräg an, ein Vorlauf gäbe einen S-Knick (Olten 531, 15.10.)
            # in das tatsächlich gezeichnete Gleis einmünden (Hinweis Region Olten 15.10.: "münden 90 Grad ins äusserste"):
            # Ziel auf der gezeichneten Linie so weit voraus, dass die Einmündung höchstens 30° zur Linie steht
            from shapely.geometry import LineString as _L3, Point as _P3
            Ld = min(g_["lines"], key=lambda l: min(math.dist(l[0], q0), math.dist(l[-1], q0)))
            # mehrere überzählige Gleise: je ein eigenes Zielgleis (Hinweis Region Olten 17.10. "Anbindung?": beide 531-Gleise
            # liefen ins äusserste Gleis; laut OSM schliessen sie an beide 540-Gleise an)
            if len(_ex) > 1 and not L0.get("einmuenden_ein_gleis") and _j < len(_ln): Ld = _ln[_j]
            Ld = [np.asarray(p, float) for p in (Ld if math.dist(Ld[0], q0) <= math.dist(Ld[-1], q0) else Ld[::-1])]
            if L0.get("einmuenden_alt") or len(Ld) < 2:
                path([pj, q0 + v_ * ((L0.get("einmuenden_versatz", 8)) + dl / TAN60)], col, w); continue
            _ls = _L3(Ld); p1 = pj + v_ * 6
            s0 = _ls.project(_P3(p1)); d0 = _ls.distance(_P3(p1))
            s1 = min(s0 + d0 * TAN60 + 4, _ls.length * 0.85)
            tq = _ls.interpolate(s1)
            path([pj, p1, np.array([tq.x, tq.y])], col, w)
    for xo in sorted(XO.get(id(r), []), key=lambda x_: x_["t"]):
        if os.environ.get("XODBG"): print("XO", nodes[na]["name"], nodes[nb]["name"], xo, len(g_["lines"]))
        if xo["n"] != len(g_["lines"]) or xo["n"] != 2: continue     # vorerst nur Doppelspur (Zuordnung bei 4 Gleisen unsicher)
        _Lp0 = float(np.sum(np.hypot(*np.diff(np.asarray(g_["lines"][0], float), axis=0).T))) or 1
        _mg = max(0.06, (30 + TG) / _Lp0)        # Abstand zu Knoten/Abzweigen am Streckenende (Rothrist Ost 19.10.: sah aus wie DKW)
        tt = min(max(xo["t"], _mg), 1 - _mg)
        pts_ = [_at(l, tt) for l in g_["lines"]]
        dsv = pts_[0][1]; nsv = np.array([-dsv[1], dsv[0]])                       # Normale im Plan (y nach unten)
        ordr = sorted(range(len(pts_)), key=lambda j: float((pts_[j][0] - pts_[0][0]) @ nsv))
        # geografisch links (lane hoch) = im Plan entgegen nsv
        lane_line = {len(ordr) - 1 - q: ordr[q] for q in range(len(ordr))}
        Li, Lj = g_["lines"][lane_line[xo["la"]]], g_["lines"][lane_line[xo["lb"]]]
        _Lpi = np.sum(np.hypot(*np.diff(np.asarray(Li, float), axis=0).T)) or 1
        def _good(_t2):
            _a2, _d2 = _at(Li, _t2); _n2 = np.array([-_d2[1], _d2[0]]); _sp = (TG / TAN60 / 2 + 9) / _Lpi
            if not (0.04 < _t2 - _sp and _t2 + _sp < 0.96): return False
            # nicht an einem Abzweig/Knoten (sonst wirkt es wie eine DKW, Rothrist Ost 19.10.)
            if any(np.linalg.norm(_a2 - pos[n_]) < 28 + TG for n_ in MAJOR if nodes[n_]["kind"] == "junction" and n_ in pos): return False
            if any(np.linalg.norm(_a2 - np.asarray(l_[e_], float)) < 28 + TG for r2_, L2_, _c, _w in RLINES if r2_ is not r for l_ in L2_ for e_ in (0, -1)): return False
            return all(abs(float(_at(L_, _t2 + q_)[1] @ _d2)) > 0.9995 and abs(abs(float((_at(Li, _t2 + q_)[0] - _at(Lj, _t2 + q_)[0]) @ _n2)) - TG) < 1
                       for L_ in (Li, Lj) for q_ in (-_sp, -_sp / 2, 0, _sp / 2, _sp))   # beide gerade, parallel, benachbart
        if not _good(tt):
            # Gleise hier nicht benachbart oder im Bogen (Rothrist Ost: fremdes Bündel dazwischen): nächste gerade Stelle
            _ok = next((q for q in sorted(np.arange(_mg, 1 - _mg, 0.004), key=lambda q: abs(q - tt)) if _good(q)), None)
            if _ok is None: continue
            tt = _ok
        _used = XO_T.setdefault(id(r), [])
        _Lp = np.sum(np.hypot(*np.diff(np.asarray(Li, float), axis=0).T)) or 1
        _gap = (TG / TAN60 + 18) / _Lp
        while any(abs(tt - u_) < _gap for u_ in _used): tt += _gap if xo["sa"] >= min(x_["sa"] for x_ in XO.get(id(r), [])) else -_gap
        _used.append(tt)
        # gleiche Stelle auf beiden Linien über Projektion (Linien können verschieden lang sein, 17.10. Schafis)
        from shapely.geometry import LineString as _L6, Point as _P6
        gi, gj = _L6(Li), _L6(Lj); ci = gi.length * tt
        ci += float(OVR_LAGE.get("xo_versatz", {}).get(str(xo.get("way")), 0))     # Lage {way: px}: Spurwechsel verschieben (Platz für den nächsten)
        cj = gj.project(gi.interpolate(ci))
        run_ = gi.interpolate(ci).distance(gj.interpolate(cj)) / TAN60
        first_a = xo["sa"] < xo["sb"]; _sg = 1 if first_a else -1
        # Lage "xo_umkehren" [[x, y], ...]: Richtung eines Spurwechsels umkehren (Ortskenntnis; Ligerz 20.10.: OSM-Richtung vertauscht)
        if os.environ.get("XODBG2"): print("XOBASIS", nodes[na]["name"], nodes[nb]["name"], np.round(_at(Li, tt)[0], 1), xo.get("way"))
        if any(np.linalg.norm(np.asarray(_at(Li, tt)[0], float) - np.asarray(q_, float)) < 6 for q_ in OVR_LAGE.get("xo_umkehren", [])): _sg = -_sg
        a_, b_ = ci - _sg * run_ / 2, cj + _sg * run_ / 2      # ausgerundet wie im Spurplan (Hinweis 14.10.: "ausrunden")
        # Abstand zu Abzweigen/Streckenenden (Rothrist Ost 19.10.: Spurwechsel direkt am Abzweig wirkte wie eine DKW)
        _jp = [np.asarray(pos[n_], float) for n_ in MAJOR if nodes[n_]["kind"] == "junction" and n_ in pos] + \
              [np.asarray(l_[e_], float) for r2_, L2_, _c, _w in RLINES if r2_ is not r for l_ in L2_ for e_ in (0, -1)] + _XOPTS
        _ok2 = False
        for _sh in [0] + [k_ * sgn_ for k_ in range(3, int(max(gi.length, gj.length)), 3) for sgn_ in (-1, 1)]:
            a2 = a_ + _sh
            if not (9 < a2 < gi.length - 9 and 9 < a2 + _sg * (run_ + 7) < gi.length - 9): continue
            # Gegenstück über Projektion (Linien können gegenläufig orientiert sein, Ligerz 20.10.: Z-förmiger Spurwechsel)
            b2 = gj.project(gi.interpolate(a2 + _sg * run_)); _b7 = gj.project(gi.interpolate(a2 + _sg * (run_ + 7)))
            _sgj = 1 if _b7 >= b2 else -1
            if min(a2, a2 - _sg * 7) < 2 or max(a2, a2 - _sg * 7) > gi.length - 2 or min(b2, b2 + _sgj * 7) < 2 or max(b2, b2 + _sgj * 7) > gj.length - 2: continue
            pa_, pb_ = np.array(gi.interpolate(a2).coords[0]), np.array(gj.interpolate(b2).coords[0])
            if any(min(np.linalg.norm(pa_ - q_), np.linalg.norm(pb_ - q_)) < 22 + TG for q_ in _jp[:len(_jp) - len(_XOPTS)]): continue
            if any(np.linalg.norm((pa_ + pb_) / 2 - q_) < 24 for q_ in _XOPTS): continue   # nicht ineinander (sonst Kreuzung wie DKW)
            # Reihenfolge der Spurwechsel entlang der Strecke wie in OSM (Ligerz 20.10.: zwei Spurwechsel vertauscht)
            if any((a2 - ps_) * (ci - bs_) < 0 for rid_, bs_, ps_ in _XO_ORD if rid_ == id(r)): continue
            def _dir(g_, t_):
                p0_ = np.array(g_.interpolate(max(0, t_ - 12)).coords[0]); p1_ = np.array(g_.interpolate(min(g_.length, t_ + 12)).coords[0])
                return np.degrees(np.arctan2(p1_[1] - p0_[1], p1_[0] - p0_[0]))
            _da = [_dir(gi, a2 - _sg * 7), _dir(gi, a2), _dir(gj, b2), _dir(gj, b2 + _sgj * 7)]
            if max(min(abs((d_ - _da[0] + 180) % 360 - 180), 180 - abs((d_ - _da[0] + 180) % 360 - 180)) for d_ in _da) > 6: continue
            _v = pb_ - pa_; _u = np.array(gi.interpolate(a2 + _sg * 5).coords[0]) - pa_
            _w = math.degrees(math.acos(abs(float(_v @ _u)) / ((np.linalg.norm(_v) * np.linalg.norm(_u)) or 1)))
            if not 40 < _w < 75: continue                 # Spurwechsel als 60°-Schräge, nie quer
            if gj.distance(_Pt(pa_)) > 1.6 * TG or gi.distance(_Pt(pb_)) > 1.6 * TG: continue   # Nachbargleis, nicht über ein drittes   # nur im geraden, parallelen Stück
            if os.environ.get("XODBG2"): print("XOOK", nodes[na]["name"], nodes[nb]["name"], np.round(pa_, 1), np.round(pb_, 1), round(_w, 1), round(run_, 1), _sg, _sgj)
            a_, b_, _ok2 = a2, b2, True; _XOPTS.append((pa_ + pb_) / 2); _SGJ = _sgj; _XO_ORD.append((id(r), ci, a2)); xo["mid"] = (pa_ + pb_) / 2; break
        if not _ok2:
            # kein gerader Platz abseits Abzweig: weglassen statt als 90°-Strich (Nebengleise zeichnet ihn sonst senkrecht)
            xo["gez"] = True; print(f"  Spurwechsel ohne Platz weggelassen: {nodes[na]['name']}–{nodes[nb]['name']}"); continue
        path([np.array(q_.coords[0]) for q_ in (gi.interpolate(a_ - _sg * 7), gi.interpolate(a_), gj.interpolate(b_), gj.interpolate(b_ + _SGJ * 7))], BK, 1.3)
        XO_N[0] += 1; xo["gez"] = True
    # Tunnelportale (Blaupause E7): Klammer quer über alle Gleise, öffnet nach aussen
    _tun_ = TUN.get(id(r), []) if "TUN" in globals() else []
    # Lage "tunnel_hand" {"A|B": [[ta, tb], ...]}: Tunnel als Anteile der gezeichneten Linie von A nach B (Ortskenntnis; der
    # geografische Anteil passt nicht, wenn die Strecke im Plan anders aufgeteilt ist, Borntunnel 20.10.: Portal verkehrt)
    _th_ = OVR_LAGE.get("tunnel_hand", {})
    if f'{nodes[na]["name"]}|{nodes[nb]["name"]}' in _th_:
        _tun_ = [(a_, b_, None, None) for a_, b_ in _th_[f'{nodes[na]["name"]}|{nodes[nb]["name"]}']]
    elif f'{nodes[nb]["name"]}|{nodes[na]["name"]}' in _th_:
        _tun_ = [(1 - b_, 1 - a_, None, None) for a_, b_ in _th_[f'{nodes[nb]["name"]}|{nodes[na]["name"]}']]
    for ta_, tb_, wa_, wb_ in _tun_:
        # kurzer Tunnel: Portale mindestens 18 px auseinander, sonst liegen sie aufeinander (Kerzers–Gümmenen 20.10.)
        _Lp_ = float(np.sum(np.hypot(*np.diff(np.asarray(g_["lines"][0], float), axis=0).T))) or 1
        if (tb_ - ta_) * _Lp_ < 18:
            _m_ = (ta_ + tb_) / 2; ta_, tb_ = _m_ - 9 / _Lp_, _m_ + 9 / _Lp_
        # Portal nicht in einen Bogen setzen (Kerzers–Gümmenen 20.10.): beide gemeinsam ins nächste gerade Stück schieben
        def _gerade_(t_):
            if not 0.02 < t_ < 0.98: return True
            d0_ = _at(g_["lines"][0], max(0, t_ - 9 / _Lp_))[1]; d1_ = _at(g_["lines"][0], min(1, t_ + 9 / _Lp_))[1]
            return float(d0_ @ d1_) > 0.996
        if not (_gerade_(ta_) and _gerade_(tb_)):
            for _k in [k_ * sg2_ for k_ in range(1, 70) for sg2_ in (1, -1)]:
                _d = 3 * _k / _Lp_
                if _gerade_(ta_ + _d) and _gerade_(tb_ + _d) and 0.02 < ta_ + _d and tb_ + _d < 0.98: ta_, tb_ = ta_ + _d, tb_ + _d; break
        for tt_, sg_, wq_, nq_ in ((ta_, -1, wa_, na), (tb_, 1, wb_, nb)):
            if not 0.02 < tt_ < 0.98: continue
            # Portal liegt im Spurplan des Bahnhofs und wird dort gezeichnet (Olten 17.10.) - nur, wenn der Spurplan Portale hat;
            # sonst fehlte das zweite Portal (Gümmenen 20.10.: "Tunnelportale beidseitig vom Tunnel")
            if wq_ in ST_WAYS(nq_) and _hat_portale(nq_): continue
            P_ = [_at(l, tt_) for l in g_["lines"]]
            d_ = P_[0][1]; n_ = np.array([-d_[1], d_[0]])
            ofs = sorted(float((p_[0] - P_[0][0]) @ n_) for p_ in P_)
            c_ = P_[0][0]; grp_ = [[ofs[0]]]
            for o_ in ofs[1:]:          # nicht benachbarte Gleise (fremdes Bündel dazwischen): je eigene Klammer
                if o_ - grp_[-1][-1] <= 1.5 * TG: grp_[-1].append(o_)
                else: grp_.append([o_])
            for gq in grp_:
                a0, a1 = c_ + n_ * (gq[0] - 4.5), c_ + n_ * (gq[-1] + 4.5)
                path([a0 + d_ * sg_ * 5 - n_ * 3, a0, a1, a1 + d_ * sg_ * 5 + n_ * 3], PORTAL, 1.2)
    # manuelle Spurwechsel (Ortskenntnis, z. B. Abzweig Zofingen Nord): Lage "xo_manuell" [{"a","b","t"}]
    for xm in OVR_LAGE.get("xo_manuell", []):
        nm_a, nm_b = nodes[na]["name"], nodes[nb]["name"]
        if {nm_a, nm_b} != {xm["a"], xm["b"]} or len(g_["lines"]) != 2: continue
        tt = xm["t"] if nm_a == xm["a"] else 1 - xm["t"]
        La_, Lb_ = g_["lines"]
        if xm.get("kehren"): La_, Lb_ = Lb_, La_
        Lpx = np.sum(np.hypot(*np.diff(np.asarray(La_, float), axis=0).T))
        dt = (TG / TAN60) / (Lpx or 1)
        _e = 7 / (Lpx or 1)
        path([_at(La_, tt - dt / 2 - _e)[0], _at(La_, tt - dt / 2)[0], _at(Lb_, tt + dt / 2)[0], _at(Lb_, tt + dt / 2 + _e)[0]], *((G, 2.4) if xm.get("pax") else (BK, 1.3))); XO_N[0] += 1
    rr_ = set(f for e in r["edges"] for f in e["refs"])
    for l, rf in zip(g_["lines"], g_["ref_of"]):
        for n_, p_ in ((na, l[0]), (nb, l[-1])):
            if nodes[n_]["kind"] == "junction":
                o_ = nb if n_ == na else na; ax_ = 1 if VERT(n_) else 0
                LANE_REFS[(n_, tuple(np.round(p_, 1)))].append((pos[o_][ax_] > pos[n_][ax_], rf, rr_, f"{nodes[o_]['name']}"))
    # Halte entlang der Strecke (geografischer Anteil)
    from shapely.geometry import LineString as _LS
    segs_ = [(np.linalg.norm(np.array(q) - np.array(p)), np.array(p, float), np.array(q, float)) for p, q in zip(core[1:-2], core[2:-1])] or \
            [(np.linalg.norm(np.array(core[-1]) - np.array(core[0])), np.array(core[0], float), np.array(core[-1], float))]
    Ls, P0, P1 = max(segs_, key=lambda t: t[0]); acc = 0.0
    u = (P1 - P0) / (np.linalg.norm(P1 - P0) or 1)
    _hl = [nid for nid in r["seq"][1:-1] if nodes[nid]["kind"] == "halt"]
    for f, nid in zip(r["edges"][:-1], r["seq"][1:-1]):
        acc += f["length"]
        if nodes[nid]["kind"] != "halt": continue
        t = 0.15 + 0.7 * acc / r["length"]
        if len(_hl) >= 2: t = 0.12 + 0.76 * (_hl.index(nid) + 0.5) / len(_hl)     # mehrere Halte: gleichmässig
        HALT_AT[nid] = (P0 + (P1 - P0) * t, u, k)
    # Mindestabstand zwischen Halten (Hinweis fw9u 17.10., D. Eckenstein 26.10.: Sommerau, Rümlingen, Buckten zu nah):
    # reicht das längste gerade Stück nicht, verteilen sich die Halte über die ganze gezeichnete Strecke
    _MINH = float(L0.get("halt_abstand_min", 60))
    if len(_hl) >= 2 and 0.76 * Ls / len(_hl) < _MINH and len(core) >= 2:
        _PLh = _LS([tuple(map(float, p_)) for p_ in core])
        _a0, _a1 = 0.10 * _PLh.length, 0.90 * _PLh.length
        for i_, nid in enumerate(_hl):
            s_ = _a0 + (_a1 - _a0) * (i_ + 0.5) / len(_hl)
            p_ = np.array(_PLh.interpolate(s_).coords[0]); q0_ = np.array(_PLh.interpolate(max(0, s_ - 6)).coords[0])
            q1_ = np.array(_PLh.interpolate(min(_PLh.length, s_ + 6)).coords[0]); u_ = (q1_ - q0_) / (np.linalg.norm(q1_ - q0_) or 1)
            HALT_AT[nid] = (p_, u_, k)
print(f"  Spurwechsel gezeichnet: {XO_N[0]}")
# Stösse zwischen Strecken an Abzweigen (Vauseyon 20.10.: "Doppelspur Achsabstand springt oder Winkel"): enden zwei Linien
# verschiedener Strecken fast am selben Punkt in ähnlicher Richtung, werden beide Enden auf den Mittelpunkt gelegt und
# die Linie dort zusammengeführt (eine Linie mit Ausrundung statt zwei Stummel)
def _stoesse():
    if L0.get("ohne_stossglaettung"): return
    E_ = []
    for k, (r_, l_, c_, w_) in enumerate(DEFER_L):
        if len(l_) < 2: continue
        for e_ in (0, -1):
            p_ = np.asarray(l_[e_], float); q_ = np.asarray(l_[1 if e_ == 0 else -2], float)
            d_ = p_ - q_; n_ = np.linalg.norm(d_)
            if n_ > 1e-6: E_.append((k, e_, id(r_), p_, d_ / n_, c_))
    used, paare = set(), []
    for i, (ka, ea, ra, pa, da, ca) in enumerate(E_):
        if i in used: continue
        best = None
        for j, (kb, eb, rb, pb, db, cb) in enumerate(E_):
            if j <= i or j in used or rb == ra or ca != cb: continue
            dist = np.linalg.norm(pa - pb)
            if dist > 0.7 * TG or float(da @ -db) < math.cos(math.radians(35)): continue
            if best is None or dist < best[0]: best = (dist, j)
        if best is None: continue
        j = best[1]; kb, eb, rb, pb, db, cb = E_[j]
        if best[0] < 0.05 and float(da @ -db) > 0.999: continue
        used |= {i, j}; paare.append((ka, ea, kb, eb))
    merged = set()
    for ka, ea, kb, eb in paare:
        if ka in merged or kb in merged: continue
        la = [np.asarray(p_, float) for p_ in DEFER_L[ka][1]]; lb = [np.asarray(p_, float) for p_ in DEFER_L[kb][1]]
        if ea == 0: la = la[::-1]
        if eb == -1: lb = lb[::-1]
        m_ = (la[-1] + lb[0]) / 2
        neu = la[:-1] + [m_] + lb[1:]
        r_, _, c_, w_ = DEFER_L[ka]; DEFER_L[ka] = (r_, neu, c_, w_); DEFER_L[kb] = (DEFER_L[kb][0], [], c_, w_)
        merged |= {ka, kb}
    if paare: print(f"  Stösse an Abzweigen zusammengeführt: {len(merged) // 2}")
_stoesse()
def _dp(pts, eps=1.6):       # kleine Versätze in einer Linie weg (Vauseyon 20.10.: Knubbel an Stössen)
    if len(pts) < 3: return pts
    a_, b_ = np.asarray(pts[0], float), np.asarray(pts[-1], float); L_ = np.linalg.norm(b_ - a_) or 1e-9
    dd_ = [abs(float((b_ - a_)[0] * (np.asarray(p_, float) - a_)[1] - (b_ - a_)[1] * (np.asarray(p_, float) - a_)[0])) / L_ for p_ in pts[1:-1]]   # 2D-Kreuzprodukt (numpy 2: np.cross nur 3D)
    i_ = int(np.argmax(dd_)) + 1
    return _dp(pts[:i_ + 1], eps)[:-1] + _dp(pts[i_:], eps) if dd_[i_ - 1] > eps else [pts[0], pts[-1]]
for r_, l_, c_, w_ in DEFER_L:
    _CUR[0] = r_
    if len(l_) > 1: path(_dp([np.asarray(p_, float) for p_ in l_]) if not L0.get("ohne_glaettung") else l_, c_, w_)
_CUR[0] = None
# Kreuzungen ohne Verbindung (Hinweis Region Olten 15.10.: "Unterführungssymbol?"): obere Strecke mit Brückenflügeln,
# untere unterbrochen. Oben/unten aus OSM (bridge/tunnel/layer der Gleise am Kreuzungspunkt).
def _kreuzungen():
    from shapely.geometry import LineString as _L2, Point as _Pt2
    n_br = 0
    pts_nodes = [np.asarray(pos[n], float) for n in pos]
    for i1 in range(len(RLINES)):
        for i2 in range(i1 + 1, len(RLINES)):
            r1, L1, c1, w1 = RLINES[i1]; r2, L2, c2, w2 = RLINES[i2]
            hits = []
            for l1 in L1:
                for l2 in L2:
                    if len(l1) < 2 or len(l2) < 2: continue
                    x_ = _L2(l1).intersection(_L2(l2))
                    for g in getattr(x_, "geoms", [x_]):
                        if g.is_empty or g.geom_type != "Point": continue
                        p = np.array([g.x, g.y])
                        if os.environ.get("KRDBG"): print("   hit", nodes[r1["a"]]["name"], nodes[r1["b"]]["name"], "/", nodes[r2["a"]]["name"], nodes[r2["b"]]["name"], p.round(), round(min(np.linalg.norm(p - q) for q in pts_nodes)))
                        if min(np.linalg.norm(p - q) for q in pts_nodes) < 30: continue
                        hits.append(p)
            if not hits: continue
            cl = []
            for p in hits:
                for c in cl:
                    if np.linalg.norm(c[0] - p) < 45: c.append(p); break
                else: cl.append([p])
            for c in cl:
                X = np.mean(c, axis=0)
                # oben/unten aus OSM
                g1, g2 = _RPT.get(id(r1)), _RPT.get(id(r2))
                if g1 is None or g2 is None or len(g1) < 2 or len(g2) < 2: continue
                gx = _L2(g1).intersection(_L2(g2))
                gp = [g for g in getattr(gx, "geoms", [gx]) if not g.is_empty and g.geom_type == "Point"]
                if not gp: continue
                s1 = s2 = 0
                def _lev(t_): return (1 if t_.get("bridge") not in (None, "no") else 0) - (1 if t_.get("tunnel") not in (None, "no") else 0) + float(t_.get("layer", 0) or 0)
                for G_ in gp:
                    near = []
                    for w_ in _R:
                        ps_ = [_P[n_] for n_ in w_["nodes"]]
                        if len(ps_) < 2: continue
                        lw = _L2(ps_)
                        if lw.distance(G_) > 60: continue
                        near.append((w_, lw))
                    for ia in range(len(near)):
                        for ib in range(ia + 1, len(near)):
                            (wa, la), (wb, lb) = near[ia], near[ib]
                            if set(wa["nodes"]) & set(wb["nodes"]) or not la.crosses(lb): continue
                            va, vb = _lev(wa["tags"]), _lev(wb["tags"])
                            if va == vb: continue
                            # welche gehört zu welcher Strecke
                            da = _L2(g1).distance(la) - _L2(g2).distance(la); db = _L2(g1).distance(lb) - _L2(g2).distance(lb)
                            if da < db: s1, s2 = va, vb
                            else: s1, s2 = vb, va
                            if os.environ.get("KRDBG"): print("    Paar", wa["id"], wb["id"], va, vb, round(da), round(db))
                if s1 == s2:
                    if os.environ.get("KRDBG"): print("  Kreuzung ohne OSM-Ebene", nodes[r1["a"]]["name"], nodes[r1["b"]]["name"], "/", nodes[r2["a"]]["name"], nodes[r2["b"]]["name"], X.round())
                    continue
                # Lage "kreuzung_tausch" [[x, y], ...]: oben/unten an dieser Kreuzung tauschen (Ortskenntnis; Rothrist Ost 20.10.:
                # 3/2 Richtung Borntunnel laufen über 4, OSM führt den Tunnel-Way schon an der Kreuzung)
                if any(np.linalg.norm(X - np.asarray(q_, float)) < 45 for q_ in OVR_LAGE.get("kreuzung_tausch", [])): s1, s2 = s2, s1
                (ro, Lo, co, wo), (ru, Lu, cu, wu) = (RLINES[i1], RLINES[i2]) if s1 > s2 else (RLINES[i2], RLINES[i1])
                def richtung(Ls):
                    best = None
                    for l in Ls:
                        for a, b in zip(l, l[1:]):
                            sg = _L2([a, b]); d = sg.distance(_Pt2(X))
                            if best is None or d < best[0]: best = (d, (b - a) / (np.linalg.norm(b - a) or 1))
                    return best[1]
                uo = richtung(Lo); no = np.array([-uo[1], uo[0]])
                uu = richtung(Lu)
                # Breite der oberen Strecke am Kreuzungspunkt
                offs = []
                for l in Lo:
                    p_ = _L2(l).interpolate(_L2(l).project(_Pt2(X)))
                    offs.append(float((np.array([p_.x, p_.y]) - X) @ no))
                lo_, hi_ = min(offs) - 5, max(offs) + 5
                sn = abs(float(uu @ no)) or 1.0
                half = (hi_ - lo_) / 2 / sn + 3; cm = X + no * (lo_ + hi_) / 2
                for l in Lu:      # untere Strecke: Lücke (nur Gleise, die die obere Strecke wirklich kreuzen; Rothrist 20.10.)
                    if len(l) < 2 or not any(len(l2_) > 1 and _L2(l).intersects(_L2(l2_)) for l2_ in Lo): continue
                    p_ = _L2(l).interpolate(_L2(l).project(_Pt2(cm)))
                    pc = np.array([p_.x, p_.y])
                    out.append(f'<path d="M{(pc - uu * half)[0]:.1f},{(pc - uu * half)[1]:.1f}L{(pc + uu * half)[0]:.1f},{(pc + uu * half)[1]:.1f}" stroke="#fff" stroke-width="{wu + 3.5:.1f}" fill="none"/>')
                for l in Lo:      # obere Strecke darüber neu
                    p_ = _L2(l).project(_Pt2(cm)); Ll = _L2(l)
                    from shapely.ops import substring as _sub
                    # Knick in der Nähe ganz mitnehmen (gleiche Ausrundung wie das Original, Rothrist 20.10.: Knubbel/Kerbe)
                    _cum = np.r_[0, np.cumsum(np.hypot(*np.diff(np.asarray(l, float), axis=0).T))][1:-1]
                    _q0, _q1 = p_ - half - 3, p_ + half + 3
                    for _ in range(4):
                        _q0 = min([_q0] + [v_ - 15 for v_ in _cum if _q0 - 15 < v_ < p_])
                        _q1 = max([_q1] + [v_ + 15 for v_ in _cum if p_ < v_ < _q1 + 15])
                    q = _sub(Ll, max(0, _q0), min(Ll.length, _q1))
                    path([np.array(c_) for c_ in q.coords], co, wo)
                ln_ = half * abs(float(uu @ uo)) + 6      # Brückenflügel beidseits der oberen Strecke
                for sg_, o_ in ((-1, lo_ - 1), (1, hi_ + 1)):
                    b0 = X + no * o_; a0 = b0 - uo * ln_; a1 = b0 + uo * ln_
                    path([a0 + no * sg_ * 4 - uo * 3, a0, a1, a1 + no * sg_ * 4 + uo * 3], BK, 1.2)
                n_br += 1
    print(f"  Kreuzungen mit Brücke: {n_br}")
if not os.environ.get("OHNE_KREUZUNG") and not OVR_LAGE.get("ohne_kreuzungen"): _kreuzungen()
# Planfenster der Spurpläne und Nebengleise/Spurwechsel auf der freien Strecke (17.10., Hinweis "zwischen Stuhl und Bank":
# Schafis, Serrières–Neuchâtel, Olten–Dulliken). Fenster: spurplan_schema.py mit SPUR_FENSTER=1 -> <bahnhof>_fenster.json
FEN_U = None; NEBEN_DONE = set(); NEBEN_N = [0]
if "_R" in globals():
    from shapely.geometry import LineString as _L5, Point as _P5
    from shapely.ops import unary_union as _uu5
    _fen = []
    for n_ in MAJOR:
        k_ = nodes[n_].get("inset")
        if not k_: continue
        f_ = k_.replace("_regional", "") + "_fenster.json"
        if os.path.exists(f_):
            F_ = json.load(open(f_))
            if len(F_["achse"]) > 1: _fen.append(_L5([_xy(a, b) for a, b in F_["achse"]]).buffer(F_["d_lim"], cap_style=2))
    if _fen: FEN_U = _uu5(_fen)
def in_plan(p):
    return FEN_U is not None and FEN_U.contains(p)
def _nebengleise():
    if "_R" not in globals() or FEN_U is None: return
    NEBEN_DONE.update(x_["way"] for v_ in XO.values() for x_ in v_ if x_.get("gez"))     # schon als Spurwechsel gezeichnet
    wl = {w_["id"]: _L5([_P[n_] for n_ in w_["nodes"]]) for w_ in _R if len(w_["nodes"]) > 1}
    wby = {w_["id"]: w_ for w_ in _R}
    rl_by = {id(r_): (L_, c_, w_) for r_, L_, c_, w_ in RLINES}
    for r in routes:
        _CUR[0] = r
        gp = _RPT.get(id(r))
        if gp is None or len(gp) < 2 or id(r) not in rl_by: continue
        G = _L5(gp); L = G.length
        lines, col, wd = rl_by[id(r)]
        if not lines: continue
        lines = [np.asarray(l_, float)[::-1] if math.dist(l_[0], pos[r["a"]]) > math.dist(l_[-1], pos[r["a"]]) else np.asarray(l_, float)
                 for l_ in lines]                     # jede Linie von a nach b
        # Hauptgleise dieser Strecke (OSM), ausserhalb der Spurpläne
        mains = []
        for w_ in _R:
            if w_["tags"].get("service"): continue
            ln = wl.get(w_["id"])
            if ln is None or ln.length < 50 or ln.distance(G) > 40: continue
            pp = [_P[n_] for n_ in w_["nodes"]]
            if sum(1 for q_ in pp if G.distance(_P5(q_)) < 40) >= 0.5 * len(pp): mains.append(w_)
        main_n = {}
        for w_ in mains:
            for n_ in w_["nodes"]: main_n.setdefault(n_, w_["id"])
        # freier Bereich in s: zwischen den Planfenstern der beiden Enden
        ss = np.arange(0, L, 10.0); free = [s_ for s_ in ss if not in_plan(G.interpolate(s_))]
        if len(free) < 3: continue
        sA, sB = min(free), max(free)
        def plan_at(s_, off=0.0):
            t_ = min(max((s_ - sA) / ((sB - sA) or 1), 0.0), 1.0)
            return _at(lines[0], t_)
        def geo_side(pt, s_):
            a_ = G.interpolate(max(s_ - 15, 0)); b_ = G.interpolate(min(s_ + 15, L))
            d_ = np.array([b_.x - a_.x, b_.y - a_.y]); v_ = np.array([pt[0] - a_.x, pt[1] - a_.y])
            return float(d_[0] * v_[1] - d_[1] * v_[0])          # >0 links (Karte, y nach Norden)
        # Komponenten aus Nebengleisen (service), die an Hauptgleise dieser Strecke anschliessen
        svc = [w_ for w_ in _R if w_["tags"].get("service") and w_["id"] not in NEBEN_DONE and wl.get(w_["id"]) is not None
               and wl[w_["id"]].distance(G) < 120]
        adj = collections.defaultdict(set)
        for w_ in svc:
            for n_ in w_["nodes"]: adj[n_].add(w_["id"])
        seen = set()
        for w0 in svc:
            if w0["id"] in seen: continue
            comp, todo = set(), [w0["id"]]
            while todo:
                x_ = todo.pop()
                if x_ in comp: continue
                comp.add(x_)
                for n_ in wby[x_]["nodes"]: todo += [y for y in adj[n_] if y not in comp]
            seen |= comp
            _hand = [h_ for h_ in L0.get("nebengleis_hand", []) if comp & set(h_["weg"])]
            if _hand:      # von Hand (Olten Ost 20.10.: Anschluss aus dem 531-Gleis Richtung Hauenstein)
                NEBEN_DONE.update(comp)
                for h_ in _hand:
                    if h_.get("_gez") or not h_.get("pts"): continue        # leere pts: Nebengleis bewusst weglassen
                    h_["_gez"] = True; path([np.array(p_, float) for p_ in h_["pts"]], BK, 1.3)
                    if h_.get("punkt", True): out.append(f'<circle cx="{h_["pts"][-1][0]:.1f}" cy="{h_["pts"][-1][1]:.1f}" r="2.4" fill="{BK}"/>')
                    NEBEN_N[0] += 1
                continue
            att = [n_ for x_ in comp for n_ in wby[x_]["nodes"] if n_ in main_n]
            if not att: continue
            pts_all = [_P[n_] for x_ in comp for n_ in wby[x_]["nodes"]]
            if any(in_plan(_P5(_P[n_])) for n_ in att): continue           # Anschluss liegt im Spurplan: dort gezeichnet
            s_att = sorted({round(G.project(_P5(_P[n_])), 1) for n_ in att})
            s_all = [min(max(G.project(_P5(q_)), sA), sB) for q_ in pts_all if not in_plan(_P5(q_))] or [G.project(_P5(_P[att[0]]))]
            NEBEN_DONE.update(comp)
            tracks_att = {main_n[n_] for n_ in att}
            if os.environ.get("NBDBG"): print("NB", nodes[r["a"]]["name"], nodes[r["b"]]["name"], sorted(comp), tracks_att, round(min(s_all)), round(max(s_all)), round(sA), round(sB))
            # Spurwechsel: kurze Verbindung zwischen zwei verschiedenen Hauptgleisen
            if len(tracks_att) >= 2 and len(lines) >= 2 and max(s_all) - min(s_all) < 400:
                sides = sorted(((geo_side(_P[n_], G.project(_P5(_P[n_]))), G.project(_P5(_P[n_])), main_n[n_]) for n_ in att))
                (_, s_r, w_r), (_, s_l, w_l) = sides[0], sides[-1]          # rechtes / linkes Gleis (Karte)
                tm = (np.mean([s_l, s_r]) - sA) / ((sB - sA) or 1)
                if not 0.03 < tm < 0.97: continue
                # Rang der beiden Gleise unter den OSM-Hauptgleisen an dieser Stelle (von rechts nach links)
                sm_ = float(np.mean([s_l, s_r])); pm_ = G.interpolate(sm_)
                here = sorted({w_["id"]: geo_side(np.array(wl[w_["id"]].interpolate(wl[w_["id"]].project(pm_)).coords[0]), sm_)
                               for w_ in mains if wl[w_["id"]].distance(pm_) < 8 + 5 * len(lines)}.items(), key=lambda t_: t_[1])
                rk = [w for w, _ in here]
                if w_r not in rk or w_l not in rk or len(rk) != len(lines):
                    if len(lines) != 2: NEBEN_DONE.difference_update(comp); continue      # Zuordnung unsicher: bleibt Befund in Prüfung 4
                    i_r, i_l = 0, 1
                else: i_r, i_l = rk.index(w_r), rk.index(w_l)
                # Linien quer sortieren (Plan-Normale), links in der Karte = Plan-Normale gespiegelt (y nach unten)
                p0, d0 = _at(lines[0], tm); nv = np.array([d0[1], -d0[0]])     # Plan-Links bei y nach unten
                order = sorted(range(len(lines)), key=lambda j: float((_at(lines[j], tm)[0] - p0) @ nv))
                if i_r == i_l: continue
                Lr, Ll = lines[order[i_r]], lines[order[i_l]]
                # gleiche Stelle auf beiden Linien über Projektion (Linien sind verschieden lang)
                L1, L2 = (Lr, Ll) if s_r < s_l else (Ll, Lr)
                g1, g2 = _L5(L1), _L5(L2)
                pc = _P5(_at(lines[order[0]], tm)[0]); c1 = g1.project(pc); c2 = g2.project(pc)
                dq = g1.interpolate(c1).distance(g2.interpolate(c2)); run = dq / TAN60
                a1 = c1 - run / 2
                # Gegenstück über Projektion (gegenläufige Linien, Ligerz 20.10.: steiler Z-Spurwechsel)
                pts_ = [g1.interpolate(a1 - 7), g1.interpolate(a1), g2.interpolate(g2.project(g1.interpolate(a1 + run))),
                        g2.interpolate(g2.project(g1.interpolate(a1 + run + 7)))]
                path([np.array(q_.coords[0]) for q_ in pts_], BK, 1.3)
                NEBEN_N[0] += 1; continue
            # Nebengleis / Anschluss: parallel neben dem äussersten Gleis auf seiner Seite
            sd = np.sign(np.mean([geo_side(q_, G.project(_P5(q_))) for q_ in pts_all])) or 1.0
            sa_, sb_ = min(s_all), max(s_all)
            ta, tb = (sa_ - sA) / ((sB - sA) or 1), (sb_ - sA) / ((sB - sA) or 1)
            if tb - ta < 0.02: tb = min(ta + 0.04, 0.98)
            ta, tb = max(ta, 0.03), min(tb, 0.97)
            pm, dm = _at(lines[0], (ta + tb) / 2); nv = np.array([dm[1], -dm[0]]) * sd       # Seite im Plan
            # äusserstes Gleis auf der Seite: geometrisch quer an derselben Stelle (Linien sind verschieden lang, Ligerz 20.10.)
            _pmP = _P5(tuple(pm))
            j_out = max(range(len(lines)), key=lambda j: float((np.array(_L5([tuple(q_) for q_ in lines[j]]).interpolate(
                _L5([tuple(q_) for q_ in lines[j]]).project(_pmP)).coords[0]) - pm) @ nv))
            Lo = lines[j_out]
            Lpx = float(np.sum(np.hypot(*np.diff(np.asarray(Lo, float), axis=0).T))) or 1
            off = 0.8 * TG; run = (off / TAN60) / Lpx
            def offp(t_):
                p_, d_ = _at(Lo, t_); n_ = np.array([d_[1], -d_[0]]) * sd
                if float(n_ @ nv) < 0: n_ = -n_          # Lo gegenläufig zu lines[0] (Ligerz 20.10.: Stummel quer über das Nachbargleis)
                return p_ + n_ * off
            ends_att = [(G.project(_P5(_P[n_])) - sA) / ((sB - sA) or 1) for n_ in att]
            a_att = any(abs(t_ - ta) < 0.03 for t_ in ends_att); b_att = any(abs(t_ - tb) < 0.03 for t_ in ends_att)
            if not b_att and not a_att: a_att = True
            _mn = 2 * run + 10 / Lpx                       # kurzer Stumpen: nicht zurückknicken (Aarburg 19.10.: Haken 90°)
            if tb - ta < _mn:
                if a_att and not b_att: tb = min(ta + _mn, 0.97); ta = min(ta, tb - _mn)
                elif b_att and not a_att: ta = max(tb - _mn, 0.03); tb = max(tb, ta + _mn)
                else: ta, tb = max(0.03, (ta + tb) / 2 - _mn / 2), min(0.97, (ta + tb) / 2 + _mn / 2)
            def _seq(ta, tb):
                q = []
                if a_att: q += [_at(Lo, ta)[0]]
                q += [offp(ta + (run if a_att else 0))] + [offp(t_) for t_ in np.linspace(ta + run, tb - run, 6)[1:-1]] + [offp(tb - (run if b_att else 0))]
                if b_att: q += [_at(Lo, tb)[0]]
                return q
            # Regel R3 (Reihenfolge, Schafis 21.10.: "Anschlussgleis auf der Seite Biel der beiden Spurwechsel"): ein Nebengleis
            # bleibt auf derselben Seite jedes Spurwechsels dieser Strecke wie in OSM
            _ta0, _tb0 = ta, tb
            _LoL = _L5([tuple(q_) for q_ in Lo])
            _xo_t = [((xo_["t"] * L - sA) / ((sB - sA) or 1), _LoL.project(_P5(tuple(xo_["mid"]))) / Lpx) for xo_ in XO.get(id(r), []) if "mid" in xo_]
            if os.environ.get("ORDDBG") and _xo_t: print("ORD", nodes[r["a"]]["name"], nodes[r["b"]]["name"], round(_ta0,3), round(_tb0,3), [(round(a,3), round(b,3)) for a, b in _xo_t], a_att, b_att)
            def _ordnung_ok(q):
                t0_ = _LoL.project(_P5(tuple(q[0]))) / Lpx; t1_ = _LoL.project(_P5(tuple(q[-1]))) / Lpx
                lo_, hi_ = min(t0_, t1_), max(t0_, t1_); m_ = (4 + TG) / Lpx
                for tg_, tx_ in _xo_t:
                    if _tb0 < tg_ and hi_ > tx_ - m_: return False
                    if _ta0 > tg_ and lo_ < tx_ + m_: return False
                return True
            def _stoert(q):
                if not _ordnung_ok(q): return True
                sq_ = _L5([tuple(q_) for q_ in q]).buffer(5.5)
                # nicht im Spurwechsel abzweigen (Ligerz 20.10.: "nach dem Spurwechsel raus", wirkte wie Kreuzung)
                if any(np.linalg.norm(np.asarray(q_, float) - x_) < 4 + TG for x_ in _XOPTS for q_ in (q[0], q[-1])): return True
                return any(_L5(l_).intersects(sq_) for r2_, L2_, _c, _w in RLINES for l_ in L2_ if len(l_) > 1 and l_ is not Lo
                           and not (r2_ is r and len(l_) == len(Lo) and np.allclose(l_, Lo))) or \
                       _L5([tuple(q_) for q_ in q[1:-1]] if len(q) > 3 else [tuple(q_) for q_ in q]).distance(_L5([tuple(q_) for q_ in Lo])) > 2 * TG
            seq = _seq(ta, tb)
            if _stoert(seq):
                # nicht weglassen (Aarburg 20.10.: "dazwischen geht noch ein Gleisanschluss raus"): entlang der Strecke
                # verschieben, bis er frei liegt (Weiche sichtbar vor genauer Lage)
                ok_ = False
                for sh_ in [k_ * sg_ for k_ in np.arange(0.02, 0.5, 0.02) for sg_ in (-1, 1)]:
                    ta2, tb2 = ta + sh_, tb + sh_
                    if ta2 < 0.03 or tb2 > 0.97: continue
                    q2 = _seq(ta2, tb2)
                    if not _stoert(q2): seq, ok_ = q2, True; break
                    if os.environ.get("NBDBG3"): print("NB3", round(sh_,2), np.round(q2[0],1), np.round(q2[-1],1))
                if not ok_:
                    # kürzer zeichnen (Schafis 21.10.: Platz zwischen Spurwechsel und Bahnhof knapp, Reihenfolge geht vor Länge)
                    for f_ in (0.6, 0.4, 0.25):
                        ln_ = max(_mn, (tb - ta) * f_)
                        for c_ in np.arange(0.04, 0.96, 0.01):
                            ta2, tb2 = c_ - ln_ / 2, c_ + ln_ / 2
                            if ta2 < 0.03 or tb2 > 0.97: continue
                            q2 = _seq(ta2, tb2)
                            if not _stoert(q2): seq, ok_ = q2, True; break
                        if ok_: break
                if not ok_:
                    if os.environ.get("NBDBG3"): print("NB3 weg", nodes[r["a"]]["name"], nodes[r["b"]]["name"])
                    continue
            if os.environ.get("NBDBG"): print("NBSEQ", np.round(seq[0],1), np.round(seq[-1],1), [round(_L5(l_).distance(_sq), 1) for r2_, L2_, _c, _w in RLINES for l_ in L2_ if len(l_) > 1 and _L5(l_).distance(_sq) < 10])
            if os.environ.get("NBDBG2"): print("NB2", nodes[r["a"]]["name"], nodes[r["b"]]["name"], sorted(comp), sorted(tracks_att), [list(np.round(q_, 1)) for q_ in seq], "j_out", j_out, len(lines), "sd", sd, a_att, b_att, round(ta, 3), round(tb, 3))
            path(seq, BK, 1.3)
            if not (a_att and b_att):          # Stumpengleis: Endpunkt
                q_ = seq[-1] if a_att else seq[0]
                out.append(f'<circle cx="{q_[0]:.1f}" cy="{q_[1]:.1f}" r="2.4" fill="{BK}"/>')
            NEBEN_N[0] += 1
    print(f"  Nebengleise/Spurwechsel freie Strecke gezeichnet: {NEBEN_N[0]}")
if not L0.get("ohne_nebengleise"): _nebengleise()
_CUR[0] = None
for (eid_, n_), a_ in anchor.items():
    if n_ not in pos: continue
    for p, q in a_.get("ext", []):
        if np.linalg.norm(p - q) > 1: path([pos[n_] + q, pos[n_] + p], G if a_["pax"] else BK, 2.4 if a_["pax"] else 1.3)
from shapely.geometry import LineString as _LS2, box as _box
def _lab_hits(lab, txt, anc, size=12):
    w_ = 0.56 * size * len(txt); x0 = lab[0] - (w_ if anc == "end" else w_ / 2 if anc == "middle" else 0)
    b_ = _box(x0 - 2, lab[1] - 0.75 * size, x0 + w_ + 2, lab[1] + 0.3 * size)
    hits = sum(1 for q in POLYS if len(q) > 1 and _LS2(q).intersects(b_))
    hits += sum(3 for bb in boxes().values() if _box(*bb).intersects(b_))
    return hits + sum(2 for t_ in LABS if t_.intersects(b_)), b_
LABS = []
for hi_, (n, (p, d, k)) in enumerate(HALT_AT.items()):
    nv = np.array([-d[1], d[0]]); half = (k - 1) / 2 * TG
    if k == 1:          # Seite mit weniger Überlagerung wählen
        def _cand(nv_):
            lab_ = p + nv_ * (half + 20); anc_ = "middle" if abs(nv_[0]) < 0.4 else ("start" if nv_[0] > 0 else "end")
            return _lab_hits(lab_ + np.array([0, 4]), nodes[n]["name"], anc_)[0]
        if _cand(-nv) < _cand(nv): nv = -nv
    nt = nodes[n].get("tracks", 1) or 1
    if k == 1 and nt >= 2:
        L_ = 30; run = TG / TAN60 + 3
        path([p - d * L_, p - d * (L_ - run) + nv * TG, p + d * (L_ - run) + nv * TG, p + d * L_], G, 2.4)
        for o in (-6, TG + 6): path([p - d * 15 + nv * o, p + d * 15 + nv * o], G, 4.2)
        lab = p + nv * (TG + 20)
    else:
        for o in ((-(half + 6), half + 6) if k >= 2 else (half + 6,)): path([p - d * 14 + nv * o, p + d * 14 + nv * o], G, 4.2)
        lab = p + nv * (half + 20)
    anc = "middle" if abs(nv[0]) < 0.4 else ("start" if nv[0] > 0 else "end")
    text(lab[0], lab[1] + 4, nodes[n]["name"], 12, anc)
    LABS.append(_lab_hits(lab + np.array([0, 4]), nodes[n]["name"], anc)[1])
for n in [n for n in MAJOR if nodes[n]["kind"] == "exit"]:
    r = next(r for r in routes if n in (r["a"], r["b"])); other = r["b"] if r["a"] == n else r["a"]
    v = pos[n] - pos[other]; v = v / (np.linalg.norm(v) or 1); v = max(DV, key=lambda q: q @ v)
    p = pos[n] + v * 12
    arrow = "→" if v[0] > 0.3 else ("←" if v[0] < -0.3 else ("↑" if v[1] < 0 else "↓"))
    anc = "start" if v[0] > 0.3 else ("end" if v[0] < -0.3 else "middle")
    dy = -5 if abs(v[1]) < 0.7 else (-22 if v[1] < 0 else 14)
    text(p[0], p[1] + dy, f"Linie {nodes[n].get('ref', '')}", 13, anc)
    town = nodes[n].get("town") or ""
    text(p[0], p[1] + dy + 16, (f"{arrow} {town}" if anc == "end" else f"{town} {arrow}").strip(), 13, anc)

# Regel «Schwarz hinter grün» (Hinweis Region Olten 19.10.): schwarze Linien (Spurwechsel, Nebengleise, Klammern) unter die grünen
_gi = next((i_ for i_, o_ in enumerate(out) if o_.startswith("<path") and f'stroke="{G}"' in o_), None)
if _gi is not None and not L0.get("schwarz_oben"):
    _bk = [o_ for o_ in out[_gi:] if o_.startswith("<path") and f'stroke="{BK}"' in o_ and 'fill="none"' in o_ and 'stroke-width="1.3"' in o_]
    _bks = set(map(id, _bk))
    out = out[:_gi] + _bk + [o_ for o_ in out[_gi:] if id(o_) not in _bks]
# Tunnelportale ganz nach vorn (über Grün)
_pt = [o_ for o_ in out if o_.startswith("<path") and f'stroke="{PORTAL}"' in o_]
if _pt: _pts_ = set(map(id, _pt)); out = [o_ for o_ in out if id(o_) not in _pts_] + _pt
xs = [float(v) for v in re.findall(r'[MLQ ](-?[\d.]+),', "".join(out))] + [p[0] for p in pos.values()]
ys = [float(v) for v in re.findall(r'[MLQ ]-?[\d.]+,(-?[\d.]+)', "".join(out))] + [p[1] for p in pos.values()]
bx = boxes()
xs += [b[0] for b in bx.values()] + [b[2] for b in bx.values()]; ys += [b[1] for b in bx.values()] + [b[3] for b in bx.values()]
minx, maxx, miny, maxy = min(xs) - 200, max(xs) + 200, min(ys) - 140, max(ys) + 120
W, H = maxx - minx, maxy - miny
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx:.0f} {miny:.0f} {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
       f'font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif"><rect x="{minx:.0f}" y="{miny:.0f}" width="{W:.0f}" height="{H:.0f}" fill="#fff"/>'
       + "".join(out) + f'<text x="{minx + 40:.0f}" y="{miny + 56:.0f}" font-size="32" font-weight="700" fill="{G}">{TITLE}</text>'
       f'<text x="{maxx - 40:.0f}" y="{maxy - 20:.0f}" font-size="12" text-anchor="end" fill="#888">Gleisdaten © OpenStreetMap-Mitwirkende (ODbL) · schematisch, nicht massstäblich</text></svg>')
open(OUTF, "w").write(svg)
print("ok", round(W), round(H))
if "--info" in sys.argv:
    for r in routes:
        def side(n, e):
            a_ = anchor.get((id(e), n))
            if not a_: return nodes[n]["kind"]
            v = a_["v"]; return ("rechts" if v[0] > 0.6 else "links" if v[0] < -0.6 else ("schräg-oben" if v[1] < 0 else "schräg-unten") + ("-re" if v[0] > 0 else "-li")) + f" x{a_['off'][0]:+.0f} y{a_['off'][1]:+.0f}"
        print(f"#{r['a']}-#{r['b']} {nodes[r['a']]['name']:18s} [{side(r['a'], r['first'])}]  →  {nodes[r['b']]['name']:18s} [{side(r['b'], r['last'])}]  Gleise {r['tracks']}  {round(r['length'])} m  via {[nodes[x]['name'] for x in r['seq'][1:-1]]}")

# ------------------------------------------------------------------ Prüfungen (--pruefen)
if "--pruefen" in sys.argv:
    nm = lambda n: nodes[n]["name"] + ("" if nodes[n]["inset"] else f" #{n}")
    print("\n== Prüfung 1: Gleise entlang der Strecken ==")
    bad1 = 0
    for r in routes:
        ends = []
        for n, e in ((r["a"], r["first"]), (r["b"], r["last"])):
            a_ = anchor.get((id(e), n)); ends.append(len(a_["pts"]) if a_ else None)
        topo = min(6, r["tracks"]); drawn = rtracks(r)
        msg = []
        if drawn != topo: msg.append(f"gezeichnet {drawn} statt {topo} Gleise (OSM-Querschnitt)")
        for (n, cnt) in zip((r["a"], r["b"]), ends):
            if cnt is not None and cnt != drawn: msg.append(f"{nm(n)}: {cnt} Anschlüsse für {drawn} Gleise")
        if msg:
            bad1 += 1; print(f"  {nm(r['a'])} – {nm(r['b'])}: " + "; ".join(msg))
    for i in [i for i in ids if nodes[i]["inset"]]:
        used = {k for (eid, n), a_ in anchor.items() if n == i for k in range(len(a_["pts"]))}
        P_ = PORTS[i]["ports"]; nused = sum(len(a_["pts"]) for (eid, n), a_ in anchor.items() if n == i)
        if nused < len(P_):
            bad1 += 1; print(f"  {nodes[i]['name']}: {len(P_) - nused} Abgänge des Spurplans ohne Strecke")
    for n in [n for n in MAJOR if nodes[n]["kind"] == "junction"]:
        sides = collections.defaultdict(set)
        for r in routes:
            if n not in (r["a"], r["b"]): continue
            lanes = JLANE.get((n, id(r)), [])
            o = r["b"] if r["a"] == n else r["a"]
            ax_ = 1 if f"#{n}" in L0.get("senkrecht", []) else 0
            sides[pos[o][ax_] > pos[n][ax_]] |= set(lanes)
        if len(sides) == 2 and sides[True] != sides[False]:
            bad1 += 1; print(f"  {nm(n)}: Spuren nur auf einer Seite {sorted(sides[True] ^ sides[False])}")
    for (n_, p_), lst in LANE_REFS.items():
        sides_ = {sd for sd, *_ in lst}
        if len(sides_) < 2: continue
        known = [(sd, rf, o) for sd, rf, rr, o in lst if rf]
        for sd, rf, o in known:
            other = [(rr, o2) for sd2, rf2, rr, o2 in lst if sd2 != sd]
            if other and not any(rf in rr for rr, _ in other):
                print(f"  Hinweis {nm(n_)}: Gleis der Linie {rf} (von {o}) wechselt auf {', '.join(o2 for _, o2 in other)} ({'/'.join(sorted(set().union(*[rr for rr, _ in other])))})")
    for (a_, b_), nx_ in ROUTE_X.items():
        if nx_: bad1 += 1; print(f"  {nm(a_)} – {nm(b_)}: Gleise kreuzen sich {nx_}× (Fahrrichtungsseite wechselt)")
    print(f"  → {bad1} Befunde")
    print("\n== Prüfung 2: Lage Nord/Süd und Ost/West gegenüber Geografie ==")
    bad2 = []
    for i, a in enumerate(MAJOR):
        for b in MAJOR[i + 1:]:
            gx = nodes[b]["x"] - nodes[a]["x"]; gy = nodes[b]["y"] - nodes[a]["y"]; gd = math.hypot(gx, gy)
            if gd < 1500: continue
            px_, py_ = pos[b][0] - pos[a][0], -(pos[b][1] - pos[a][1])
            if abs(gy) > 0.5 * gd and abs(gy) > 1500 and py_ * gy < 0 and abs(py_) > 60:
                bad2.append((abs(gy), f"{nm(b)} liegt {abs(gy)/1000:.1f} km {'nördlich' if gy > 0 else 'südlich'} von {nm(a)}, im Plan {'darunter' if gy > 0 else 'darüber'}"))
            if abs(gx) > 0.5 * gd and abs(gx) > 1500 and px_ * gx < 0 and abs(px_) > 60:
                bad2.append((abs(gx), f"{nm(b)} liegt {abs(gx)/1000:.1f} km {'östlich' if gx > 0 else 'westlich'} von {nm(a)}, im Plan {'links' if gx > 0 else 'rechts'} davon"))
    for _, m in sorted(bad2, reverse=True): print("  " + m)
    print(f"  → {len(bad2)} Befunde")
    # ---------------------------------------------------------------- Prüfung 3: Achs- und Seitenlage gegen die Karte
    print("\n== Prüfung 3: Achsen und Seiten der Spurpläne gegen die Karte ==")
    bad3 = 0
    def geo(p): return np.array([(p["lon"] - 7.9) * 75500, (p["lat"] - 47.35) * 111200])
    def plan_map(v): return np.array([v[0], -v[1]])          # SVG (y nach unten) -> Kartenrichtung (y nach Norden)
    def compass(v):
        a = math.degrees(math.atan2(v[0], v[1])) % 360
        return ["N", "NO", "O", "SO", "S", "SW", "W", "NW"][int((a + 22.5) // 45) % 8]
    for i in [i for i in ids if nodes[i]["inset"]]:
        P_ = PORTS[i]; ports = [p for p in P_["ports"] if "lat" in p]
        if not ports: continue
        cx = (P_["x_lo"] + P_["x_hi"]) / 2; cy = (P_["y_lo"] + P_["y_hi"]) / 2; r_ = ROT.get(i, 0)
        R_ = [geo(p) for p in ports if p["kind"] == "edge" and p["dx"] > 0]; L_ = [geo(p) for p in ports if p["kind"] == "edge" and p["dx"] < 0]
        if not R_ or not L_: continue
        sg_ = np.mean(R_, 0) - np.mean(L_, 0); sg_ /= np.linalg.norm(sg_)
        sp_ = plan_map(rotv(np.array([1.0, 0.0]), r_))
        ang = math.degrees(math.acos(max(-1, min(1, float(sg_ @ sp_)))))
        name = nodes[i]["name"]
        if ang > 60:
            bad3 += 1; print(f"  {name}: Achse zeigt im Plan nach {compass(sp_)}, auf der Karte nach {compass(sg_)} ({ang:.0f}°)")
        # Seitenlage: Abgänge am selben Ende / seitliche Abgänge links oder rechts der Achse wie auf der Karte?
        cg = np.mean([geo(p) for p in ports], 0)
        cp = np.mean([plan_map(rotv(np.array([(p["x"] - cx) * S, (p["y"] - cy) * S]), r_)) for p in ports], 0)
        for end in (1, -1):
            E_ = [p for p in ports if (p["kind"] == "edge" and p["dx"] == end)]
            if len(E_) < 2: continue
            for a in range(len(E_)):
                for b in range(a + 1, len(E_)):
                    pa_, pb_ = E_[a], E_[b]
                    if abs(float(sg_ @ (geo(pb_) - geo(pa_)))) > 40: continue      # nur Abgänge auf gleicher Höhe vergleichen
                    gside = float(_cr(sg_, geo(pb_) - geo(pa_)))
                    pside = float(_cr(sp_, plan_map(rotv(np.array([(pb_["x"] - pa_["x"]) * S, (pb_["y"] - pa_["y"]) * S]), r_))))
                    if abs(gside) > 8 and abs(pside) > 3 and gside * pside < 0:
                        bad3 += 1
                        print(f"  {name}: Abgang {pb_['ref']} ({pb_['town']}) liegt auf der Karte {'links' if gside > 0 else 'rechts'} von {pa_['ref']} ({pa_['town']}), im Plan {'links' if pside > 0 else 'rechts'} (Blick in Achsrichtung)")
        for p in [p for p in ports if p["kind"] == "side"]:
            gside = float(_cr(sg_, geo(p) - cg))
            pside = float(_cr(sp_, plan_map(rotv(np.array([(p["x"] - cx) * S, (p["y"] - cy) * S]), r_)) - cp))
            if abs(gside) > 30 and gside * pside < 0:
                bad3 += 1; print(f"  {name}: seitlicher Abgang {p['ref']} ({p['town']}) liegt auf der Karte {'links' if gside > 0 else 'rechts'} der Achse, im Plan auf der anderen Seite")
    # Strecken an derselben Spurplanseite: Reihenfolge wie auf der Karte?
    for (n, vk), lst in _grp.items():
        if len(lst) < 2 or not nodes[n]["inset"]: continue
        v = np.array(vk, float); nrm = np.array([-v[1], v[0]])
        def gdir(r, n):
            e = r["first"] if r["a"] == n else r["last"]
            g = e["geom"]; p0 = np.array([nodes[n]["x"], nodes[n]["y"]])
            if math.dist(g[0], p0) > math.dist(g[-1], p0): g = g[::-1]
            L = 0; q = np.array(g[0])
            for pt in g[1:]:
                L += math.dist(q, pt); q = np.array(pt)
                if L > 1500: break
            return q - np.array(g[0])
        nrm_map = plan_map(nrm)
        order_plan = sorted(lst, key=lambda t: float(STACK.get(t[0], t[3]["off"]) @ nrm))
        # Kartenreihenfolge: Richtung der Strecke 1.5 km weg, quer zur Austrittsrichtung (in Karten-Koordinaten)
        vmap = plan_map(v)
        def gkey(t):
            d = gdir(t[1], n); return float(_cr(vmap, d))     # >0 = links der Austrittsrichtung
        order_geo = sorted(lst, key=lambda t: -gkey(t))
        if [t[0] for t in order_plan] != [t[0] for t in order_geo]:
            a_ = [nm(t[2]) for t in order_plan]; b_ = [nm(t[2]) for t in order_geo]
            bad3 += 1; print(f"  {nodes[n]['name']}: Strecken-Reihenfolge an einer Seite im Plan {a_}, auf der Karte {b_}")
    print(f"  → {bad3} Befunde")

    # ---------------------------------------------------------------- Prüfung 4: freie Strecke gegen OSM (17.10.)
    # Hinweis D. Eckenstein: "Zwischen Regionalplan und Bahnhöfen können Dinge zwischen Stuhl und Bank fallen"
    # (Olten–Dulliken, Schafis, Serrières–Neuchâtel). Alles, was auf der freien Strecke liegt (nicht in einem
    # gezeichneten Spurplan), wird mit dem Regionalplan verglichen: Gleiszahl, Spurwechsel, Abzweige/Nebengleise.
    print("\n== Prüfung 4: freie Strecke gegen OSM ==")
    bad4 = 0; P4 = []
    if "_R" in globals():
        from shapely.geometry import LineString as _L4, Point as _P4
        from shapely.strtree import STRtree as _T4
        _wl = {w_["id"]: _L4([_P[n_] for n_ in w_["nodes"]]) for w_ in _R if len(w_["nodes"]) > 1}
        _wid = list(_wl); _tree = _T4([_wl[i] for i in _wid])
        _wby = {w_["id"]: w_ for w_ in _R}
        _FEN = {}
        for n_ in MAJOR:                      # Planfenster der Spurpläne (spurplan_schema.py mit SPUR_FENSTER=1)
            k_ = nodes[n_].get("inset")
            if not k_: continue
            f_ = k_.replace("_regional", "") + "_fenster.json"
            if os.path.exists(f_):
                F_ = json.load(open(f_))
                if len(F_["achse"]) > 1: _FEN[n_] = _L4([_xy(a, b) for a, b in F_["achse"]]).buffer(F_["d_lim"], cap_style=2)
        _FALL = _P4(0, 0).buffer(0)
        _FENU = None
        if _FEN:
            from shapely.ops import unary_union as _uu
            _FENU = _uu(list(_FEN.values()))
        print(f"  Planfenster: {len(_FEN)} von {sum(1 for n_ in MAJOR if nodes[n_].get('inset'))} Spurplänen")
        def _in_plan(p): return _FENU is not None and _FENU.contains(p)
        _xo_w = {x_["way"] for v_ in XO.values() for x_ in v_}
        _deg4 = collections.Counter(n_ for w_ in _R for n_ in w_["nodes"])
        for r in routes:
            g_poly = _RPT.get(id(r))
            if g_poly is None or len(g_poly) < 2: continue
            G = _L4(g_poly); L = G.length; k_draw = rtracks(r)
            cov = set()
            nm_ = f"{nodes[r['a']]['name']} – {nodes[r['b']]['name']}"
            runs = []; cur = None
            for s_ in np.arange(30, L - 30, 25.0):
                p = G.interpolate(s_); q = G.interpolate(min(s_ + 5, L)); d_ = np.array([q.x - p.x, q.y - p.y]); d_ /= (np.linalg.norm(d_) or 1)
                _rad = 8 + 5 * k_draw                 # Suchbreite je nach Gleiszahl (4 Gleise liegen bis 20 m auseinander)
                near = [_wid[i] for i in _tree.query(p.buffer(_rad))]
                near = [w for w in near if _wl[w].distance(p) < _rad]
                if _in_plan(p): cur = None; continue          # im Spurplan eines Bahnhofs
                par = []
                for w in near:
                    t_ = _wby[w]["tags"]
                    if t_.get("service") in ("yard", "spur", "siding", "crossover"): continue
                    ln = _wl[w]; s2 = ln.project(p); a_ = ln.interpolate(max(s2 - 6, 0)); b_ = ln.interpolate(min(s2 + 6, ln.length))
                    v_ = np.array([b_.x - a_.x, b_.y - a_.y]); v_ /= (np.linalg.norm(v_) or 1)
                    if abs(float(v_ @ d_)) > 0.94: par.append(w)
                k_osm = len(par)
                if k_osm == 0: cur = None; continue                          # Achse liegt neben den Gleisen (grobe Topologie)
                if cur and cur[2] == k_osm: cur[1] = s_
                else: cur = [s_, s_, k_osm]; runs.append(cur)
            for a_, b_, k_ in runs:
                if k_ != k_draw and b_ - a_ >= 75:
                    bad4 += 1; P4.append(dict(art="gleiszahl", strecke=nm_, s0=round(a_), s1=round(b_), osm=k_, plan=k_draw))
                    print(f"  {nm_}: {round(a_)}–{round(b_)} m ab {nodes[r['a']]['name']}: OSM {k_} Gleise, Plan {k_draw}")
            # Abzweige/Nebengleise und Spurwechsel auf der freien Strecke
            main_n = set()
            for w_ in _R:
                if w_["tags"].get("service") or w_["id"] in cov: continue
                ln = _wl.get(w_["id"])
                if ln is None or ln.length < 50 or ln.distance(G) > 40: continue
                _pp = [_P[n_] for n_ in w_["nodes"]]
                if sum(1 for q_ in _pp if G.distance(_P4(q_)) < 40) >= 0.5 * len(_pp): main_n |= set(w_["nodes"])
            for w_ in _R:
                t_ = w_["tags"]
                if w_["id"] in cov or not t_.get("service") or w_["id"] in _xo_w or w_["id"] in NEBEN_DONE: continue
                ends = [n_ for n_ in (w_["nodes"][0], w_["nodes"][-1]) if n_ in main_n]
                if not ends: continue
                pt = _P4(_P[ends[0]]); s_ = G.project(pt)
                if G.distance(pt) > 40 or s_ < 30 or s_ > L - 30 or _in_plan(pt): continue
                both = all(n_ in main_n for n_ in (w_["nodes"][0], w_["nodes"][-1]))
                art = "spurwechsel" if (both and t_.get("service") == "crossover") else "nebengleis"
                bad4 += 1; P4.append(dict(art=art, strecke=nm_, s=round(s_), way=w_["id"], service=t_.get("service"), name=t_.get("name")))
                print(f"  {nm_}: {round(s_)} m ab {nodes[r['a']]['name']}: {'Spurwechsel' if art == 'spurwechsel' else 'Nebengleis/Anschluss'} "
                      f"(Way {w_['id']}, {t_.get('service')}{', ' + t_['name'] if t_.get('name') else ''}) nicht im Plan")
        json.dump(P4, open(f"{NAME}_pruef4.json", "w"), ensure_ascii=False, indent=1)
    print(f"  → {bad4} Befunde")
