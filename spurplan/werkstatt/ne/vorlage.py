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
   "gleise": ["1", "2"], "pax": [true, true]               (von oben nach unten, wie gezeichnet)
   "zusaetze": [                                           (alle Seiten- und Perronangaben wie gezeichnet, auch gespiegelt)
     {"art": "spurwechsel", "ende": "links|rechts", "anzahl": 1|2, "richtung": "steigend|fallend"},
     {"art": "anschluss", "ende": "links|rechts", "lage": "innen|aussen", "seite": "oben|unten", "stumpen": 1|2, "pfeil": false,
      "gleich_lang": false, "verlaengern": 0, "t_form": false, "t_laenge": 60},   # t_form: zweiter Stumpen am Fuss in Gegenrichtung   # gleich_lang (nur innen): alle Stumpen enden gleich, verlaengern px über den Perron hinaus
     {"art": "abzweig", "ende": "links|rechts", "seite": "oben|unten"},
     {"art": "doppelspurbeginn", "ende": "links|rechts", "seite": "oben|unten", "aus": "kreuzungsgleis"?} ]}
Grundriss (kanonisch, vor dem Spiegeln): Kreuzungs- und Überholgleise liegen oben bzw. aussen, Anschlüsse am
äussersten Gleis ihrer Seite. Masse wie Blaupause: Ebenen 24 px, 60°, Ausrundung 7 px, Perron 110 px, Nummer in der Mitte.
Ausgabe wie der allgemeine Lauf (<b>_spurplan.svg, _spurplan_check.svg, _bare.svg, _ports.json); die OSM-Abgänge des
allgemeinen Laufs werden als <b>_osm_ports.json gesichert und zugeordnet (Liniennummer, Ort, Peilung bleiben).
"""
import json, math, sys, os, shutil

G, K = "#00862f", "#111"
HW, NW = 3.6, 1.6
LANE = 24; T60 = math.tan(math.radians(60)); DX = LANE / T60; R = 7.0
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
            x0 = (SR + 34) if rechts else (SL - 34 - 2 * DX - 12)
            if n_ >= 2:
                lines.append(([(x0, yb), (x0 + DX, ya)], False, None)); lines.append(([(x0 + DX + 12, ya), (x0 + 2 * DX + 12, yb)], False, None))
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
            yn = ys[h] + (LANE if unten else -LANE)
            if yn < ys[0]: ys.insert(0, yn)
            if yn > ys[-1]: ys.append(yn)
            xs = (XH - 60) if rechts else (XL + 60)
            pe = PR if rechts else PL
            if rechts: lines.append(([(xs, ys[h]), (xs + DX, yn), (pe, yn)], True, None))
            else: lines.append(([(pe, yn), (xs - DX, yn), (xs, ys[h])], True, None))
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
            if not innen and not on_neben and any(z_["art"] == "spurwechsel" and z_.get("ende", "rechts") == a.get("ende", "rechts") for z_ in zs):
                xs += (1 if rechts else -1) * (2 * DX + 75)      # nicht im Spurwechsel abzweigen (Grandson 20.10.: wirkte wie Kreuzung)
            for j in range(stp):
                y_ = gi_y + sg * LANE * (1 + 0.55 * j); x_s = xs + dirx * 40 * j
                y_from = gi_y if j == 0 else gi_y + sg * LANE
                x_d = x_s + dirx * abs(y_ - y_from) / T60
                L_ = 90 - 20 * j
                if innen:
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
                lines.append(([(xk, ys[i]), (x_e, ys[i])], False, None))
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
        for k in sys.argv[1:]: run(k)
