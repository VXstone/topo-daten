"""Hauptgleis-Topologie als Sperre (Schritt HT, Entscheid D. Eckenstein 18.11.2026: «Hauptgleise Weichen die weg gehen,
Hauptgleise Topologie immer korrekt, sprich korrekte Seite weg und korrekte Fahrwege»). REGELN 0.1 und Kopf «HT».

Anlass: Giesshübel (T-SZU) – der OSM-Abgleich meldete am Code-Plan 52 Befunde, gesperrt hat nur G0 (Geometrie); Schere statt
zweier Spurwechsel, fehlende Depot-Anschlüsse und Gl. 43 auf der falschen Seite fielen nur Daniel auf.

  python3 hauptgleis.py <plan.svg> <netz.json> --osm <schweiz_bahn.json.gz> [--json out.json]
  python3 hauptgleis.py --alle <plaene_dir> --netz-dir <dir> --osm <...> --out <ordner> [--basis hauptgleis_basis.json]
                        [--basis-setzen] [--abschnitt plaene|pruefstand] [--rekursiv]
  python3 hauptgleis.py --basis-aus <zaehlung.json> --basis <json> [--abschnitt …]
  python3 hauptgleis.py --selbsttest <faelle_dir> --osm <...>   (Prüffälle <name>.svg + <name>_netz.json + <name>.json)

Nur Pläne mit Netzmodell (<key>_netz.json aus spurplan_schema). Hauptgleis = grün (REGELN 1.21/1.24; im Netzmodell pax).
  HT1  OSM-Weiche an einem Hauptgleis ohne Abzweig im Plan (= VB1 aus osm_abgleich, Hauptgleis beteiligt)
  HT2  Abzweig an einem grünen Gleis im Plan ohne OSM-Weiche, z. B. Schere statt zweier Spurwechsel (= VB2, grün beteiligt)
  HT3  grünes Gleis an der falschen Weiche angebunden (= VC1, grün beteiligt)
  HT4  Abzweig zur falschen Seite: an einer OSM-Weiche mit Hauptgleis liegen die zwei Äste im Plan (Netzmodell-Lage) links/
       rechts vertauscht gegenüber OSM (in Fahrrichtung vom Weichenanfang her; REGELN 2.1)
  HT5  Fahrweg falsch: Menge der Fahrwege (ohne Richtungswechsel an einer Weiche) zwischen den Enden der Hauptgleise
       (Abgänge, Gleisenden) und zu den Perrongleisen, im GEZEICHNETEN Plan ≠ OSM (zusätzlich oder fehlend)
Sperre wie G0: mit --basis ist jede Zunahme einer Regel in einem Plan ein NEUER Befund -> Rückgabewert 1 (Workflow rot).

Fahrwege, Regel an einem Knoten (Plan und OSM gleich): die Äste werden nach der Hauptrichtung des Knotens in zwei Seiten
geteilt; man darf nur von einer Seite auf die andere wechseln (kein Richtungswechsel). An einer Kreuzung ohne Weiche (OSM
railway_crossing; im Plan Schnitt ohne DKW-Symbol) nur geradeaus (gleicher Way bzw. gleiche gezeichnete Linie).
"""
import argparse, collections, glob, gzip, json, math, os, sys
import numpy as np
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import osm_abgleich as OA

REGELN = ["HT1", "HT2", "HT3", "HT4", "HT5"]
TEXT = {"HT1": "OSM-Weiche am Hauptgleis ohne Abzweig im Plan", "HT2": "Abzweig am Hauptgleis im Plan ohne OSM-Weiche",
        "HT3": "Gleis an der falschen Weiche (Hauptgleis)", "HT4": "Abzweig zur falschen Seite",
        "HT5": "Fahrweg im Plan ≠ OSM"}
NICHT_PLAENE = {"fragen", "pruefstand"}

# ---------------------------------------------------------------- OSM
_OSM = {}
def osm_laden(pfad):
    """Tags (alle Knoten mit Tags), Way-Knotenlisten und Koordinaten aller Way-Knoten (aus der Way-Geometrie)"""
    if pfad in _OSM: return _OSM[pfad]
    D = json.load(gzip.open(pfad) if pfad.endswith(".gz") else open(pfad))
    T, W, K, WT = {}, {}, {}, {}
    for e in (D["elements"] if isinstance(D, dict) else D):
        if e["type"] == "node":
            T[e["id"]] = e.get("tags", {})
            if "lat" in e: K[e["id"]] = (e["lat"], e["lon"])
        elif e["type"] == "way":
            W[e["id"]] = e.get("nodes", []); WT[e["id"]] = e.get("tags", {})
            for n, g in zip(e.get("nodes", []), e.get("geometry") or []):
                if g: K.setdefault(n, (g["lat"], g["lon"]))
    _OSM[pfad] = (T, W, K, WT)
    return _OSM[pfad]


def _xy(ll, lat0):
    return np.array([ll[1] * 111320 * math.cos(math.radians(lat0)), ll[0] * 110540])


def _kreuz(a, b): return float(a[0] * b[1] - a[1] * b[0])


def _einheit(v):
    n = np.linalg.norm(v); return v / n if n > 1e-9 else None


