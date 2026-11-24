"""Grundprüfung als Sperre (Schritt G0, Entscheid D. Eckenstein 18.11.2026: «so Dinge wie nicht überschneiden, paralleler
Abstand etc. sollten funktionieren»). REGELN «Grundprüfung als Sperre» (Kopf), Prüfcodes GS–GT bei 0.1–0.6, 1.2, 1.14,
1.15, 2.5, 2.7.

Prüft NUR das gezeichnete SVG – ohne OSM-Zuordnung. Anlass: S2 meldete «Gl.-6-Schräge kreuzt nichts», tatsächlich Schnitt
bei 558/283 (Konolfingen v153); der OSM-Abgleich hatte die Kreuzung einer nahen Weiche (< 40 px) zugeordnet.

  python3 grundpruefung.py <plan.svg> [--netz <key>.json] [--json out.json]
  python3 grundpruefung.py --alle <plaene_dir> [--netz-dir <dir>] --out <ordner> [--basis grundpruefung_basis.json]
                           [--basis-setzen] [--abschnitt plaene|pruefstand] [--rekursiv]
  python3 grundpruefung.py --basis-aus <zaehlung.json> --basis <json> [--abschnitt …]   (Basis aus einem Workflow-Lauf)
  python3 grundpruefung.py --selbsttest <faelle_dir>        (Prüffälle mit Erwartung, z. B. Konolfingen v153 558/283)

Befunde (Regel, x, y, Text) – Plan-px, Ebenenabstand je Plan geschätzt (häufigster Abstand paralleler Hauptgleise):
  GS  Schnitt: zwei gezeichnete Gleise kreuzen sich ausserhalb ihrer Endpunkte, ohne DKW-Symbol (Bögen/Klammern), ohne
      OSM-Kreuzungsknoten (railway=railway_crossing im Netzmodell, ≤ 9 px) und ohne Niveautrennung (Lücke/Flügel)
      (REGELN 2.4/2.5)
  GG  Gleis auf Gleis: zwei Gleise laufen > 12 px aufeinander (0,5 px Toleranz, wie VD1) und verdecken eines: beide laufen
      über die Auflage hinaus oder die Auflage ist > 3 Ebenen (Einlauf eines endenden Gleises = Weiche; nicht unter Schild)
  GQ  Querabstand paralleler Gleise nach einem gemeinsamen Knick ≠ davor (REGELN 1.15/2.7; = QK aus pruefstand_messen)
  GP  Pfeil zeigt nach innen / auf ein Nachbargleis: Strahl ab der Spitze trifft innert 1,5 Ebenen ein Gleis, oder die
      Spitze liegt näher als ½ Ebene an einem fremden Gleis (REGELN 1.14)
  GW  90°: Knick ≥ 80° in einem Gleis (inkl. Spitzkehre) oder Gleisende stösst unter ≥ 75° auf ein anderes Gleis (REGELN 1.2)
  GT  Treppe: hin und zurück ohne Anschluss dazwischen (Wunsch 5.1; = T7 Treppe aus ruhe.py)

Sperre: mit --basis ist jede Zunahme einer Regel in einem Plan gegenüber der Basis ein NEUER Befund -> Rückgabewert 1
(Workflow `seite` rot). Neue Pläne (nicht in der Basis) zählen mit Basis 0. --basis-setzen schreibt die Zählung als Basis.
Abschnitte der Basis: «plaene» (Seite, Workflow seite) und «pruefstand» (Fälle <fall>/<plan>.svg, Workflow pruefstand,
--rekursiv). Fehlt der Abschnitt in der Basis, wird nur gezählt (keine Sperre) – Basis dann bewusst mit --basis-aus setzen.
"""
import argparse, collections, glob, json, math, os, re, sys
import xml.etree.ElementTree as ET
import numpy as np
from svgpathtools import parse_path, Line, QuadraticBezier
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pruefstand_messen as PM
import ruhe

