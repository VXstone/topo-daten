"""Bahnhofsvorlagen: Reinform + Zusätze (Standardisieren statt Manufaktur; Daniel 16.10.2026).
  python3 vorlage.py <bahnhof> [...]            Plan nach Override-Schlüssel "vorlage" zeichnen
  python3 vorlage.py --blaupause2 <datei.svg>    Blatt «Blaupause 2 – Bahnhofstypen» aus demselben Code

Beschreibung (Override "vorlage"):
  {"strecke": "einspur" | "doppelspur",
   "form": "halt" | "kreuzung" (einspur) | "ueberholung" (doppelspur),
   "ueberholgleise": "beide" | "oben" | "unten"           (ueberholung, Standard beide)
   "perrons": "aussen" | "mittel" | "oben" | "unten" | "keine" | Kombination mit "+",
   "spiegeln": false                                       (true = oben/unten vertauscht, z. B. Kreuzungsgleis unten)
   "orte": {"links": "Murten", "rechts": "Fribourg"}      (optional: Zielort je Seite, wenn die Peilung irrt)
   "abgaenge_knoten": {"rechts": [osm, osm]}              (optional: OSM-Knoten der Abgänge je Seite von oben nach unten, V4e)
   jeder Zusatz optional "weichen": [[osm, x, y]]         (OSM-Weiche am gezeichneten Abzweig festlegen, V4e)
   "gleise": ["1", "2"], "pax": [true, true]               (von oben nach unten, wie gezeichnet)
   "zusaetze": [                                           (alle Seiten- und Perronangaben wie gezeichnet, auch gespiegelt)
     {"art": "spurwechsel", "ende": "links|rechts", "anzahl": 1|2, "richtung": "steigend|fallend"},
     {"art": "anschluss", "ende": "links|rechts", "lage": "innen|aussen", "seite": "oben|unten", "stumpen": 1|2, "pfeil": false,
      "gleich_lang": false, "verlaengern": 0, "t_form": false, "t_laenge": 60, "gegen": false},   # t_form: zweiter Stumpen am Fuss in Gegenrichtung   # gleich_lang (nur innen): alle Stumpen enden gleich, verlaengern px über den Perron hinaus
     {"art": "abzweig", "ende": "links|rechts", "seite": "oben|unten"},
     {"art": "doppelspurbeginn", "ende": "links|rechts", "seite": "oben|unten", "aus": "kreuzungsgleis"?} ]}
Grundriss (kanonisch, vor dem Spiegeln): Kreuzungs- und Überholgleise liegen oben bzw. aussen, Anschlüsse am
äussersten Gleis ihrer Seite. Masse wie Blaupause: Ebenen 24 px, 60°, Ausrundung 7 px, Perron 110 px, Nummer in der Mitte.
Ausgabe wie der allgemeine Lauf (<b>_spurplan.svg, _spurplan_check.svg, _bare.svg, _ports.json); die OSM-Abgänge des
allgemeinen Laufs werden als <b>_osm_ports.json gesichert und zugeordnet (Liniennummer, Ort, Peilung bleiben).
"""
import collections, json, math, sys, os, shutil

G, K = "#00862f", "#111"
HW, NW = 3.6, 1.6
LANE = 24; T60 = math.tan(math.radians(60)); DX = LANE / T60; R = 7.0
# Doppelter Spurwechsel (V4e 22.11.2026, REGELN 2.1/HT5): Abstand der zwei Diagonalen längs. Mit 12 px lag der Anfang der
# zweiten Weiche (gezeichnet je ~10 px Ausrundung) 8 px VOR dem Ende der ersten – Reihenfolge am gemeinsamen Gleis
# vertauscht (Bevaix: OSM erst 1→2, dann 2→1; im Plan zweigte 2→1 vor der Einmündung 1→2 ab). 28 px = 8 px Gerade dazwischen.
SW_GAP = 28
Y0 = 110; XL = 330; ANL = 70; LOOP = 200; PER = 110

