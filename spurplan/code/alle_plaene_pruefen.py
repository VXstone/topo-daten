"""Regression über ALLE Pläne der Feedback-Seite (6.11.2026, Befund Olten: nur plaene/regionen wurden verglichen,
die Werkstatt-Pläne aus dem Workflow seite – Region Olten, Region Neuchâtel, Referenzen – nie).

  python3 spurplan/code/alle_plaene_pruefen.py <abnahmen> <ausgabe_ordner> [--ref origin/ergebnisse] [--seit <commit>]
          [--neu <ordner mit <key>.svg>] [--seite <index.html>]

<abnahmen>: spurplan/abnahmen.json ({bahnhof: am}) oder ein Export der Sammlung «abnahme» der Feedback-Seite
(ArtifactData list mit out_dir, je Bahnhof eine JSON-Datei mit «bahnhof» und «am»).
Vergleich je Plan (ergebnisse/seite/plaene/<key>.svg auf dem Branch «ergebnisse»):
  - abgenommen: Fassung zur Abnahmezeit (ältere Abnahmen als das Archiv: erste Fassung, 23.10.2026) gegen heute
  - nicht abgenommen: zuletzt veröffentlichte Fassung (--seit <commit auf ergebnisse>) bzw. erste Fassung gegen heute
«heute» = --neu <ordner> (Workflow seite: frisch gerechnete Pläne vor dem Commit), sonst der Stand von --ref.
--seite <index.html>: Kartenlabel der geänderten Pläne und Untertitel um die Einordnung ergänzen (Workflow seite).
--osm-abgleich <ordner>: Befunde von osm_abgleich.py (V1, 12.11.2026) je Plan; die OSM-Regeln VA/VB/VC/VD zählen zur
Topologie. Alt-Stand aus ergebnisse/seite/osm_abgleich/<key>.json der Basis-Fassung (fehlt er, nur der heutige Stand).
--grund <ordner> [--grund-basis <json>]: Grundprüfung G0 (grundpruefung.py, REGELN «Grundprüfung als Sperre», 18.11.2026). Alt gegen neu wird
G0 auf beiden SVGs gerechnet (GS/GG zählen zur Topologie, GQ/GP/GW zu den Regeln, GT ist T7); Spalte «G0» = Stand gegen
die Sperr-Basis (fett = neuer Befund, macht den Workflow seite rot).
--ht <ordner> [--ht-basis <json>]: Hauptgleis-Topologie HT (hauptgleis.py, REGELN 0.1 / Kopf «HT», 18.11.2026); Spalte «HT» =
Stand gegen die Sperr-Basis wie G0 (nur Pläne mit Netzmodell).

Einordnung je geändertem Plan (Wunsch D. Eckenstein 6.11.: «vorschlagen, wo ein Plan verändert, aber vielleicht
verbessert wurde – ich schaue rasch drauf»). Gemessen wird nur auf den SVGs, alt gegen neu:
  topo  = Regelprüfung G5–G8 (Spurwechsel kreuzen, Knubbel, Gleis nicht angebunden, Gleise doppelt) – oberste Regel
  rest  = Regelprüfung G1–G4 (Nummern, Rundungen, Ecken, 90°)
  Wünsche (REGELN 5, wuensche.py, 17.11.2026) = gewichtete Summe aus T7 (Treppen/Ecken, 8), W53 S-Kurven (6),
          W55 Bahnhofsabstand im Regionalplan (3), W56 Leerlänge im Bahnhofsplan (3)
  «Fehler? Topologie»  topo steigt                      -> zuerst ansehen, gilt als Fehler bis erklärt
  «schlechter?»        topo gleich/kleiner, rest steigt – oder Wunsch-Summe steigt
  «vermutlich besser»  topo sinkt (Rest egal, Rangfolge), oder keine Regel steigt und die Wunsch-Summe sinkt (bzw. bleibt
                       und eine Zahl sinkt) -> Daniel nickt ab oder widerspricht
  «gleichwertig»       alle Zahlen gleich (Lage, Perrons, Darstellung) -> Differenzbild erklären
Ausgabe: tabelle.json, tabelle.md und je Änderung <key>_diff.png (+ <key>_alt.svg, <key>_neu.svg).
Jede geänderte Zeile muss erklärt sein (gewollte Regel E9 oder Fehler) – sonst ist die Runde nicht fertig.
"""
import collections, datetime, glob, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wuensche
import grundpruefung as GPR