TRACK = {"#00862f", "#111", "#111111", "#000", "#9a5b1e", "#9a5b1f"}
GRUEN = {"#00862f"}
REGELN = ["GS", "GG", "GQ", "GP", "GW", "GT", "GE"]
TEXT = {"GS": "Schnitt ohne DKW/Kreuzung/Niveautrennung", "GG": "Gleis auf Gleis", "GQ": "Querabstand nach Knick ≠ davor",
        "GP": "Pfeil nach innen / auf Nachbargleis", "GW": "Knick oder Abgang 90°", "GT": "Treppe",
        "GE": "loses Gleisende (kein Prellbock, Pfeil, Abgang oder Gleis)"}
LANE_B, LANE_R = 24.0, 24 * 0.42          # Ebenenabstand Bahnhofplan / Regionalplan (S = 0,42)
NICHT_PLAENE = {"fragen", "pruefstand", "osm_verdacht"}          # Werkzeugkasten-Karten ohne Gleise im Plansinn


def _mat(tr):
    M = np.eye(3)
    for f, a in re.findall(r"(\w+)\(([^)]*)\)", tr or ""):
        v = [float(x) for x in re.split(r"[ ,]+", a.strip()) if x]
        if f == "translate": T = np.array([[1, 0, v[0]], [0, 1, v[1] if len(v) > 1 else 0], [0, 0, 1]])
        elif f == "scale": T = np.diag([v[0], v[1] if len(v) > 1 else v[0], 1])
        elif f == "rotate":
            c, s = math.cos(math.radians(v[0])), math.sin(math.radians(v[0]))
            T = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
            if len(v) == 3: T = np.array([[1, 0, v[1]], [0, 1, v[2]], [0, 0, 1]]) @ T @ np.array([[1, 0, -v[1]], [0, 1, -v[2]], [0, 0, 1]])
        elif f == "matrix": T = np.array([[v[0], v[2], v[4]], [v[1], v[3], v[5]], [0, 0, 1]])
        else: continue
        M = M @ T
    return M


