"""Typvorschlag für kleine Bahnhöfe aus OSM (Standardisieren statt Manufaktur, 16.10.2026).
  python3 typ_vorschlag.py <bahnhof> [...]     -> druckt den Vorschlag (JSON) für "vorlage" im Override
Liest <bahnhof>.json (OSM-Ausschnitt) und <bahnhof>_osm_ports.json bzw. <bahnhof>_ports.json (Abgänge aus dem
allgemeinen Lauf). Ergebnis: typ (halt | halt2 | kreuzung | ueberholung | manufaktur), Gleise im Querschnitt am
Bahnhof (oben -> unten), Personengleise, Gleisnummern, Perrons, Anschlussgleise, seitliche Abzweige.
"""
import json, math, sys, os, collections
import networkx as nx

TOPO = "ne_region_topologie.json"

def lade(key):
    E = json.load(open(f"{key}.json"))["elements"]
    pf = f"{key}_osm_ports.json" if os.path.exists(f"{key}_osm_ports.json") else f"{key}_ports.json"
    P = json.load(open(pf))
    return E, P

def vorschlag(key):
    E, PO = lade(key)
    st = next(e for e in E if e["type"] == "node" and e.get("tags", {}).get("railway") == "station")
    lat0, lon0 = st["lat"], st["lon"]; kx = 111320 * math.cos(math.radians(lat0))
    xy = lambda la, lo: ((lo - lon0) * kx, (la - lat0) * 110540)
    rails = [w for w in E if w["type"] == "way" and w["tags"].get("railway") == "rail" and w["tags"].get("gauge", "1435") == "1435"]
    WP = {w["id"]: [xy(g["lat"], g["lon"]) for g in w["geometry"]] for w in rails}
    NP = {}
    for w in rails:
        for n, p in zip(w["nodes"], WP[w["id"]]): NP[n] = p
    ports = [p for p in PO["ports"] if p["kind"] == "edge"]
    side = [p for p in PO["ports"] if p["kind"] == "side"]
    L = [p for p in ports if p["dx"] < 0]; R = [p for p in ports if p["dx"] > 0]
    # Richtung links -> rechts aus den Abgängen (Mittel), sonst aus der längsten Hauptgleis-Strecke
    if L and R:
        a = xy(sum(p["lat"] for p in L) / len(L), sum(p["lon"] for p in L) / len(L))
        b = xy(sum(p["lat"] for p in R) / len(R), sum(p["lon"] for p in R) / len(R))
    else:
        a, b = (-1, 0), (1, 0)
    u = (b[0] - a[0], b[1] - a[1]); nu = math.hypot(*u); u = (u[0] / nu, u[1] / nu)
    nrm = (-u[1], u[0])                       # links der Fahrrichtung = oben im Plan
    proj = lambda p: (p[0] * u[0] + p[1] * u[1], p[0] * nrm[0] + p[1] * nrm[1])
    # Querschnitt in der Bahnhofsmitte: Mitte der Perrons (bis 600 m vom Stationsknoten), sonst Stationsknoten
    S0 = 0.0
    _ps = []
    for e in E:
        tg = e.get("tags", {})
        if e["type"] == "way" and (tg.get("railway") == "platform" or tg.get("public_transport") == "platform"):
            pts_ = [proj(xy(g["lat"], g["lon"])) for g in e["geometry"]]
            s_ = sum(p[0] for p in pts_) / len(pts_)
            if abs(s_) < 600: _ps.append(s_)
    if _ps: S0 = sorted(_ps)[len(_ps) // 2]
    NEBEN = ("yard", "spur", "industrial")
    def profil(S, dmax=60):
        pr_ = []
        for w in rails:
            if w["tags"].get("service") in NEBEN: continue
            pts = [proj(p) for p in WP[w["id"]]]
            for (s0, d0), (s1, d1) in zip(pts, pts[1:]):
                if (s0 <= S <= s1 or s1 <= S <= s0) and s0 != s1:
                    d = d0 + (d1 - d0) * (S - s0) / (s1 - s0)
                    if abs(d) < dmax: pr_.append((d, w))
        pr_.sort(key=lambda t: -t[0]); out = []
        for d, w in pr_:
            if out and abs(out[-1]["d"] - d) < 2.5: continue
            t = w["tags"]
            out.append(dict(d=round(d, 1), way=w["id"], service=t.get("service"), nr=t.get("railway:track_ref"),
                            pax=not t.get("service") or t.get("service") == "siding" and bool(t.get("railway:track_ref"))))
        return out
    tracks = profil(S0)
    # Gleise an den Bahnhofsenden (450 m vor/nach der Mitte, ohne Abstell-/Kreuzungsgleise): Einspur/Doppelspur je Seite
    ENDE = 450
    # Streckengleise je Seite: Abgänge des allgemeinen Laufs, ergänzt um die Gleiszahl der anschliessenden Strecke
    # aus der Netztopologie (Querschnitt mitten auf der Strecke; fängt z. B. Doppelspurbeginn knapp hinter Zihlbrücke)
    end_n = {-1: len(L), 1: len(R)}
    tf = TOPO if os.path.exists(TOPO) else None
    if tf:
        T = json.load(open(tf)); nm = PO.get("title")
        st_n = [n for n in T["nodes"] if n["name"] == nm and n["kind"] in ("station", "halt")]
        if st_n:
            sn = st_n[0]
            for e in T["edges"]:
                if sn["id"] not in (e["a"], e["b"]): continue
                g = e["geom"] if e["a"] == sn["id"] else e["geom"][::-1]
                acc = 0; q = g[-1]
                for p0, p1 in zip(g, g[1:]):
                    acc += math.dist(p0, p1)
                    if acc > 300: q = p1; break
                s_, _ = proj((q[0] - sn["x"], q[1] - sn["y"]))
                k = -1 if s_ < 0 else 1
                end_n[k] = max(end_n[k], int(e.get("tracks", 1)))
    end_l = [None] * end_n[-1]; end_r = [None] * end_n[1]
    # Hauptweg zwischen den Abgängen (bevorzugt usage=main, ohne service)
    G = nx.Graph()
    for w in rails:
        f = 1 if w["tags"].get("usage") == "main" else 2 if not w["tags"].get("service") else 6
        for x_, y_ in zip(w["nodes"], w["nodes"][1:]): G.add_edge(x_, y_, w=math.dist(NP[x_], NP[y_]) * f, way=w["id"])
    main_ways = set()
    for pl in L:
        for pr in R:
            try:
                wa = next(w for w in rails if w["id"] == pl.get("way")); wb = next(w for w in rails if w["id"] == pr.get("way"))
                path = min((nx.shortest_path(G, s_, t_, weight="w") for s_ in (wa["nodes"][0], wa["nodes"][-1]) for t_ in (wb["nodes"][0], wb["nodes"][-1])),
                           key=lambda p_: sum(G[x_][y_]["w"] for x_, y_ in zip(p_, p_[1:])))
                main_ways |= {G[x_][y_]["way"] for x_, y_ in zip(path, path[1:])}
            except Exception:
                pass
    for t in tracks: t["haupt"] = t["way"] in main_ways
    # Perrons: Lage relativ zu den Gleisen im Querschnitt
    perrons = []
    for e in E:
        tg = e.get("tags", {})
        if e["type"] == "way" and (tg.get("railway") == "platform" or tg.get("public_transport") == "platform") \
                and not (tg.get("disused") == "yes" or "disused:public_transport" in tg):      # stillgelegt zählt nicht (20.10.)
            pts = [proj(xy(g["lat"], g["lon"])) for g in e["geometry"]]
            d = sum(p[1] for p in pts) / len(pts); s = sum(p[0] for p in pts) / len(pts)
            if abs(s - S0) > 400: continue
            ab = [t["d"] for t in tracks]
            ober = [x for x in ab if x > d]; unter = [x for x in ab if x < d]
            lage = "zwischen" if ober and unter else ("oben" if not ober else "unten")
            perrons.append(dict(d=round(d, 1), lage=lage, ref=tg.get("ref")))
    # Weichen zu Nebengleisen (nicht im Querschnitt): Anschlüsse
    prof_ways = {t["way"] for t in tracks}
    deg = collections.Counter(n for w in rails for n in (w["nodes"][0], w["nodes"][-1]))
    allnodes = collections.Counter(n for w in rails for n in w["nodes"])
    anschl = []
    neben = [w for w in rails if w["tags"].get("service") in NEBEN or (w["tags"].get("service") == "siding" and w["id"] not in prof_ways)]
    H = nx.Graph()
    for w in neben:
        for x_, y_ in zip(w["nodes"], w["nodes"][1:]): H.add_edge(x_, y_)
    hauptnodes = {n for w in rails if w["id"] not in {x["id"] for x in neben} for n in w["nodes"]}
    for comp in nx.connected_components(H):
        att = [n for n in comp if n in hauptnodes]
        if not att: continue
        sa, da = proj(NP[att[0]]); sa -= S0
        if abs(sa) > 600: continue
        enden = [n for n in comp if deg[n] == 1 and allnodes[n] == 1 and n not in hauptnodes]
        # Verbindung zwischen zwei Hauptgleisen (Nebengleis-Ways als Spurwechsel/Weichenleiter, Bevaix 20.10.: "woher kommt
        # dieses Gleis?") ist kein Anschluss; ein Anschluss hat Stumpenden oder läuft aus dem Ausschnitt
        _da = sorted(proj(NP[n])[1] for n in att)
        if len(att) >= 2 and _da[-1] - _da[0] > 2.5: continue
        if not enden and all(math.hypot(*NP[n]) < 1100 for n in comp): continue
        ds = [proj(NP[n])[1] for n in comp]
        ss = [proj(NP[n])[0] - S0 for n in comp]
        seite = "oben" if sum(ds) / len(ds) > da else "unten"
        ende = "links" if sa < 0 else "rechts"
        innen = (sum(ss) / len(ss) - sa) * (1 if ende == "links" else -1) > 0
        anschl.append(dict(ende=ende, lage="innen" if innen else "aussen", seite=seite, stumpen=max(1, min(len(enden), 2)),
                           s=round(sa), knoten=att[0]))
    # Spurwechsel zwischen zwei Streckengleisen (kurze Ways mit Querversatz, ±600 m)
    spw = []
    for w in rails:
        if w["tags"].get("service") in NEBEN or w["id"] in {t_["way"] for t_ in tracks}: continue
        pts = [proj(p) for p in WP[w["id"]]]
        ds_ = pts[-1][1] - pts[0][1]; ss_ = pts[-1][0] - pts[0][0]
        L_ = sum(math.dist(p, q) for p, q in zip(WP[w["id"]], WP[w["id"]][1:]))
        if (w["tags"].get("service") == "crossover" or (L_ < 250 and abs(ds_) > 2.5)) and abs(ds_) < 8 \
                and abs((pts[0][0] + pts[-1][0]) / 2 - S0) < 600 and deg[w["nodes"][0]] + 0 and deg[w["nodes"][-1]]:
            spw.append(dict(s=round((pts[0][0] + pts[-1][0]) / 2 - S0), richtung="steigend" if ds_ * ss_ > 0 else "fallend"))
    # Reinform
    nL, nR = len(end_l), len(end_r); nT = len(tracks)
    strecke = "doppelspur" if nL >= 2 and nR >= 2 else "einspur"
    v = dict(strecke=strecke)
    hi = [i for i, t in enumerate(tracks) if t["haupt"]] or [i for i, t in enumerate(tracks) if not t["service"]]
    z = []
    if strecke == "einspur":
        if nT == 1: v["form"] = "halt"
        elif nT == 2:
            v["form"] = "kreuzung"
            h = hi[:1] or [1]
            if h == [0]: v["spiegeln"] = True
        else: v["form"] = "manufaktur"
        for ende, n_, prof_ in (("links", nL, end_l), ("rechts", nR, end_r)):
            if n_ == 2:
                z.append(dict(art="doppelspurbeginn", ende=ende, seite="unten"))
            elif n_ > 2: v["form"] = "manufaktur"
    else:
        if nT == 2: v["form"] = "halt"
        elif nT == 4: v["form"] = "ueberholung"
        elif nT == 3:
            v["form"] = "ueberholung"
            v["ueberholgleise"] = "oben" if not tracks[0]["haupt"] else "unten"
        else: v["form"] = "manufaktur"
        for side_, grp in (("links", [s_ for s_ in spw if s_["s"] < 0]), ("rechts", [s_ for s_ in spw if s_["s"] >= 0])):
            if grp:
                rr = {s_["richtung"] for s_ in grp}
                z.append(dict(art="spurwechsel", ende=side_, anzahl=2 if len(rr) == 2 else 1, richtung=grp[0]["richtung"]))
    v["gleise"] = [t["nr"] for t in tracks]
    v["pax"] = [bool(t["pax"]) for t in tracks]
    lg = sorted({p["lage"] for p in perrons})
    if not perrons: v["perrons"] = "keine"
    elif lg == ["zwischen"]: v["perrons"] = "mittel"
    elif lg == ["oben", "unten"]: v["perrons"] = "aussen"
    else: v["perrons"] = "+".join(lg)
    z += [dict(art="anschluss", **{k: a_[k] for k in ("ende", "lage", "seite", "stumpen")}) for a_ in anschl]
    z += [dict(art="abzweig", ende="rechts" if p["dx"] > 0 else "links", seite="oben" if p.get("dy", 0) < 0 else "unten") for p in side]
    if z: v["zusaetze"] = z
    v["_osm"] = dict(querschnitt=[(t["d"], t["nr"], t["service"], t["haupt"]) for t in tracks], enden=[nL, nR], abzweige=len(side),
                     perrons=[(p["d"], p["lage"], p["ref"]) for p in perrons], spurwechsel=spw)
    return v

def mit_ortskenntnis(key, v):
    """Gleisnummern und Perronlage aus den von Daniel geprüften Overrides (nummern_px, perrons_px) übernehmen."""
    try: o = json.load(open(f"{key}_override.json"))
    except Exception: return v
    nums = sorted(o.get("nummern_px", []), key=lambda t: t[2])
    n = len(v.get("gleise", []))
    if nums and len(nums) == n: v["gleise"] = [t[0] for t in nums]
    per = o.get("perrons_px", [])
    if per and nums and len(nums) == n:
        ys = [t[2] for t in nums]; teile = []
        for x0, x1, y in per:
            lage = "oben" if y < min(ys) else "unten" if y > max(ys) else "zwischen"
            if lage not in teile: teile.append(lage)
        v["perrons"] = "aussen" if sorted(teile) == ["oben", "unten"] else "mittel" if teile == ["zwischen"] else "+".join(sorted(teile))
    return v

if __name__ == "__main__":
    for key in sys.argv[1:]:
        try:
            v = vorschlag(key); o = v.pop("_osm")
            print(key, json.dumps(v, ensure_ascii=False), " | OSM", json.dumps(o, ensure_ascii=False))
        except Exception as ex:
            print(key, "FEHLER", ex)