def rund(pts, r=R):
    pts = [p for i, p in enumerate(pts) if i == 0 or math.dist(p, pts[i - 1]) > 0.05]
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1):
        (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[i + 1]
        l1, l2 = math.dist(pts[i - 1], pts[i]), math.dist(pts[i], pts[i + 1])
        rr = min(r, l1 / 2, l2 / 2)
        p_ = (bx + (ax - bx) * rr / l1, by + (ay - by) * rr / l1); q_ = (bx + (cx - bx) * rr / l2, by + (cy - by) * rr / l2)
        d += f"L{p_[0]:.1f},{p_[1]:.1f}Q{bx:.1f},{by:.1f} {q_[0]:.1f},{q_[1]:.1f}"
    return d + f"L{pts[-1][0]:.1f},{pts[-1][1]:.1f}"

def normalisiere(V):
    """Alte Beschreibung (typ halt/halt2/kreuzung/ueberholung, 16.10. Mittag) in Reinform + Zusätze umsetzen."""
    if "strecke" in V: return V
    V = dict(V); t = V.pop("typ")
    V["strecke"] = "einspur" if t in ("halt", "kreuzung") else "doppelspur"
    V["form"] = {"halt": "halt", "halt2": "halt", "kreuzung": "kreuzung", "ueberholung": "ueberholung"}[t]
    if t == "kreuzung" and V.pop("kreuzungsgleis", "oben") == "unten": V["spiegeln"] = True
    z = [dict(a, art="anschluss") for a in V.pop("anschluesse", [])] + [dict(a, art="abzweig") for a in V.pop("abzweige", [])]
    z += [{"art": "spurwechsel", "ende": e, "anzahl": 2} for e in V.pop("spurwechsel", [])]
    V["zusaetze"] = z
    return V

def zeichne(V, osm=None, title="Bahnhof", mit_text=True):
    V = normalisiere(V)
    st, form = V["strecke"], V.get("form", "halt")
    ueb = V.get("ueberholgleise", "beide")
    zs = V.get("zusaetze", [])
    if V.get("spiegeln"):       # Seitenangaben gelten wie gezeichnet: vor dem kanonischen Zeichnen umkehren
        zs = [dict(a, seite={"oben": "unten", "unten": "oben"}[a["seite"]]) if "seite" in a else a for a in zs]
    # Ebenen (kanonisch): Hauptgleise, Kreuzungs-/Überholgleise
    if st == "einspur":
        haupt = [1] if form == "kreuzung" else [0]
        nebenl = [0] if form == "kreuzung" else []
    else:
        if form == "ueberholung":
            top = ueb in ("beide", "oben"); bot = ueb in ("beide", "unten")
            haupt = [1, 2] if top else [0, 1]; nebenl = ([0] if top else []) + ([haupt[1] + 1] if bot else [])
        else:
            haupt = [0, 1]; nebenl = []
    nlanes = max(haupt + nebenl) + 1
    ys = [Y0 + i * LANE for i in range(nlanes)]
    ext_l = 120 if any(a.get("ende") == "links" and (a["art"] in ("abzweig", "doppelspurbeginn") or a.get("lage") == "aussen" or a["art"] == "spurwechsel") for a in zs) else 0
    ext_r = 120 if any(a.get("ende", "rechts") == "rechts" and (a["art"] in ("abzweig", "doppelspurbeginn") or a.get("lage") == "aussen" or a["art"] == "spurwechsel") for a in zs) else 0
    SL = XL + ANL + ext_l; SR = SL + 2 * DX + LOOP; M = (SL + SR) / 2; XH = SR + ANL + ext_r
    PL, PR = XL - 55, XH + 12
    x0p, x1p = M - PER / 2, M + PER / 2
    lines, dots, arrows, ends, side_ports = [], [], [], {-1: [], 1: []}, []
    pax_of = {}
    for i in haupt:
        lines.append(([(PL, ys[i]), (PR, ys[i])], True, i)); ends[-1].append(ys[i]); ends[1].append(ys[i])
    for i in nebenl:
        h = haupt[0] if i < haupt[0] else haupt[-1]
        st_ = V.get("stumpf")          # Grandson 20.10.: Gleis 1 ist ein Stumpengleis am Hausperron ("rechts" = Prellbock rechts)
        if st_ == "rechts":
            lines.append(([(SL, ys[h]), (SL + DX * abs(i - h), ys[i]), (x1p + 16, ys[i])], True, i)); dots.append((x1p + 16, ys[i]))
        elif st_ == "links":
            lines.append(([(x0p - 16, ys[i]), (SR - DX * abs(i - h), ys[i]), (SR, ys[h])], True, i)); dots.append((x0p - 16, ys[i]))
        else:
            lines.append(([(SL, ys[h]), (SL + DX * abs(i - h), ys[i]), (SR - DX * abs(i - h), ys[i]), (SR, ys[h])], True, i))
    # Zusätze
    for a in zs:
        art = a["art"]; rechts = a.get("ende", "rechts") == "rechts"; unten = a.get("seite", "unten") == "unten"
        if art == "spurwechsel" and len(haupt) >= 2:
            ya, yb = ys[haupt[0]], ys[haupt[1]]
            n_ = int(a.get("anzahl", 1)); steig = a.get("richtung", "steigend") == "steigend"
            x0 = (SR + 34) if rechts else (SL - 34 - 2 * DX - (SW_GAP if n_ >= 2 else 12))   # einfacher Spurwechsel links wie bisher
            if n_ >= 2 and not steig:      # doppelt, zuerst fallend (Tüscherz 25.10.: OSM erst 1→2, dann 2→1; R3 Reihenfolge)
                lines.append(([(x0, ya), (x0 + DX, yb)], False, None)); lines.append(([(x0 + DX + SW_GAP, yb), (x0 + 2 * DX + SW_GAP, ya)], False, None))
            elif n_ >= 2:
                lines.append(([(x0, yb), (x0 + DX, ya)], False, None)); lines.append(([(x0 + DX + SW_GAP, ya), (x0 + 2 * DX + SW_GAP, yb)], False, None))
            else:
                lines.append(([(x0, yb if steig else ya), (x0 + DX, ya if steig else yb)], False, None))
            # Spurwechsel schwarz (Riedbach/Rosshäusern 20.10.: "Spurwechsel alle schwarz"), wie im Regionalplan
        elif art == "doppelspurbeginn" and a.get("aus") == "kreuzungsgleis" and nebenl:
            # Kreuzungsgleis läuft als zweites Streckengleis weiter (Gümmenen: Doppelspur bis in den Bahnhof, 17.10.)
            for li_, (pts_, px_, i_) in enumerate(lines):
                if i_ == nebenl[0]:
                    yk = ys[i_]
                    lines[li_] = ((pts_[:2] + [(PR, yk)]) if rechts else ([(PL, yk)] + pts_[2:]), px_, i_)
                    ends[1 if rechts else -1].append(yk)
        elif art == "doppelspurbeginn":
            h = haupt[0] if not unten else haupt[-1]
            yh = ys[h]; yn = yh + (LANE if unten else -LANE)
            # V4e 22.11.2026 (Ligerz, seite «oben»): früher ys.insert(0, …) – danach zeigte ys[h] auf das neue Gleis und die
            # Schräge fehlte. Neue Ebene hinten anhängen, Indizes der Hauptgleise bleiben gültig.
            if yn not in ys: ys.append(yn)
            xs = (XH - 60) if rechts else (XL + 60)
            pe = PR if rechts else PL
            if rechts: lines.append(([(xs, yh), (xs + DX, yn), (pe, yn)], True, None))
            else: lines.append(([(pe, yn), (xs - DX, yn), (xs, yh)], True, None))
            ends[1 if rechts else -1].append(yn)
        elif art == "anschluss":
            alle = sorted(set(ys))
            gi_y = max(ys[i] for i in haupt + nebenl) if unten else min(ys[i] for i in haupt + nebenl)
            sg = 1 if unten else -1
            innen = a.get("lage", "aussen") == "innen"; stp = max(1, min(int(a.get("stumpen", 1)), 3))
            on_neben = any(ys[i] == gi_y for i in nebenl)
            if innen: xs = ((SR - 20) if rechts else (SL + 20)) - (1 if rechts else -1) * (28 if a.get("gleich_lang") else 0)   # nicht in der Kreuzungsweiche
            elif on_neben: xs = (SR - DX - 30) if rechts else (SL + DX + 30)
            else: xs = (SR + 30) if rechts else (SL - 30)
            dirx = (-1 if innen else 1) * (1 if rechts else -1)
            # V4e (22.11.2026, Riedbach, Daniel): "gegen": der Anschluss zweigt innen ab, läuft aber nach aussen (von der
            # Bahnhofseite her direkt befahrbar); der T-Stumpen zeigt dann zum Bahnhof (Zurücksetzen)
            gegen = innen and a.get("gegen", False)
            if gegen: dirx = -dirx
            if not innen and not on_neben and any(z_["art"] == "spurwechsel" and z_.get("ende", "rechts") == a.get("ende", "rechts") for z_ in zs):
                xs += (1 if rechts else -1) * (2 * DX + 75)      # nicht im Spurwechsel abzweigen (Grandson 20.10.: wirkte wie Kreuzung)
            for j in range(stp):
                y_ = gi_y + sg * LANE * (1 + 0.55 * j); x_s = xs + dirx * 40 * j
                y_from = gi_y if j == 0 else gi_y + sg * LANE
                x_d = x_s + dirx * abs(y_ - y_from) / T60
                L_ = 90 - 20 * j
                if innen and not gegen:
                    rand = (x1p + 12) if rechts else (x0p - 12)
                    L_ = max(36 - 8 * j, abs(rand - x_d) - 22 * j)
                x_e = x_d + dirx * L_
                if innen and a.get("gleich_lang"):      # Les Hauts-Geneveys 20.10.: "beide Gleise ca. gleich lang", "länger"
                    x_e = ((x0p + 30) if rechts else (x1p - 30)) + dirx * float(a.get("verlaengern", 0))   # bis gegen das andere Perronende
                lines.append(([(x_s, y_from), (x_d, y_), (x_e, y_)], False, None))
                if a.get("t_form") and j == 0:
                    # umgekehrtes T (Riedbach 20.10.): am Fuss der Weichenverbindung zweites Stumpengleis in Gegenrichtung,
                    # erreichbar mit Zurücksetzen
                    x_b = x_d - dirx * float(a.get("t_laenge", 60))
                    lines.append(([(x_b, y_), (x_d + dirx * 8, y_)], False, None)); dots.append((x_b, y_))
                if a.get("pfeil") and j == 0: arrows.append((x_e, y_, 0 if dirx > 0 else math.pi))
                else: dots.append((x_e, y_))
        elif art == "schutzstumpen":
            # Kurzer gerader Stumpen in Verlängerung des Überhol-/Kreuzungsgleises über seine Weiche hinaus (Schutzweiche,
            # D. Eckenstein 20.10.: "Ministummel horizontal", Le Landeron/Gorgier/Grandson); "prellbock": Punkt am Ende
            for i in (nebenl[:1] if a.get("gleis", "neben") == "neben" else []):
                h = haupt[0] if i < haupt[0] else haupt[-1]
                xk = (SL + DX * abs(i - h)) if not rechts else (SR - DX * abs(i - h))
                if (V.get("stumpf") == "links" and not rechts) or (V.get("stumpf") == "rechts" and rechts): continue
                x_e = xk + (1 if rechts else -1) * float(a.get("laenge", 26))
                # Beginn am Anfang der Ausrundung (V4c 21.11.: an der Ecke selbst berührte der Stumpen das ausgerundete Gleis
                # nicht – Weiche im Plan nicht erkannt, HT1 St-Blaise Lac); gezeichnet unter dem Gleis, sieht gleich aus
                lines.append(([(xk - (1 if rechts else -1) * R, ys[i]), (x_e, ys[i])], False, None))
                if a.get("prellbock", True): dots.append((x_e, ys[i]))
        elif art == "linie":
            # Ergänzung von Hand in Pixeln (Gorgier 20.10.: Weichenverbindung und Stumpen der Anschlussgleise nach OSM);
            # Koordinaten wie gezeichnet (bei "spiegeln" kanonisch), Ausrundung an Weichen wie bei allen Linien
            lines.append(([tuple(map(float, p)) for p in a["pts"]], bool(a.get("pax")), None))
            if a.get("punkt_ende"): dots.append(tuple(map(float, a["pts"][-1])))
            if a.get("punkt_anfang"): dots.append(tuple(map(float, a["pts"][0])))
        elif art == "abzweig":
            oben = a.get("seite", "oben") == "oben"
            gi = haupt[0] if oben else haupt[-1]; yt = ys[gi]; sg = -1 if oben else 1
            xs = (SR + 40) if rechts else (SL - 40); dirx = 1 if rechts else -1
            ye = yt + sg * 2 * LANE; xe = xs + dirx * 2 * LANE / T60
            lines.append(([(xs, yt), (xe, ye)], True, None))
            side_ports.append(dict(x=xe, y=ye, dx=dirx, dy=sg))
    # Perrons (kanonisch: oben = über dem obersten Gleis der Anlage)
    gy = sorted({ys[i] for i in haupt + nebenl})
    rects = []
    teile = set(V.get("perrons", "keine").replace("aussen", "oben+unten").replace("mittel", "zwischen").split("+"))
    sp = bool(V.get("spiegeln"))
    if sp: teile = {{"oben": "unten", "unten": "oben"}.get(t, t) for t in teile}      # Perronangaben gelten wie gezeichnet
    if "oben" in teile: rects.append((x0p, gy[0] - 11))
    if "unten" in teile: rects.append((x0p, gy[-1] + 11))
    if "zwischen" in teile:
        if len(gy) == 4: rects += [(x0p, gy[0] + 12), (x0p, gy[2] + 12)]
        elif len(gy) >= 2: rects.append((x0p, gy[0] + 12))
    if "zwischen_unten" in teile and len(gy) >= 3: rects.append((x0p, gy[-2] + 12))   # Mittelperron zwischen den unteren Gleisen (Grandson 2/3)
    # Spiegeln (oben/unten)
    if sp:
        yc = (min(gy) + max(gy)) / 2; fy = lambda y: 2 * yc - y
        lines = [([(x, fy(y)) for x, y in pts], px, i) for pts, px, i in lines]
        dots = [(x, fy(y)) for x, y in dots]; arrows = [(x, fy(y), a_) for x, y, a_ in arrows]
        rects = [(x, fy(y)) for x, y in rects]; ends = {k: [fy(y) for y in v] for k, v in ends.items()}
        for s_ in side_ports: s_["y"] = fy(s_["y"]); s_["dy"] = -s_["dy"]
        gy = sorted(fy(y) for y in gy)
    # Gleise in Zeichenreihenfolge: Nummern und Personengleis
    gl = V.get("gleise") or []; pax = V.get("pax") or []
    tr_y = sorted({pts[1][1] if len(pts) > 2 else pts[0][1] for pts, px, i in lines if i is not None})
    nums = []
    def zeig(nr):
        try: return nr is not None and 0 < int(nr) < 30
        except ValueError: return nr is not None and len(nr) <= 3
    # Gleisnummern (Regeln D. Eckenstein 20.10.): nur Gleise mit Perron; Halt mit einem Gleis ohne Nummer;
    # Perrongleis ohne Nummer in allen Quellen -> Fragezeichen (von Hand eintragen)
    _mit_perron = lambda y: any(abs(ry - y) <= 13 for _, ry in rects)
    for k, y in enumerate(tr_y):
        if len(tr_y) == 1 or not _mit_perron(y): continue
        nums.append((M, y, gl[k] if k < len(gl) and zeig(gl[k]) else "?"))
    lines = [(pts, (pax[tr_y.index(pts[1][1] if len(pts) > 2 else pts[0][1])] if i is not None and pax and
                    tr_y.index(pts[1][1] if len(pts) > 2 else pts[0][1]) < len(pax) else px), i) for pts, px, i in lines]
    # Abgänge
    befund, ports = [], []
    for dx in (-1, 1):
        t = sorted(set(ends[dx]))
        o = sorted([p for p in (osm or {}).get("ports", []) if p["kind"] == "edge" and p["dx"] == dx], key=lambda p: p["y"]) if osm else []
        if osm and len(o) != len(t):
            befund.append(f"{'links' if dx < 0 else 'rechts'}: {len(t)} Abgänge in der Vorlage, {len(o)} im allgemeinen Lauf")
        for j, y in enumerate(t):
            p = dict(o[min(j, len(o) - 1)]) if o else dict(kind="edge", ref="000", town="Ort", bearing=90 if dx > 0 else 270)
            p.update(kind="edge", x=round(PL if dx < 0 else PR, 1), y=float(y), dx=dx, dy=0, pax=True)
            _ort = (V.get("orte") or {}).get("links" if dx < 0 else "rechts")     # Ortskenntnis: Zielort je Seite
            if _ort: p["town"] = _ort
            # V4e (22.11.2026, Zihlbrücke): der allgemeine Lauf kennt nur einen Abgang, die Vorlage zeichnet zwei (Doppel-
            # spurbeginn am Rand) -> beide bekamen denselben OSM-Knoten (HT5). OSM-Knoten je Abgang von oben nach unten.
            _kn = (V.get("abgaenge_knoten") or {}).get("links" if dx < 0 else "rechts") or []
            if j < len(_kn) and _kn[j]:
                if p.get("knoten") != _kn[j]: p.pop("aus_ll", None)
                p["knoten"] = int(_kn[j])
            ports.append(p)
    os_side = [p for p in (osm or {}).get("ports", []) if p["kind"] == "side"] if osm else []
    if osm and len(os_side) != len(side_ports): befund.append(f"{len(side_ports)} seitliche Abzweige in der Vorlage, {len(os_side)} im allgemeinen Lauf")
    for j, s_ in enumerate(side_ports):
        p = dict(os_side[j]) if j < len(os_side) else dict(kind="side", ref="000", town="Ort", bearing=45)
        p.update(kind="side", x=round(s_["x"], 1), y=round(s_["y"], 1), dx=s_["dx"], dy=s_["dy"]); ports.append(p)
    # Weichen ausrunden (Regelprüfung G2, D. Eckenstein 19.10.: "Weichenrundungen"): eine Schräge, die auf einem Gleis
    # beginnt oder endet, bekommt dort ein kurzes gerades Stück auf dem Gleis, damit rund() den Bogen zeichnen kann
    _hz = [(min(p[0][0], p[-1][0]), max(p[0][0], p[-1][0]), p[0][1]) for pts, _, _ in lines for p in [pts] if len(pts) >= 2]
    _hz = [(min(a[0], b[0]), max(a[0], b[0]), a[1]) for pts, _, _ in lines for a, b in zip(pts, pts[1:]) if abs(a[1] - b[1]) < 0.01]
    def _auf_gleis(p): return any(abs(p[1] - y) < 0.6 and x0 - 0.6 <= p[0] <= x1 + 0.6 for x0, x1, y in _hz)
    _neu = []
    for pts, px, i in lines:
        pts = list(pts)
        if len(pts) >= 2 and abs(pts[1][1] - pts[0][1]) > 0.5 and _auf_gleis(pts[0]):
            sx = 1 if pts[1][0] >= pts[0][0] else -1; pts.insert(0, (pts[0][0] - sx * (R + 3), pts[0][1]))
        if len(pts) >= 2 and abs(pts[-1][1] - pts[-2][1]) > 0.5 and _auf_gleis(pts[-1]):
            sx = 1 if pts[-1][0] >= pts[-2][0] else -1; pts.append((pts[-1][0] + sx * (R + 3), pts[-1][1]))
        _neu.append((pts, px, i))
    lines = _neu
    # Masse und SVG
    allys = [y for pts, _, _ in lines for _, y in pts] + [y for _, y in rects]
    ymax, ymin = max(allys) + 4, min(allys) - 4
    W = PR + 330; title_y = ymax + 52; H = title_y + 45
    body = ['<g fill="none" stroke-linecap="round" stroke-linejoin="round">']
    for px in (False, True):
        ds = " ".join(rund(pts) for pts, p, _ in lines if bool(p) == px)
        if ds: body.append(f'<path d="{ds}" stroke="{G if px else K}" stroke-width="{HW if px else NW}"/>')
    body.append("</g>")
    for x, y in rects: body.append(f'<rect x="{x:.1f}" y="{y - 4:.1f}" width="{PER:.1f}" height="8" rx="1.5" fill="{G}"/>')
    for x, y, t in nums:
        if t == "?":
            body.append(f'<rect x="{x - 13:.1f}" y="{y - 8:.1f}" width="26" height="16" fill="#fff" stroke="none"/>'
                        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8.5" fill="#fff" stroke="#c05800" stroke-width="1.6"/>'
                        f'<text x="{x:.1f}" y="{y + 5.5:.1f}" font-size="15" font-weight="700" text-anchor="middle" fill="#c05800">?</text>')
            continue
        body.append(f'<rect x="{x - 13:.1f}" y="{y - 8:.1f}" width="26" height="16" fill="#fff" stroke="none"/>'
                    f'<text x="{x:.1f}" y="{y + 6.5:.1f}" font-size="19" text-anchor="middle" fill="{G}">{t}</text>')
    for x, y in dots: body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{K}"/>')
    for x, y, ang in arrows:
        c, s = math.cos(ang), math.sin(ang)
        pts = [(x + 9 * c, y + 9 * s), (x - 4 * s, y + 4 * c), (x + 4 * s, y - 4 * c)]
        body.append('<path d="M' + "L".join(f"{a:.1f},{b:.1f}" for a, b in pts) + f'Z" fill="{K}"/>')
    labels = []
    if mit_text:
        for dx in (-1, 1):
            grp = {}
            for p in ports:
                if p["dx"] == dx and p["kind"] == "edge": grp.setdefault((p["ref"], p.get("town")), []).append(p["y"])
            for (ref, town), yy in grp.items():
                ym = sum(yy) / len(yy); x = (PL - 12) if dx < 0 else (PR + 12); anc = "end" if dx < 0 else "start"
                labels.append(f'<text x="{x:.1f}" y="{ym - 13:.1f}" font-size="22" text-anchor="{anc}" fill="{G}">Linie {ref}</text>')
                labels.append(f'<text x="{x:.1f}" y="{ym + 13:.1f}" font-size="22" text-anchor="{anc}" fill="{G}">' + (f"← {town}" if dx < 0 else f"{town} →") + "</text>")
        for p in ports:
            if p["kind"] != "side": continue
            x = p["x"]; y = p["y"] + (-22 if p["dy"] < 0 else 30)
            ar = {(1, -1): "↗", (1, 1): "↘", (-1, -1): "↖", (-1, 1): "↙"}[(p["dx"], p["dy"])]
            labels.append(f'<text x="{x:.1f}" y="{y - 22:.1f}" font-size="22" text-anchor="middle" fill="{G}">Linie {p["ref"]}</text>'
                          f'<text x="{x:.1f}" y="{y:.1f}" font-size="22" text-anchor="middle" fill="{G}">{p.get("town", "")} {ar}</text>')
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
            f'font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif">\n<rect width="100%" height="100%" fill="#fff"/>\n')
    full = head + "\n".join(body + labels) + f'\n<text x="{M:.1f}" y="{title_y:.1f}" font-size="38" font-weight="700" text-anchor="middle" fill="{G}">{title}</text>\n</svg>\n'
    top = min(0, ymin - 40)
    bare = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {top:.0f} {W:.0f} {H - top:.0f}" width="{W:.0f}" height="{H - top:.0f}" '
            f'font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif">\n<rect y="{top:.0f}" width="100%" height="100%" fill="#fff"/>\n'
            + "\n".join(body) + "\n</svg>\n")
    P = dict(ports=ports, W=W, H=H, title=title, x_lo=XL, x_hi=XH, y_lo=70, y_hi=ymax + 16, ways=(osm or {}).get("ways", []),
             vorlage=f'{st} {form}')
    return full, bare, P, befund, "\n".join(body), (W, ymin, ymax, M, PL, PR)

