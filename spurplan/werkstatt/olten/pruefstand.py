"""
Prüfstand: alle Bahnhöfe mit dem aktuellen Regelsatz neu zeichnen, alle Prüfungen laufen lassen,
mit der Basis vergleichen und einen Kontaktbogen erzeugen.

  python3 pruefstand.py                 # prüfen + Kontaktbogen
  python3 pruefstand.py --abnehmen thun ins   # aktuelle Ergebnisse dieser Bahnhöfe als Basis übernehmen

Regel: Ein abgenommener Bahnhof darf nach der Rangfolge der Grundsätze nicht schlechter werden (lexikografisch:
1 Topologie > 2 Lage > 3 Weiche sichtbar > 4 keine 90° > 5 Abstand > 6 gerade > 7 Detailgrad > 8 Darstellung).
Prüfungen je Bahnhof
  A  Verbindung nicht geschlossen      B  Scheinverbindung / Überlagerung
  C  Kreuzung ohne Knoten              D  Querreihenfolge falsch
  E  zu nah (zwei Gleise < 10,7 px)    W  Weiche verdeckt (Abzweig klebt am Stammgleis)
  R  90-Grad-Stück (Gleis quer zur Achse, steiler als 75°)
"""
import os, sys, json, ast, shutil, subprocess, datetime, re
HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "reg")
BASIS = os.path.join(HERE, "pruefstand_basis.json")
ERG = os.path.join(HERE, "pruefstand_ergebnis.json")
SCRIPTS = ["spurplan_schema.py", "spurplan_warp.py", "spurplan_check.py", "run.sh"]

GROSS = {"olten", "daniken", "olten_hammer"}          # grosse Knoten: im Regionalplan nur Hauptgleise (Detailblatt separat); kleine Bahnhöfe ganze Anlage
# (Schlüssel, Verzeichnis, Zusatzargumente, Anzeigename)
STATIONS = [("thun", REG, [], "Thun"), ("ins", REG, [], "Ins"), ("murten", REG, [], "Murten"), ("kerzers", REG, [], "Kerzers")] + [
    (k, HERE, ["--hauptgleise"] if k in GROSS else [], n) for k, n in [
        ("olten", "Olten"), ("aarburg_oftringen", "Aarburg-Oftringen"), ("rothrist", "Rothrist"), ("zofingen", "Zofingen"),
        ("safenwil", "Safenwil"), ("wangen_bei_olten", "Wangen b. O."), ("dulliken", "Dulliken"), ("daniken", "Däniken"),
        ("schonenwerd", "Schönenwerd"), ("tecknau", "Tecknau"), ("laufelfingen", "Läufelfingen"), ("olten_hammer", "Olten Hammer")]]
GRUND = [("1 Topologie", ["A", "B", "C"]), ("2 Lage", ["D"]), ("3 Weiche sichtbar", ["W"]), ("4 Keine 90°", ["R"]), ("5 Abstand", ["E"])]
# 6 Gerade, 7 Detailgrad, 8 Darstellung: noch ohne automatische Prüfung
KEYS = ["A", "B", "C", "D", "E", "W", "R"]

def run_station(key, d, extra):
    out = subprocess.run(["sh", "run.sh", key] + extra, cwd=d, capture_output=True, text=True).stdout
    m = re.search(r"Befunde: (\{.*\})", out)
    cnt = {k: 0 for k in KEYS}
    if m: cnt.update(ast.literal_eval(m.group(1)))
    else: cnt["fehler"] = out[-300:]
    js = os.path.join(d, f"{key}_abstand.json")
    subprocess.run(["python3", os.path.join(HERE, "abstand.py"), f"{key}_spurplan.svg", "--min", "10.7", "--winkel", "--json", js],
                   cwd=d, capture_output=True, text=True)
    ab = json.load(open(js)) if os.path.exists(js) else []
    cnt["E"] = sum(1 for a in ab if a["art"] == "zu nah"); cnt["W"] = sum(1 for a in ab if a["art"] == "Weiche verdeckt")
    cnt["R"] = sum(1 for a in ab if a["art"] == "90 Grad")
    return cnt, ab