def lesen(svg_text):
    """Gleise (Polylinien, Ausrundung = Ecke am Kontrollpunkt), DKW-Bögen, Lücken, Flügel, Pfeile, Punkte"""
    root = ET.fromstring(svg_text)
    linien, boegen, luecken, fluegel, pfeile, punkte, schilder, texte = [], [], [], [], [], [], [], []

    def walk(el, M, st):
        if el.get("class") == "befund": return
        tag = el.tag.split("}")[-1]
        M = M @ _mat(el.get("transform"))
        st = dict(st)
        for k in ("stroke", "stroke-width", "fill", "stroke-opacity", "stroke-dasharray"):
            if el.get(k) is not None: st[k] = el.get(k)
        tp = lambda z: (M @ np.array([z.real, z.imag, 1.0]))[:2]
        if tag == "text":                                    # Abgangsbeschriftung («Zürich HB →») für GE
            t_ = "".join(el.itertext())
            if "→" in t_ or "←" in t_ or t_.startswith("Linie"):
                texte.append(tp(complex(float(el.get("x", 0) or 0), float(el.get("y", 0) or 0))))
            return
        if tag == "rect" and (el.get("fill") or "").lower() in ("#fff", "#ffffff", "white") and "%" not in (el.get("width") or "") \
                and max(float(el.get("width", 0)), float(el.get("height", 0))) <= 60:          # Schild der Gleisnummer, nicht das Planblatt
            x, y, w_, h_ = (float(el.get(k, 0)) for k in ("x", "y", "width", "height"))
            from shapely.geometry import Polygon
            schilder.append(Polygon([tp(complex(a, b)) for a, b in ((x, y), (x + w_, y), (x + w_, y + h_), (x, y + h_))]))
        if tag == "circle":
            punkte.append(tp(complex(float(el.get("cx", 0)), float(el.get("cy", 0)))))
        if tag == "path" and el.get("d"):
            try: P = parse_path(el.get("d"))
            except Exception: P = None
            col = (st.get("stroke") or "").lower(); fill = (st.get("fill") or "none").lower()
            if P is None: pass
            elif el.get("data-pfeil") is not None or (fill in TRACK and col in ("", "none")):
                pts = [tp(s.start) for s in P]
                if len(P) == 2: pts.append(tp(P[-1].end))                # offenes Dreieck «M a L b L c» (Referenzen)
                if len(pts) == 4 and np.linalg.norm(pts[3] - pts[0]) < 0.1: pts = pts[:3]   # geschlossen mit L zurück
                if len(pts) == 3:                                     # Dreieck (schräge Perronflächen sind Vierecke)
                    _, i = min((np.linalg.norm(pts[i] - pts[(i + 1) % 3]), i) for i in range(3))
                    a, b, tip = pts[i], pts[(i + 1) % 3], pts[(i + 2) % 3]
                    d = tip - (a + b) / 2
                    if np.linalg.norm(d) > 0.5: pfeile.append(((a + b) / 2, tip, d / np.linalg.norm(d)))
            elif el.get("data-fluegel"):
                for s in P: fluegel.append((tp(s.start) + tp(s.end)) / 2)
            elif col in ("#fff", "#ffffff", "white"):
                w = float(st.get("stroke-width") or 1) * math.sqrt(abs(np.linalg.det(M[:2, :2])))
                if w >= 4:
                    for sub in P.continuous_subpaths():
                        q = [tp(s.start) for s in sub] + [tp(sub[-1].end)]
                        if len(q) > 1: luecken.append(LineString(q).buffer(w / 2))
            elif col in TRACK and fill == "none" and not st.get("stroke-dasharray"):
                subs = list(P.continuous_subpaths())
                L = sum(s.length() for s in P)
                if float(st.get("stroke-opacity", "1")) < 0.9 or (len(subs) == 1 and L < 9 and any(not isinstance(s, Line) for s in P)):
                    for s in P: boegen.append(tp(s.point(0.5)))         # DKW-Klammern und -Bögen
                else:
                    w = float(st.get("stroke-width") or 1) * math.sqrt(abs(np.linalg.det(M[:2, :2])))
                    for sub in subs:
                        pts, echt, n_seg = [], [], 0
                        for seg in sub:
                            if seg.length() < 0.05: continue
                            n_seg += 1
                            if isinstance(seg, Line): q = r = [seg.start, seg.end]
                            else:
                                r = [seg.point(t) for t in np.linspace(0, 1, 9)]          # echte Kurve (Schnitt/Auflage)
                                q = [seg.start, seg.control, seg.end] if isinstance(seg, QuadraticBezier) else r
                            for z in q:                                                  # Ausrundung -> Ecke (Winkel)
                                p = tp(z)
                                if not pts or np.linalg.norm(p - pts[-1]) > 0.05: pts.append(p)
                            for z in r:
                                p = tp(z)
                                if not echt or np.linalg.norm(p - echt[-1]) > 0.05: echt.append(p)
                        if len(pts) >= 2: linien.append(dict(pts=np.array(pts), echt=np.array(echt), col=col, w=w,
                                                             gerade=(n_seg == 1 and all(isinstance(x, Line) for x in sub))))
        for ch in el: walk(ch, M, st)

    walk(root, np.eye(3), {})
    return dict(linien=linien, boegen=boegen, luecken=luecken, fluegel=fluegel, pfeile=pfeile, punkte=punkte, schilder=schilder, texte=texte)


def ebene_schaetzen(linien):
    """häufigster Querabstand langer paralleler Gleisstücke (grün zuerst), 6–40 px"""
    for farben in (GRUEN, TRACK):
        segs = []
        for li, g in enumerate(linien):
            if g["col"] not in farben: continue
            p = PM._dp(g["pts"])
            for a, b in zip(p, p[1:]):
                L = float(np.linalg.norm(b - a))
                if L > 30: segs.append((a, (b - a) / L, L, li))
        h = collections.Counter()
        for i in range(len(segs)):
            a1, u1, L1, l1 = segs[i]; n1 = np.array([-u1[1], u1[0]])
            for j in range(i + 1, len(segs)):
                a2, u2, L2, l2 = segs[j]
                if l1 == l2 or abs(float(u1 @ u2)) < 0.9999: continue
                d = abs(float((a2 - a1) @ n1))
                if not 6 <= d <= 40: continue
                s = sorted((float((a2 - a1) @ u1), float((a2 + u2 * L2 - a1) @ u1)))
                ov = min(L1, s[1]) - max(0.0, s[0])
                if ov > 30: h[round(d * 2) / 2] += ov
        if h: return h.most_common(1)[0][0]
    return 24.0