ABN, OUT = sys.argv[1], sys.argv[2]
opt = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
REF = opt("--ref") or "origin/ergebnisse"
SEIT, NEU, SEITE = opt("--seit"), opt("--neu"), opt("--seite")
OSA = opt("--osm-abgleich")
GRUND, GRUND_BASIS = opt("--grund"), opt("--grund-basis")
HTD, HT_BASIS = opt("--ht"), opt("--ht-basis")
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
WUNSCH = tuple(wuensche.GEWICHT)        # T7, W53, W55, W56 (REGELN 5)
_RT = {"region": "spurplan/werkstatt/olten/olten_region_topologie.json", "region_ne": "spurplan/werkstatt/ne/ne_region_topologie.json",
       "region_mob": "ergebnisse/region_mob/mob_region_topologie.json", "region_vereina": "ergebnisse/region_vereina/vereina_region_topologie.json"}
TOPO = ("G5", "G6", "G7", "G8", "VA1", "VA2", "VB1", "VB2", "VC1", "VD1", "VD2", "GS", "GG")   # V*: OSM-Abgleich (V1, 12.11.), GS/GG: G0


def osa_zahlen(raw):
    try:
        d = json.loads(raw)
        return dict(collections.Counter(b["regel"] for b in d.get("befunde", [])))
    except Exception:
        return None


def git(*a):
    return subprocess.run(["git"] + list(a), capture_output=True).stdout


def abnahmen(pfad):
    if os.path.isfile(pfad):
        d = json.load(open(pfad)); return {k: v for k, v in d.items() if not k.startswith("_")}
    A = {}
    for f in glob.glob(os.path.join(pfad, "**", "*.json"), recursive=True):
        d = json.load(open(f))
        if d.get("bahnhof") and d.get("am"): A[d["bahnhof"]] = d["am"]
    return A


def messen(svg_bytes, key):
    """Regelprüfung G1–G8 und Ruhe T7 auf einem SVG; {regel: anzahl}"""
    z = collections.Counter()
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, f"{key}_spurplan.svg"); open(f, "wb").write(svg_bytes)
        try:
            subprocess.run([sys.executable, os.path.join(HERE, "regel_pruefung.py"), f, "--json", os.path.join(d, "r.json")],
                           capture_output=True, timeout=300)
            r = json.load(open(os.path.join(d, "r.json"))); r = r if isinstance(r, list) else r.get("befunde", [])
            z.update(b.get("regel") for b in r if b.get("regel"))
        except Exception as e:
            z["fehler_regel"] = 1; print("Regelprüfung", key, e, file=sys.stderr)
        try:
            subprocess.run([sys.executable, os.path.join(HERE, "ruhe.py"), d, "--json", os.path.join(d, "t.json")],
                           capture_output=True, timeout=300)
            t = json.load(open(os.path.join(d, "t.json")))
            t = t.get("befunde", t) if isinstance(t, dict) else t
            z["T7"] = len(t) if isinstance(t, list) else sum(len(v) for v in t.values() if isinstance(v, list))
        except Exception as e:
            print("Ruhe", key, e, file=sys.stderr)
    try:                                       # Wünsche 5.3/5.5/5.6 (REGELN 5)
        topo = None
        if key in _RT:
            raw = open(_RT[key], "rb").read() if os.path.exists(_RT[key]) else git("show", f"{REF}:{_RT[key]}")
            topo = json.loads(raw) if raw else None
        z.update(wuensche.messen(svg_bytes.decode("utf-8", "replace"), key, topo))
    except Exception as e:
        print("Wünsche", key, e, file=sys.stderr)
    try:                                       # Grundprüfung G0 (REGELN «Grundprüfung als Sperre»); GT = T7, nicht doppelt zählen
        g = GPR.pruefen(svg_bytes.decode("utf-8", "replace"), None,
                        lane=GPR.LANE_R if key.startswith("region") else GPR.LANE_B)["zaehl"]
        z.update({r: n for r, n in g.items() if r != "GT" and n})
    except Exception as e:
        print("Grundprüfung", key, e, file=sys.stderr)
    return dict(z)


