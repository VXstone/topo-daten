"""Blaupausen-Prüfstand (Schritt 1, UEBERGABE 8.11.2026) – nur messen, noch nichts korrigieren.

  python3 spurplan/code/blaupausen_pruefstand.py <ausgabe> [--basis spurplan/pruefstand_basis.json] [--basis-setzen]
                                                 [--nur baustein,…] [--jobs 4]
  python3 spurplan/code/blaupausen_pruefstand.py --basis-aus <tabelle.json> --basis spurplan/pruefstand_basis.json
                                                 (Basis aus einem Workflow-Lauf übernehmen, ohne zu rechnen)

Grundsatz: parallel bleibt parallel im gleichen Querabstand, in jeder Drehung und jedem Abgangswinkel; dazu die Regeln,
die bei Daniels Hinweisen immer wieder auffielen (Unterwerfung, Zwischengerade, Gleissprung, schräger Abgang, Perronformen).

Zwei Stufen, beide mit dem Code der echten Pläne:
  osm      Bausteine aus pruefstand_bausteine.py (synthetisches OSM) -> region_lauf.py (Kette der Linien-Regionen MOB/Vereina:
           Bahnhofplan aus OSM, Ports, Pfeile, Lage, connector). Gemessen: Regionalplan und die Bahnhofpläne Alpha/Beta.
  vorlage  Felder der Blaupause 2 (vorlage.py, Typvorlagen der Region Neuchâtel) -> netz_lage.py mit fester Lage.
Varianten je Baustein: d0, d30, dm30, d60, dm60, d90 = Bahnhof und Strecke gleich gedreht (Verbindung muss gerade bleiben);
a30, a60 = Bahnhof waagrecht, Strecken verlassen ihn unter 30°/60° (Abgänge).
Messung: pruefstand_messen.py (Q P F K Z E X T PF) + regel_pruefung.py (G2–G8); Drehinvarianz «D»: der Bahnhofplan eines
gedrehten OSM-Bausteins muss gleich sein wie ungedreht (Zahl der Linien und Befunde).

Ausgabe: <ausgabe>/tabelle.json, tabelle.md, pruefstand.svg (Kontaktbogen mit Befundmarken, Plan «Prüfstand» der Seite),
je Fall <fall>/region.svg (+ Bahnhofpläne). Mit --basis: Vergleich je Fall und Regel; jede Zunahme = Verschlechterung,
Rückgabewert 1 (Workflow rot). --basis-setzen schreibt die aktuelle Tabelle als Basis.
"""
import os, sys, json, math, shutil, subprocess, time, argparse, collections, re
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pruefstand_bausteine as PB
import pruefstand_messen as PM

LANE_R = 24 * 0.42          # Ebenenabstand im Regionalplan (S = 0,42)
LANE_B = 24.0               # Ebenenabstand im Bahnhofplan
VARIANTEN = [("d0", 0, 0), ("d30", 30, 30), ("dm30", -30, -30), ("d60", 60, 60), ("dm60", -60, -60), ("d90", 90, 90),
             ("a30", 30, 0), ("a60", 60, 0)]          # (Name, Drehung der Geografie, Drehung der Bahnhöfe im Plan)
REGELN = ["T", "PF", "X", "E", "K", "Q", "P", "F", "Z", "D", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]   # Rangfolge: Topologie zuerst
ERWARTUNG = {       # je OSM-Baustein: Strecken am Planrand {ref: Gleise}, Perronflächen je Bahnhof, Formen (Flächen mit >1 Balken)
    "r3_kreuzung": dict(strecken={"900": 1}, perrons={"alpha": 2}),
    "r5_halt": dict(strecken={"900": 2}, perrons={"alpha": 2}),
    "r7_ueberholung": dict(strecken={"900": 2}, perrons={"alpha": 2}),
    "ab30": dict(strecken={"900": 2, "901": 2}, perrons={"alpha": 2}),
    "ab60": dict(strecken={"900": 2, "901": 2}, perrons={"alpha": 2}),
    "sagliains": dict(strecken={"900": 2}, perrons={"alpha": 2}),
    "unterwerfung": dict(strecken={"900": 2, "901": 1}, perrons={"alpha": 2}),
    "zwischengerade": dict(strecken={"900": 2}, perrons={"alpha": 2}),
    "gleissprung": dict(strecken={"900": 2}, perrons={"alpha": 2}),
    "perronformen": dict(strecken={"900": 2}, perrons={"alpha": 3}, formen={"alpha": 2}),
}