def main():
    for s in SCRIPTS: shutil.copy(os.path.join(HERE, s), os.path.join(REG, s))     # ein Regelsatz für alle
    basis = json.load(open(BASIS)) if os.path.exists(BASIS) else {}
    erg, abst = {}, {}
    for key, d, extra, name in STATIONS:
        erg[key], abst[key] = run_station(key, d, extra)
    if "--abnehmen" in sys.argv:
        for key in sys.argv[sys.argv.index("--abnehmen") + 1:]:
            basis[key] = dict(erg[key], abgenommen=str(datetime.date.today()))
        json.dump(basis, open(BASIS, "w"), indent=1, ensure_ascii=False)
    # Grundsätze in Rangfolge (D. Eckenstein 13.10.2026): ein höherer Grundsatz geht immer vor
    def rang(c): return tuple(sum(c.get(k, 0) for k in ks) for _, ks in GRUND)
    def schlechter(neu, alt):          # lexikografisch: erster unterschiedlicher Grundsatz entscheidet
        for i, (x, y) in enumerate(zip(neu, alt)):
            if x != y: return (GRUND[i][0] if x > y else None)
        return None
    rueck = []
    for key, d, extra, name in STATIONS:
        b = basis.get(key)
        if not b: continue
        g = schlechter(rang(erg[key]), rang(b))
        if g: rueck.append(f"{name}: Grundsatz {g} {rang(b)} → {rang(erg[key])}")
    alt = json.load(open(ERG))["ergebnis"] if os.path.exists(ERG) else {}
    tot_neu = tuple(map(sum, zip(*[rang(erg[k]) for k, _, _, _ in STATIONS]))); tot_alt = tuple(map(sum, zip(*[rang(alt[k]) for k, _, _, _ in STATIONS if k in alt]))) if alt else None
    json.dump(dict(ergebnis=erg, rueckschritte=rueck), open(ERG, "w"), indent=1, ensure_ascii=False)
    print(f"{'Bahnhof':20s} " + " ".join(f"{k:>3s}" for k in KEYS) + "  Rang " + "/".join(g.split()[0] for g, _ in GRUND) + "  Status")
    for key, d, extra, name in STATIONS:
        c = erg[key]; tot = sum(c.get(k, 0) for k in KEYS)
        st = "abgenommen" if key in basis else ("sauber" if tot == 0 else "offen")
        print(f"{name:20s} " + " ".join(f"{c.get(k, 0):3d}" for k in KEYS) + f"  {str(rang(c)):18s} {st}")
    print("Gesamt nach Grundsätzen:", tot_neu, ("(vorher %s%s)" % (tot_alt, ", Rückschritt bei Grundsatz " + schlechter(tot_neu, tot_alt) if tot_alt and schlechter(tot_neu, tot_alt) else "")) if tot_alt else "")
    print("Rückschritte:", rueck or "keine")
    kontaktbogen(erg, abst, basis, rueck)
    return 1 if rueck else 0

def kontaktbogen(erg, abst, basis, rueck):
    import cairosvg
    from PIL import Image, ImageDraw, ImageFont
    def font(sz, bold=False):
        for f in (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold else []) + ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
            if os.path.exists(f): return ImageFont.truetype(f, sz)
        return ImageFont.load_default()
    TW = 1500; tiles = []
    for key, d, extra, name in STATIONS:
        svg = open(os.path.join(d, f"{key}_spurplan_check.svg")).read()
        _cm = {"zu nah": ("#c0f", "E"), "Weiche verdeckt": ("#f80", "W"), "90 Grad": ("#e00", "R")}
        mk = "".join(f'<circle cx="{a["x"]}" cy="{a["y"]}" r="14" fill="none" stroke="{_cm[a["art"]][0]}" stroke-width="3"/>'
                     f'<text x="{a["x"] + 16}" y="{a["y"] - 10}" font-size="16" fill="{_cm[a["art"]][0]}">{_cm[a["art"]][1]}</text>'
                     for a in abst[key])
        png = os.path.join(d, f"{key}_kontakt.png")
        cairosvg.svg2png(bytestring=svg.replace("</svg>", mk + "</svg>").encode(), write_to=png, output_width=TW)
        im = Image.open(png).convert("RGB")
        c = erg[key]; tot = sum(c.get(k, 0) for k in KEYS)
        st = "abgenommen" if key in basis else ("sauber" if tot == 0 else "offen")
        col = (0, 134, 47) if tot == 0 else ((200, 120, 0) if st != "abgenommen" else (0, 100, 160))
        head = Image.new("RGB", (TW, 70), "white"); dr = ImageDraw.Draw(head)
        dr.text((20, 12), name, fill=(20, 20, 20), font=font(34, True))
        dr.text((480, 20), "  ".join(f"{k} {c.get(k, 0)}" for k in KEYS), fill=col, font=font(26))
        dr.text((TW - 260, 20), st, fill=col, font=font(26, True))
        t = Image.new("RGB", (TW, head.height + im.height), "white"); t.paste(head, (0, 0)); t.paste(im, (0, head.height))
        tiles.append(t)
    cols = 2; W = cols * TW + 60
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    H = 160 + sum(max(t.height for t in r) + 30 for r in rows)
    sheet = Image.new("RGB", (W, H), "white"); dr = ImageDraw.Draw(sheet)
    dr.text((30, 25), f"Kontaktbogen Spurpläne – {datetime.date.today():%d.%m.%Y}", fill=(0, 134, 47), font=font(48, True))
    legend = ("A Verbindung offen · B Scheinverbindung/Überlagerung · C Kreuzung ohne Knoten · D Reihenfolge · "
              "E zu nah (violett) · W Weiche verdeckt (orange) · R 90-Grad-Stück")
    dr.text((30, 95), legend + ("   |   Rückschritte: " + "; ".join(rueck) if rueck else "   |   keine Rückschritte"), fill=(90, 90, 90), font=font(24))
    y = 160
    for r in rows:
        for i, t in enumerate(r): sheet.paste(t, (20 + i * (TW + 20), y))
        y += max(t.height for t in r) + 30
    out = os.path.join(HERE, f"{datetime.date.today():%Y%m%d}_Kontaktbogen Spurplaene.png")
    sheet.save(out)
    print("Kontaktbogen:", out)

if __name__ == "__main__":
    sys.exit(main())
