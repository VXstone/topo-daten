import os
"""Automatische Lage für Regionalpläne (Daniel 16.10.2026): gerade Strecken zwischen den Bahnhöfen, keine Treppen,
Bahnhöfe auf 60° gedreht, Streckenlänge grob proportional zur echten Distanz (gestaucht).

Aufruf aus netz_lage.py, wenn die Lagedatei {"auto": {...}} enthält. Parameter (Standard):
  c0 30, c1 70, p 0.7   Ziel-Länge Anschluss-zu-Anschluss [px] = c0 + c1 * (Streckenlänge km)^p
  lmin 30               kürzeste Strecke zwischen zwei Kästen [px]
  abgang 110            Länge der Strecke zu einem Abgang am Rand [px]
  rand 26               Mindestabstand zwischen Kästen [px]
Verfahren: jede Strecke ist entweder gerade (beide Enden zeigen gegeneinander) oder hat einen Knick (zwei Schenkel in
den Austrittsrichtungen der Enden). Unbekannt sind die Kastenmitten und die Schenkellängen; gelöst wird ein lineares
Ausgleichsproblem mit Schranken (scipy lsq_linear): Richtungen hart, Längen weich, schwacher Zug zur Geografie.
Überlappende Kästen werden in Folgedurchgängen mit Abstandsbedingungen getrennt.
"""
import math, collections
import numpy as np
from scipy.optimize import lsq_linear

def uvec(dg): return np.array([math.cos(math.radians(dg)), -math.sin(math.radians(dg))])
def snap(dg, step=60): return (round(dg / step) * step) % 360

def loese(nodes, MAJOR, routes, anchor, ROT, PORTS, S, P, geo_bearing, L0):
    P = dict(dict(c0=30, c1=70, p=0.7, lmin=30, abgang=110, rand=26, w=60.0, wg=0.02, wm=6.0), **(P if isinstance(P, dict) else {}))
    idx = {n: k for k, n in enumerate(MAJOR)}; nv = 2 * len(MAJOR)
    geo = {n: np.array([nodes[n]["x"], -nodes[n]["y"]]) for n in MAJOR}
    # Enden jeder Strecke: Abstand zur Kastenmitte und Austrittsrichtung (Bildschirm, y nach unten)
    R = []
    for r in routes:
        ends = []
        for n, e in ((r["a"], r["first"]), (r["b"], r["last"])):
            a_ = anchor.get((id(e), n))
            if a_ is not None:
                v = np.array(a_["v"], float); v /= np.linalg.norm(v); ends.append([n, np.array(a_["off"], float), v, True])
            else:
                ends.append([n, np.zeros(2), uvec(snap(geo_bearing(e, n))), False])
        (na, oa, va, fa), (nb, ob, vb, fb) = ends
        # freies Ende (Abzweig, Abgang): wenn möglich gerade gegenüber dem festen Ende
        if not fb and fa and float(-va @ vb) > 0.49: ends[1][2] = -va
        if not fa and fb and float(-vb @ va) > 0.49: ends[0][2] = -vb
        if not fa and not fb:
            d = geo[nb] - geo[na]; dg = math.degrees(math.atan2(-d[1], d[0])); ends[0][2] = uvec(snap(dg)); ends[1][2] = -ends[0][2]
        ex = nodes[na]["kind"] == "exit" or nodes[nb]["kind"] == "exit"
        Lt = P["abgang"] if ex else P["c0"] + P["c1"] * (r["length"] / 1000.0) ** P["p"]
        R.append(dict(r=r, ends=ends, Lt=Lt))
    def solve(extra):
        rows, rhs, lo, hi = [], [], [], []
        nvar = nv; var_lo = [-np.inf] * nv; var_hi = [np.inf] * nv
        def newvar(l=-np.inf, h=np.inf):
            nonlocal nvar; var_lo.append(l); var_hi.append(h); nvar += 1; return nvar - 1
        eq = []          # (dict var->coef, rhs, weight)
        for q in R:
            (na, oa, va, _), (nb, ob, vb, _) = q["ends"]
            ia, ib = idx[na], idx[nb]
            dot = float(va @ vb)
            for k in range(2):
                pass
            if dot < -0.98:          # gerade: Pb - Pa = l*va + m*w
                w = np.array([-va[1], va[0]]); l = newvar(P["lmin"]); m = newvar()
                for k in range(2):
                    eq.append(({2 * ib + k: 1, 2 * ia + k: -1, l: -va[k], m: -w[k]}, oa[k] - ob[k], P["w"]))
                eq.append(({m: 1}, 0, P["wm"])); eq.append(({l: 1}, q["Lt"], 1.0))
            else:                    # Knick: Pb - Pa = l1*va - l2*vb (+ m*w bei gleicher Richtung)
                l1 = newvar(P["lmin"] * 0.6); l2 = newvar(P["lmin"] * 0.6)
                same = dot > 0.98; w = np.array([-va[1], va[0]]); m = newvar() if same else None
                for k in range(2):
                    c = {2 * ib + k: 1, 2 * ia + k: -1, l1: -va[k], l2: vb[k]}
                    if same: c[m] = -w[k]
                    eq.append((c, oa[k] - ob[k], P["w"]))
                eq.append(({l1: 1, l2: 1}, q["Lt"], 1.0)); eq.append(({l1: 1, l2: -1}, 0, 0.15))
        for n in MAJOR:              # schwacher Zug zur Geografie (Massstab aus den Ziel-Längen)
            for k in range(2): eq.append(({2 * idx[n] + k: 1}, KG * geo[n][k], P["wg"]))
        for (a, b, nrm, need) in extra:    # Kästen trennen: nrm·(pb - pa) - t = 0, t >= need
            t = newvar(need)
            eq.append(({2 * idx[b]: nrm[0], 2 * idx[b] + 1: nrm[1], 2 * idx[a]: -nrm[0], 2 * idx[a] + 1: -nrm[1], t: -1}, 0, P["w"]))
        A = np.zeros((len(eq), nvar)); bb = np.zeros(len(eq))
        for r_, (c, rh, wt) in enumerate(eq):
            for j, v in c.items(): A[r_, j] += v * wt
            bb[r_] = rh * wt
        res = lsq_linear(A, bb, bounds=(np.array(var_lo), np.array(var_hi)), lsmr_tol="auto", max_iter=5000)
        z = res.x
        return {n: np.array([z[2 * idx[n]], z[2 * idx[n] + 1]]) for n in MAJOR}
    # Massstab zum Zug an die Geografie: mittleres Verhältnis Ziel-Länge / Luftlinie
    rat = [q["Lt"] / max(1.0, float(np.linalg.norm(geo[q["ends"][1][0]] - geo[q["ends"][0][0]]))) for q in R if q["Lt"] != P["abgang"]]
    KG = float(np.median(rat)) if rat else 0.05
    def box(n, pos):
        Pp = PORTS[n]; w = (Pp["x_hi"] - Pp["x_lo"] + 40) * S; h = (Pp["y_hi"] - Pp["y_lo"] + 50) * S
        a = math.radians(ROT.get(n, 0)); c, s = abs(math.cos(a)), abs(math.sin(a))
        return w * c + h * s, w * s + h * c
    extra = []
    for it in range(12):
        pos = solve(extra)
        ins = [n for n in MAJOR if nodes[n]["inset"]]
        neu = 0
        for i, a in enumerate(ins):
            for b in ins[i + 1:]:
                wa, ha = box(a, pos); wb, hb = box(b, pos)
                d = pos[b] - pos[a]
                ox = (wa + wb) / 2 + P["rand"] - abs(d[0]); oy = (ha + hb) / 2 + P["rand"] - abs(d[1])
                if ox > 0 and oy > 0 and not any((a, b) == (x[0], x[1]) for x in extra):
                    # trennen in der Richtung, die weniger verschieben muss (gerundet auf Achse)
                    if ox / max(1, wa + wb) < oy / max(1, ha + hb):
                        nrm = np.array([1.0 if d[0] >= 0 else -1.0, 0.0]); need = (wa + wb) / 2 + P["rand"]
                    else:
                        nrm = np.array([0.0, 1.0 if d[1] >= 0 else -1.0]); need = (ha + hb) / 2 + P["rand"]
                    extra.append((a, b, nrm, need)); neu += 1
        if not neu: break
    print(f"  Lage automatisch: {len(R)} Strecken, {len(extra)} Trennbedingungen, Massstab Geografie {KG:.3f} px/m")
    return pos