def _monoton(paare):
    """Stützpunkte (a, b): gleiche a gemittelt, dann längste Teilfolge mit b steigend oder fallend (die längere gewinnt)"""
    import collections
    g = collections.defaultdict(list)
    for a, b in paare: g[round(a, 1)].append(b)
    P = sorted((a, sum(v) / len(v)) for a, v in g.items())
    def lis(sg):
        n = len(P); best = [1] * n; prev = [-1] * n
        for i in range(n):
            for j in range(i):
                if sg * (P[i][1] - P[j][1]) > 0.05 and best[j] + 1 > best[i]: best[i] = best[j] + 1; prev[i] = j
        if not n: return []
        i = max(range(n), key=lambda k: best[k]); out = []
        while i >= 0: out.append(P[i]); i = prev[i]
        return out[::-1]
    a, b = lis(1), lis(-1)
    return (a, 1) if len(a) >= len(b) else (b, -1)


def _abbildung(paare):
    """stückweise lineare, monotone Abbildung durch die Stützpunkte; ausserhalb Steigung ±1"""
    S, sg = _monoton(paare)
    if not S: return lambda v: v
    def f(v):
        if v <= S[0][0]: return S[0][1] + sg * (v - S[0][0])
        if v >= S[-1][0]: return S[-1][1] + sg * (v - S[-1][0])
        for (a0, b0), (a1, b1) in zip(S, S[1:]):
            if a0 <= v <= a1: return b0 + (b1 - b0) * (v - a0) / (a1 - a0)
        return v
    return f