def g0_spalte(k):
    """Stand G0 gegen die Sperr-Basis: «GS 3 · GG 1», neue Befunde fett mit Basis"""
    if not GRUND or not os.path.exists(os.path.join(GRUND, "zaehlung.json")): return ""
    z = json.load(open(os.path.join(GRUND, "zaehlung.json"))).get(k)
    if not z: return ""
    b = (json.load(open(GRUND_BASIS)).get("plaene", {}) if GRUND_BASIS and os.path.exists(GRUND_BASIS) else {}).get(k, {})
    t = [(f"**{r} {z[r]} (Basis {b.get(r, 0)})**" if z[r] > b.get(r, 0) else f"{r} {z[r]}") for r in GPR.REGELN if z.get(r)]
    return " · ".join(t) or "0"


def ht_spalte(k):
    """Stand HT gegen die Sperr-Basis: «HT2 3 · HT5 1», neue Befunde fett mit Basis; «–» ohne Netzmodell"""
    if not HTD or not os.path.exists(os.path.join(HTD, "zaehlung.json")): return ""
    z = json.load(open(os.path.join(HTD, "zaehlung.json"))).get(k)
    if not z: return "–"
    b = (json.load(open(HT_BASIS)).get("plaene", {}) if HT_BASIS and os.path.exists(HT_BASIS) else {}).get(k, {})
    t = [(f"**{r} {z[r]} (Basis {b.get(r, 0)})**" if z[r] > b.get(r, 0) else f"{r} {z[r]}") for r in ("HT1", "HT2", "HT3", "HT4", "HT5") if z.get(r)]
    return " · ".join(t) or "0"


def einordnen(alt, neu):
    keys = set(alt) | set(neu)
    d = {k: neu.get(k, 0) - alt.get(k, 0) for k in keys if neu.get(k, 0) != alt.get(k, 0)}
    t = sum(d.get(k, 0) for k in TOPO)          # Rangfolge der Grundsätze: Topologie zuerst, dann der Rest
    ws = wuensche.summe({k: neu.get(k, 0) for k in WUNSCH}) - wuensche.summe({k: alt.get(k, 0) for k in WUNSCH})
    if any(d.get(k, 0) > 0 for k in TOPO): e = "Fehler? Topologie"
    elif t < 0: e = "vermutlich besser"
    elif any(v > 0 for k, v in d.items() if k not in WUNSCH): e = "schlechter?"
    elif ws > 0: e = "schlechter?"
    elif ws < 0 or d: e = "vermutlich besser"
    else: e = "gleichwertig"
    txt = ", ".join(f"{k} {alt.get(k, 0)}→{neu.get(k, 0)}" for k in sorted(d))
    if ws: txt += f" (Wunsch-Summe {'+' if ws > 0 else ''}{ws})"
    return e, txt


if SEITE or not NEU:
    html = open(SEITE).read() if SEITE else git("show", f"{REF}:ergebnisse/seite/index.html").decode()
else:
    html = git("show", f"{REF}:ergebnisse/seite/index.html").decode()