# ---------------------------------------------------------------- Achsen-Gerüst (Schritt L1, 27.11.2026)
LETZTE_ACHSEN = []      # für netz_lage (Lagedatei «achsen_auto») und lage_suche (eine Stellschraube je Achse)

def _wink(a, b):
    """Winkel zwischen zwei Richtungen in Grad (0…180)."""
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if not na or not nb: return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b) / na / nb))))

def achsen(nodes, MAJOR, routes, anchor, chains, inner, hubs, geo, fix, P):
    """REGELN 4.15: Achsen-Gerüst. (1) An jedem Knoten werden die beiden Ketten gepaart, die gerade durchlaufen (Knoten mit
    Spurplan: links gegen rechts, gleiche Linie bevorzugt, Winkel > achs_paar_min 100°; Abzweig ohne Plan: > 150°). (2) Gepaarte
    Ketten bilden eine Achse über die Knoten hinweg. (3) Eine Achse wird nur dort in Abschnitte geteilt, wo die Geografie
    deutlich knickt (Knick > achs_knick 75° oder Abweichung von der Sehne > achs_abw 0.35 der Länge; Geografie gibt nur
    Reihenfolge und Seite, Daniel 27.11.). (4) Jeder Abschnitt hat eine
    Richtung = Luftlinie seiner Enden, gerundet auf achs_schritt (15°); ist ein Knotenbahnhof von Hand gedreht, gibt er seinem
    Abschnitt die Richtung. (5) Drehung jedes Knotenbahnhofs = Richtung seines Abschnitts (an einem Teilungspunkt: der längere,
    bei Drehung von Hand der passendere); Richtung jeder Kette = Richtung ihres Abschnitts."""
    global LETZTE_ACHSEN
    SCH = float(P.get("achs_schritt", 15)); KN = float(P.get("achs_knick", 75)); ABW = float(P.get("achs_abw", 0.35))
    PMIN = float(P.get("achs_paar_min", 100)); JMIN = float(P.get("achs_paar_abzweig", 150))
    def anc(k, n):
        r = routes[k]; e = r["first"] if r["a"] == n else r["last"]
        return anchor.get((id(e), n))
    ends = collections.defaultdict(list)          # Knoten -> [(Kette-Index, Ende 0/-1)]
    for ci, ch in enumerate(chains):
        if ch["seq"][0] == ch["seq"][-1]: continue
        ends[ch["seq"][0]].append((ci, 0)); ends[ch["seq"][-1]].append((ci, -1))
    def info(n, ci, j):
        ch = chains[ci]; k = ch["ks"][0] if j == 0 else ch["ks"][-1]
        nb = ch["seq"][1] if j == 0 else ch["seq"][-2]
        a_ = anc(k, n); g = geo[nb] - geo[n]
        s = 0 if (a_ is None or a_.get("side") or not nodes[n].get("inset")) else (1 if a_["v"][0] > 0 else -1)
        refs = set(a_.get("refs", [])) if a_ else set()
        if not refs: refs = set(routes[k]["first" if routes[k]["a"] == n else "last"].get("refs", []))
        return dict(g=g, s=s, refs={str(x) for x in refs if x})
    paar = {}                                     # (ci, j) -> (ci2, j2)
    for n in hubs:
        if n in inner or nodes[n]["kind"] == "exit": continue
        E = ends.get(n, [])
        if len(E) < 2: continue
        I = {e: info(n, *e) for e in E}
        best = None
        for x in range(len(E)):
            for y in range(x + 1, len(E)):
                e1, e2 = E[x], E[y]; i1, i2 = I[e1], I[e2]
                w = _wink(i1["g"], i2["g"])
                if nodes[n].get("inset"):
                    if i1["s"] * i2["s"] != -1 or w < PMIN: continue
                elif w < JMIN: continue
                sc = (1.0 if i1["refs"] & i2["refs"] else 0.0) + w / 180.0
                if best is None or sc > best[0]: best = (sc, e1, e2)
        if best: paar[best[1]] = best[2]; paar[best[2]] = best[1]
        if os.environ.get("ACHSDBG"):
            print("PAAR?", nodes[n]["name"], [(nodes[chains[c]["seq"][-1 if j == 0 else 0]]["name"], I[(c, j)]["s"], sorted(I[(c, j)]["refs"]),
                  round(math.degrees(math.atan2(I[(c, j)]["g"][1], I[(c, j)]["g"][0])))) for c, j in E], "->", best and (best[1], best[2]))
    # Achsen ablaufen: Knotenfolge n0..nk, Ketten dazwischen (ci, vorwärts)
    seen, axes = set(), []
    def walk(ci, j):
        nl, cl = [chains[ci]["seq"][j]], []
        while ci not in seen:
            seen.add(ci); fw = j == 0; ch = chains[ci]
            cl.append((ci, fw)); far = ch["seq"][-1] if fw else ch["seq"][0]; nl.append(far)
            nxt = paar.get((ci, -1 if fw else 0))
            if nxt is None: break
            ci, j = nxt
        return nl, cl
    for ci in range(len(chains)):              # zuerst von offenen Enden aus, dann Ringe
        for j in (0, -1):
            if ci not in seen and (ci, j) not in paar and chains[ci]["seq"][0] != chains[ci]["seq"][-1]: axes.append(walk(ci, j))
    for ci in range(len(chains)):
        if ci not in seen and chains[ci]["seq"][0] != chains[ci]["seq"][-1]: axes.append(walk(ci, 0))
    segs = []                                  # (nl, cl) Abschnitte
    def teilen(nl, cl):
        if len(cl) >= 2:
            sehne = geo[nl[-1]] - geo[nl[0]]; Ls = float(np.linalg.norm(sehne)) or 1.0
            kand = []
            for i in range(1, len(nl) - 1):
                bend = _wink(geo[nl[i]] - geo[nl[i - 1]], geo[nl[i + 1]] - geo[nl[i]])
                # auch der Knick zum nächsten Bahnhof der Kette zählt (MOB Montbovon: Les Sciernes – Montbovon – La Tine
                # knickt um 120°, die Knoten Montreux – Montbovon – Zweisimmen liegen fast auf einer Linie; La Tine und
                # Rossinière lagen sonst über Les Sciernes, L2)
                ci0, fw0 = cl[i - 1]; ci1, fw1 = cl[i]
                vor = chains[ci0]["seq"][-2] if fw0 else chains[ci0]["seq"][1]
                nach = chains[ci1]["seq"][1] if fw1 else chains[ci1]["seq"][-2]
                bend = max(bend, _wink(geo[nl[i]] - geo[vor], geo[nach] - geo[nl[i]]))
                q = geo[nl[i]] - geo[nl[0]]; abw = abs(float(sehne[0] * q[1] - sehne[1] * q[0])) / Ls / Ls
                if bend > KN or abw > ABW: kand.append((max(bend / KN, abw / ABW), i))
            if kand:
                i = max(kand)[1]; teilen(nl[:i + 1], cl[:i]); teilen(nl[i:], cl[i:]); return
        segs.append((nl, cl))
    for nl, cl in axes: teilen(nl, cl)
    def rund(a): return ((round(a / SCH) * SCH + 180) % 360) - 180
    S_ = []
    for nl, cl in segs:
        d = geo[nl[-1]] - geo[nl[0]]
        S_.append(dict(nl=nl, cl=cl, phi=rund(math.degrees(math.atan2(d[1], d[0]))), roh=round(math.degrees(math.atan2(d[1], d[0])), 1), km=sum(chains[ci]["km"] for ci, _ in cl), fest=None))
    # Knoten -> Abschnitte, an denen er liegt (Kette, die den Knoten verlässt, und ob in Achsrichtung)
    am = collections.defaultdict(list)          # n -> [(si, ci, j, plus)]
    for si, sg in enumerate(S_):
        for i, (ci, fw) in enumerate(sg["cl"]):
            a, b = sg["nl"][i], sg["nl"][i + 1]
            am[a].append((si, ci, 0 if fw else -1, True)); am[b].append((si, ci, -1 if fw else 0, False))
    def hubrot(n, phi, ci, j, plus):            # Drehung, bei der die Kette (ci, Ende j) in Richtung ±phi den Plan verlässt
        s = info(n, ci, j)["s"]
        if not s: return None
        return ((phi + (0 if (s > 0) == plus else 180)) + 180) % 360 - 180
    eigen, wechsel = {}, []
    for n, L_ in sorted(am.items(), key=lambda t: (t[0] not in fix, -len(ends.get(t[0], [])))):   # von Hand gedrehte, grosse Knoten zuerst
        if not nodes[n].get("inset") or n in inner: continue
        L_ = [x for x in L_ if info(n, x[1], x[2])["s"]]
        if not L_: continue
        # gepaarter Knoten: nur Abschnitte der Achse durch ihn; ungepaarter mit mehr als einer Kette: kein eigener Abschnitt
        gp = [x for x in L_ if (x[1], x[2]) in paar]
        if gp: L_ = gp
        elif len(ends.get(n, [])) > 1: continue
        # Achswechsel (die Achse durch den Knoten wird an ihm geteilt, z. B. MOB Montbovon): Drehung bleibt beim Knoten
        # selbst (aus seinen Anschlüssen) und ist eine eigene Stellschraube der Lagesuche – Knick nur hier
        if len({x[0] for x in L_}) > 1:
            wechsel.append(n); continue          # von Hand / von der Suche gedreht: dreht nur den Knoten, nicht die Abschnitte
        if n in fix:
            def _d(x):
                ph2 = ((fix[n] + (0 if (info(n, x[1], x[2])["s"] > 0) == x[3] else 180)) + 180) % 360 - 180
                return abs(((ph2 - S_[x[0]]["phi"]) + 180) % 360 - 180), ph2
            x = min(L_, key=lambda x: _d(x)[0])
            if S_[x[0]]["fest"] is None: S_[x[0]]["fest"] = n; S_[x[0]]["phi"] = _d(x)[1]
            continue
        eigen[n] = max(L_, key=lambda x: (S_[x[0]]["km"], len(S_[x[0]]["cl"])))
    # Abschnitt ohne eigenen oder von Hand gedrehten Knotenbahnhof: nichts muss zu ihm passen – Richtung ungerundet aus der
    # Geografie (SZU Giesshübel – Saalsporthalle: 82° auf 75° gerundet lief gegen den seitlichen Abgang, 2 Haken T6)
    for si, sg in enumerate(S_):
        if sg["fest"] is None and not any(x[0] == si for x in eigen.values()): sg["phi"] = sg["roh"]
    rot = {}
    for n, (si, ci, j, plus) in eigen.items():
        r_ = hubrot(n, S_[si]["phi"], ci, j, plus)
        if r_ is not None: rot[n] = r_
    dirv = {}
    for si, sg in enumerate(S_):
        # einzelne Kette zu einem Abgang ohne eigenen Knotenbahnhof: keine Achse, es gilt «Abgang gerade aus dem Plan»
        # (abgang_knick, 4.11. Klosters Platz – Abgang 915 Davos; in L1 erst als Haken aufgefallen)
        if len(sg["cl"]) == 1 and len(chains[sg["cl"][0][0]]["seq"]) == 2 and sg["fest"] is None and not any(x[0] == si for x in eigen.values()) \
                and any(nodes[m]["kind"] == "exit" for m in (sg["nl"][0], sg["nl"][-1])): continue
        u = np.array([math.cos(math.radians(sg["phi"])), math.sin(math.radians(sg["phi"]))])
        for ci, fw in sg["cl"]: dirv[id(chains[ci])] = u if fw else -u
    LETZTE_ACHSEN = [dict(knoten=[nodes[n]["name"] for n in sg["nl"]], richtung=sg["phi"], geo=sg["roh"], fest=nodes[sg["fest"]]["name"] if sg["fest"] is not None else None,
                          eigen=[nodes[n]["name"] for n, x in eigen.items() if x[0] == si]) for si, sg in enumerate(S_)]
    LETZTE_ACHSEN.append(dict(knoten=[nodes[n]["name"] for n in wechsel], achswechsel=True, richtung=None, fest=None,
                              eigen=[nodes[n]["name"] for n in wechsel]))
    if os.environ.get("ACHSDBG"):
        for a_ in LETZTE_ACHSEN: print("ACHSE", a_)
    print(f"  Achsen: {len(axes)} Achsen, {len(S_)} Abschnitte, {len(rot)} Knotenbahnhöfe aus der Achse gedreht")
    return dict(rot=rot, dir=dirv, segs=S_)