# ------------------------------------------------------------------ Stufe OSM
def _repo(root):
    os.makedirs(os.path.join(root, "spurplan", "regionen"), exist_ok=True)
    if not os.path.exists(os.path.join(root, "spurplan", "code")): os.symlink(HERE, os.path.join(root, "spurplan", "code"))


def fall_osm(baustein, var, geo, plan, root, out):
    fall = f"ps_{baustein}_{var}"; d = os.path.join(out, f"osm_{baustein}_{var}"); os.makedirs(d, exist_ok=True)
    daten = os.path.join(d, "daten.json.gz"); N = PB.bau(baustein, geo, daten)
    st = [e["tags"]["name"] for e in N.el if e["type"] == "node" and e["tags"].get("railway") == "station"]
    K = dict(titel=f"Prüfstand {baustein} · {var}", bbox=N.bbox_stationen(), linien=["900", "901"], betreiber=["PS"], radius=600,
             name=f"{fall}_region",
             override_standard=dict(cfg=dict(sw_search_m=350, min_half_window_m=150, s_pad=60, lt_dist_w=2.0, margin_x=230)),
             lage=dict(auto=dict(c0=30, c1=32, p=0.6, gap=58, wg=0.01), osm="region.json",
                       cfg=dict(cover_m=200, merge_station_m=300, merge_junction_m=200),
                       drehung={s: -plan for s in st if s in ("Alpha", "Beta")}))
    kd = os.path.join(root, "spurplan", "regionen", fall); os.makedirs(kd, exist_ok=True)
    json.dump(K, open(os.path.join(kd, "region.json"), "w"), ensure_ascii=False, indent=1)
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(root, "spurplan", "code", "region_lauf.py"), fall, "--daten", daten],
                       capture_output=True, text=True, timeout=1500)
    erg = os.path.join(root, "ergebnisse", f"region_{fall}")
    res = dict(stufe="osm", baustein=baustein, variante=var, sekunden=round(time.time() - t0))
    if not os.path.exists(os.path.join(erg, "region.svg")):
        res["fehler"] = (r.stderr or r.stdout)[-600:]; return res
    for f in os.listdir(erg):
        if f.endswith(".svg") or f == "bericht.json": shutil.copy(os.path.join(erg, f), d)
    shutil.rmtree(erg, ignore_errors=True); shutil.rmtree(kd, ignore_errors=True)
    shutil.rmtree(os.path.join("/tmp/spurplan_region", fall), ignore_errors=True)
    return _auswerten(res, d, ERWARTUNG.get(baustein, {}))