m_pl = re.search(r"const PLANS = (\[.*?\]);\n", html, re.S)
PLANS = json.loads(m_pl.group(1))
A = abnahmen(ABN)
# Von Daniel bestätigte Änderungen (7.11.2026: «Murten, Dulliken … sind ok»): neuere Basis als die Abnahme, keine Abnahme
_OKF = os.path.join(os.path.dirname(os.path.abspath(ABN)) if os.path.isfile(ABN) else ".", "regression_ok.json")
OK = {k: v for k, v in (json.load(open(_OKF)).items() if os.path.exists(_OKF) else []) if not k.startswith("_")}
zeilen = []
for p in PLANS:
    k = p["key"]; path = f"ergebnisse/seite/plaene/{k}.svg"
    if k == "pruefstand": continue     # Prüfstand (8.11.2026): eigener Vergleich gegen spurplan/pruefstand_basis.json im Workflow «pruefstand»
    log = [l.split() for l in git("log", REF, "--format=%h %cI", "--", path).decode().splitlines() if l.strip()]
    if not log: zeilen.append(dict(key=k, gruppe=p.get("gruppe"), basis="neu", stellen=None)); continue
    if k in OK and (k not in A or OK[k] > A[k]):
        t = datetime.datetime.fromisoformat(OK[k].replace("Z", "+00:00"))
        vor = [x for x in log if datetime.datetime.fromisoformat(x[1]) <= t]
        base, art = (vor[0], "bestätigt " + OK[k][:10]) if vor else (log[-1], "bestätigt " + OK[k][:10])
    elif k in A:
        t = datetime.datetime.fromisoformat(A[k].replace("Z", "+00:00"))
        vor = [x for x in log if datetime.datetime.fromisoformat(x[1]) <= t]
        base, art = (vor[0], "Abnahme " + A[k][:10]) if vor else (log[-1], "Archivbeginn (Abnahme " + A[k][:10] + ")")
    elif SEIT:
        vor = [x for x in log if subprocess.run(["git", "merge-base", "--is-ancestor", x[0], SEIT]).returncode == 0]
        base, art = (vor[0], "veröffentlicht") if vor else (log[-1], "erste Fassung")
    else:
        base, art = log[-1], "erste Fassung"
    alt = git("show", f"{base[0]}:{path}")
    if NEU:
        fn_ = os.path.join(NEU, f"{k}.svg"); neu = open(fn_, "rb").read() if os.path.exists(fn_) else b""
    else:
        neu = git("show", f"{REF}:{path}")
    z = dict(key=k, name=p.get("name"), gruppe=p.get("gruppe"), abgenommen=k in A, basis=art, basis_commit=base[0])
    if alt == neu:
        zeilen.append(dict(z, stellen=0)); continue
    fa, fn = os.path.join(OUT, f"{k}_alt.svg"), os.path.join(OUT, f"{k}_neu.svg")
    open(fa, "wb").write(alt); open(fn, "wb").write(neu)
    r = subprocess.run([sys.executable, os.path.join(HERE, "diff_bild.py"), fa, fn, os.path.join(OUT, f"{k}_diff.png"),
                        "--px", "1600"], capture_output=True, text=True)
    m = re.search(r"Differenzbild: (\d+)", r.stdout + r.stderr)
    ma, mn = messen(alt, k), messen(neu, k)
    v_neu = osa_zahlen(open(os.path.join(OSA, f"{k}.json")).read()) if OSA and os.path.exists(os.path.join(OSA, f"{k}.json")) else None
    v_alt = osa_zahlen(git("show", f"{base[0]}:ergebnisse/seite/osm_abgleich/{k}.json") or b"") if v_neu is not None else None
    if v_neu is not None and v_alt is not None: ma.update(v_alt); mn.update(v_neu)
    e, delta = einordnen(ma, mn)
    if v_neu is not None and v_alt is None: delta += (" · " if delta else "") + "OSM " + (", ".join(f"{r} {c}" for r, c in sorted(v_neu.items())) or "ok") + " (kein Alt-Stand)"
    zeilen.append(dict(z, stellen=int(m.group(1)) if m else -1, letzte_aenderung=log[0][1][:16],
                       einordnung=e, delta=delta, alt=ma, neu=mn))
    print(f"{k:28s} {art:32s} {zeilen[-1]['stellen']:>4} Stellen  {e}  {delta}")

