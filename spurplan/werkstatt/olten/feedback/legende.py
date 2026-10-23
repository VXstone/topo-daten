"""
Zeichenerklärung der Spurpläne und des Regionalplans, im selben Stil wie spurplan_schema.py / netz_lage.py.
  python3 feedback/legende.py   -> feedback/legende.svg (für den Plot) + feedback/legende.json (für die Feedback-Seite)
Die Begriffe sind zugleich das gemeinsame Vokabular für Hinweise.
"""
import json, os, math
G, K = "#00862f", "#111"
HW, NW = 3.6, 1.6                         # Hauptgleis, Nebengleis (Spurplan)
W, H = 150, 64                            # Symbolfeld
LANE = 22; DX = LANE / math.tan(math.radians(60))
Y1, Y2 = 21, 21 + LANE                    # zwei Spuren
YC = (Y1 + Y2) / 2

def p(d, col=G, w=HW): return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def xo(x, ya, yb, r=4):
    """Diagonale (60°) von Spur ya nach yb ab x, mit gerundeten Ecken wie im Spurplan"""
    s = 1 if yb > ya else -1; ux, uy = 0.5, s * 0.866
    xb = x + DX
    return (f"M{x - r:.1f},{ya}Q{x:.1f},{ya} {x + ux * r:.1f},{ya + uy * r:.1f}"
            f"L{xb - ux * r:.1f},{yb - uy * r:.1f}Q{xb:.1f},{yb} {xb + r:.1f},{yb}")