# ------------------------------------------------------------------ Stufe Vorlage
def fall_vorlage(kenn, V, var, geo, plan, out):
    import vorlage
    d = os.path.join(out, f"vorlage_{kenn}_{var}"); os.makedirs(d, exist_ok=True)
    full, bare, P, bef, body, geo_ = vorlage.zeichne(V, None, kenn, False)
    nodes = [dict(id=0, name="Alpha", kind="station", x=0.0, y=0.0, tracks=2)]; edges = []; lage = {"Alpha": [0, 0]}
    refs = {}
    for k, p in enumerate(P["ports"]):
        # Abgangsrichtung im Bahnhof (Karte: y nach Norden) + Drehung der Strecke gegenüber dem Bahnhof
        vx, vy = (p["dx"], 0.0) if p["kind"] == "edge" else (p["dx"] * 0.5, -p["dy"] * 0.866)
        w = math.degrees(math.atan2(vy, vx)) + (geo - plan if p["kind"] == "edge" else 0) + plan
        key = (p["kind"], p["dx"], p.get("dy", 0)); r = refs.setdefault(key, str(900 + len(refs)))
        p.update(ref=r, bearing=round(w % 360, 1), town=f"Ort {r}"); p.setdefault("pax", True)
    for key, r in refs.items():
        ps = [p for p in P["ports"] if p["ref"] == r]; w = ps[0]["bearing"]; i = len(nodes)
        nodes.append(dict(id=i, name=f"Ende {r}", kind="exit", x=3000 * math.cos(math.radians(w)), y=3000 * math.sin(math.radians(w))))
        edges.append(dict(a=0, b=i, ref=r, refs=[r], tracks=len(ps), length=3000.0, geom=[[0, 0], [nodes[i]["x"], nodes[i]["y"]]]))
        # Abgang genau in der Verlängerung des Bündels (Mitte der Ports, gedreht wie der Bahnhof): eine gerade Strecke
        # verlangt keinen Versatz – macht der Plan trotzdem einen, ist es ein Befund des Codes, nicht des Aufbaus
        cx_, cy_ = (P["x_lo"] + P["x_hi"]) / 2, (P["y_lo"] + P["y_hi"]) / 2
        ox = sum(q["x"] - cx_ for q in ps) / len(ps) * 0.42; oy = sum(q["y"] - cy_ for q in ps) / len(ps) * 0.42
        c_, s_ = math.cos(math.radians(-plan)), math.sin(math.radians(-plan)); ox, oy = ox * c_ - oy * s_, ox * s_ + oy * c_
        lage[f"Ende {r} #{i}"] = [round(ox + 420 * math.cos(math.radians(w))), round(oy - 420 * math.sin(math.radians(w)))]
    open(os.path.join(d, "alpha_bare.svg"), "w").write(bare); json.dump(P, open(os.path.join(d, "alpha_ports.json"), "w"))
    json.dump(dict(nodes=nodes, edges=edges, bbox=[0, 0, 0, 0]), open(os.path.join(d, "ps_topologie.json"), "w"))
    lage["drehung"] = {"Alpha": -plan}
    json.dump(lage, open(os.path.join(d, "ps_lage.json"), "w"))
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(HERE, "netz_lage.py"), "ps", f"Prüfstand {kenn} · {var}", "region.svg"],
                       cwd=d, capture_output=True, text=True, timeout=600)
    res = dict(stufe="vorlage", baustein=kenn, variante=var, sekunden=round(time.time() - t0))
    if not os.path.exists(os.path.join(d, "region.svg")): res["fehler"] = (r.stderr or r.stdout)[-600:]; return res
    return _auswerten(res, d, dict(gesamt=len(P["ports"])))


# ------------------------------------------------------------------ Auswerten
def _auswerten(res, d, erw):
    svg = os.path.join(d, "region.svg")
    m = PM.messen(open(svg).read(), LANE_R); g = PM.regeln(svg)
    z = collections.Counter(m["zaehl"]); z.update(g)
    bef = list(m["befunde"])
    # T: erwartete Strecken am Planrand mit ihrer Gleiszahl (oberste Regel Topologie)
    if erw.get("gesamt"):
        hat = m["freie_enden"]; n = erw["gesamt"]
        if hat < n: z["T"] += n - hat; bef.append(dict(regel="T", x=None, y=None, text=f"{hat} statt {n} Gleise an den Abgängen"))
    for ref, n in erw.get("strecken", {}).items():
        hat = m["strecken"].get(ref, [])
        if not hat: z["T"] += n; bef.append(dict(regel="T", x=None, y=None, text=f"Strecke {ref} fehlt im Plan ({n} Gleise erwartet)"))
        elif max(hat) < n: z["T"] += n - max(hat); bef.append(dict(regel="T", x=None, y=None, text=f"Strecke {ref}: {max(hat)} statt {n} Gleise"))
    bahnhof = {}
    for f in sorted(os.listdir(d)):
        if not f.endswith("_spurplan.svg"): continue
        b = f[:-len("_spurplan.svg")]; mb = PM.messen(open(os.path.join(d, f)).read(), LANE_B)
        bahnhof[b] = dict(zaehl=mb["zaehl"], linien=mb["linien"], perron_flaechen=mb["perron_flaechen"], befunde=mb["befunde"])
        for k, v in mb["zaehl"].items():
            if k in ("Q", "P", "F", "K", "E", "X"): z[k] += v; bef += [dict(b_, bahnhof=b) for b_ in mb["befunde"] if b_["regel"] == k]
        n_erw = erw.get("perrons", {}).get(b)
        if n_erw and len(mb["perron_flaechen"]) < n_erw:
            z["PF"] += n_erw - len(mb["perron_flaechen"]); bef.append(dict(regel="PF", x=None, y=None, bahnhof=b, text=f"{len(mb['perron_flaechen'])} statt {n_erw} Perronflächen"))
        f_erw = erw.get("formen", {}).get(b)
        if f_erw:
            n_f = sum(1 for x in mb["perron_flaechen"] if x > 1)
            if n_f < f_erw: z["PF"] += f_erw - n_f; bef.append(dict(regel="PF", x=None, y=None, bahnhof=b, text=f"{n_f} statt {f_erw} Perronformen (U/L/T als eine Fläche)"))
    res.update(zaehl={k: z[k] for k in REGELN if z.get(k)}, befunde=bef, bahnhof=bahnhof, strecken=m["strecken"], ordner=os.path.basename(d))
    return res