def pruefen(svg_text, netz=None, lane=None):
    svg_text = re.sub(r"</(\w+)<", r"</\1><", svg_text)        # Basel/Bern (fest): «</text<circle» – Browser verzeiht es
    D = lesen(svg_text)
    linien = D["linien"]
    if lane is None: lane = ebene_schaetzen(linien)
    B = []
    def bef(r, p, t): B.append(dict(regel=r, x=round(float(p[0]), 1), y=round(float(p[1]), 1), text=t))
    G = [LineString(g["echt"]) for g in linien]            # gezeichnete Kurve
    tree = STRtree(G) if G else None
    enden = [(i, g["echt"][0]) for i, g in enumerate(linien)] + [(i, g["echt"][-1]) for i, g in enumerate(linien)]
    in_luecke = lambda p: any(l_.contains(Point(p)) for l_ in D["luecken"])
    unter_schild = lambda p: any(s_.buffer(0.5).contains(Point(p)) for s_ in D["schilder"])

    def richtung(i, p, weg=3.0):
        L_ = G[i]; t = L_.project(Point(p))
        q0, q1 = L_.interpolate(max(0, t - weg)), L_.interpolate(min(L_.length, t + weg))
        u = np.array([q1.x - q0.x, q1.y - q0.y]); n = np.linalg.norm(u)
        return u / n if n > 1e-9 else None

    # Messungen aus dem Prüfstand (gleiche Definitionen): X, QK, K
    M = PM.messen(svg_text, lane)
    kreuz = []
    if netz:
        kreuz = [np.array([v["x"], v["y"]]) for v in netz.get("knoten", {}).values()
                 if v.get("typ") == "railway_crossing" and v.get("y") is not None]

    # GS Schnitt: eigene Suche über ganze Linien (auch an Ecken der Polylinie), dann Ausnahmen
    gesehen = []
    for i in range(len(G)):
        for j in tree.query(G[i]):
            j = int(j)
            if j <= i: continue
            x = G[i].intersection(G[j])
            if x.is_empty: continue
            for q in getattr(x, "geoms", [x]):
                if q.geom_type != "Point": continue
                p = np.array([q.x, q.y])
                if any(np.linalg.norm(p - e) < 2.0 for _, e in enden): continue           # Knoten (Weiche, Stoss)
                ui, uj = richtung(i, p), richtung(j, p)
                if ui is None or uj is None: continue
                w = math.degrees(math.acos(min(1.0, abs(float(ui @ uj)))))
                if w < 10: continue                                                     # tangential (Weichenbogen)
                # sichtbar ein Schnitt nur, wenn beide Gleise über die Strichbreite des anderen hinaus weiterlaufen; sonst
                # ist es eine Einmündung mit Überstand (Weiche, im Regionalplan oft 1–4 px)
                rest = lambda a, b: min(G[a].project(Point(p)), G[a].length - G[a].project(Point(p))) * math.sin(math.radians(w))
                if rest(i, j) <= linien[j]["w"] / 2 + 1.0 or rest(j, i) <= linien[i]["w"] / 2 + 1.0: continue
                if unter_schild(p): continue
                if sum(np.linalg.norm(p - b) < 14 for b in D["boegen"]) >= 2: continue  # DKW-Symbol
                if any(np.linalg.norm(p - k) <= 9 for k in kreuz): continue              # OSM-Kreuzung (gleiche Ebene)
                if in_luecke(p) or any(np.linalg.norm(p - f) < 12 for f in D["fluegel"]): continue   # Niveautrennung
                if any(np.linalg.norm(p - g) < 3 for g in gesehen): continue
                gesehen.append(p); bef("GS", p, f"Gleise kreuzen sich ({w:.0f}°) ohne DKW, Kreuzung oder Niveautrennung")

    # GG Gleis auf Gleis (VD1-Definition)
    for i in range(len(G)):
        for j in tree.query(G[i].buffer(0.5)):
            j = int(j)
            if j <= i: continue
            ov = G[i].intersection(G[j].buffer(0.5))
            if ov.length > 12 and G[j].intersection(G[i].buffer(0.5)).length > 12:
                # Randstück eines Abgangs (gerades Einzelstück <= 30 px ganz auf dem Gleis, wie G8) ist kein zweites Gleis
                k_ = min((i, j), key=lambda m: G[m].length)
                if linien[k_]["gerade"] and G[k_].length <= 30 and ov.length >= 0.9 * G[k_].length: continue
                # Einlauf (REGELN 0.1, G0): ein Gleis läuft auf das andere ein und endet auf ihm, Auflage <= 3 Ebenen – sichtbar
                # eine Weiche (wo die Weiche nach OSM hingehört, prüft VD1 im OSM-Abgleich). Zwei Gleise, die beide über die
                # Auflage hinauslaufen, oder eine lange Auflage verdecken ein Gleis.
                ovb = ov.buffer(1.5)
                endet = [m for m in (i, j) if any(ovb.contains(Point(q_)) for q_ in (G[m].coords[0], G[m].coords[-1]))]
                if len(endet) == 1 and ov.length <= 3 * lane: continue
                c = ov.centroid
                if not in_luecke((c.x, c.y)) and not unter_schild((c.x, c.y)): bef("GG", (c.x, c.y), f"zwei Gleise {ov.length:.0f} px aufeinander")

    # GQ parallel durch den Knick
    for b in M["befunde"]:
        if b["regel"] == "QK": bef("GQ", (b["x"], b["y"]), b["text"])

    # GP Pfeile
    for base, tip, d in D["pfeile"]:
        strahl = LineString([tip + d * 0.5, tip + d * 1.5 * lane])
        eigene = {int(k) for k in tree.query(Point(base).buffer(2.0)) if G[int(k)].distance(Point(base)) < 2.0} if tree else set()
        treffer = [int(k) for k in tree.query(strahl) if int(k) not in eigene and G[int(k)].intersects(strahl)] if tree else []
        if treffer:
            bef("GP", tip, f"Pfeil zeigt innert {1.5 * lane:.0f} px auf ein Gleis"); continue
        nah = []
        for k in (tree.query(Point(tip).buffer(0.5 * lane)) if tree else []):
            k = int(k)
            if k in eigene or G[k].distance(Point(tip)) >= 0.5 * lane: continue
            u = richtung(k, (lambda q: (q.x, q.y))(G[k].interpolate(G[k].project(Point(tip)))))
            if u is not None and abs(float(u @ d)) > 0.97: continue    # paralleles Nachbargleis: Abstand regeln Q/F
            nah.append(G[k].distance(Point(tip)))
        if nah: bef("GP", tip, f"Pfeilspitze {min(nah):.1f} px neben einem Gleis (< ½ Ebene)")

    # GW 90°: Knick ≥ 80° in einer Linie (inkl. Spitzkehre K) und Gleisende unter ≥ 75° auf ein anderes Gleis
    for i, g in enumerate(linien):
        p = PM._dp(g["pts"])
        for k in range(1, len(p) - 1):
            u, v = p[k] - p[k - 1], p[k + 1] - p[k]
            if np.linalg.norm(u) < 0.5 or np.linalg.norm(v) < 0.5: continue
            t = PM._winkel(u, v)
            if 80 <= t < 178 and not any(b["regel"] == "GW" and math.dist((b["x"], b["y"]), p[k]) < 3 for b in B):
                bef("GW", p[k], f"Knick {t:.0f}° im Gleis")          # ≥ 178°: Linie läuft auf sich zurück (unsichtbar)
    for i, g in enumerate(linien):
        p = PM._dp(g["pts"])
        if len(p) == 2 and np.linalg.norm(p[1] - p[0]) < 4: continue                    # Kleinststücke
        for e, v in ((p[0], p[0] - p[1]), (p[-1], p[-1] - p[-2])):
            if np.linalg.norm(v) < 1e-6: continue
            v = v / np.linalg.norm(v)
            for k in tree.query(Point(e).buffer(1.2)):
                k = int(k)
                if k == i or G[k].distance(Point(e)) > 1.2: continue
                t_ = G[k].project(Point(e))
                if t_ < 1.5 or t_ > G[k].length - 1.5: continue                          # Stoss/Fortsetzung
                u = richtung(k, e)
                if u is None: continue
                a = math.degrees(math.acos(min(1.0, abs(float(u @ v)))))
                if a >= 75: bef("GW", e, f"Gleis stösst unter {a:.0f}° auf ein anderes Gleis"); break

    # GT Treppe (T7-Definition aus ruhe.py), motiviert = anderes Gleis ≤ 6 px, Prellbock/Pfeil ≤ 14 px
    marken = list(D["punkte"]) + [t for _, t, _ in D["pfeile"]] + [b for b, _, _ in D["pfeile"]]
    for i, g in enumerate(linien):
        andere = [G[int(k)] for k in tree.query(G[i].buffer(6.0)) if int(k) != i]
        def motiv(p, andere=andere):
            if any(math.dist(p, m) <= 14 for m in marken): return True
            P_ = Point(p); return any(a.distance(P_) <= 6.0 for a in andere)
        for x in ruhe.pruefe_linien([(g["w"], g["pts"])], motiv):
            if x["art"] == "Treppe": bef("GT", (x["x"], x["y"]), f"Treppe, Versatz {x['versatz']} px")

    # GE loses Gleisende (REGELN 1.30, Entscheid Daniel 24.11.): jedes gezeichnete Gleisende ist ein Prellbock (Punkt), ein
    # Pfeil, ein beschrifteter Abgang («→/←», «Linie …») oder mündet in ein anderes Gleis (≤ 2 px). Stoss 2–6 px wird als solcher benannt.
    pfeil_pkte = [b for b, _, _ in D["pfeile"]] + [t for _, t, _ in D["pfeile"]]
    EN = _ge_enden(linien, G, tree)
    for i, (e, d, L, v) in enumerate(EN):
        if any(math.dist(e, m) <= max(6.0, 0.3 * lane) for m in D["punkte"]): continue
        # Unterbruch an einer Niveautrennung (Gleis taucht unter einem anderen durch, ohne weisse Lücke): gegenüber, jenseits
        # eines anderen Gleises, setzt ein Ende in derselben Richtung fort (≤ 2,5 Ebenen, ≤ 8°)
        if v is not None and d <= 0.8 * lane and any(
                j != i and w is not None and float(v @ w) < -0.99 and 0 < float((np.asarray(f) - e) @ v) <= 2.5 * lane
                and abs(float(v[0] * (f[1] - e[1]) - v[1] * (f[0] - e[0]))) <= 1.5 for j, (f, _, _, w) in enumerate(EN)): continue
        if any(math.dist(e, m) <= max(4.0, 0.3 * lane) for m in pfeil_pkte): continue
        if any(math.dist(e, m) <= 3.0 * lane for m in D["texte"]): continue
        if in_luecke(e): continue
        bef("GE", e, (f"Gleisende {d:.1f} px neben einem Gleis (Stoss)" if d <= 6 else "loses Gleisende")
            + f", Stück {L:.0f} px")

    zaehl = {r: sum(1 for b in B if b["regel"] == r) for r in REGELN}
    return dict(ebene=lane, zaehl=zaehl, befunde=B)