def lab(x, y, t, size=13, col=G, anc="middle", wt=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{wt}" text-anchor="{anc}" fill="{col}">{t}</text>'
def _dkw(cx, cy, hp=True):
    """DKW-Klammern wie im Spurplan (Standard 14.10.): parallel neben den Gleisen, tangential ausgerundet"""
    import numpy as _np, math as _m
    L_, OFF, W_, col = (12.0, 3.0, 2.2, G) if hp else (9.0, 2.2, 1.4, K)
    out_ = ""
    for a_, b_ in (((1, 0), (-0.5, -0.866)), ((-1, 0), (0.5, 0.866))):
        a_, b_ = _np.array(a_, float), _np.array(b_, float); bis = (a_ + b_) / _np.linalg.norm(a_ + b_); c0 = _np.array([cx, cy])
        pa = _np.array([-a_[1], a_[0]]); pa = pa if pa @ bis > 0 else -pa
        pb = _np.array([-b_[1], b_[0]]); pb = pb if pb @ bis > 0 else -pb
        half = _m.acos(float(a_ @ b_)) / 2
        p0 = c0 + a_ * L_ + pa * OFF; p1 = c0 + b_ * L_ + pb * OFF; cq = c0 + bis * OFF / _m.sin(half)
        t_ = 0.1 * 22 / 0.866; f0 = c0 + a_ * t_; f1 = c0 + b_ * t_
        out_ += f'<path d="M{f0[0]:.1f},{f0[1]:.1f}Q{cx:.1f},{cy:.1f} {f1[0]:.1f},{f1[1]:.1f}" fill="none" stroke="{col}" stroke-width="{3.6 if hp else 1.6}" stroke-linecap="round"/>'
        out_ += (f'<path d="M{p0[0]:.1f},{p0[1]:.1f}Q{cq[0]:.1f},{cq[1]:.1f} {p1[0]:.1f},{p1[1]:.1f}" fill="none" '
                 f'stroke="{col}" stroke-opacity="0.55" stroke-width="{W_}" stroke-linecap="round"/>')
    return out_
def two(): return p(f"M10,{Y1}H{W - 10}") + p(f"M10,{Y2}H{W - 10}")

E = [
 ("Hauptgleis", "Gleis mit Personenverkehr: Strecken- und Perrongleise. Im Regionalplan nur diese.",
  p(f"M10,{(Y1 + Y2) / 2}H{W - 10}")),
 ("Nebengleis", "Güter-, Abstell-, Dienst- und Anschlussgleise. In grossen Knoten (Olten) im Regionalplan nur als Abgang angedeutet.",
  p(f"M10,{(Y1 + Y2) / 2}H{W - 10}", K, NW)),
 ("Perron und Gleisnummer", "Grüner Balken = Perronkante; Zahl im weissen Feld = Gleisnummer.",
  p(f"M10,{Y2}H{W - 10}") + f'<rect x="30" y="{Y2 - 15}" width="90" height="6" rx="1.5" fill="{G}"/>'
  + f'<rect x="62" y="{Y2 - 7}" width="26" height="14" fill="#fff"/>' + lab(75, Y2 + 5, "3", 15)),
 ("Weiche", "Ein Gleis zweigt von einem anderen ab (immer 60°).",
  p(f"M10,{Y1}H{W - 10}") + p(xo(50, Y1, Y2) + f"H{W - 10}")),
 ("Einfacher Spurwechsel", "2 Weichen: Verbindung zwischen zwei parallelen Gleisen in eine Richtung.",
  two() + p(xo(62, Y1, Y2))),
 ("Doppelter Spurwechsel", "4 Weichen: zwei Spurwechsel hintereinander, gegenläufig, mit kleiner Zwischengerade.",
  two() + p(xo(30, Y2, Y1)) + p(xo(30 + DX + 10, Y1, Y2))),
 ("Hosenträger", "Gekreuzter Spurwechsel (auch Mittelstück): zwei Spurwechsel übereinander, mit Kreuzung in der Mitte.",
  two() + p(f"M{75 - DX},{Y1}L{75 + DX},{Y2}") + p(f"M{75 - DX},{Y2}L{75 + DX},{Y1}")),
 ("DKW", "Doppelte Kreuzungsweiche: die Schräge läuft gerade durch, zwei Klammern in den stumpfen Winkeln (= Bogenfahrwege). An einem Hauptgleis gross und hellgrün.",
  p(f"M10,{YC}H{W - 10}") + p(f"M{75 - 26 * 0.5},{YC - 26 * 0.866}L{75 + 26 * 0.5},{YC + 26 * 0.866}") + _dkw(75, YC)),
 ("DKW Nebengleis", "DKW nur zwischen Nebengleisen: gleiches Zeichen, kleiner und grau.",
  p(f"M10,{YC}H{W - 10}", K, NW) + p(f"M{75 - 26 * 0.5},{YC - 26 * 0.866}L{75 + 26 * 0.5},{YC + 26 * 0.866}", K, NW) + _dkw(75, YC, False)),
 ("Kreuzung", "Zwei Gleise kreuzen ohne Verbindung (auch Überwerfung / Unterführung).",
  p(f"M10,{(Y1 + Y2) / 2}H{W - 10}") + p(f"M{75 - 1.4 * DX},{Y1 - 6}L{75 + 1.4 * DX},{Y2 + 6}", K, NW)),
 ("Prellbock", "Gleisende (Stumpfgleis). Grün auf Hauptgleis, schwarz auf Nebengleis.",
  p(f"M10,{Y1}H{W - 30}") + f'<circle cx="{W - 30}" cy="{Y1}" r="4.5" fill="{G}"/>'
  + p(f"M10,{Y2}H{W - 50}", K, NW) + f'<circle cx="{W - 50}" cy="{Y2}" r="3.2" fill="{K}"/>'),
 ("Meterspur", "Schmalspurgleis (1000 mm), braun; ohne Verbindung zur Normalspur. Dick = Strecken-/Perrongleis, dünn = Abstellgleis.",
  p(f"M10,{Y1}H{W - 10}", "#9a5b1e") + p(f"M10,{Y2}H{70}", "#9a5b1e", NW) + p(xo(70, Y2, Y1)[:0] + f"M70,{Y2}L{70 + DX},{Y1}", "#9a5b1e", NW)),
 ("Pfeil am Planrand", "Nebengleis läuft über den Planausschnitt hinaus weiter.",
  p(f"M10,{(Y1 + Y2) / 2}H{W - 30}", K, NW) + f'<path d="M{W - 30},{(Y1 + Y2) / 2 - 4}L{W - 21},{(Y1 + Y2) / 2}L{W - 30},{(Y1 + Y2) / 2 + 4}Z" fill="{K}"/>'),
 ("Seitlicher Abgang", "Nebengleis verlässt den Plan seitlich (schräger Stummel mit Pfeil).",
  p(f"M10,{Y1}H{W - 10}", K, NW) + p(f"M60,{Y1}L{60 + 13},{Y1 + 22.5}", K, NW)
  + f'<path d="M{60 + 13 + 4.5},{Y1 + 22.5 + 7.8}L{60 + 13 - 3.5},{Y1 + 22.5 + 2}L{60 + 13 + 3.5},{Y1 + 22.5 - 2}Z" fill="{K}"/>'),
 ("Versatz (S-Kurve)", "Gleis wechselt die Höhe ohne Weiche. Nur wo es nicht anders geht.",
  p(f"M10,{Y1}H{60 - 4:.1f}" + xo(60, Y1, Y2)[xo(60, Y1, Y2).index("Q"):] + f"H{W - 10}")),
 ("Streckenabgang", "Ende des Plans: Liniennummer und Richtung (Regionalplan).",
  p(f"M10,{(Y1 + Y2) / 2 - 4}H90") + p(f"M10,{(Y1 + Y2) / 2 + 4}H90")
  + lab(96, (Y1 + Y2) / 2 - 3, "Linie 450", 12, G, "start") + lab(96, (Y1 + Y2) / 2 + 12, "Bern →", 12, G, "start")),
 ("Haltestelle", "Halt ohne Weichen: kurze Perronstriche beidseits (Regionalplan).",
  p(f"M10,{(Y1 + Y2) / 2}H{W - 10}") + p(f"M58,{(Y1 + Y2) / 2 - 7}H92", G, 4.2) + p(f"M58,{(Y1 + Y2) / 2 + 7}H92", G, 4.2)
  + lab(75, (Y1 + Y2) / 2 - 13, "Hägendorf", 11)),
 ("Abzweigstelle", "Verzweigung auf freier Strecke, ohne Bahnhof (Regionalplan).",
  p(f"M10,{Y1}H{W - 10}") + p(f"M10,{Y1 + 8}H{70}" + f"L{70 + 0.5 * 26},{Y1 + 8 + 0.866 * 26}H{W - 10}")),
]

def tile(svg): return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">{svg}</svg>'

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    json.dump([dict(begriff=b, text=t, svg=tile(s)) for b, t, s in E], open(os.path.join(here, "legende.json"), "w"), ensure_ascii=False)
    # Plot-Fassung: Raster 2 Spalten
    cols, cw, rh = 2, 560, 84
    rows = math.ceil(len(E) / cols); Wt, Ht = cols * cw + 40, rows * rh + 80
    body = [f'<rect width="{Wt}" height="{Ht}" fill="#fff"/>', lab(20, 40, "Zeichenerklärung", 24, G, "start", 700)]
    for i, (b, t, s) in enumerate(E):
        x0, y0 = 20 + (i % cols) * cw, 60 + (i // cols) * rh
        body.append(f'<g transform="translate({x0},{y0})">{s}</g>')
        body.append(lab(x0 + W + 12, y0 + 26, b, 15, "#111", "start", 600))
        import textwrap
        for k, ln in enumerate(textwrap.wrap(t, 64)[:2]): body.append(lab(x0 + W + 12, y0 + 43 + k * 14, ln, 11, "#555", "start"))
    open(os.path.join(here, "legende.svg"), "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wt} {Ht}" width="{Wt}" height="{Ht}" font-family="Fira Sans, Helvetica, Arial, sans-serif">' + "".join(body) + "</svg>")
    print(len(E), "Einträge")
