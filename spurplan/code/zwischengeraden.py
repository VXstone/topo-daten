"""Zwischengeraden in Bahnhofplänen zählen (Schritt K0, 19.11.2026; REGELN 1.9, Messung W8 aus region_geometrie.py).

  python3 zwischengeraden.py <plaene_dir|plan.svg ...> [--json aus.json] [--md aus.md] [--lane 24]

Eine Zwischengerade (ZG) ist ein kurzes waagrechtes Stück (< 2 Ebenen; länger bis 8 Ebenen = ZL) zwischen zwei Knicken, bei dem das Gleis vorher und
nachher in **dieselbe** Richtung die Ebene wechselt (Treppe: Gleis 3 → halbe Ebene → Gleis 4) und an beiden Knicken weder eine
Weiche noch ein Gleisende liegt. Ein «Höcker» (hinauf, kurz waagrecht, wieder hinunter) wird getrennt gezählt (HK).

Anders als W8 im Regionalplan werden die Teilpfade eines Plans zuerst zu durchgehenden Gleisen verkettet (die Schemazeichnung
setzt ein Gleis aus vielen Teilpfaden zusammen: Gerade, Weichenverbindung, Gerade …). Nur Gleisfarben (grün, schwarz, braun).
Ausgabe je Plan: Anzahl ZG und HK mit Lage (x, y der Mitte des waagrechten Stücks).
"""
import re, sys, os, json, math, collections

FARBEN = ("#00862f", "#111", "#9a5b1e")


def zahlen(t): return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", t)]


def polylinien(svg):
    """Teilpfade der Gleise als Eckpunkt-Listen (M, H/L-Enden, Q-Kontrollpunkte; kollineare Punkte weg)."""
    out = []
    for m in re.finditer(r"<path\b[^>]*>", svg):
        t = m.group(0)
        if "fill=\"none\"" not in t and "stroke=" not in t: continue
        st = re.search(r'stroke="([^"]*)"', t)
        if not st or st.group(1) not in FARBEN: continue
        if re.search(r'fill="(?!none)[^"]*"', t): continue
        if 'stroke-opacity' in t or 'stroke-dasharray' in t: continue     # DKW-Bögen, Dreischienen-Strich
        d = re.search(r'\bd="([^"]*)"', t)
        if not d: continue
        for sub in re.split(r"(?=M)", d.group(1)):
            toks = re.findall(r"([MHLQCV])([^MHLQCV]*)", sub)
            if not toks: continue
            pts = []; cur = None; krumm = False
            for c, a in toks:
                v = zahlen(a)
                if c == "M": cur = (v[0], v[1]); pts.append(cur)
                elif c == "H":
                    for x in v: cur = (x, cur[1]); pts.append(cur)
                elif c == "V":
                    for y in v: cur = (cur[0], y); pts.append(cur)
                elif c == "L":
                    for i in range(0, len(v) - 1, 2): cur = (v[i], v[i + 1]); pts.append(cur)
                elif c == "Q":
                    for i in range(0, len(v) - 3, 4): pts.append((v[i], v[i + 1])); cur = (v[i + 2], v[i + 3])
                    pts.append(cur)
                elif c == "C": krumm = True; cur = (v[-2], v[-1]); pts.append(cur)
            p2 = []
            for p in pts:
                if p2 and math.dist(p, p2[-1]) < 0.15: continue
                p2.append(p)
            if len(p2) < 2: continue
            out.append(dict(pts=_ecken(p2), farbe=st.group(1), krumm=krumm))
    return out


def _ecken(p):
    q = [p[0]]
    for i in range(1, len(p) - 1):
        a, b, c = q[-1], p[i], p[i + 1]
        u = (b[0] - a[0], b[1] - a[1]); w = (c[0] - b[0], c[1] - b[1])
        if abs(u[0] * w[1] - u[1] * w[0]) < 0.02 * (math.hypot(*u) * math.hypot(*w) + 1e-9) and u[0] * w[0] + u[1] * w[1] > 0: continue
        q.append(b)
    q.append(p[-1]); return q


def _abst_seg(p, a, b):
    ax, ay = a; bx, by = b; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy), t


def ist_knoten(p, polys, ausser=(), tol=1.0):
    """Liegt an p eine Weiche oder ein Gleisende (anderer Teilpfad endet dort oder läuft durch)?"""
    n = 0
    for k, P in enumerate(polys):
        if k in ausser: continue
        pts = P["pts"]
        if min(pts[0][0], pts[-1][0], *(q[0] for q in pts)) - tol > p[0] or max(q[0] for q in pts) + tol < p[0]: continue
        for a, b in zip(pts, pts[1:]):
            if _abst_seg(p, a, b)[0] <= tol: return True
    return False