def _ist_fluegel(p):
    """Brückenflügel «M a L b L c L d»: zwei kurze Schenkel (≤ 6 px) schräg zum Mittelstück (Bahnhofplan, dünn schwarz)"""
    if len(p) != 4: return False
    s0, s1, s2 = (np.linalg.norm(p[k + 1] - p[k]) for k in range(3))
    if not (s0 <= 6 and s2 <= 6 and s1 > 2 * max(s0, s2)): return False
    return all(20 <= PM._winkel(p[k] - p[k - 1], p[k + 1] - p[k]) <= 70 for k in (1, 2))


def _ge_enden(linien, G, tree):
    """Enden der gezeichneten Gleise, die nicht in ein anderes Gleis münden: [(Punkt, Abstand zum nächsten Gleis, Länge)].
    Teilstücke (Subpfade), die sich berühren, zählen als verbunden."""
    R = []
    for i, g in enumerate(linien):
        q = g["echt"]
        if LineString(q).length < 0.5 or _ist_fluegel(g["pts"]): continue
        for e, e2 in ((q[0], q[1]), (q[-1], q[-2])):
            P_ = Point(e); dmin = 1e9
            for k in (tree.query(P_.buffer(6.5)) if tree else []):
                k = int(k)
                if k == i: continue
                dmin = min(dmin, G[k].distance(P_))
            if dmin <= 2.0: continue                                   # Stoss bis 2 px gilt als verbunden (sichtbar zu)
            v = np.asarray(e) - np.asarray(e2); n = np.linalg.norm(v)
            R.append((e, dmin, G[i].length, v / n if n > 1e-6 else None))
    return R