def drehinvarianz(ergebnisse):
    """D: Bahnhofplan Alpha eines gedrehten OSM-Bausteins wie ungedreht (Linienzahl und Befunde)"""
    ref = {(r["baustein"]): r.get("bahnhof", {}).get("alpha") for r in ergebnisse if r["stufe"] == "osm" and r["variante"] == "d0"}
    for r in ergebnisse:
        if r["stufe"] != "osm" or r["variante"] == "d0" or "fehler" in r: continue
        a, b = ref.get(r["baustein"]), r.get("bahnhof", {}).get("alpha")
        if a and b and (a["linien"] != b["linien"] or a["zaehl"] != b["zaehl"] or a["perron_flaechen"] != b["perron_flaechen"]):
            r["zaehl"]["D"] = r["zaehl"].get("D", 0) + 1
            r["befunde"].append(dict(regel="D", x=None, y=None, bahnhof="alpha",
                                     text=f"Bahnhofplan anders als ungedreht (Linien {a['linien']}→{b['linien']}, Befunde {a['zaehl']}→{b['zaehl']})"))


# ------------------------------------------------------------------ Kontaktbogen
def kontaktbogen(ergebnisse, out, stand):
    TW, TH, KOPF = 420, 260, 150
    zeilen = []
    for r in ergebnisse:
        k = (r["stufe"], r["baustein"])
        if k not in [z[0] for z in zeilen]: zeilen.append((k, []))
        [z for z in zeilen if z[0] == k][0][1].append(r)
    W = KOPF + TW * len(VARIANTEN) + 20; H = 110 + TH * len(zeilen) + 20
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif">',
         f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="20" y="40" font-size="28" font-weight="700" fill="#00862f">Prüfstand – Bausteine × Drehungen</text>',
         f'<text x="20" y="66" font-size="14" fill="#555">Stand {stand} · nur messen · rote Marke = Befund (Kennung: T Topologie/Strecke, X Kreuzung ohne Knoten, E Ebenenwechsel, '
         f'K Spitzkehre, Q Querabstand, P nicht parallel, F Pfeile, Z Zwischengerade, PF Perron, D Drehung, G2–G8 Regelprüfung)</text>']
    for j, (v, geo, plan) in enumerate(VARIANTEN):
        o.append(f'<text x="{KOPF + j * TW + TW / 2}" y="98" font-size="15" font-weight="700" text-anchor="middle" fill="#333">'
                 f'{v} · {"Drehung " + str(plan) + "°" if v.startswith("d") else "Abgang " + str(geo) + "°"}</text>')
    for i, ((stufe, b), rs) in enumerate(zeilen):
        y0 = 110 + i * TH
        o.append(f'<text x="14" y="{y0 + 30}" font-size="14" font-weight="700" fill="#00862f">{b}</text><text x="14" y="{y0 + 48}" font-size="11" fill="#777">{stufe}</text>')
        for j, (v, _, _) in enumerate(VARIANTEN):
            r = next((x for x in rs if x["variante"] == v), None); x0 = KOPF + j * TW
            o.append(f'<rect x="{x0 + 4}" y="{y0 + 4}" width="{TW - 8}" height="{TH - 8}" rx="6" fill="none" stroke="#ddd"/>')
            if not r: continue
            if "fehler" in r:
                o.append(f'<text x="{x0 + 14}" y="{y0 + 30}" font-size="13" fill="#c00">Lauf fehlgeschlagen</text>'); continue
            s = open(os.path.join(out, r["ordner"], "region.svg")).read()
            vb = [float(t) for t in re.search(r'viewBox="([^"]+)"', s).group(1).split()]
            inner = re.sub(r"^<svg[^>]*>", "", s.strip()); inner = re.sub(r"</svg>\s*$", "", inner)
            inner = re.sub(r'<text[^>]*font-size="(3[0-9]|4[0-9])"[^>]*>[^<]*</text>', "", inner)      # Titel weg
            inner = re.sub(r'<text[^>]*>Gleisdaten[^<]*</text>', "", inner)
            inner = inner.replace(' data-st="', ' data-ps-st="').replace(' data-name="', ' data-ps-name="')   # keine Bahnhöfe der Seite
            inner = re.sub(r'^\s*<rect[^>]*fill="#fff"/>', "", inner, count=1)                         # Hintergrund des Plans
            # Ausschnitt: Gleise (ohne Titel/Fussnote) – Rahmen aus den Linienpunkten
            lin, _, _, _ = PM.lesen(s)
            import numpy as np
            P_ = np.vstack([p for p, w in lin]) if lin else np.array([[vb[0], vb[1]], [vb[0] + vb[2], vb[1] + vb[3]]])
            bx0, by0 = P_.min(axis=0) - 40; bx1, by1 = P_.max(axis=0) + 40
            sc = min((TW - 24) / (bx1 - bx0), (TH - 50) / (by1 - by0))
            marks = "".join(f'<circle cx="{b_["x"]}" cy="{b_["y"]}" r="{9 / sc:.1f}" fill="none" stroke="#e00" stroke-width="{2.2 / sc:.2f}"/>'
                            f'<text x="{b_["x"] + 11 / sc:.1f}" y="{b_["y"] - 9 / sc:.1f}" font-size="{12 / sc:.1f}" font-weight="700" fill="#e00">{b_["regel"]}</text>'
                            for b_ in r["befunde"] if b_.get("x") is not None and not b_.get("bahnhof"))
            o.append(f'<clipPath id="c{i}_{j}"><rect x="{x0 + 5}" y="{y0 + 5}" width="{TW - 10}" height="{TH - 34}"/></clipPath>'
                     f'<g clip-path="url(#c{i}_{j})"><g transform="translate({x0 + 12},{y0 + 12}) scale({sc:.4f}) translate({-bx0:.1f},{-by0:.1f})">{inner}{marks}</g></g>')
            zt = " ".join(f"{k} {n}" for k, n in r["zaehl"].items()) or "ohne Befund"
            o.append(f'<text x="{x0 + 14}" y="{y0 + TH - 14}" font-size="12" fill="{"#c00" if r["zaehl"] else "#00862f"}">{zt}</text>')
    o.append("</svg>")
    open(os.path.join(out, "pruefstand.svg"), "w").write("\n".join(o))


