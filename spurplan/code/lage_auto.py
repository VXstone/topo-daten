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
import math
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
    for n in hubs:
        if not nodes[n]["inset"] or n in rot: continue
        Pp = PORTS[n]["ports"]
        bb = [p["bearing"] for p in Pp if p["kind"] == "edge" and p["dx"] > 0] + [p["bearing"] + 180 for p in Pp if p["kind"] == "edge" and p["dx"] < 0]
        if not bb: rot[n] = 0; continue
        th = math.degrees(math.atan2(np.mean([math.sin(math.radians(b)) for b in bb]), np.mean([math.cos(math.radians(b)) for b in bb])))
        a = round(-th / P["schritt"]) * P["schritt"]; rot[n] = ((a + 180) % 360) - 180
    def port(n, k):         # Anschlusspunkt der Strecke k am Knoten n relativ zur Mitte (gedreht)
        a_ = anc(k, n)
        if a_ is None or n in inner: return np.zeros(2)
        return rotv(np.array(a_["off"], float), rot.get(n, 0))
    def need(ch):           # Platzbedarf der inneren Bahnhöfe entlang der Kette (an Abzweigen mehr Luft)
        inn = ch["seq"][1:-1]
        extra_ = sum((P["abzweig_gap"] if not nodes[h_]["inset"] else P["knoten_gap"]) - P["gap"] for h_ in (ch["seq"][0], ch["seq"][-1]) if nodes[h_]["kind"] != "exit")
        return sum(boxwh(n)[0] for n in inn) + (len(inn) + 1) * P["gap"] + extra_
    for ch in chains:
        a, b = ch["seq"][0], ch["seq"][-1]
        ex = nodes[a]["kind"] == "exit" or nodes[b]["kind"] == "exit"
        L = max(need(ch), (P["abgang"] if ex and len(ch["seq"]) == 2 else P["c0"] + P["c1"] * ch["km"] ** P["p"]) + (need(ch) if ex else 0))
        d = geo[b] - geo[a]; ch["T"] = d / (np.linalg.norm(d) or 1) * L
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
            if float(u_ @ d) > 0.5 * (np.linalg.norm(d) or 1): ch["T"] = u_ * L; ch["w"] = P.get("seiten_gewicht", 1.0)
            if os.environ.get("KDBG"): print("SEITE", [nodes[x]["name"] for x in ch["seq"]], u_.round(2), (d / (np.linalg.norm(d) or 1)).round(2))
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
                    for c_, s_, d_ in ((c1, s1, -dl), (c2, s2, dl)):
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
        pos = dict(hp)
        for ch in chains:
            a, b = ch["seq"][0], ch["seq"][-1]
            A = hp[a] + port(a, ch["ks"][0]); B = hp[b] + port(b, ch["ks"][-1])
            inn = ch["seq"][1:-1]
            if not inn: continue
            dv = B - A; Ltot = np.linalg.norm(dv) or 1.0; u = dv / Ltot
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
            # kein Zwischenraum unter dem Mindestabstand (sonst überlagern sich die Stummel zweier Bahnhöfe)
            for _ in range(5):
                lo = [i_ for i_, g_ in enumerate(gaps) if g_ < P["gap"] - 0.5]
                if not lo: break
                dl = sum(P["gap"] - gaps[i_] for i_ in lo)
                hi = [i_ for i_, g_ in enumerate(gaps) if g_ > P["gap"] + 0.5]
                cap = sum(gaps[i_] - P["gap"] for i_ in hi)
                for i_ in lo: gaps[i_] = P["gap"]
                if cap > 0:
                    f_ = min(1.0, dl / cap)
                    for i_ in hi: gaps[i_] -= (gaps[i_] - P["gap"]) * f_
            s = 0.0
            for j, n in enumerate(inn):
                s += gaps[j] + ws[j] / 2; pos[n] = A + u * s; s += ws[j] / 2
                left_k = [k for k in inc[n] if anc(k, n)["v"][0] < 0][0]
                prev_k = ch["ks"][j]           # Strecke Richtung A
                r = th if prev_k == left_k else th + 180
                rot[n] = ((r + 180) % 360) - 180
                # quer so verschieben, dass die Anschlusspunkte auf der Kettenachse liegen (keine Stufe zwischen Nachbarn)
                nv = np.array([-u[1], u[0]])
                q = np.mean([float(rotv(np.array(anc(k, n)["off"], float), rot[n]) @ nv) for k in inc[n] if anc(k, n) is not None] or [0.0])
                pos[n] = pos[n] - nv * q
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