def _netz(netz_dir, key):
    if not netz_dir: return None
    f = os.path.join(netz_dir, key + ".json")
    return json.load(open(f)) if os.path.exists(f) else None


def _basis_lesen(basis):
    return json.load(open(basis)) if basis and os.path.exists(basis) else {}


def basis_schreiben(basis, abschnitt, tab, quelle):
    B = _basis_lesen(basis)
    B["_quelle"] = "grundpruefung.py (Schritt G0, REGELN «Grundprüfung als Sperre»); je Abschnitt Zählung je Plan und Regel"
    B[abschnitt] = {k: {r: v.get(r, 0) for r in REGELN} for k, v in sorted(tab.items()) if "fehler" not in v}
    B.setdefault("_stand", {})[abschnitt] = quelle
    json.dump(B, open(basis, "w"), ensure_ascii=False, indent=1, sort_keys=True)
    print(f"Basis gesetzt: {basis} [{abschnitt}] {len(B[abschnitt])} Pläne ({quelle})")


def alle(plaene, netz_dir, out, basis=None, basis_setzen=False, abschnitt="plaene", rekursiv=False):
    os.makedirs(out, exist_ok=True)
    tab = {}
    muster = os.path.join(plaene, "**", "*.svg") if rekursiv else os.path.join(plaene, "*.svg")
    for f in sorted(glob.glob(muster, recursive=rekursiv)):
        key = os.path.relpath(f, plaene)[:-4].replace(os.sep, "/")
        if key in NICHT_PLAENE or key.endswith("_bare") or os.path.basename(key) in NICHT_PLAENE: continue
        os.makedirs(os.path.dirname(os.path.join(out, key + ".json")), exist_ok=True)
        try: R = pruefen(open(f).read(), _netz(netz_dir, key), lane=LANE_R if os.path.basename(key).startswith("region") else LANE_B)
        except Exception as e:
            print(f"FEHLER {key}: {e}", file=sys.stderr); tab[key] = dict(fehler=str(e)); continue
        json.dump(R, open(os.path.join(out, key + ".json"), "w"), ensure_ascii=False, indent=1)
        tab[key] = dict(R["zaehl"], ebene=R["ebene"])
    json.dump(tab, open(os.path.join(out, "zaehlung.json"), "w"), ensure_ascii=False, indent=1, sort_keys=True)
    neu = []
    BB = _basis_lesen(basis); sperre = abschnitt in BB and not basis_setzen
    B = BB.get(abschnitt, {})
    for key, z in sorted(tab.items()):
        if "fehler" in z: neu.append((key, "FEHLER", 0, 1)); continue
        b = B.get(key, {})
        for r in REGELN:
            if z.get(r, 0) > b.get(r, 0): neu.append((key, r, b.get(r, 0), z[r]))
    # Bericht
    L = ["# Grundprüfung G0 (REGELN «Grundprüfung als Sperre») – nur gezeichnete Geometrie", "",
         f"{len(tab)} Pläne; Basis: {basis or '—'} [{abschnitt}]" + ("" if sperre else " – **keine Sperre** (Abschnitt fehlt)")
         + ". Neue Befunde (Zunahme gegen Basis) machen den Workflow rot.", "",
         "| Plan | " + " | ".join(REGELN) + " | Ebene |", "|---|" + "---|" * (len(REGELN) + 1)]
    for key, z in sorted(tab.items()):
        if "fehler" in z: L.append(f"| {key} | Fehler: {z['fehler'][:60]} |"); continue
        b = B.get(key, {})
        cell = lambda r: (f"**{z[r]}** (Basis {b.get(r, 0)})" if z[r] > b.get(r, 0) else (f"{z[r]} ↓{b.get(r, 0)}" if z[r] < b.get(r, 0) else str(z[r]) if z[r] else "·"))
        L.append(f"| {key} | " + " | ".join(cell(r) for r in REGELN) + f" | {z['ebene']} |")
    L += ["", "Regeln: " + "; ".join(f"{r} = {TEXT[r]}" for r in REGELN)]
    if neu:
        L += ["", "## NEUE Befunde", ""]
        for key, r, b, n in neu:
            L.append(f"- **{key}** {r}: {b} → {n}")
            if r != "FEHLER":
                for x in json.load(open(os.path.join(out, key + ".json")))["befunde"]:
                    if x["regel"] == r: L.append(f"  - {x['x']}/{x['y']}: {x['text']}")
    open(os.path.join(out, "grundpruefung.md"), "w").write("\n".join(L) + "\n")
    if basis_setzen and basis: basis_schreiben(basis, abschnitt, tab, f"--basis-setzen {plaene}")
    summe = collections.Counter()
    for z in tab.values():
        for r in REGELN: summe[r] += z.get(r, 0)
    print("Grundprüfung:", dict(summe), f"– {len(tab)} Pläne")
    for key, r, b, n in neu: print(f"{'NEU' if sperre else 'ohne Basis'} {key} {r}: {b} -> {n}")
    return 1 if (neu and sperre) else 0