# ---------------------------------------------------------------- Ketten-Verfahren (16.10. abends)
def rotv(v, a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a)); return np.array([v[0] * c - v[1] * s, v[0] * s + v[1] * c])

def ketten(nodes, MAJOR, routes, anchor, PORTS, S, P, fix, L0):
    """Bahnhöfe zwischen zwei Knoten (Abzweig, Abgang, Bahnhof mit mehr als zwei Strecken) liegen auf einer geraden
    Linie, in deren Richtung gedreht (beliebiger Winkel). Die Knoten selbst: Ausgleichsrechnung mit den Ketten als
    Soll-Vektoren (Richtung = Geografie, Länge = max(Platzbedarf, c0 + c1 * km^p)). Knoten-Bahnhöfe: Achse aus der
    Geografie auf 30° gerundet (oder fest aus "drehung")."""
    P = dict(dict(c0=40, c1=45, p=0.75, gap=72, wg=0.015, rand=24, abgang=90, schritt=30, abzweig_gap=170, knoten_gap=110), **(P if isinstance(P, dict) else {}))
    geo = {n: np.array([nodes[n]["x"], -nodes[n]["y"]]) for n in MAJOR}
    inc = {n: [] for n in MAJOR}
    for k, r in enumerate(routes): inc[r["a"]].append(k); inc[r["b"]].append(k)
    def anc(k, n):
        r = routes[k]; e = r["first"] if r["a"] == n else r["last"]
        return anchor.get((id(e), n))
    def other(k, n): return routes[k]["b"] if routes[k]["a"] == n else routes[k]["a"]
    def boxwh(n):           # Breite bis zu den äussersten Abgängen (Anschlusspunkte liegen ausserhalb x_lo/x_hi)
        Pp = PORTS[n]; xs = [Pp["x_lo"], Pp["x_hi"]] + [p["x"] for p in Pp["ports"]]
        return (max(xs) - min(xs) + 20) * S, (Pp["y_hi"] - Pp["y_lo"] + 50) * S
    # innere Bahnhöfe: Spurplan mit genau zwei Strecken, eine links, eine rechts
    inner = set()
    for n in MAJOR:
        if nodes[n]["inset"] and len(inc[n]) == 2 and n not in fix:
            vs = [anc(k, n) for k in inc[n]]
            if all(v is not None for v in vs) and vs[0]["v"][0] * vs[1]["v"][0] < 0: inner.add(n)
    hubs = [n for n in MAJOR if n not in inner]
    # Ketten ablaufen
    chains, seen = [], set()
    for h in hubs:
        for k in inc[h]:
            if k in seen: continue
            seq, ks, cur, kk = [h], [k], h, k
            while True:
                seen.add(kk); nxt = other(kk, cur); seq.append(nxt)
                if nxt not in inner: break
                kk = [x for x in inc[nxt] if x != kk][0]; ks.append(kk); cur = nxt
            chains.append(dict(seq=seq, ks=ks, km=sum(routes[x]["length"] for x in ks) / 1000.0))
    # Drehung der Knoten-Bahnhöfe
    rot = dict(fix)
    # Achsen-Gerüst (REGELN 4.15, Schritt L1, 27.11.2026): durchgehende Strecken über Knoten hinweg sind Achsen; Drehung der
    # Knotenbahnhöfe und Richtung der Ketten kommen aus der Achse (ein Codeweg für alle Regionen). Der alte Weg (Drehung je
    # Bahnhof aus seinen Anschlüssen, Kette aus der Luftlinie) nur noch zum Vergleich: Lage auto.achsen false.
    ACH = achsen(nodes, MAJOR, routes, anchor, chains, inner, hubs, geo, fix, P) if P.get("achsen", True) else None
    if ACH:
        for n, r_ in ACH["rot"].items():
            if n not in rot: rot[n] = r_
    _slug = {nodes[m]["inset"]: m for m in MAJOR if nodes[m].get("inset")}
    def _peil(n, p):
        """Peilung eines Anschlusses für die Drehung: Richtung zum Zielbahnhof, wenn bekannt (3.11.2026, Montbovon: die
        Gleise nach La Tine peilten nach OSM-Fernpunkt nach Südwesten, der Plan lag 120–150° gedreht und die Strecke
        machte eine Schlaufe). Lage auto.peilung_ziel (Standard aus: verschlechterte Zweisimmen und Rochers de Naye)."""
        _ab = P.get("peilung_ziel_ab", 60 if P.get("linien_region") else None)
        z_ = _slug.get(p.get("ziel")) if (P.get("peilung_ziel", False) or _ab is not None) else None
        if z_ is None or z_ == n: return p["bearing"]
        zb_ = math.degrees(math.atan2(nodes[z_]["y"] - nodes[n]["y"], nodes[z_]["x"] - nodes[n]["x"])) % 360
        # Kurvenbahnhof (4.11. spät, Klosters Platz: Gleis zeigt am Südende nach Westen, Selfranga liegt im Süden, Haken):
        # Peilung zum Zielplan nur, wenn sie mehr als «peilung_ziel_ab» (Linien-Regionen 60°) von der Gleisrichtung abweicht
        if not P.get("peilung_ziel", False) and _ab is not None:
            dd_ = abs((zb_ - p["bearing"] + 180) % 360 - 180)
            if dd_ <= _ab: return p["bearing"]
        return zb_
    for n in hubs:
        if not nodes[n]["inset"] or n in rot: continue
        Pp = [dict(p, bearing=_peil(n, p)) for p in PORTS[n]["ports"]]
        bb = [p["bearing"] for p in Pp if p["kind"] == "edge" and p["dx"] > 0] + [p["bearing"] + 180 for p in Pp if p["kind"] == "edge" and p["dx"] < 0]
        if not bb: rot[n] = 0; continue
        th = math.degrees(math.atan2(np.mean([math.sin(math.radians(b)) for b in bb]), np.mean([math.cos(math.radians(b)) for b in bb])))
        # je Seite eine Stimme (3.11.2026, Sagliains Sasslatsch: zwei Tunnelgleise links überstimmten den Schenkel rechts,
        # der Plan lag in Tunnelrichtung und die Gleise zum Autoverlad machten ein V). Lage auto.seiten_stimme (Standard an)
        if P.get("seiten_stimme", True):
            _sd = []
            for sg_ in (1, -1):
                b_ = [p["bearing"] + (0 if sg_ > 0 else 180) for p in Pp if p["kind"] == "edge" and p["dx"] * sg_ > 0]
                if b_: _sd.append(math.atan2(np.mean([math.sin(math.radians(b)) for b in b_]), np.mean([math.cos(math.radians(b)) for b in b_])))
            th = math.degrees(math.atan2(np.mean([math.sin(a_) for a_ in _sd]), np.mean([math.cos(a_) for a_ in _sd])))
        a = round(-th / P["schritt"]) * P["schritt"]; rot[n] = ((a + 180) % 360) - 180
    def port(n, k, weiche=False):         # Anschlusspunkt der Strecke k am Knoten n relativ zur Mitte (gedreht)
        a_ = anc(k, n)
        if a_ is None or n in inner: return np.zeros(2)
        # REGELN 4.12 (23.11.2026, Muntelier): seitlicher Abgang mit einfachem Stummel – die Kette (innere Bahnhöfe) liegt
        # auf der Geraden ab der Weiche, ihr Winkel passt sich an (netz_lage _abgang_winkel); sonst wandert der Knick zum
        # Nachbarbahnhof. Nur in place(), die Knoten-Ausgleichsrechnung bleibt beim Stummelende (keine Fernwirkung).
        if weiche and a_.get("weiche") and (L0.get("abgang_winkel", True) if isinstance(L0, dict) else True):
            return rotv(np.array(a_["weiche"]["off"], float), rot.get(n, 0))
        return rotv(np.array(a_["off"], float), rot.get(n, 0))
    def need(ch):           # Platzbedarf der inneren Bahnhöfe entlang der Kette (an Abzweigen mehr Luft)
        inn = ch["seq"][1:-1]
        extra_ = sum((P["abzweig_gap"] if not nodes[h_]["inset"] else P["knoten_gap"]) - P["gap"] for h_ in (ch["seq"][0], ch["seq"][-1]) if nodes[h_]["kind"] != "exit")
        # Halte brauchen Platz (4.11. abends, Château-d'Oex – Flendruz: drei Halte auf 40 px, Beschriftungen übereinander):
        # je Strecke mit h Halten mindestens (h + 1) × halt_abstand_min statt des normalen Abstands
        _hm = float(L0.get("halt_abstand_min", 60)) if isinstance(L0, dict) else 60.0
        _gaps = 0.0
        for k_ in ch["ks"]:
            nh_ = sum(1 for x_ in routes[k_].get("seq", [])[1:-1] if nodes[x_]["kind"] == "halt")
            _gaps += max(P["gap"], (nh_ + 1) * _hm) if (nh_ and P.get("linien_region")) else P["gap"]
        return sum(boxwh(n)[0] for n in inn) + _gaps + extra_
    for ch in chains:
        a, b = ch["seq"][0], ch["seq"][-1]
        ex = nodes[a]["kind"] == "exit" or nodes[b]["kind"] == "exit"
        L = max(need(ch), (P["abgang"] if ex and len(ch["seq"]) == 2 else P["c0"] + P["c1"] * ch["km"] ** P["p"]) + (need(ch) if ex else 0))
        d = geo[b] - geo[a]; ch["T"] = d / (np.linalg.norm(d) or 1) * L
        if ACH and id(ch) in ACH["dir"]: ch["T"] = ACH["dir"][id(ch)] * L; ch["achse"] = True
        # Kettenrichtung von Hand (Lage auto.kette_winkel {Bahnhof: Grad, 0 = rechts, 90 = oben}), Murten–Fribourg 18.10.
        for nm_, wk_ in P.get("kette_winkel", {}).items():
            ix_ = [i_ for i_, n_ in enumerate(ch["seq"]) if nodes[n_]["name"] == nm_]
            if ix_ and 0 < ix_[0] < len(ch["seq"]) - 1:
                u_ = np.array([math.cos(math.radians(wk_)), -math.sin(math.radians(wk_))])
                if float(u_ @ d) < 0: u_ = -u_
                ch["T"] = u_ * L
        # Seitlicher Abgang am Knotenbahnhof (Regionalvariante Kerzers 27.10., Hinweis eojeak: zwei unter 60° kreuzende
        # Achsen): die Kette läuft in der Abgangsrichtung weiter, sonst knickt sie gleich nach dem Abgang wieder ab.
        # Nur für Bahnhöfe in Lage auto.seiten_richtung; Gewicht der Kette in der Ausgleichsrechnung: auto.seiten_gewicht
        for j_, h_, sg_ in ((0, a, 1), (-1, b, -1)):
            a_ = anc(ch["ks"][j_], h_)
            if h_ in inner or not a_ or not a_.get("side") or nodes[h_]["name"] not in P.get("seiten_richtung", []): continue
            u_ = rotv(np.array(a_["v"], float), rot.get(h_, 0)); u_ = sg_ * u_ / (np.linalg.norm(u_) or 1)
            if float(u_ @ d) > 0.5 * (np.linalg.norm(d) or 1): ch["T"] = u_ * L; ch["w"] = P.get("seiten_gewicht", 1.0); ch["seite"] = (j_, u_)
            if os.environ.get("KDBG"): print("SEITE", [nodes[x]["name"] for x in ch["seq"]], u_.round(2), (d / (np.linalg.norm(d) or 1)).round(2))
    # Seitlicher Anschluss gibt nach (4.11. abends, Sasslatsch: der seitliche Abgang 960 zog Sagliains 14 px tiefer, die
    # gerade 910 von Sagliains Sasslatsch machte ein V): eine Kette, die an einem Ende seitlich (Abgang quer aus dem Plan)
    # anschliesst, ist ohnehin schräg und bekommt in der Ausgleichsrechnung das Gewicht auto.seite_nachgiebig (Linien-Regionen 0.6, sonst 1).
    if P.get("seite_nachgiebig", 0.6 if P.get("linien_region") else 1.0) != 1.0:
        for ch in chains:
            if "w" in ch: continue
            if any((a_ := anc(ch["ks"][j_], h_)) and a_.get("side") and h_ not in inner
                   for j_, h_ in ((0, ch["seq"][0]), (-1, ch["seq"][-1]))):
                ch["w"] = P.get("seite_nachgiebig", 0.6 if P.get("linien_region") else 1.0)
    # Abgang gerade aus dem Plan (4.11. spät, Klosters Platz – Abgang 915 Davos: Kehre gleich nach dem Plan, der Abgang lag
    # nach der Kehre und die Strecke machte einen Haken): weicht die Richtung zum Abgang um mehr als «abgang_knick» (60°)
    # von der Anschlussrichtung ab, liegt der Abgang in Anschlussrichtung. Nur Linien-Regionen.
    if P.get("linien_region"):
        for ch in chains:
            a, b = ch["seq"][0], ch["seq"][-1]
            if len(ch["seq"]) != 2 or (nodes[a]["kind"] == "exit") == (nodes[b]["kind"] == "exit") or ch.get("achse"): continue
            j_, h_, sg_ = (0, a, 1) if nodes[b]["kind"] == "exit" else (-1, b, -1)
            a_ = anc(ch["ks"][j_], h_)
            if not a_ or h_ in inner: continue
            u_ = rotv(np.array(a_["v"], float), rot.get(h_, 0)); u_ = sg_ * u_ / (np.linalg.norm(u_) or 1)
            T_ = np.asarray(ch["T"], float); L_ = float(np.linalg.norm(T_)) or 1.0
            if float(u_ @ T_) / L_ < math.cos(math.radians(P.get("abgang_knick", 60))):
                if os.environ.get("KDBG"): print("ABGANG gerade", nodes[h_]["name"], (T_ / L_).round(2), u_.round(2))
                ch["T"] = u_ * L_
    # Ketten, die an einem Knoten fast in dieselbe Richtung abgehen, auf mindestens 28° spreizen (sonst überlagern sie sich)
    for h in hubs:
        cs = [(ch, 1) for ch in chains if ch["seq"][0] == h] + [(ch, -1) for ch in chains if ch["seq"][-1] == h]
        if len(cs) < 2: continue
        for _ in range(4):
            ang = sorted(((math.degrees(math.atan2(sg * ch["T"][1], sg * ch["T"][0])), ch, sg) for ch, sg in cs), key=lambda t: t[0])
            done = True
            for (a1, c1, s1), (a2, c2, s2) in zip(ang, ang[1:]):
                if a2 - a1 < 28:
                    dl = (28 - (a2 - a1)) / 2; done = False
                    _f = [(c1, s1, -dl), (c2, s2, dl)]
                    if bool(c1.get("achse")) != bool(c2.get("achse")):        # Achskette bleibt gerade, die andere spreizt ganz
                        _f = [(c_, s_, 2 * d_) for c_, s_, d_ in _f if not c_.get("achse")]
                    for c_, s_, d_ in _f:
                        L_ = np.linalg.norm(c_["T"]); a_ = math.atan2(s_ * c_["T"][1], s_ * c_["T"][0]) + math.radians(d_)
                        c_["T"] = s_ * L_ * np.array([math.cos(a_), math.sin(a_)])
            if done: break
    hidx = {n: i for i, n in enumerate(hubs)}
    KG = float(np.median([np.linalg.norm(ch["T"]) / max(1.0, np.linalg.norm(geo[ch["seq"][-1]] - geo[ch["seq"][0]])) for ch in chains]))
    def solve(extra):
        rows, rhs = [], []
        for ch in chains:
            a, b = ch["seq"][0], ch["seq"][-1]
            oa, ob = port(a, ch["ks"][0]), port(b, ch["ks"][-1])
            w_ = ch.get("w", 1.0)
            for c in range(2):
                r = np.zeros(2 * len(hubs)); r[2 * hidx[b] + c] += w_; r[2 * hidx[a] + c] -= w_
                rows.append(r); rhs.append(w_ * (ch["T"][c] + oa[c] - ob[c]))
        for n in hubs:
            for c in range(2):
                r = np.zeros(2 * len(hubs)); r[2 * hidx[n] + c] = P["wg"]; rows.append(r); rhs.append(P["wg"] * KG * geo[n][c])
        for (a, b, v, w) in extra:      # Trennung: (pb - pa) ≈ v (Gewicht w)
            for c in range(2):
                r = np.zeros(2 * len(hubs)); r[2 * hidx[b] + c] = w; r[2 * hidx[a] + c] = -w; rows.append(r); rhs.append(w * v[c])
        z = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)[0]
        return {n: z[2 * hidx[n]: 2 * hidx[n] + 2] for n in hubs}
    def place(hp):
        pos = dict(hp); _qn = {}
        for ch in chains:
            a, b = ch["seq"][0], ch["seq"][-1]
            A = hp[a] + port(a, ch["ks"][0]); B = hp[b] + port(b, ch["ks"][-1])
            # REGELN 4.12: Kette ab der Weiche eines seitlichen Abgangs, wenn der Abgangswinkel dann in den Grenzen liegt
            for j_, h_ in ((0, a), (-1, b)):
                a_ = anc(ch["ks"][j_], h_)
                if not (a_ and a_.get("weiche") and h_ not in inner and (L0.get("abgang_winkel", True) if isinstance(L0, dict) else True)): continue
                W_ = hp[h_] + port(h_, ch["ks"][j_], True); a_["weiche"]["lage"] = False
                Z_ = B if j_ == 0 else A
                u_ = Z_ - W_; u_ = u_ / (np.linalg.norm(u_) or 1); m_ = rotv(np.array(a_["weiche"]["m"], float), rot.get(h_, 0))
                e_ = rotv(np.array(a_["weiche"]["e"], float), rot.get(h_, 0))
                w_ = math.degrees(math.acos(max(-1, min(1, float(m_ @ u_)))))
                _L = L0 if isinstance(L0, dict) else {}
                if (m_[0] * u_[1] - m_[1] * u_[0]) * (m_[0] * e_[1] - m_[1] * e_[0]) > 0 and _L.get("abgang_winkel_min", 20) <= w_ <= _L.get("abgang_winkel_max", 75) \
                        and abs(w_ - a_["weiche"]["a_alt"]) <= _L.get("abgang_winkel_dmax", 40):
                    a_["weiche"]["lage"] = True
                    if j_ == 0: A = W_
                    else: B = W_
            inn = ch["seq"][1:-1]
            if not inn: continue
            dv = B - A; Ltot = np.linalg.norm(dv) or 1.0; u = dv / Ltot
            # Kette ab einem seitlichen Abgang (seiten_richtung): Bahnhöfe auf der Abgangsrichtung, Knick erst am
            # anderen Ende (D. Eckenstein 28.10.: Müntschemier im Winkel von Kerzers, oben ein Winkel Richtung Ins)
            _sei = ch.get("seite")
            if _sei: u = np.asarray(_sei[1], float) / (np.linalg.norm(_sei[1]) or 1)
            th = math.degrees(math.atan2(u[1], u[0]))
            ws = [boxwh(n)[0] for n in inn]
            lens = [routes[x]["length"] for x in ch["ks"]]
            free = max(Ltot - sum(ws), P["gap"] * (len(inn) + 1))
            gaps = [free * l / sum(lens) for l in lens]
            # an Abzweigen mehr Abstand: dort gehen mehrere Ketten auseinander, Kästen dürfen sich nicht berühren
            for j_, h_ in ((0, a), (-1, b)):
                want = P["abzweig_gap"] if not nodes[h_]["inset"] else P["knoten_gap"]
                if gaps[j_] < want:
                    k_ = len(gaps) - 1 if j_ == -1 else 0; dl = want - gaps[k_]; gaps[k_] += dl
                    rest = [g_ for i_, g_ in enumerate(gaps) if i_ != k_]
                    if rest and sum(rest) > dl:
                        for i_ in range(len(gaps)):
                            if i_ != k_: gaps[i_] -= dl * gaps[i_] / sum(rest)
            # kein Zwischenraum unter dem Mindestabstand (sonst überlagern sich die Stummel zweier Bahnhöfe); mit Halten
            # (h + 1) × halt_abstand_min (4.11. abends, Château-d'Oex – Flendruz)
            _hm = float(L0.get("halt_abstand_min", 60)) if isinstance(L0, dict) else 60.0
            mins = []
            for k_ in ch["ks"]:
                nh_ = sum(1 for x_ in routes[k_].get("seq", [])[1:-1] if nodes[x_]["kind"] == "halt")
                mins.append(max(P["gap"], (nh_ + 1) * _hm) if (nh_ and P.get("linien_region")) else P["gap"])
            for _ in range(8):
                lo = [i_ for i_, g_ in enumerate(gaps) if g_ < mins[i_] - 0.5]
                if not lo: break
                dl = sum(mins[i_] - gaps[i_] for i_ in lo)
                hi = [i_ for i_, g_ in enumerate(gaps) if g_ > mins[i_] + 0.5]
                cap = sum(gaps[i_] - mins[i_] for i_ in hi)
                for i_ in lo: gaps[i_] = mins[i_]
                if cap > 0:
                    f_ = min(1.0, dl / cap)
                    for i_ in hi: gaps[i_] -= (gaps[i_] - mins[i_]) * f_
            s = 0.0
            for j, n in enumerate(inn):
                s += gaps[j] + ws[j] / 2; pos[n] = (B - u * (Ltot - s)) if (_sei and _sei[0] == -1) else (A + u * s); s += ws[j] / 2
                left_k = [k for k in inc[n] if anc(k, n)["v"][0] < 0][0]
                prev_k = ch["ks"][j]           # Strecke Richtung A
                r = th if prev_k == left_k else th + 180
                rot[n] = ((r + 180) % 360) - 180
                # quer so verschieben, dass die Anschlusspunkte auf der Kettenachse liegen (keine Stufe zwischen Nachbarn)
                nv = np.array([-u[1], u[0]])
                q = np.mean([float(rotv(np.array(anc(k, n)["off"], float), rot[n]) @ nv) for k in inc[n] if anc(k, n) is not None] or [0.0])
                # Durchgehende Gerade (3.11.2026, Regel 1, MOB La Tine – Oeschseite): nicht die Mitte der Anschlussbündel,
                # sondern das durchgehende Gleis auf die Kettenachse: das Anschlusspaar links/rechts mit dem kleinsten
                # Querversatz (das Gleis, das gerade durch den Bahnhof läuft). Lage auto.gerade_kette (Standard an).
                _as = [anc(k, n) for k in inc[n] if anc(k, n) is not None and anc(k, n).get("pts")]
                if P.get("gerade_kette", True) and len(_as) == 2:
                    _q1 = [float(rotv(np.array(p_, float), rot[n]) @ nv) for p_ in _as[0]["pts"]]
                    _q2 = [float(rotv(np.array(p_, float), rot[n]) @ nv) for p_ in _as[1]["pts"]]
                    x_, y_ = min(((x_, y_) for x_ in _q1 for y_ in _q2), key=lambda t: abs(t[0] - t[1]))
                    # Paarung mit dem Nachbarn (23.11.2026, V4d, Hinweis pjyb Riedbach – Bern Brünnen): bei Doppelspur gibt es
                    # zwei gleich gerade Paare (Gl. 1 oder Gl. 2 auf der Achse); gewählt wird das, dessen Gleise an die Gleise
                    # des vorherigen Bahnhofs der Kette anschliessen – sonst ein Gleisabstand Versatz auf der Strecke
                    # (S-Kurve). Lage auto.kette_paarung (Standard an), REGELN 4.5.
                    _kp = inn[j - 1] if j > 0 else None
                    if P.get("kette_paarung", True) and _kp is not None and _kp in _qn and anc(prev_k, _kp) is not None \
                            and anc(prev_k, n) is not None and anc(prev_k, _kp).get("pts") and anc(prev_k, n).get("pts"):
                        _d0 = abs(x_ - y_)
                        _kand = sorted({(round(a1, 3), round(a2, 3)) for a1 in _q1 for a2 in _q2 if abs(a1 - a2) <= _d0 + 0.5})
                        _pv = [float(rotv(np.array(p_, float), rot[_kp]) @ nv) - _qn[_kp] for p_ in anc(prev_k, _kp)["pts"]]
                        _cv = [float(rotv(np.array(p_, float), rot[n]) @ nv) for p_ in anc(prev_k, n)["pts"]]
                        def _miss(t_):
                            qq_ = (t_[0] + t_[1]) / 2
                            return sum(min(abs(c_ - qq_ - v_) for v_ in _pv) for c_ in _cv)
                        if len(_kand) > 1:
                            x_, y_ = min(_kand, key=_miss)
                            if os.environ.get("KIPPDBG"): print("PAAR", nodes[n]["name"], _kand, round(_miss((x_, y_)), 1))
                    q = (x_ + y_) / 2
                    # Kippen statt Versatz (4.11.2026, Punkt 4, Château-d'Oex: Einspur links auf Gl. 1, rechts auf Gl. 3):
                    # liegen Ein- und Ausfahrt quer versetzt, wird der Plan um höchstens «kipp_max» Grad (8°) gedreht,
                    # sodass beide auf der Kettenachse liegen; die Nachbarstrecken bleiben gerade.
                    if abs(x_ - y_) > 0.5 and P.get("kipp_max", 8) > 0:
                        _p1 = min(_as[0]["pts"], key=lambda p_: abs(float(rotv(np.array(p_, float), rot[n]) @ nv) - x_))
                        _p2 = min(_as[1]["pts"], key=lambda p_: abs(float(rotv(np.array(p_, float), rot[n]) @ nv) - y_))
                        best_k = (abs(x_ - y_), 0.0)
                        _v = rotv(np.array(_p2, float) - np.array(_p1, float), rot[n])
                        _a0 = math.degrees(math.atan2(float(_v @ nv), float(_v @ u)))
                        for a_ in (_a0, -_a0, 180 - _a0, _a0 - 180):
                            a_ = ((a_ + 180) % 360) - 180
                            if abs(a_) > P.get("kipp_max", 8): continue
                            r_ = rot[n] + a_
                            d_ = abs(float(rotv(np.array(_p1, float), r_) @ nv) - float(rotv(np.array(_p2, float), r_) @ nv))
                            if d_ < best_k[0] - 1e-6: best_k = (d_, a_)
                        if os.environ.get("KIPPDBG"): print("KIPP", nodes[n]["name"], round(x_, 1), round(y_, 1), best_k)
                        if best_k[1] and best_k[0] < 0.5:
                            rot[n] = rot[n] + best_k[1]
                            q = (float(rotv(np.array(_p1, float), rot[n]) @ nv) + float(rotv(np.array(_p2, float), rot[n]) @ nv)) / 2
                pos[n] = pos[n] - nv * q; _qn[n] = q
        return pos
    def bbox(n, p):
        w, h = boxwh(n); a = math.radians(rot.get(n, 0)); c, s = abs(math.cos(a)), abs(math.sin(a))
        W, H = w * c + h * s, w * s + h * c; return (p[0] - W / 2, p[1] - H / 2, p[0] + W / 2, p[1] + H / 2)
    extra = []
    for it in range(30):
        hp = solve(extra); pos = place(hp)
        ins = [n for n in MAJOR if nodes[n]["inset"]]
        bad = []
        def corners(n):
            w, h = boxwh(n); w += P["rand"]; h += P["rand"]; a = math.radians(rot.get(n, 0))
            ux, uy = np.array([math.cos(a), math.sin(a)]), np.array([-math.sin(a), math.cos(a)])
            c = pos[n]; return [c + sx * ux * w / 2 + sy * uy * h / 2 for sx in (-1, 1) for sy in (-1, 1)], (ux, uy)
        def overlap(a, b):          # Trennachsen-Test für gedrehte Rechtecke
            ca, axa = corners(a); cb, axb = corners(b)
            for ax in axa + axb:
                pa = [float(p @ ax) for p in ca]; pb = [float(p @ ax) for p in cb]
                if max(pa) <= min(pb) or max(pb) <= min(pa): return False
            return True
        for i, a in enumerate(ins):
            for b in ins[i + 1:]:
                if not overlap(a, b): continue
                A_, B_ = bbox(a, pos[a]), bbox(b, pos[b])
                ox = min(A_[2], B_[2]) - max(A_[0], B_[0]) + P["rand"]; oy = min(A_[3], B_[3]) - max(A_[1], B_[1]) + P["rand"]
                bad.append((a, b, max(ox, 1), max(oy, 1)))
        kurz = []                       # Ketten, die kürzer geraten sind als ihre Bahnhöfe brauchen
        for ch in chains:
            a_, b_ = ch["seq"][0], ch["seq"][-1]
            if len(ch["seq"]) < 3 or a_ not in hidx or b_ not in hidx: continue
            A = hp[a_] + port(a_, ch["ks"][0]); B = hp[b_] + port(b_, ch["ks"][-1])
            Lt = float(np.linalg.norm(B - A)); nd = need(ch)
            if Lt < nd * 0.98:
                kurz.append(ch)
                u_ = (B - A) / (Lt or 1.0)
                extra.append((a_, b_, hp[b_] - hp[a_] + u_ * (nd * 1.04 - Lt), 3.0))
        if not bad and not kurz: break
        for a, b, ox, oy in bad:        # Ketten-Enden auseinanderschieben (bei gemeinsamem Anfang die anderen Enden)
            def chain_of(n):
                for ch in chains:
                    if n in ch["seq"][1:-1]: return ch
                return None
            ca, cb = chain_of(a), chain_of(b)
            ends_a = [a] if ca is None else [ca["seq"][0], ca["seq"][-1]]
            ends_b = [b] if cb is None else [cb["seq"][0], cb["seq"][-1]]
            cand = [(ha, hb) for ha in ends_a for hb in ends_b if ha != hb and ha in hidx and hb in hidx]
            if not cand: continue
            # das Paar, dessen Verbindung am ehesten quer zur Überlappung liegt: am weitesten auseinander
            ha, hb = max(cand, key=lambda t_: np.linalg.norm(hp[t_[1]] - hp[t_[0]]))
            d = hp[hb] - hp[ha]; dab = pos[b] - pos[a]
            nrm = dab / (np.linalg.norm(dab) or 1.0); amt = max(min(ox, oy), 20) + 30
            extra.append((ha, hb, d + nrm * amt, 2.0))
    if kurz: print("  zu kurze Ketten:", [nodes[ch["seq"][1]]["name"] for ch in kurz])
    if bad: print("  Überlappungen:", [(nodes[a]["name"], nodes[b]["name"]) for a, b, _, _ in bad][:12])
    print(f"  Lage Ketten: {len(chains)} Ketten, {len(hubs)} Knoten, {len(inner)} Bahnhöfe auf Ketten, {it + 1} Durchgänge, Rest-Überlappungen {len(bad)}")
    return pos, rot