def _verbindungen(key, N, weichen, max_ways=5):
    """Ketten von OSM-Ways ausserhalb des Netzmodells, die zwei Weichen des Netzmodells verbinden (ohne weitere Weiche
    dazwischen): [(knotenkette, {way: knotenmenge}, {way: tags})]. Quelle: OSM-Ausschnitt <key>.json im Arbeitsordner."""
    import collections
    if not os.path.exists(f"{key}.json"): return [], {}
    D = json.load(open(f"{key}.json")); D = D["elements"] if isinstance(D, dict) else D
    drin = {g["way"] for g in N["gleise"]} | {g["way"] // 100 for g in N["gleise"]}
    W = {e["id"]: e for e in D if e["type"] == "way" and e["id"] not in drin and e.get("tags", {}).get("railway") == "rail"}
    LL = {}
    for e in W.values():
        for n, g in zip(e.get("nodes", []), e.get("geometry") or []):
            if g: LL.setdefault(n, (g["lat"], g["lon"]))
    nb = collections.defaultdict(list)
    for w, e in W.items():
        for n in e["nodes"]: nb[n].append(w)
    out, gesehen = [], set()
    for s in sorted(weichen):
        stapel = [(s, [s], [])]
        while stapel:
            n, kette, ws = stapel.pop()
            for w in nb[n]:
                if w in ws: continue
                nd = W[w]["nodes"]; i = nd.index(n)
                for rng in (range(i + 1, len(nd)), range(i - 1, -1, -1)):
                    k2 = list(kette)
                    for k in rng:
                        m = nd[k]; k2.append(m)
                        if m in weichen:
                            if m != s and (min(s, m), max(s, m)) not in gesehen:
                                gesehen.add((min(s, m), max(s, m)))
                                wsn = ws + [w]
                                out.append((k2, {x: set(W[x]["nodes"]) for x in wsn}, {x: W[x].get("tags", {}) for x in wsn}))
                            break
                        if m in kette: break
                        if (len(nb[m]) > 1 or k in (0, len(nd) - 1)) and len(ws) + 1 < max_ways:
                            stapel.append((m, k2[:], ws + [w]))
    return out, LL


def _schnitt_bereinigen(N):
    """V4e (22.11.2026, Grandson/Riedbach/Tüscherz, HT5 «künstlicher Schnitt» + HT2): Der allgemeine Lauf führte ein totes
    Nebengleis bis aufs Streckengleis und teilte dieses dort mit einem künstlichen Knoten (negative ID) – OSM hat keine
    Verbindung (Riedbach: Ende 68 m neben dem Gleis). Die Typvorlage zeichnet den Bahnhof neu; im Netzmodell werden die zwei
    Stücke desselben Ways wieder zusammengesetzt und das Nebengleis endet an seinem letzten OSM-Knoten."""
    ends = collections.defaultdict(list)
    for i, g in enumerate(N["gleise"]):
        for e in (0, -1):
            n = g["knoten"][e]
            if n < 0: ends[n].append((i, e))
    weg = set()
    for n, L in ends.items():
        ways = collections.Counter(N["gleise"][i]["way"] for i, _ in L)
        durch = [w for w, c in ways.items() if c == 2]
        if len(L) < 3 or len(durch) != 1: continue
        (i1, e1), (i2, e2) = [(i, e) for i, e in L if N["gleise"][i]["way"] == durch[0]]
        a, b = N["gleise"][i1]["knoten"], N["gleise"][i2]["knoten"]
        a = a if e1 == -1 else a[::-1]; b = b if e2 == 0 else b[::-1]
        N["gleise"][i1]["knoten"] = a[:-1] + b[1:]; weg.add(i2)
        for i, e in L:
            if N["gleise"][i]["way"] == durch[0]: continue
            kn = N["gleise"][i]["knoten"]
            N["gleise"][i]["knoten"] = kn[:-1] if e == -1 else kn[1:]
        N["knoten"].pop(str(n), None); N["knoten"].pop(n, None)
    N["gleise"] = [g for i, g in enumerate(N["gleise"]) if i not in weg]


def _reihenfolge_halten(gleise, KN, alt_x, fest):
    """V4e (22.11.2026, Gorgier Gl. 512): Die Weichen springen an den gezeichneten Abzweig, die übrigen Knoten folgen nur der
    Längsabbildung – ein Knoten kurz hinter einer Weiche landete so VOR ihr (Gl. 512: 2-m-Stück hinter der Spurwechselweiche
    lag im Netzmodell auf der anderen Seite des Abzweigs -> HT5 «fehlt im Plan» ohne Fehler im Plan). Längs jedes Gleises
    bleibt die Reihenfolge der Knoten wie im Lauf: ein freier Knoten wird zwischen die festen Nachbarn (Weichen) geschoben."""
    for _ in range(3):
        for g in gleise:
            L = [n for n in g["knoten"] if n in KN and KN[n].get("x") is not None and alt_x.get(n) is not None]
            if len(L) < 2: continue
            s = 1 if alt_x[L[-1]] >= alt_x[L[0]] else -1
            for i, n in enumerate(L):
                if n in fest: continue
                vor = [KN[m]["x"] for m in L[:i] if m in fest and s * (alt_x[n] - alt_x[m]) > 0]
                nach = [KN[m]["x"] for m in L[i + 1:] if m in fest and s * (alt_x[m] - alt_x[n]) > 0]
                x = KN[n]["x"]
                lo = (max(vor) if s > 0 else None) if vor else None
                hi = (min(nach) if s > 0 else None) if nach else None
                if s < 0:
                    lo = max(nach) if nach else None; hi = min(vor) if vor else None
                if lo is not None and hi is not None and lo > hi: continue
                if lo is not None and x <= lo: x = lo + min(2.0, ((hi - lo) / 2) if hi is not None else 2.0)
                if hi is not None and x >= hi: x = hi - min(2.0, ((hi - lo) / 2) if lo is not None else 2.0)
                KN[n]["x"] = round(float(x), 1)


def netz_mitschreiben(key, full, P):
    """V4c (21.11.2026, REGELN 0.1 / Kopf «HT»): die Typvorlage zeichnet den Bahnhof neu, das Netzmodell <key>_netz.json
    (spurplan_schema, allgemeiner Lauf) trug noch die alte Lage – HT/G0/OSM-Abgleich fanden die Weichen nicht (Paar HT1+HT2,
    Gümmenen, Sugiez …). Hier wird das Netzmodell auf den GEZEICHNETEN Plan gelegt: OSM-Knoten und -Weichen bleiben, nur ihre
    Planlage folgt der Vorlage. Abbildung quer über Abgänge und Gleisnummern, längs über Abgänge und die zugeordneten
    Weichen (OSM-Weiche ↔ Abzweig der Vorlage, eins zu eins, Reihenfolge längs bleibt); Weichen liegen genau am Abzweig.
    Das Netzmodell des allgemeinen Laufs bleibt als <key>_netz_lauf.json."""
    import re
    try:
        import osm_abgleich as OA
    except ImportError:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import osm_abgleich as OA
    import numpy as np
    fn = f"{key}_netz.json"; fl = f"{key}_netz_lauf.json"
    if not os.path.exists(fn): return None
    N = json.load(open(fn))
    if N.get("vorlage"):
        if not os.path.exists(fl): return "Netzmodell schon auf der Vorlage, Lauf-Fassung fehlt"
        N = json.load(open(fl))
    else:
        shutil.copy(fn, fl)
    _schnitt_bereinigen(N)
    KN = {int(k): v for k, v in N["knoten"].items()}
    abg = {a.get("knoten"): a for a in N.get("abgaenge", []) if a.get("knoten") is not None}
    # quer: Abgänge und Gleisnummern
    nums = [(float(m.group(1)), float(m.group(2)) - 6.5, m.group(3)) for m in
            re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)" font-size="19" text-anchor="middle"[^>]*>([^<]+)</text>', full)]
    py_ = [(abg[p["knoten"]]["y"], p["y"]) for p in P["ports"] if p.get("knoten") in abg and p["kind"] == "edge"]
    for _, y, t in nums:
        py_ += [(g["y"], y) for g in N["gleise"] if g.get("y") is not None and g.get("pax") and str(g.get("gleis")) == t]
    fy = _abbildung(py_)
    # längs: Abgänge, dann Weichen
    px_ = [(abg[p["knoten"]]["x"], p["x"]) for p in P["ports"] if p.get("knoten") in abg and p["kind"] == "edge"]
    # Perronmitte als Stützpunkt (Serrières 21.11.: nur über die Abgänge lag die OSM-Weiche 70 px neben dem Abzweig)
    pv = [(float(m.group(1)) + float(m.group(3)) / 2) for m in
          re.finditer(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="8" rx="1.5"', full)]
    pn = [(p_["x0"] + p_["x1"]) / 2 for p_ in N.get("perrons", [])]
    if pv and pn: px_.append((sum(pn) / len(pn), sum(pv) / len(pv)))
    fx0 = _abbildung(px_)
    gleise, _, _, luecken = OA.plan_lesen(full)
    PK = [k for k in OA.plan_knoten(gleise, luecken) if k[4] >= 3] if gleise else []
    lagen = {}
    for g in N["gleise"]:
        if g.get("y") is None: continue
        for n in g["knoten"]: lagen.setdefault(n, set()).add(g["y"])
    sw = [n for n, v in KN.items() if v.get("typ") in ("switch", "railway_crossing") and v.get("y") is not None]
    for n in sw: lagen.setdefault(n, set()).add(KN[n]["y"])
    # Zuordnung reihenfolgetreu (wie Sequenzabgleich): OSM-Weichen und Abzweige je längs sortiert, Paar nur bei passender
    # Ebene; Auslassen kostet SKIP. Serrières 21.11.: die reine Kostenminimierung tauschte Anschluss- und Spurwechselweiche.
    zu = {}
    # V4e (22.11.2026, Gorgier Anschlussring, Tüscherz): Weichen an Zusätzen der Vorlage ({"art": …, "weichen": [[osm, x, y]]})
    # stehen fest – das Netzmodell des Laufs legt alle Anschlussweichen auf eine Ebene, die Vorlage zeichnet sie auf zwei;
    # über die Ebene allein fand der Abgleich keinen Partner (HT2 am gezeichneten Abzweig)
    try:
        _V = json.load(open(f"{key}_override.json")).get("vorlage") or {}
    except Exception:
        _V = {}
    for z_ in _V.get("zusaetze", []):
        for w_ in z_.get("weichen", []):
            if int(w_[0]) in KN: zu[int(w_[0])] = (float(w_[1]), float(w_[2]))
    sw_alle = len(sw); sw = [n for n in sw if n not in zu]
    SKIP = 150.0
    def kost(n, k):
        dy = min(abs(fy(y) - k[1]) for y in lagen[n])
        return abs(fx0(KN[n]["x"]) - k[0]) + 4 * dy if dy < 6 else None
    # V4e (22.11.2026, Tüscherz): Reihenfolge nur JE GLEIS (Ebene der Weiche im Netzmodell ↔ Ebene des Abzweigs im Plan).
    # Über alle Gleise zusammen sortiert verlangte der Abgleich, dass auch Weichen auf verschiedenen Gleisen in gleicher
    # Reihenfolge liegen (OSM: Spurwechsel oben 615 m vor Anschluss unten 668 m; Vorlage umgekehrt) -> eine Weiche blieb
    # ohne Partner (HT1 + HT2), obwohl jedes Gleis für sich stimmt.
    gruppen_ = []
    if sw and PK:
        ebenen = sorted({round(k[1], 1) for k in PK})
        def ebene(n):
            y = fy(KN[n]["y"]); e = min(ebenen, key=lambda q: abs(q - y))
            return e if abs(e - y) < 6 else None
        for e in ebenen:
            gruppen_.append(([n for n in sw if ebene(n) == e], [k for k in PK if round(k[1], 1) == e]))
        rest = [n for n in sw if ebene(n) is None]
        if rest: gruppen_.append((rest, [k for k in PK]))
    for sw_g, PK_g in gruppen_:
        if not sw_g or not PK_g: continue
        S_ = sorted(sw_g, key=lambda n: (fx0(KN[n]["x"]), KN[n]["y"])); K_ = sorted(PK_g, key=lambda k: (k[0], k[1]))
        I, J = len(S_), len(K_)
        D = [[0.0] * (J + 1) for _ in range(I + 1)]; Z = [[None] * (J + 1) for _ in range(I + 1)]
        for i in range(I + 1):
            for j in range(J + 1):
                if i == 0 and j == 0: continue
                best = []
                if i: best.append((D[i - 1][j] + SKIP, "s"))
                if j: best.append((D[i][j - 1] + SKIP, "k"))
                if i and j:
                    c = kost(S_[i - 1], K_[j - 1])
                    if c is not None and c < 2 * SKIP: best.append((D[i - 1][j - 1] + c, "p"))
                D[i][j], Z[i][j] = min(best)
        i, j = I, J
        while i or j:
            z = Z[i][j]
            if z == "p":
                if K_[j - 1] not in zu.values() and (K_[j - 1][0], K_[j - 1][1]) not in zu.values(): zu[S_[i - 1]] = K_[j - 1]
                i -= 1; j -= 1
            elif z == "s": i -= 1
            else: j -= 1
    # Längsabbildung der übrigen Knoten nur aus der monotonen Teilfolge (_abbildung); die Weichen selbst bleiben an ihrem
    # Abzweig, auch wenn sie gleisübergreifend anders liegen als in OSM (V4e: Reihenfolge gilt je Gleis, s. oben)
    fx = _abbildung(px_ + [(KN[n]["x"], k[0]) for n, k in zu.items()])
    r1 = lambda v: round(float(v), 1)
    alt_x = {n: v.get("x") for n, v in KN.items()}
    for n, v in KN.items():
        if n in zu: v["x"], v["y"] = r1(zu[n][0]), r1(zu[n][1])
        else:
            v["x"] = r1(fx(v["x"])) if v.get("x") is not None else None
            v["y"] = r1(fy(v["y"])) if v.get("y") is not None else None
    for g in N["gleise"]:
        if g.get("y") is not None: g["y"] = r1(fy(g["y"]))
    _reihenfolge_halten(N["gleise"], KN, alt_x, set(zu))
    # Abgänge mit festgelegtem OSM-Knoten (abgaenge_knoten): das Gleisstück vom Abgang bis zur ersten Weiche liegt auf der
    # Höhe des Abgangs (Zihlbrücke: der Lauf zeichnete das andere Gleis gerade, eine Höhenabbildung passt nicht für beide)
    _fest_kn = {int(k_) for v_ in (_V.get("abgaenge_knoten") or {}).values() for k_ in v_ if k_}
    for p_ in P["ports"]:
        if p_.get("knoten") not in _fest_kn or p_["kind"] != "edge": continue
        for g in N["gleise"]:
            kn = g["knoten"]
            if p_["knoten"] not in (kn[0], kn[-1]): continue
            for n in kn:
                if n in zu or n not in KN: continue
                KN[n]["y"] = r1(p_["y"])
            if g.get("y") is not None: g["y"] = r1(p_["y"])
    # OSM-Verbindungen zwischen zwei Weichen des Netzmodells, die der allgemeine Lauf nicht gezeichnet hat (St-Blaise CFF:
    # Spurwechsel 49773692 fehlte im Netzmodell -> HT5 «Fahrweg im Plan, nicht in OSM», obwohl OSM ihn hat). Die Vorlage
    # zeichnet solche Spurwechsel; das Netzmodell bekommt die OSM-Ways (Zwischenknoten auf der Geraden zwischen den Weichen).
    N["gleise"] = [g for g in N["gleise"] if not g.get("vorlage_verbindung")]
    zusatz, LL = _verbindungen(key, N, {n for n, v in KN.items() if v.get("typ") == "switch"})
    for kette, ways, tags in zusatz:
        a, b = KN[kette[0]], KN[kette[-1]]
        for i, n in enumerate(kette[1:-1], 1):
            if n in KN: continue
            t = i / (len(kette) - 1)
            KN[n] = dict(lat=(LL.get(n) or (None, None))[0], lon=(LL.get(n) or (None, None))[1], x=r1(a["x"] + t * (b["x"] - a["x"])), y=r1(a["y"] + t * (b["y"] - a["y"])), typ=None)
        for w in ways:
            kn = [n for n in kette if n in ways[w]]
            N["gleise"].append(dict(id=f"v{w}", way=w, knoten=kn, ebene=None, y=None, pax=not tags[w].get("service"),
                                    service=tags[w].get("service"), usage=tags[w].get("usage"), ref=tags[w].get("ref"),
                                    gleis=tags[w].get("railway:track_ref"), spur=tags[w].get("gauge"), stillgelegt=False,
                                    vorlage_verbindung=True))
    N["knoten"] = {str(n): v for n, v in KN.items()}
    neu_abg = []
    for p in P["ports"]:
        a = dict(abg.get(p.get("knoten"), {k_: v_ for k_, v_ in p.items()}))
        a.update(kind=p["kind"], x=p["x"], y=p["y"], dx=p["dx"], dy=p["dy"]); neu_abg.append(a)
    N["abgaenge"] = neu_abg
    N["perrons"] = [dict(x0=r1(m.group(1)), y=r1(float(m.group(2)) + 4), x1=r1(float(m.group(1)) + float(m.group(3))))
                    for m in re.finditer(r'<rect x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="8" rx="1.5"', full)]
    N["nummern"] = [dict(text=t, x=r1(x), y=r1(y)) for x, y, t in nums]
    N["W"], N["H"] = r1(P["W"]), r1(P["H"])
    N["vorlage"] = dict(weichen=sw_alle, zugeordnet=len(zu), abzweige_plan=len(PK), verbindungen=len(zusatz),
                        gezeichnet=sorted(int(n) for n in zu))      # Weichen mit Abzweig in der Vorlage (hauptgleis: Abgang an Weiche)
    json.dump(N, open(fn, "w"), ensure_ascii=False, indent=0)
    return None if len(zu) == sw_alle else f"Netzmodell: {len(zu)} von {sw_alle} OSM-Weichen einem Abzweig der Vorlage zugeordnet"


def weichen_festlegen(key):
    """V4e (22.11.2026, Chambrelien): Pläne mit Hand-Linien («zeichnen» im Override) – das Netzmodell kennt die Lage der dort
    gezeichneten Weichen nicht (HT1/HT2 als Messartefakt). «zeichnen.weichen»: [[osm, x, y]] legt sie an den gezeichneten
    Abzweig; Ways in «zeichnen.weg» behalten sonst ihre Lage aus dem Lauf."""
    ov = json.load(open(f"{key}_override.json")); W_ = (ov.get("zeichnen") or {}).get("weichen") or []
    fn = f"{key}_netz.json"
    if not ov.get("zeichnen") or not os.path.exists(fn): return None
    N = json.load(open(fn)); n_ = 0
    for o, x, y in W_:
        v = N["knoten"].get(str(int(o)))
        if v is not None: v["x"], v["y"] = round(float(x), 1), round(float(y), 1); n_ += 1
    # OSM-Verbindungen zwischen zwei Weichen des Netzmodells, die der Lauf nicht zeichnet, weil die Hand-Linie sie ersetzt
    # (Cornaux: Spurwechsel 49776111 «weglassen» + von Hand) – sonst fehlt der Fahrweg auf der OSM-Seite (HT5 «im Plan, nicht in OSM»)
    KN = {int(k): v for k, v in N["knoten"].items()}
    N["gleise"] = [g for g in N["gleise"] if not g.get("vorlage_verbindung")]
    zusatz, LL = _verbindungen(key, N, {n for n, v in KN.items() if v.get("typ") == "switch"})
    ersetzt = set(ov.get("weglassen") or []) | set((ov.get("zeichnen") or {}).get("weg") or [])
    zusatz = [z for z in zusatz if set(z[1]) <= ersetzt]          # nur Ways, die eine Hand-Linie ersetzt
    r1 = lambda v: round(float(v), 1)
    for kette, ways, tags in zusatz:
        a, b = KN[kette[0]], KN[kette[-1]]
        if None in (a.get("x"), a.get("y"), b.get("x"), b.get("y")): continue
        for i, n in enumerate(kette[1:-1], 1):
            if n in KN: continue
            t = i / (len(kette) - 1)
            KN[n] = dict(lat=(LL.get(n) or (None, None))[0], lon=(LL.get(n) or (None, None))[1], x=r1(a["x"] + t * (b["x"] - a["x"])), y=r1(a["y"] + t * (b["y"] - a["y"])), typ=None)
        for w in ways:
            kn = [n for n in kette if n in ways[w]]
            N["gleise"].append(dict(id=f"v{w}", way=w, knoten=kn, ebene=None, y=None, pax=not tags[w].get("service"),
                                    service=tags[w].get("service"), usage=tags[w].get("usage"), ref=tags[w].get("ref"),
                                    gleis=tags[w].get("railway:track_ref"), spur=tags[w].get("gauge"), stillgelegt=False,
                                    vorlage_verbindung=True))
    N["knoten"] = {str(n): v for n, v in KN.items()}
    json.dump(N, open(fn, "w"), ensure_ascii=False, indent=0)
    print(key, f"Netzmodell: {n_} von {len(W_)} Weichen an die Hand-Linien gelegt, {len(zusatz)} OSM-Verbindungen ergänzt")


def run(key):
    ov = json.load(open(f"{key}_override.json"))
    V = ov.get("vorlage")
    if not V: print(key, "kein 'vorlage' im Override"); return None
    pp = json.load(open(f"{key}_ports.json"))
    if not pp.get("vorlage"): shutil.copy(f"{key}_ports.json", f"{key}_osm_ports.json")
    osm = json.load(open(f"{key}_osm_ports.json"))
    full, bare, P, bef, _, _ = zeichne(V, osm, osm.get("title") or key)
    # Abgleich mit OSM: Streckengleise je Seite (Abgänge des allgemeinen Laufs + Gleiszahl der Nachbarstrecke)
    try:
        from typ_vorschlag import vorschlag
        nL, nR = vorschlag(key)["_osm"]["enden"]
        tL = sum(1 for p in P["ports"] if p["kind"] == "edge" and p["dx"] < 0); tR = sum(1 for p in P["ports"] if p["kind"] == "edge" and p["dx"] > 0)
        bef = [b for b in bef if "allgemeinen Lauf" not in b or "seitliche" in b]
        if tL != nL: bef.append(f"links: {tL} Streckengleise in der Vorlage, {nL} in OSM")
        if tR != nR: bef.append(f"rechts: {tR} Streckengleise in der Vorlage, {nR} in OSM")
    except Exception as ex:
        bef.append(f"OSM-Abgleich nicht möglich: {ex}")
    try:
        nb = netz_mitschreiben(key, full, P)
        if nb: bef.append(nb)
    except Exception as ex:
        bef.append(f"Netzmodell nicht mitgeschrieben: {ex}")
    open(f"{key}_spurplan.svg", "w").write(full); open(f"{key}_spurplan_check.svg", "w").write(full)
    open(f"{key}_bare.svg", "w").write(bare); json.dump(P, open(f"{key}_ports.json", "w"), ensure_ascii=False)
    json.dump(bef, open(f"{key}_vorlage_befund.json", "w"), ensure_ascii=False)
    print(f"{key:20s} {P['vorlage']:22s} Befunde: {bef or 'keine'}")
    return bef

# ---------------------------------------------------------------- Blaupause 2
BP2 = [
 ("Reinformen", [
  ("R1", "Einspur, Halt, Perron oben", {"strecke": "einspur", "form": "halt", "perrons": "oben"}),
  ("R2", "Einspur, Halt, Perron unten", {"strecke": "einspur", "form": "halt", "perrons": "unten"}),
  ("R3", "Einspur, Kreuzungsgleis, zwei Aussenperrons", {"strecke": "einspur", "form": "kreuzung", "perrons": "aussen", "gleise": ["1", "2"]}),
  ("R4", "Einspur, Kreuzungsgleis, Mittelperron", {"strecke": "einspur", "form": "kreuzung", "perrons": "mittel", "gleise": ["1", "2"]}),
  ("R5", "Doppelspur, Halt, zwei Aussenperrons", {"strecke": "doppelspur", "form": "halt", "perrons": "aussen", "gleise": ["1", "2"]}),
  ("R6", "Doppelspur, Halt, Mittelperron", {"strecke": "doppelspur", "form": "halt", "perrons": "mittel", "gleise": ["1", "2"]}),
  ("R7", "Doppelspur, Überholgleise beidseits", {"strecke": "doppelspur", "form": "ueberholung", "perrons": "mittel", "gleise": ["1", "2", "3", "4"]}),
  ("R8", "Doppelspur, Überholgleis einseitig", {"strecke": "doppelspur", "form": "ueberholung", "ueberholgleise": "oben", "perrons": "aussen", "gleise": ["1", "2", "3"]}),
 ]),
 ("Lage", [
  ("L1", "Spiegeln: Kreuzungsgleis unten (= R3 gespiegelt)", {"strecke": "einspur", "form": "kreuzung", "perrons": "aussen", "spiegeln": True, "gleise": ["1", "2"]}),
  ("L2", "Kreuzungsgleis nur als Nebengleis (schwarz)", {"strecke": "einspur", "form": "kreuzung", "perrons": "unten", "pax": [False, True]}),
  ("L3", "Drehen im Regionalplan: 0°, 60°, 90°, 120°", None),
 ]),
 ("Zusätze", [
  ("Z1", "Spurwechsel rechts, einfach steigend", {"strecke": "doppelspur", "form": "halt", "perrons": "aussen", "zusaetze": [{"art": "spurwechsel", "ende": "rechts", "anzahl": 1, "richtung": "steigend"}]}),
  ("Z2", "Spurwechsel links, einfach fallend", {"strecke": "doppelspur", "form": "halt", "perrons": "aussen", "zusaetze": [{"art": "spurwechsel", "ende": "links", "anzahl": 1, "richtung": "fallend"}]}),
  ("Z3", "Doppelter Spurwechsel beidseits", {"strecke": "doppelspur", "form": "halt", "perrons": "aussen", "zusaetze": [{"art": "spurwechsel", "ende": "links", "anzahl": 2}, {"art": "spurwechsel", "ende": "rechts", "anzahl": 2}]}),
  ("Z4", "Anschluss innen (Stumpen läuft zum Perron hin)", {"strecke": "einspur", "form": "kreuzung", "perrons": "aussen", "zusaetze": [{"art": "anschluss", "ende": "rechts", "lage": "innen", "seite": "unten", "stumpen": 1}]}),
  ("Z5", "Anschluss aussen, zwei Stumpen", {"strecke": "einspur", "form": "halt", "perrons": "oben", "zusaetze": [{"art": "anschluss", "ende": "rechts", "lage": "aussen", "seite": "unten", "stumpen": 2}]}),
  ("Z6", "Anschluss läuft aus dem Plan (Pfeil)", {"strecke": "doppelspur", "form": "halt", "perrons": "aussen", "zusaetze": [{"art": "anschluss", "ende": "links", "lage": "aussen", "seite": "oben", "stumpen": 1, "pfeil": True}]}),
  ("Z7", "Seitlicher Abzweig einer Strecke", {"strecke": "einspur", "form": "halt", "perrons": "unten", "zusaetze": [{"art": "abzweig", "ende": "rechts", "seite": "oben"}]}),
  ("Z8", "Doppelspurbeginn (Einspur wird Doppelspur)", {"strecke": "einspur", "form": "halt", "perrons": "oben", "zusaetze": [{"art": "doppelspurbeginn", "ende": "rechts", "seite": "unten"}]}),
 ]),
]

def blaupause2(out):
    TW, TH, COLS = 560, 190, 3
    o = []; y = 80
    o.append(f'<text x="20" y="40" font-size="24" font-weight="700" fill="{G}">Blaupause 2 – Bahnhofstypen (Reinform + Zusätze)</text>')
    o.append(f'<text x="20" y="62" font-size="13" fill="#555">Gezeichnet mit vorlage.py, also genau so wie die Pläne · Beschreibung je Feld = Override "vorlage" · Kennung (R1 …) für Hinweise</text>')
    for grp, tiles in BP2:
        o.append(f'<text x="20" y="{y + 18}" font-size="17" font-weight="700" fill="{G}">{grp}</text>'); y += 30
        for k, (kenn, titel, V) in enumerate(tiles):
            cx, cy = 20 + (k % COLS) * TW, y + (k // COLS) * TH
            o.append(f'<g transform="translate({cx},{cy})"><rect width="{TW - 12}" height="{TH - 12}" rx="6" fill="none" stroke="#ddd"/>'
                     f'<text x="10" y="18" font-size="13" font-weight="700" fill="{G}">{kenn}</text><text x="40" y="18" font-size="12" fill="#333">{titel}</text>')
            if V is None:       # L3: Drehungen als kleine Kästen
                for j, a in enumerate((0, 60, 90, 120)):
                    _, bare, _, _, body, (W, ymin, ymax, M, PL, PR) = zeichne({"strecke": "einspur", "form": "kreuzung", "perrons": "aussen"}, None, "", False)
                    s = 0.17; bx = 70 + j * 125; by = 95
                    o.append(f'<g transform="translate({bx},{by}) rotate({a}) scale({s}) translate({-(PL + PR) / 2:.0f},{-(ymin + ymax) / 2:.0f})">{body}</g>'
                             f'<text x="{bx}" y="165" font-size="12" text-anchor="middle" fill="#555">{a}°</text>')
            else:
                _, _, _, _, body, (W, ymin, ymax, M, PL, PR) = zeichne(V, None, "", False)
                s = min((TW - 40) / (PR - PL + 40), 95 / (ymax - ymin + 20))
                o.append(f'<g transform="translate({(TW - 12) / 2:.0f},{30 + 55}) scale({s:.3f}) translate({-(PL + PR) / 2:.0f},{-(ymin + ymax) / 2:.0f})">{body}</g>')
                js = json.dumps(V, ensure_ascii=False).replace("&", "&amp;").replace("<", "&lt;")
                if len(js) > 95: js = js[:92] + "…"
                o.append(f'<text x="10" y="{TH - 22}" font-size="9.5" fill="#888">{js}</text>')
            o.append("</g>")
        y += ((len(tiles) + COLS - 1) // COLS) * TH + 10
    W = 20 + COLS * TW + 10; H = y + 20
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif">'
           f'<rect width="100%" height="100%" fill="#fff"/>' + "".join(o) + "</svg>")
    open(out, "w").write(svg); print(out, W, H)

if __name__ == "__main__":
    if sys.argv[1:2] == ["--blaupause2"]: blaupause2(sys.argv[2] if len(sys.argv) > 2 else "blaupause2.svg")
    else:
        if sys.argv[1:2] == ["--weichen"]:
            for k in sys.argv[2:]: weichen_festlegen(k)
        else:
            for k in sys.argv[1:]: run(k)