def tabelle_md(ergebnisse, vergleich, stand):
    L = [f"# Prüfstand – Bausteine × Drehungen ({stand})", "",
         "Zählung je Fall (Regel Anzahl); leer = ohne Befund. Rangfolge der Regeln: " + ", ".join(REGELN), ""]
    L.append("| Stufe | Baustein | " + " | ".join(v for v, _, _ in VARIANTEN) + " |")
    L.append("|---|---|" + "---|" * len(VARIANTEN))
    zeilen = collections.OrderedDict()
    for r in ergebnisse: zeilen.setdefault((r["stufe"], r["baustein"]), {})[r["variante"]] = r
    for (st, b), rs in zeilen.items():
        z_ = []
        for v, _, _ in VARIANTEN:
            r = rs.get(v)
            z_.append("—" if not r else ("FEHLER" if "fehler" in r else " ".join(f"{k} {n}" for k, n in r["zaehl"].items())))
        L.append(f"| {st} | {b} | " + " | ".join(z_) + " |")
    L += ["", "## Befunde je Regel (Summe über alle Fälle)", ""]
    s = collections.Counter()
    for r in ergebnisse: s.update(r.get("zaehl", {}))
    L.append(" · ".join(f"{k} {s[k]}" for k in REGELN if s.get(k)) or "keine")
    if vergleich is not None:
        L += ["", "## Gegen die Basis", ""]
        L += [f"- {x}" for x in vergleich] or ["- keine Verschlechterung"]
    L += ["", "## Befundliste", ""]
    for r in ergebnisse:
        for b_ in r.get("befunde", []):
            L.append(f"- {r['stufe']} {r['baustein']} {r['variante']}: **{b_['regel']}** {b_['text']}" + (f" (Bahnhof {b_['bahnhof']})" if b_.get("bahnhof") else ""))
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ausgabe", nargs="?"); ap.add_argument("--basis"); ap.add_argument("--basis-aus"); ap.add_argument("--basis-setzen", action="store_true")
    ap.add_argument("--nur"); ap.add_argument("--jobs", type=int, default=4); ap.add_argument("--stufe", default="osm,vorlage")
    A = ap.parse_args()
    if A.basis_aus:
        T = json.load(open(A.basis_aus))
        json.dump(dict(gesetzt=T["stand"], quelle=os.path.basename(A.basis_aus), faelle=T["faelle"], fehler=sorted(T.get("fehler", {}))), open(A.basis, "w"),
                  ensure_ascii=False, indent=1, sort_keys=True)
        print("Basis gesetzt aus", A.basis_aus, T["stand"], len(T["faelle"]), "Fälle"); return 0
    out = os.path.abspath(A.ausgabe); os.makedirs(out, exist_ok=True)
    root = os.path.join("/tmp", "pruefstand_repo"); _repo(root)
    nur = set(A.nur.split(",")) if A.nur else None
    auf = []
    if "osm" in A.stufe:
        for b in PB.BAUSTEINE:
            if nur and b not in nur: continue
            for v, geo, plan in VARIANTEN: auf.append(("osm", b, v, geo, plan))
    if "vorlage" in A.stufe:
        import vorlage
        for grp, tiles in vorlage.BP2:
            for kenn, titel, V in tiles:
                if V is None or (nur and kenn not in nur): continue
                for v, geo, plan in VARIANTEN: auf.append(("vorlage", kenn, v, geo, plan, V))
    def eins(a):
        try:
            if a[0] == "osm": return fall_osm(a[1], a[2], a[3], a[4], root, out)
            return fall_vorlage(a[1], a[5], a[2], a[3], a[4], out)
        except Exception as e:
            return dict(stufe=a[0], baustein=a[1], variante=a[2], fehler=repr(e)[-600:])
    t0 = time.time()
    with ThreadPoolExecutor(A.jobs) as ex: ergebnisse = list(ex.map(eins, auf))
    drehinvarianz(ergebnisse)
    for r in ergebnisse: r.setdefault("zaehl", {})
    stand = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    vergleich = None; schlechter = []
    if A.basis and os.path.exists(A.basis) and not A.basis_setzen:
        B = json.load(open(A.basis)).get("faelle", {}); vergleich = []
        for r in ergebnisse:
            k = f"{r['stufe']}/{r['baustein']}/{r['variante']}"
            if k not in B: continue
            if "fehler" in r:
                if k not in json.load(open(A.basis)).get("fehler", []): schlechter.append(f"{k}: Lauf fehlgeschlagen")
                continue
            for reg in REGELN:
                n0, n1 = B[k].get(reg, 0), r["zaehl"].get(reg, 0)
                if n1 > n0: schlechter.append(f"{k}: {reg} {n0} → {n1}")
                elif n1 < n0: vergleich.append(f"{k}: {reg} {n0} → {n1} (besser)")
        vergleich = [f"SCHLECHTER {x}" for x in schlechter] + vergleich
    T = dict(stand=stand, sekunden=round(time.time() - t0), varianten=[v for v, _, _ in VARIANTEN], regeln=REGELN,
             faelle={f"{r['stufe']}/{r['baustein']}/{r['variante']}": r["zaehl"] for r in ergebnisse},
             fehler={f"{r['stufe']}/{r['baustein']}/{r['variante']}": r["fehler"] for r in ergebnisse if "fehler" in r},
             summe=dict(sum((collections.Counter(r["zaehl"]) for r in ergebnisse), collections.Counter())),
             schlechter=schlechter, vergleich=vergleich, ergebnisse=ergebnisse)
    json.dump(T, open(os.path.join(out, "tabelle.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(out, "tabelle.md"), "w").write(tabelle_md(ergebnisse, vergleich, stand))
    kontaktbogen(ergebnisse, out, stand)
    lab = (f"Prüfstand {stand[:16]} · {len(ergebnisse)} Fälle · Befunde " + ", ".join(f"{k} {T['summe'][k]}" for k in REGELN if T['summe'].get(k))
           + (f" · {len(schlechter)} schlechter als Basis" if schlechter else (" · nicht schlechter als Basis" if vergleich is not None else "")))
    open(os.path.join(out, "label.txt"), "w").write(lab)
    if A.basis_setzen and A.basis:
        json.dump(dict(gesetzt=stand, faelle=T["faelle"], fehler=sorted(T["fehler"])), open(A.basis, "w"), ensure_ascii=False, indent=1, sort_keys=True)
        print("Basis gesetzt:", A.basis)
    print(lab)
    for x in schlechter: print("SCHLECHTER", x)
    for k, e in T["fehler"].items(): print("FEHLER", k, e[-200:])
    return 1 if schlechter else 0


if __name__ == "__main__":
    sys.exit(main())