# Wünsche je Plan (REGELN 5, 17.11.2026): Übersicht über alle Pläne, nicht nur geänderte – wo lohnt sich Verbesserung
wl = []
for p in PLANS:
    k = p["key"]
    if k in ("pruefstand", "fragen") or k.startswith("blaupause"): continue
    fn_ = os.path.join(NEU, f"{k}.svg") if NEU else None
    raw = open(fn_, "rb").read() if fn_ and os.path.exists(fn_) else git("show", f"{REF}:ergebnisse/seite/plaene/{k}.svg")
    if not raw: continue
    try:
        topo = None
        if k in _RT:
            r_ = open(_RT[k], "rb").read() if os.path.exists(_RT[k]) else git("show", f"{REF}:{_RT[k]}")
            topo = json.loads(r_) if r_ else None
        w_ = wuensche.messen(raw.decode("utf-8", "replace"), k, topo)
    except Exception as ex:
        print("Wünsche", k, ex, file=sys.stderr); continue
    wl.append(dict(key=k, gruppe=p.get("gruppe"), summe=wuensche.summe(w_), **w_))
wl.sort(key=lambda x: -x["summe"])
json.dump(wl, open(os.path.join(OUT, "wuensche.json"), "w"), ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "wuensche.md"), "w") as f:
    f.write("Wünsche je Plan (REGELN 5: W53 S-Kurven ×6, W55 Bahnhofsabstand ×3, W56 Leerlänge ×3; T7 im Vergleich ×8)\n\n"
            "| Plan | Gruppe | W53 | W55 | W56 | Summe |\n|---|---|---|---|---|---|\n")
    for x in wl:
        f.write(f"| {x['key']} | {x['gruppe']} | {x.get('W53', '')} | {x.get('W55', '')} | {x.get('W56', '')} | {x['summe']} |\n")

RANG = {"Fehler? Topologie": 0, "schlechter?": 1, "gleichwertig": 2, "vermutlich besser": 3}
gz = [z for z in zeilen if z.get("stellen")]
zus = collections.Counter(z["einordnung"] for z in gz)
json.dump(dict(erzeugt=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), plaene=len(zeilen), geaendert=len(gz),
               einordnung=dict(zus), zeilen=zeilen), open(os.path.join(OUT, "tabelle.json"), "w"), ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "tabelle.md"), "w") as f:
    f.write(f"{len(zeilen)} Pläne, {len(gz)} geändert: " + ", ".join(f"{v} {k}" for k, v in zus.items()) + "\n\n")
    f.write("| Plan | Gruppe | Basis | Stellen | Einordnung | Kennzahlen alt→neu | G0 | HT | letzte Änderung |\n|---|---|---|---|---|---|---|---|---|\n")
    for z in sorted(gz, key=lambda z: (RANG.get(z["einordnung"], 9), not z["abgenommen"], -z["stellen"])):
        f.write(f"| {z['key']} | {z['gruppe']} | {z['basis']} | {z['stellen']} | {z['einordnung']} | {z['delta']} | "
                f"{g0_spalte(z['key'])} | {ht_spalte(z['key'])} | {z.get('letzte_aenderung', '')} |\n")
    if GRUND and os.path.exists(os.path.join(GRUND, "grundpruefung.md")):
        f.write("\nGrundprüfung G0 aller Pläne: `ergebnisse/seite/grundpruefung/grundpruefung.md`\n")
    if HTD and os.path.exists(os.path.join(HTD, "hauptgleis.md")):
        f.write("Hauptgleis-Topologie HT aller Pläne mit Netzmodell: `ergebnisse/seite/hauptgleis/hauptgleis.md`\n")
print(f"Regression: {len(zeilen)} Pläne, {len(gz)} geändert", dict(zus))

if SEITE:   # Kartenlabel und Untertitel ergänzen
    by = {z["key"]: z for z in gz}
    for p in PLANS:
        z = by.get(p["key"])
        if z: p["label"] = (p.get("label") or "") + f" · Regression: {z['einordnung']} ({z['stellen']} Stellen gegen {z['basis']})"
    html = html[:m_pl.start(1)] + json.dumps(PLANS, ensure_ascii=False) + html[m_pl.end(1):]
    txt = f"Regression {len(gz)}/{len(zeilen)} geändert" + (" (" + ", ".join(f"{v} {k}" for k, v in zus.items()) + ")" if zus else "")
    html = re.sub(r'(<span class="sub">)(.*?)(</span>)', lambda m: m.group(1) + m.group(2) + " · " + txt + m.group(3), html, 1, re.S)
    open(SEITE, "w").write(html)