def ketten(polys):
    """Teilpfade an Punkten mit genau zwei Enden (und keinem durchlaufenden Gleis) verketten."""
    key = lambda p: (round(p[0] * 2) / 2, round(p[1] * 2) / 2)
    enden = collections.defaultdict(list)
    for k, P in enumerate(polys):
        enden[key(P["pts"][0])].append((k, 0)); enden[key(P["pts"][-1])].append((k, 1))
    def durch(p, ks):
        return ist_knoten(p, polys, ausser=set(ks))
    nb = {}
    for kp, l in enden.items():
        if len(l) == 2 and l[0][0] != l[1][0] and not durch(kp, [l[0][0], l[1][0]]):
            nb[l[0]] = l[1]; nb[l[1]] = l[0]
    seen = set(); out = []
    for k in range(len(polys)):
        if k in seen: continue
        # Anfang der Kette suchen
        cur, ende = k, 0; guard = 0
        while (cur, ende) in nb and guard < 500:
            j, e = nb[(cur, ende)]
            if j == k: break
            cur, ende = j, 1 - e; guard += 1
        pts = []; ids = []; c, e = cur, ende
        while c not in seen:
            seen.add(c); ids.append(c)
            p = polys[c]["pts"] if e == 0 else polys[c]["pts"][::-1]
            pts += p if not pts else p[1:]
            if (c, 1 - e) not in nb: break
            c, e = nb[(c, 1 - e)]; e = e
        out.append(dict(pts=_ecken(pts), ids=ids, farbe=polys[cur]["farbe"]))
    return out


def finden(svg, lane=24.0):
    polys = polylinien(svg)
    tx = [(float(a), float(b)) for a, b in re.findall(r'<text\b[^>]*?\bx="(-?[\d.]+)"[^>]*?\by="(-?[\d.]+)"', svg)]
    befunde = []
    for K in ketten(polys):
        p = K["pts"]
        for i in range(1, len(p) - 2):
            a0, a1, a2, a3 = p[i - 1], p[i], p[i + 1], p[i + 2]
            if abs(a2[1] - a1[1]) > 0.3: continue                       # Mittelstück waagrecht
            L = abs(a2[0] - a1[0])
            if not (0.3 < L < 8 * lane): continue
            dy1 = a1[1] - a0[1]; dy3 = a3[1] - a2[1]
            if abs(dy1) < 0.5 or abs(dy3) < 0.5: continue               # beide Nachbarn schräg
            # Knicke = keine Weiche / kein Gleisende eines anderen Teilpfads
            if ist_knoten(a1, polys, ausser=set(K["ids"])) or ist_knoten(a2, polys, ausser=set(K["ids"])): continue
            xm, ym = (a1[0] + a2[0]) / 2, a1[1]
            if any(abs(x - xm) < L / 2 + 14 and abs(y - 6.5 - ym) < 4 for x, y in tx): continue     # Gleisnummer auf dem Stück
            gleich = (dy1 > 0) == (dy3 > 0)
            if not gleich and L >= 2 * lane: continue
            art = ("ZG" if L < 2 * lane else "ZL") if gleich else "HK"
            befunde.append(dict(art=art, x=round(xm, 1), y=round(ym, 1), laenge=round(L, 1), farbe=K["farbe"],
                                von=[round(a1[0], 1), round(a1[1], 1)], bis=[round(a2[0], 1), round(a2[1], 1)]))
    return befunde


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    lane = float(opt("--lane", 24))
    args = [a for a in args if a not in (opt("--json"), opt("--md"), opt("--lane"))]
    dateien = []
    for a in args:
        if os.path.isdir(a): dateien += sorted(os.path.join(a, f) for f in os.listdir(a) if f.endswith(".svg"))
        else: dateien.append(a)
    erg = {}
    for f in dateien:
        name = os.path.splitext(os.path.basename(f))[0]
        if name.startswith("region") or name.startswith("blaupause"): continue     # nur Bahnhofpläne
        try: b = finden(open(f).read(), lane)
        except Exception as ex: erg[name] = dict(fehler=str(ex)[:200]); continue
        erg[name] = dict(ZG=sum(1 for x in b if x["art"] == "ZG"), ZL=sum(1 for x in b if x["art"] == "ZL"), HK=sum(1 for x in b if x["art"] == "HK"), befunde=b)
    sZG = sum(v.get("ZG", 0) for v in erg.values()); sZL = sum(v.get("ZL", 0) for v in erg.values()); sHK = sum(v.get("HK", 0) for v in erg.values())
    print(f"{len(erg)} Bahnhofpläne: Zwischengeraden ZG {sZG} (< 2 Ebenen), lang ZL {sZL}, Höcker HK {sHK}; Pläne mit ZG: {sum(1 for v in erg.values() if v.get('ZG'))}")
    for n, v in sorted(erg.items(), key=lambda t: (-t[1].get("ZG", 0), -t[1].get("ZL", 0))):
        if v.get("ZG") or v.get("ZL") or v.get("HK"): print(f"  {n:32} ZG {v.get('ZG', 0):3}  ZL {v.get('ZL', 0):3}  HK {v.get('HK', 0):3}")
    if opt("--json"): json.dump(dict(ZG=sZG, ZL=sZL, HK=sHK, plaene=erg), open(opt("--json"), "w"), ensure_ascii=False, indent=1)
    if opt("--md"):
        with open(opt("--md"), "w") as fh:
            fh.write(f"# Zwischengeraden in Bahnhofplänen (REGELN 1.9)\n\nZG {sZG} (< 2 Ebenen, legt der Code zusammen), ZL {sZL} (länger), HK {sHK} (Höcker)\n\n| Plan | ZG | ZL | HK | Lage (x/y) |\n|---|---|---|---|---|\n")
            for n, v in sorted(erg.items(), key=lambda t: (-t[1].get("ZG", 0), -t[1].get("ZL", 0))):
                if v.get("ZG") or v.get("ZL") or v.get("HK"):
                    fh.write(f"| {n} | {v['ZG']} | {v['ZL']} | {v['HK']} | {', '.join(b['art'] + ' ' + format(b['x'], '.0f') + '/' + format(b['y'], '.0f') for b in v['befunde'])} |\n")