def selbsttest(faelle):
    """Prüffälle: <name>.svg + <name>.json {erwartet: [{regel,x,y}], nicht: [{regel,x,y}], netz?}"""
    fehler = 0
    for f in sorted(glob.glob(os.path.join(faelle, "*.json"))):
        E = json.load(open(f)); svg = f[:-5] + ".svg"
        R = pruefen(open(svg).read(), json.load(open(os.path.join(faelle, E["netz"]))) if E.get("netz") else None)
        def da(e): return any(b["regel"] == e["regel"] and math.dist((b["x"], b["y"]), (e["x"], e["y"])) < e.get("r", 6) for b in R["befunde"])
        for e in E.get("erwartet", []):
            ok = da(e); fehler += not ok
            print(f"{'OK  ' if ok else 'FEHLT'} {os.path.basename(svg)} {e['regel']} {e['x']}/{e['y']} – {e.get('anlass', '')}")
        for e in E.get("nicht", []):
            ok = not da(e); fehler += not ok
            print(f"{'OK  ' if ok else 'FALSCH'} {os.path.basename(svg)} kein {e['regel']} bei {e['x']}/{e['y']} – {e.get('anlass', '')}")
    print("Selbsttest:", "bestanden" if not fehler else f"{fehler} Fehler")
    return 1 if fehler else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", nargs="?"); ap.add_argument("--netz"); ap.add_argument("--json")
    ap.add_argument("--alle"); ap.add_argument("--netz-dir"); ap.add_argument("--out")
    ap.add_argument("--basis"); ap.add_argument("--basis-setzen", action="store_true"); ap.add_argument("--selbsttest")
    ap.add_argument("--abschnitt", default="plaene"); ap.add_argument("--rekursiv", action="store_true"); ap.add_argument("--basis-aus")
    A = ap.parse_args()
    if A.selbsttest: sys.exit(selbsttest(A.selbsttest))
    if A.basis_aus:
        basis_schreiben(A.basis, A.abschnitt, json.load(open(A.basis_aus)), A.basis_aus); sys.exit(0)
    if A.alle: sys.exit(alle(A.alle, A.netz_dir, A.out, A.basis, A.basis_setzen, A.abschnitt, A.rekursiv))
    R = pruefen(open(A.svg).read(), json.load(open(A.netz)) if A.netz else None)
    if A.json: json.dump(R, open(A.json, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"ebene": R["ebene"], "zaehl": R["zaehl"]}, ensure_ascii=False))
    for b in R["befunde"]: print(f"  {b['regel']} {b['x']}/{b['y']} {b['text']}")