def _seiten(dirs):
    """Hauptrichtung (doppelter Winkel gemittelt) und Seite je Ast (+1/-1)"""
    z = sum(complex(math.cos(2 * math.atan2(d[1], d[0])), math.sin(2 * math.atan2(d[1], d[0]))) for d in dirs)
    a = math.atan2(z.imag, z.real) / 2; u = np.array([math.cos(a), math.sin(a)])
    return [1 if float(np.dot(d, u)) >= 0 else -1 for d in dirs]


class Graph:
    """Kanten mit zwei Enden; Knoten mit Ästen (kante, ende, richtung, linie). Übergänge nach der Knotenregel."""
    def __init__(self):
        self.kanten = []                     # (a, b, linie)
        self.aeste = collections.defaultdict(list)
        self.kreuzung = set()
        self._paare = {}
        self.fern = {}

    def kante(self, a, b, linie, da, db, doppelt_pruefen=False):
        if doppelt_pruefen:
            sch = (min(a, b), max(a, b), linie if linie < 10 ** 10 else linie // 100)
            if sch in self._paare: return self._paare[sch]
        i = len(self.kanten); self.kanten.append((a, b, linie))
        if doppelt_pruefen: self._paare[sch] = i
        if da is not None: self.aeste[a].append((i, 0, da, linie))
        if db is not None: self.aeste[b].append((i, 1, db, linie))
        return i

    def uebergaenge(self):
        """{(kante, ende_ankunft): [(kante, ende_abfahrt)]} – ende 0 = Anfang der Kante liegt am Knoten"""
        U = collections.defaultdict(list)
        for n, A in self.aeste.items():
            if len(A) < 2: continue
            if len(A) == 2:
                (i, e, di, _), (j, f, dj, _) = A
                if float(np.dot(di, dj)) < 0.3:                   # kein Richtungswechsel (Spitzkehre)
                    U[(i, e)].append((j, f)); U[(j, f)].append((i, e))
                continue
            S = _seiten([a[2] for a in A])
            for p, (i, e, di, li) in enumerate(A):
                for q, (j, f, dj, lj) in enumerate(A):
                    if p == q or S[p] == S[q]: continue
                    if n in self.kreuzung:
                        if li != lj and float(np.dot(di, dj)) > -0.9: continue
                    U[(i, e)].append((j, f))
        return U

    def erreichbar(self, start, U):
        """Zustände (kante, ende an dem sie verlassen wird), die von den Startzuständen ohne Richtungswechsel erreicht werden"""
        seen, stack = set(), list(start)
        while stack:
            k, e = stack.pop()
            if (k, e) in seen: continue
            seen.add((k, e))
            for j, f in U.get((k, e), ()):                  # bei f in die Kante j hinein, verlassen am anderen Ende
                stack.append((j, 1 - f))
        return seen

    def ende(self, n, aussen=None):
        """Start-/Zielzustände eines Endes am Knoten n: hinein über die Äste, die nach innen zeigen (Abgang mit Richtung
        nach aussen; ein Abgangsknoten kann eine Weiche sein, Tecknau 500 Luzern), Ziel = an n ankommen, Fahrt nach aussen"""
        A = self.aeste.get(n, [])
        if aussen is not None and len(A) > 1:
            innen = [a for a in A if float(np.dot(a[2], aussen)) < 0] or A
        else: innen = A
        return {(k, 1 - e) for k, e, _, _ in innen}, {(k, e) for k, e, _, _ in innen}


def _rich_k(pos, a, b):
    pa, pb = pos(a), pos(b)
    return _einheit(pb - pa) if pa is not None and pb is not None else None


def osm_graph(N, T, W, K, WT):
    """OSM-Topologie, wie das Netzmodell sie zeichnet: Kanten zwischen aufeinanderfolgenden Knoten der Gleisstücke"""
    G = Graph(); lat0 = next(iter(K.values()))[0] if K else 47.0
    KN = {int(k): v for k, v in N["knoten"].items()}
    def pos(n):
        if n in K: return _xy(K[n], lat0)
        v = KN.get(n)
        return _xy((v["lat"], v["lon"]), lat0) if v and v.get("lat") is not None else None
    # je Way der Abschnitt zwischen dem ersten und letzten Knoten, den das Netzmodell zeichnet, mit ALLEN OSM-Knoten
    # dazwischen (die Gleisstücke des Netzmodells lassen Knoten aus, an denen andere Ways anschliessen – Giesshübel)
    aus_kn = {a.get("knoten") for a in N.get("abgaenge", [])}
    spanne = collections.defaultdict(set)
    for gl in N["gleise"]:
        w = gl["way"] if gl["way"] in W else gl["way"] // 100      # geteilter Way (Netzmodell): 324969020 01 -> 324969020
        nd = W.get(w, []); idx = {n: i for i, n in enumerate(nd)}
        if nd: spanne[w].update(idx[n] for n in gl["knoten"] if n in idx)
    benutzt = collections.Counter()
    for w, I in spanne.items():
        nd = W.get(w, [])
        if I: benutzt.update(nd[min(I):max(I) + 1])
    for gl in N["gleise"]:                       # geteilte Ways (künstliche IDs, nicht in OSM): Gleisstücke des Netzmodells direkt
        if gl["way"] in W: continue
        kn = gl["knoten"]
        for a, b in zip(kn, kn[1:]):
            if a < 0 or b < 0: continue              # künstlicher Schnittknoten des Netzmodells: nicht OSM
            if a in aus_kn and b in aus_kn: continue  # Stück ausserhalb des Plans (Tecknau: Spurwechsel hinter dem Rand)
            if a != b: G.kante(a, b, gl["way"], _rich_k(pos, a, b), _rich_k(pos, b, a), True)
    for w, I in spanne.items():
        if not I: continue
        nd = W[w]; i0, i1 = min(I), max(I)
        # Kanten zwischen «wichtigen» Knoten: Enden, Knoten mehrerer Ways, getaggte Knoten
        wichtig = [i for i in range(i0, i1 + 1) if i in (i0, i1) or benutzt[nd[i]] > 1 or T.get(nd[i], {}).get("railway")]
        def rich(i, j, weit=12):
            pv = pos(nd[i])
            if pv is None: return None
            st = 1 if j > i else -1
            for k in range(i + st, j + st, st):
                q = pos(nd[k])
                if q is not None and np.linalg.norm(q - pv) >= weit: return _einheit(q - pv)
            q = pos(nd[j]); return _einheit(q - pv) if q is not None else None
        for i, j in zip(wichtig, wichtig[1:]):
            if nd[i] in aus_kn and nd[j] in aus_kn: continue
            if nd[i] != nd[j]:
                k = G.kante(nd[i], nd[j], w, rich(i, j), rich(j, i), True)
                G.fern[(k, 0)] = rich(i, j, 35); G.fern[(k, 1)] = rich(j, i, 35)     # Seite (HT4): Richtung auf ~35 m
    for n in list(G.aeste):
        t = T.get(n, {})
        if t.get("railway") == "railway_crossing": G.kreuzung.add(n)
    return G


# ---------------------------------------------------------------- Plan
def plan_graph(gleise, luecken, boegen):
    """Graph aus den gezeichneten Linien: Knoten = Enden, Berührungen, Schnitte (ohne Lücke); Schnitt ohne DKW-Bögen = Kreuzung"""
    Gs = [g["geo"] for g in gleise]
    tree = STRtree(Gs)
    pts = []
    for i, g in enumerate(Gs):
        pts += [Point(g.coords[0]), Point(g.coords[-1])]
        for j in tree.query(g):
            j = int(j)
            if j <= i: continue
            x = g.intersection(Gs[j])
            for q in getattr(x, "geoms", [x]):
                if not q.is_empty and q.geom_type == "Point": pts.append(q)
    gap = lambda p: any(l.contains(p) for l in luecken)
    # DKW-Symbol (Bögen/Klammern): ein Knoten, an den alle Linienenden bis 12 px heranreichen (der Plan unterbricht das
    # durchgehende Gleis unter den Klammern, Aarburg-Oftringen Gl. 2 647–657)
    dkw = []
    for b in boegen:
        for c in dkw:
            if math.hypot(c[0] - b.x, c[1] - b.y) < 12: c[0] = (c[0] * c[2] + b.x) / (c[2] + 1); c[1] = (c[1] * c[2] + b.y) / (c[2] + 1); c[2] += 1; break
        else: dkw.append([b.x, b.y, 1])
    knoten = [[c[0], c[1]] for c in dkw]; R_DKW_KN = 12.0
    radius = lambda j: R_DKW_KN if j < len(dkw) else 6.0
    for p in pts:
        if gap(p): continue
        for j, k in enumerate(knoten):
            if math.hypot(k[0] - p.x, k[1] - p.y) < radius(j): break
        else: knoten.append([p.x, p.y])
    KP = [Point(k) for k in knoten]
    ktree = STRtree(KP)
    G = Graph(); lage = {}                               # kante -> (linie, LineString)
    for li, g in enumerate(Gs):
        L = g.length
        ts = sorted({0.0, L} | {g.project(KP[int(j)]) for j in ktree.query(g.buffer(1.5)) if g.distance(KP[int(j)]) < 1.5 and int(j) >= len(dkw)}
                    | {g.project(KP[j]) for j in range(len(dkw)) if g.distance(KP[j]) < 4})
        ts2 = [ts[0]]
        for t in ts[1:]:
            if t - ts2[-1] > 0.8: ts2.append(t)
        if ts2[-1] < L - 1e-6 and L - ts2[-1] <= 0.8: ts2[-1] = L
        for t0, t1 in zip(ts2, ts2[1:]):
            def kid(t):
                p = g.interpolate(t)
                c = [int(j) for j in ktree.query(p.buffer(R_DKW_KN)) if KP[int(j)].distance(p) < radius(int(j))]
                return min(c, key=lambda j: (j >= len(dkw), KP[j].distance(p))) if c else None
            a, b = kid(t0), kid(t1)
            if a is None or b is None or a == b and t1 - t0 < 15: continue      # Schleife im Knoten-Cluster
            pa, pb = np.array(g.interpolate(t0).coords[0]), np.array(g.interpolate(t1).coords[0])
            da = _einheit(np.array(g.interpolate(min(t0 + 10, (t0 + t1) / 2 if t1 - t0 < 20 else t0 + 10)).coords[0]) - pa)
            db = _einheit(np.array(g.interpolate(max(t1 - 10, (t0 + t1) / 2 if t1 - t0 < 20 else t1 - 10)).coords[0]) - pb)
            if da is not None: da = da * np.array([1, -1])     # Plan-y nach unten -> wie Karte
            if db is not None: db = db * np.array([1, -1])
            k = G.kante(a, b, li, da, db)
            from shapely.ops import substring
            lage[k] = substring(g, t0, t1)
    # Kreuzung: Knoten, an dem Linien durchgehen (innen) und kein DKW-Bogen nahe ist
    for n, A in G.aeste.items():
        if len(A) >= 4 and n >= len(dkw):                   # nur der DKW-Knoten selbst erlaubt Übergänge (Olten: Schnitt 13 px neben DKW)
            if len({a[3] for a in A}) < len(A): G.kreuzung.add(n)
    return G, lage, knoten


# ---------------------------------------------------------------- Prüfung
def pruefen(svg_text, N, osm):
    T, W, K, WT = osm
    BEF = []
    bef = lambda r, x, y, t, **o: BEF.append(dict(regel=r, x=round(x, 1), y=round(y, 1), text=t, **o))
    KN = {int(k): v for k, v in N["knoten"].items()}
    pax_ways = {g["way"] for g in N["gleise"] if g.get("pax")}
    knoten_pax = set()
    for g in N["gleise"]:
        if g.get("pax"):
            knoten_pax.update(g["knoten"])
    # HT1–HT3 aus dem OSM-Abgleich
    VA, info = OA.abgleich(svg_text, N, T, W)
    for b in VA:
        r = b["regel"]
        if r == "VB1" and b.get("osm") in knoten_pax:
            bef("HT1", b["x"], b["y"], b["text"], osm=b["osm"])
        elif r == "VB2" and (set(b.get("ways", ())) & pax_ways or "gruen" in b.get("farben", ())):
            bef("HT2", b["x"], b["y"], b["text"], ways=b.get("ways"))
        elif r == "VC1" and set(b.get("ways", ())) & pax_ways:
            bef("HT3", b["x"], b["y"], b["text"], osm=b.get("osm"), ways=b.get("ways"))
    # Graphen
    GO = osm_graph(N, T, W, K, WT)
    gleise, boegen, perrons, luecken = OA.plan_lesen(svg_text)
    gleise = _ohne_doppel(gleise)
    GP_, lage, pknoten = plan_graph(gleise, luecken, boegen) if gleise else (Graph(), {}, [])
    # HT4 Seite: an OSM-Weichen (3 Äste, einer am Hauptgleis) die zwei Äste auf der Weichenseite
    lat0 = next(iter(K.values()))[0] if K else 47.0
    for n, A in GO.aeste.items():
        if len(A) != 3 or T.get(n, {}).get("railway") != "switch" or n not in knoten_pax: continue
        v = KN.get(n)
        if not v or v.get("x") is None or v.get("y") is None: continue
        S = _seiten([a[2] for a in A])
        stamm = [i for i in range(3) if S.count(S[i]) == 1]
        if len(stamm) != 1: continue
        aeste = [i for i in range(3) if i != stamm[0]]
        d_osm = [GO.fern.get((A[i][0], A[i][1])) if GO.fern.get((A[i][0], A[i][1])) is not None else A[i][2] for i in aeste]
        c_osm = _kreuz(d_osm[0], d_osm[1])
        # Plan-Richtung je Ast: nächster Knoten entlang der Kante mit Planlage (Netzmodell), y nach unten -> gespiegelt
        d_pl = []
        for i in aeste:
            k, e = A[i][0], A[i][1]
            a, b, w = GO.kanten[k]
            d_pl.append(_plan_richtung(GO, KN, n, k, e, v))
        if any(d is None for d in d_pl): continue
        c_pl = _kreuz(d_pl[0], d_pl[1])
        # nur klare Fälle: in OSM > ~1,5° auseinander, im Plan > 5°
        if abs(c_osm) < 0.025 or abs(c_pl) < 0.08: continue
        if (c_osm > 0) != (c_pl > 0):
            ws = [GO.kanten[A[i][0]][2] for i in aeste]
            bef("HT4", v["x"], v["y"], f"Weiche {n}: Äste (Ways {ws[0]}, {ws[1]}) im Plan auf der anderen Seite als in OSM", osm=n, ways=ws)
    # HT5 Fahrwege
    BEF += _fahrwege(N, KN, GO, GP_, lage, gleise, pax_ways, knoten_pax, T, W, K)
    zaehl = {r: sum(1 for b in BEF if b["regel"] == r) for r in REGELN}
    return dict(zaehl=zaehl, befunde=BEF, osm_abgleich={r: sum(1 for b in VA if b["regel"] == r) for r in sorted({b["regel"] for b in VA})})


def _plan_richtung(GO, KN, n, k, e, v):
    """Richtung im Plan (Karten-Orientierung) vom Knoten n entlang Kante k bis zum ersten Knoten mit Planlage ≥ 6 px weg"""
    seen = {n}; cur_k, cur_e = k, e; p0 = np.array([v["x"], v["y"]])
    for _ in range(12):
        a, b, w = GO.kanten[cur_k]
        m = b if cur_e == 0 else a
        if m in seen: return None
        seen.add(m)
        q = KN.get(m)
        if q and q.get("x") is not None and q.get("y") is not None:
            d = np.array([q["x"], q["y"]]) - p0
            if np.linalg.norm(d) >= 6: return _einheit(d * np.array([1, -1]))
        # weiter nur über Knoten mit genau zwei Ästen
        A = GO.aeste.get(m, [])
        if len(A) != 2: return None
        nxt = [(i, f) for i, f, _, _ in A if i != cur_k]
        if not nxt: return None
        cur_k, cur_e = nxt[0]
    return None


def _schnitte(N, KN, W, K):
    """Künstliche Knoten (negative IDs) an den Enden der Gleisstücke: Schnitt am Planrand. Läuft der Way auf der Seite des
    Schnitts im Plan weiter (andere Stücke desselben Ways zeichnen Knoten dahinter), ist der Schnitt künstlich (das Gleis
    ist im Plan unterbrochen, z. B. Giesshübel Achsknick 65°, REGELN 2.15) -> Befund. Sonst echter Ausgang: Ersatzknoten =
    äusserster echter Knoten des Stücks. Rückgabe ({künstlich-id: ersatz-id}, {künstlich-id: (x, y)} der Befunde)"""
    basis = lambda w: w if w in W else w // 100
    gez = collections.defaultdict(list)                  # Way -> [(stück-index, {indices})]
    for i, gl in enumerate(N["gleise"]):
        nd = W.get(basis(gl["way"]), []); idx = {n: j for j, n in enumerate(nd)}
        gez[basis(gl["way"])].append((i, {idx[n] for n in gl["knoten"] if n in idx}))
    ersatz, befund = {}, {}
    for i, gl in enumerate(N["gleise"]):
        w = basis(gl["way"]); nd = W.get(w, [])
        if not nd: continue
        idx = {n: j for j, n in enumerate(nd)}
        echt = [n for n in gl["knoten"] if n in idx]
        if not echt: continue
        R = {idx[n] for n in echt}
        for s_ in (gl["knoten"][0], gl["knoten"][-1]):
            if s_ >= 0 or s_ in idx: continue
            v = KN.get(s_, {})
            if v.get("lat") is None: continue
            # Seite des Schnitts: nächster Way-Knoten
            d = [((K[n][0] - v["lat"]) ** 2 + ((K[n][1] - v["lon"]) * 0.68) ** 2, j) for j, n in enumerate(nd) if n in K]
            if not d: continue
            d.sort(); p = d[0][1]; q = d[1][1] if len(d) > 1 else p
            pos = p + 0.5 * ((q > p) - (q < p))           # liegt zwischen den zwei nächsten Way-Knoten
            if min(R) <= pos <= max(R): continue
            hoch = pos > max(R)
            andere = set().union(*[I for k, I in gez[w] if k != i]) if len(gez[w]) > 1 else set()
            weiter = {j for j in andere if (j > max(R) if hoch else j < min(R))}
            if weiter and v.get("x") is not None and v.get("y") is not None:
                befund[s_] = (v["x"], v["y"])
            else:
                ersatz[s_] = nd[max(R)] if hoch else nd[min(R)]
    return ersatz, befund


def _beide(ks):
    S_ = {(k, e) for k in ks for e in (0, 1)}
    return S_, S_


def _ohne_doppel(gleise):
    G = [g["geo"] for g in gleise]; tree = STRtree(G); weg = set()
    for i, g in enumerate(G):
        for j in tree.query(g.buffer(1.0)):
            j = int(j)
            if j == i or j in weg: continue
            if g.length <= G[j].length and g.intersection(G[j].buffer(1.0)).length >= 0.9 * g.length and (g.length < G[j].length or i > j):
                weg.add(i); break
    return [g for i, g in enumerate(gleise) if i not in weg]


def _fahrwege(N, KN, GO, GP_, lage, gleise, pax_ways, knoten_pax, T, W, K):
    """Enden der Hauptgleise (Abgänge, Gleisenden) und Perrongleise in beiden Graphen; Mengen der Paare vergleichen"""
    BEF = []
    # Enden in OSM: Abgänge (grün) und Knoten mit einem Ast an einem Hauptgleis
    ziele = {}                                         # name -> ((start, ziel) in OSM, plan-xy, art)
    lat0 = next(iter(K.values()))[0] if K else 47.0
    richtung = {}
    ersatz, kuenstlich = _schnitte(N, KN, W, K)
    for n, (x, y) in kuenstlich.items():
        BEF.append(dict(regel="HT5", x=round(x, 1), y=round(y, 1), art="kuenstlich", osm=n,
                        text=f"Gleisende {n} am Planrand: in OSM läuft das Gleis im Plan weiter (künstlicher Schnitt, Gleis fehlt dazwischen)"))
    abg_kn = {ersatz.get(a.get("knoten"), a.get("knoten")) for a in N.get("abgaenge", [])} | {a.get("knoten") for a in N.get("abgaenge", [])}
    for a in N.get("abgaenge", []):
        n = a.get("knoten"); n = ersatz.get(n, n)
        if not a.get("pax") or n not in GO.aeste: continue
        ll = a.get("aus_ll") or None
        aussen = _einheit(_xy(ll, lat0) - _xy(K[n], lat0)) if ll and n in K else None
        name = f"Abgang {a.get('ref') or ''} {a.get('town') or ''} ({n})".replace("  ", " ")
        ziele[name] = (GO.ende(n, aussen), (a["x"], a["y"]), "ende")
        richtung[name] = ((a.get("ref"), a.get("town"), a.get("dx"), a.get("dy")), (a.get("dx") or 0, a.get("dy") or 0))
    for n, A in GO.aeste.items():
        if len(A) != 1 or n not in knoten_pax: continue
        if n in abg_kn: continue
        v = KN.get(n)
        if not v or v.get("x") is None or v.get("y") is None: continue
        if not any(GO.kanten[k][2] in pax_ways for k, _, _, _ in A): continue
        ziele[f"Gleisende {n}"] = (GO.ende(n), (v["x"], v["y"]), "ende")
    # Perrongleise: Gleisnummer im Netzmodell (Feld «gleis»; sonst Gleisstück unter dem Nummernschild, Wangen b. O.)
    basis = lambda w: w if w in W else w // 100
    widx = {}
    def idx(w):
        if w not in widx: widx[w] = {n: j for j, n in enumerate(W.get(w, []))}
        return widx[w]
    def stueck_kanten(gl):
        w = gl["way"]
        if w not in W:
            P = set(zip(gl["knoten"], gl["knoten"][1:]))
            return {i for i, (p, q, ww) in enumerate(GO.kanten) if ww == w and ((p, q) in P or (q, p) in P)}
        I = idx(w); R = [I[n] for n in gl["knoten"] if n in I]
        if not R: return set()
        lo, hi = min(R), max(R)
        return {i for i, (p, q, ww) in enumerate(GO.kanten) if ww == w and p in I and q in I and lo <= I[p] <= hi and lo <= I[q] <= hi}
    pg = collections.defaultdict(list)
    for gl in N["gleise"]:
        if gl.get("gleis") and gl.get("pax"): pg[str(gl["gleis"])].append(gl)
    for m in N.get("nummern", []):
        nr = str(m.get("text"))
        if nr in pg: continue
        for gl in N["gleise"]:
            xs = [KN[n]["x"] for n in gl["knoten"] if KN.get(n, {}).get("x") is not None]
            if gl.get("pax") and gl.get("y") is not None and abs(gl["y"] - m["y"]) < 1 and xs and min(xs) <= m["x"] <= max(xs):
                pg[nr].append(gl)
    for nr, gls in pg.items():
        ks = set(); xy = []
        for gl in gls:
            ks |= stueck_kanten(gl)
            xy += [(KN[n]["x"], KN[n]["y"]) for n in gl["knoten"] if KN.get(n, {}).get("x") is not None and KN.get(n, {}).get("y") is not None]
        # Lage: Gleisnummer-Schild im Plan (Netzmodell «nummern»), sonst Mitte der Knoten auf der Ebene des Gleisstücks
        schild = [(m["x"], m["y"]) for m in N.get("nummern", []) if str(m.get("text")) == nr]
        if ks and schild:
            ziele[f"Gl. {nr}"] = (_beide(ks), schild[0], "perron")
        elif ks and xy:
            ebene = collections.Counter(gl.get("y") for gl in gls if gl.get("y") is not None).most_common(1)
            yy = ebene[0][0] if ebene else collections.Counter(p[1] for p in xy).most_common(1)[0][0]
            xs = sorted(p[0] for p in xy if abs(p[1] - yy) < 1) or sorted(p[0] for p in xy)
            ziele[f"Gl. {nr}"] = (_beide(ks), (xs[len(xs) // 2], yy), "perron")
    if len(ziele) < 2 or not GP_.kanten: return BEF
    # Lage im gezeichneten Plan. Enden (Abgänge, Gleisenden) -> Enden der grünen Linien im Plan, eins zu eins (Ungarische
    # Methode, Abstand zur Netzmodell-Lage; der Plan zeichnet Abgänge oft schräg weg, Aarburg-Oftringen 451 Rothrist), danach
    # innerhalb einer Abgangsgruppe (gleiche Netzmodell-x) die Reihenfolge quer wie im Netzmodell. Perrongleise -> nächste
    # grüne Kante (≤ 14 px).
    from scipy.optimize import linear_sum_assignment
    gruen = lambda k: gleise[GP_.kanten[k][2]]["farbe"] == "gruen"
    pk = [k for k in lage if gruen(k)] or list(lage)
    ptree = STRtree([lage[k] for k in pk])
    plan_ziel = {}
    pe = []                                            # (knoten, xy, kante)
    for n, A in GP_.aeste.items():
        if len(A) == 1 and gruen(A[0][0]):
            k, e = A[0][0], A[0][1]; c = lage[k].coords[0 if e == 0 else -1]; pe.append((n, c, k))
    en = [n for n in ziele if ziele[n][2] == "ende"]
    if en and pe:
        C = np.array([[math.dist(ziele[n][1], p[1]) for p in pe] for n in en])
        C2 = np.where(C <= 200, C, 1e6)
        ri, ci = linear_sum_assignment(C2)
        zu = {en[r]: c for r, c in zip(ri, ci) if C2[r, c] < 1e6}
        gruppen = collections.defaultdict(list)          # Abgänge gleicher Linie und Richtung; quer sortiert (drehfest)
        for n in zu:
            if n in richtung: gruppen[richtung[n][0]].append(n)
        for g, ns in gruppen.items():
            if len(ns) < 2: continue
            dx, dy = richtung[ns[0]][1]; quer = lambda p: -dy * p[0] + dx * p[1]
            cs = sorted((quer(pe[zu[n]][1]), zu[n]) for n in ns)
            for n, (_, c) in zip(sorted(ns, key=lambda n: quer(ziele[n][1])), cs): zu[n] = c
        for n, c in zu.items():
            pn = pe[c][0]; plan_ziel[n] = GP_.ende(pn)
    for name, (ks, (x, y), art) in ziele.items():
        if name in plan_ziel: continue
        p = Point(x, y)
        c = [pk[int(j)] for j in ptree.query(p.buffer(14))]
        if not c: continue
        k = min(c, key=lambda k: lage[k].distance(p))
        if lage[k].distance(p) <= 14: plan_ziel[name] = _beide({k})
    namen = sorted(n for n in ziele if n in plan_ziel)
    UO, UP = GO.uebergaenge(), GP_.uebergaenge()
    def paare(G, U, zu):
        P = set()
        for i, a in enumerate(namen):
            R = G.erreichbar(zu(a)[0], U)
            for b in namen[i + 1:]:
                if ziele[a][2] == "perron" and ziele[b][2] == "perron": continue
                if zu(b)[1] & R: P.add((a, b))
        return P
    PO = paare(GO, UO, lambda a: ziele[a][0])
    PP = paare(GP_, UP, lambda a: plan_ziel[a])
    for a, b in sorted(PP - PO):
        (xa, ya), (xb, yb) = ziele[a][1], ziele[b][1]
        BEF.append(dict(regel="HT5", x=round((xa + xb) / 2, 1), y=round((ya + yb) / 2, 1), text=f"Fahrweg {a} ↔ {b} im Plan, nicht in OSM", von=a, nach=b, art="zusaetzlich"))
    for a, b in sorted(PO - PP):
        (xa, ya), (xb, yb) = ziele[a][1], ziele[b][1]
        BEF.append(dict(regel="HT5", x=round((xa + xb) / 2, 1), y=round((ya + yb) / 2, 1), text=f"Fahrweg {a} ↔ {b} in OSM, fehlt im Plan", von=a, nach=b, art="fehlt"))
    BEF.append(dict(regel="_info", x=0, y=0, text=f"Fahrwege: {len(namen)}/{len(ziele)} Ziele im Plan gefunden, OSM {len(PO)}, Plan {len(PP)}",
                    ohne_lage=sorted(set(ziele) - set(namen))))
    return BEF


# ---------------------------------------------------------------- alle / Basis / Selbsttest
def _basis_lesen(b): return json.load(open(b)) if b and os.path.exists(b) else {}


def basis_schreiben(basis, abschnitt, tab, quelle):
    B = _basis_lesen(basis)
    B["_quelle"] = "hauptgleis.py (Schritt HT, REGELN 0.1 / Kopf «HT»); je Abschnitt Zählung je Plan und Regel"
    B[abschnitt] = {k: {r: v.get(r, 0) for r in REGELN} for k, v in sorted(tab.items()) if "fehler" not in v}
    B.setdefault("_stand", {})[abschnitt] = quelle
    json.dump(B, open(basis, "w"), ensure_ascii=False, indent=1, sort_keys=True)
    print(f"Basis gesetzt: {basis} [{abschnitt}] {len(B[abschnitt])} Pläne ({quelle})")


def _netz_datei(netz_dir, key):
    for f in (key + "_netz.json", key + ".json"):
        p = os.path.join(netz_dir, f)
        if os.path.exists(p): return p
    return None


def alle(plaene, netz_dir, osm, out, basis=None, basis_setzen=False, abschnitt="plaene", rekursiv=False):
    os.makedirs(out, exist_ok=True); O = osm_laden(osm); tab = {}
    muster = os.path.join(plaene, "**", "*.svg") if rekursiv else os.path.join(plaene, "*.svg")
    for f in sorted(glob.glob(muster, recursive=rekursiv)):
        key = os.path.relpath(f, plaene)[:-4].replace(os.sep, "/")
        if os.path.basename(key) in NICHT_PLAENE or key.endswith("_bare"): continue
        nf = _netz_datei(netz_dir, key)
        if not nf: continue
        os.makedirs(os.path.dirname(os.path.join(out, key + ".json")), exist_ok=True)
        try: R = pruefen(open(f).read(), json.load(open(nf)), O)
        except Exception as e:
            print(f"FEHLER {key}: {e}", file=sys.stderr); tab[key] = dict(fehler=str(e)[:200]); continue
        json.dump(R, open(os.path.join(out, key + ".json"), "w"), ensure_ascii=False, indent=1)
        tab[key] = dict(R["zaehl"])
        print(f"{key:<38} " + " ".join(f"{r} {R['zaehl'][r]}" for r in REGELN))
    json.dump(tab, open(os.path.join(out, "zaehlung.json"), "w"), ensure_ascii=False, indent=1, sort_keys=True)
    BB = _basis_lesen(basis); sperre = abschnitt in BB and not basis_setzen; B = BB.get(abschnitt, {})
    neu = []
    for key, z in sorted(tab.items()):
        if "fehler" in z: neu.append((key, "FEHLER", 0, 1)); continue
        for r in REGELN:
            if z.get(r, 0) > B.get(key, {}).get(r, 0): neu.append((key, r, B.get(key, {}).get(r, 0), z[r]))
    L = ["# Hauptgleis-Topologie HT (REGELN 0.1 / Kopf «HT») – Plan aus Code gegen OSM, nur Hauptgleise", "",
         f"{len(tab)} Pläne mit Netzmodell; Basis: {basis or '—'} [{abschnitt}]" + ("" if sperre else " – **keine Sperre** (Abschnitt fehlt)")
         + ". Ziel ist 0 in jedem Plan; neue Befunde (Zunahme gegen Basis) machen den Workflow rot.", "",
         "| Plan | " + " | ".join(REGELN) + " | Summe |", "|---|" + "---|" * (len(REGELN) + 1)]
    for key, z in sorted(tab.items(), key=lambda kv: (-sum(kv[1].get(r, 0) for r in REGELN), kv[0])):
        if "fehler" in z: L.append(f"| {key} | Fehler: {z['fehler'][:60]} |"); continue
        b = B.get(key, {})
        cell = lambda r: (f"**{z[r]}** (Basis {b.get(r, 0)})" if z[r] > b.get(r, 0) else (f"{z[r]} ↓{b.get(r, 0)}" if z[r] < b.get(r, 0) else str(z[r]) if z[r] else "·"))
        L.append(f"| {key} | " + " | ".join(cell(r) for r in REGELN) + f" | {sum(z[r] for r in REGELN)} |")
    L += ["", "Regeln: " + "; ".join(f"{r} = {TEXT[r]}" for r in REGELN)]
    if neu:
        L += ["", "## NEUE Befunde", ""]
        for key, r, b, n in neu:
            L.append(f"- **{key}** {r}: {b} → {n}")
            if r != "FEHLER":
                for x in json.load(open(os.path.join(out, key + ".json")))["befunde"]:
                    if x["regel"] == r: L.append(f"  - {x['x']}/{x['y']}: {x['text']}")
    open(os.path.join(out, "hauptgleis.md"), "w").write("\n".join(L) + "\n")
    if basis_setzen and basis: basis_schreiben(basis, abschnitt, tab, f"--basis-setzen {plaene}")
    summe = collections.Counter()
    for z in tab.values(): summe.update({r: z.get(r, 0) for r in REGELN})
    print("Hauptgleis HT:", dict(summe), f"– {len(tab)} Pläne, {sum(1 for z in tab.values() if any(z.get(r, 0) for r in REGELN))} mit HT > 0")
    for key, r, b, n in neu: print(f"{'NEU' if sperre else 'ohne Basis'} {key} {r}: {b} -> {n}")
    return 1 if (neu and sperre) else 0


def selbsttest(faelle, osm):
    """Prüffälle: <name>.svg + <name>_netz.json + <name>.json {erwartet: [{regel,x?,y?,r?,text?}], nicht: [...]}"""
    O = osm_laden(osm); fehler = 0
    for f in sorted(glob.glob(os.path.join(faelle, "*.json"))):
        if f.endswith("_netz.json"): continue
        E = json.load(open(f)); svg = f[:-5] + ".svg"
        R = pruefen(open(svg).read(), json.load(open(f[:-5] + "_netz.json")), O)
        def da(e):
            for b in R["befunde"]:
                if b["regel"] != e["regel"]: continue
                if "x" in e and math.dist((b["x"], b["y"]), (e["x"], e["y"])) >= e.get("r", 12): continue
                if "text" in e and e["text"] not in b["text"]: continue
                return True
            return False
        for e in E.get("erwartet", []):
            ok = da(e); fehler += not ok
            print(f"{'OK  ' if ok else 'FEHLT'} {os.path.basename(svg)} {e['regel']} {e.get('x', '')}/{e.get('y', '')} {e.get('text', '')} – {e.get('anlass', '')}")
        for e in E.get("nicht", []):
            ok = not da(e); fehler += not ok
            print(f"{'OK  ' if ok else 'FALSCH'} {os.path.basename(svg)} kein {e['regel']} {e.get('x', '')}/{e.get('y', '')} {e.get('text', '')} – {e.get('anlass', '')}")
    print("Selbsttest HT:", "bestanden" if not fehler else f"{fehler} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", nargs="?"); ap.add_argument("netz", nargs="?"); ap.add_argument("--osm")
    ap.add_argument("--json"); ap.add_argument("--alle"); ap.add_argument("--netz-dir"); ap.add_argument("--out")
    ap.add_argument("--basis"); ap.add_argument("--basis-setzen", action="store_true"); ap.add_argument("--selbsttest")
    ap.add_argument("--abschnitt", default="plaene"); ap.add_argument("--rekursiv", action="store_true"); ap.add_argument("--basis-aus")
    A = ap.parse_args()
    if A.basis_aus: basis_schreiben(A.basis, A.abschnitt, json.load(open(A.basis_aus)), A.basis_aus); sys.exit(0)
    if A.selbsttest: sys.exit(selbsttest(A.selbsttest, A.osm))
    if A.alle: sys.exit(alle(A.alle, A.netz_dir, A.osm, A.out, A.basis, A.basis_setzen, A.abschnitt, A.rekursiv))
    R = pruefen(open(A.svg).read(), json.load(open(A.netz)), osm_laden(A.osm))
    if A.json: json.dump(R, open(A.json, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"zaehl": R["zaehl"], "osm_abgleich": R["osm_abgleich"]}, ensure_ascii=False))
    for b in R["befunde"]: print(f"  {b['regel']} {b['x']}/{b['y']} {b['text']}" + (f"  ohne Lage: {b['ohne_lage']}" if b.get('ohne_lage') else ""))
