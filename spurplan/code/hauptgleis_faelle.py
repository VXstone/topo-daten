"""Prüffälle für die Sperre HT (Schritt HT, REGELN 0.1 / Kopf «HT») bauen – je Fall 0° und 90° gedreht.

  python3 hauptgleis_faelle.py <plaene_dir> <netz_dir> <ziel_dir>

Quelle: Seite (ergebnisse/seite/plaene + netz.tgz). Fälle:
  giesshuebel      szu__zurich_giesshubel aus Code (Stand v155): Kreuzung ohne OSM (HT2), künstliche Schnitte am Planrand
                   (HT5, Achsknick), OSM-Weiche ohne Abzweig (HT1)
  wangen_fehlt     Wangen b. O. ohne den Spurwechsel West (Gl. 4 -> Gl. 3): HT1 + HT5 «fehlt»
  wangen_schere    Wangen b. O. mit zusätzlicher Gegendiagonale am Spurwechsel Ost (Schere statt eines Spurwechsels):
                   HT2 + HT5 «zusätzlich»
  wangen_seite     Wangen b. O., Netzmodell: Spurwechsel Ost zweigt nach oben statt nach unten ab: HT4
  wangen           unverändert: kein HT-Befund
Drehung 90°: SVG-Inhalt in <g transform="rotate(90)">, Netzmodell (x, y) -> (-y, x), Abgangsrichtung ebenso.
"""
import copy, json, os, re, sys

SCHERE = ('<path d="M840.8,237.2Q847.8,237.2 851.3,231.1L858.2,219.3Q861.7,213.2 868.7,213.2" fill="none" '
          'stroke="#111" stroke-width="2"/>')
WEST = "M291.0,237.2H291.0Q298.0,237.2 301.5,231.1L308.4,219.3Q311.9,213.2 318.9,213.2H318.9"


def drehen_svg(svg, grad):
    if not grad: return svg
    m = re.search(r"<svg[^>]*>", svg)
    return svg[:m.end()] + f'<g transform="rotate({grad})">' + svg[m.end():].replace("</svg>", "</g></svg>")


def drehen_xy(x, y, grad):
    return (x, y) if not grad else (-y, x)


def drehen_netz(N, grad):
    N = copy.deepcopy(N)
    if not grad: return N
    for v in N["knoten"].values():
        if v.get("x") is not None and v.get("y") is not None: v["x"], v["y"] = drehen_xy(v["x"], v["y"], grad)
        elif v.get("x") is not None: v["x"] = None           # Zwischenknoten ohne Ebene: nicht gedreht verwendbar
    for a in N.get("abgaenge", []):
        a["x"], a["y"] = drehen_xy(a["x"], a["y"], grad); a["dx"], a["dy"] = drehen_xy(a.get("dx", 0), a.get("dy", 0), grad)
    for m in N.get("nummern", []): m["x"], m["y"] = drehen_xy(m["x"], m["y"], grad)
    for m in N.get("angedeutet", []): m["x"], m["y"] = drehen_xy(m["x"], m["y"], grad)      # Regel 39b (V4e)
    return N


def schreiben(ziel, name, svg, N, erwartet, nicht, quelle):
    for grad in (0, 90):
        k = f"{name}_{grad}"
        open(os.path.join(ziel, k + ".svg"), "w").write(drehen_svg(svg, grad))
        json.dump(drehen_netz(N, grad), open(os.path.join(ziel, k + "_netz.json"), "w"), ensure_ascii=False)
        dr = lambda L: [dict(e, **dict(zip(("x", "y"), drehen_xy(e["x"], e["y"], grad)))) if "x" in e else e for e in L]
        json.dump(dict(_quelle=quelle + f", gedreht {grad}°", erwartet=dr(erwartet), nicht=dr(nicht)),
                  open(os.path.join(ziel, k + ".json"), "w"), ensure_ascii=False, indent=1)


def main(plaene, netz, ziel):
    os.makedirs(ziel, exist_ok=True)
    lies = lambda k: (open(os.path.join(plaene, k + ".svg")).read(), json.load(open(os.path.join(netz, k + ".json"))))
    svg, N = lies("szu__zurich_giesshubel")
    schreiben(ziel, "giesshuebel", svg, N,
              [dict(regel="HT2", x=1328.2, y=184.4, anlass="Gleise kreuzen sich im Depot, in OSM keine Kreuzung (T-SZU)"),
               dict(regel="HT5", x=2020.4, y=232.4, text="künstlicher Schnitt", anlass="Achsknick 65°: Gleis endet am Planrand statt durchzulaufen (REGELN 2.15)"),
               dict(regel="HT5", x=225.5, y=208.4, text="künstlicher Schnitt", anlass="dito, Mittelgleis"),
               dict(regel="HT1", x=1697.4, y=-178.0, anlass="Weiche 1262541542 an 717 ohne Abzweig")],
              [], "Seite v155 (ergebnisse 644a346), Giesshübel aus Code – Anlass Schritt HT")
    svg, N = lies("wangen_bei_olten")
    schreiben(ziel, "wangen", svg, N, [], [dict(regel=r, anlass="unverändert: kein Befund") for r in ("HT1", "HT2", "HT3", "HT4", "HT5")],
              "Seite v155, Wangen b. O. (abgenommen 13.10.)")
    assert WEST in svg
    schreiben(ziel, "wangen_fehlt", svg.replace(WEST, ""), N,
              [dict(regel="HT1", x=291.0, y=237.2, r=20, anlass="Weiche Spurwechsel West ohne Abzweig"),
               dict(regel="HT5", text="fehlt im Plan", anlass="Fahrweg Solothurn Gl. 4-Seite -> Gl. 3 fehlt")],
              [dict(regel="HT4")], "Wangen b. O. ohne Spurwechsel West (künstlicher Fehler)")
    schreiben(ziel, "wangen_schere", svg.replace("</svg>", SCHERE + "</svg>"), N,
              [dict(regel="HT2", x=854.7, y=225.2, r=8, anlass="Kreuzung der Scherendiagonalen ohne OSM-Kreuzung"),
               dict(regel="HT5", text="im Plan, nicht in OSM", anlass="zusätzlicher Fahrweg über die Gegendiagonale")],
              [dict(regel="HT4")], "Wangen b. O. mit Schere statt Spurwechsel Ost (künstlicher Fehler)")
    N2 = copy.deepcopy(N)
    N2["knoten"]["1765359533"]["y"] = 189.2                 # Ziel des Spurwechsels Ost oberhalb statt unterhalb Gl. 3
    schreiben(ziel, "wangen_seite", svg, N2,
              [dict(regel="HT4", x=840.8, y=213.2, anlass="Spurwechsel Ost zweigt im Netzmodell zur falschen Seite ab")],
              [], "Wangen b. O., Netzmodell mit Abzweig zur falschen Seite (künstlicher Fehler)")


if __name__ == "__main__":
    main(*sys.argv[1:4])
