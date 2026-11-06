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

Einordnung je geändertem Plan (Wunsch D. Eckenstein 6.11.: «vorschlagen, wo ein Plan verändert, aber vielleicht
verbessert wurde – ich schaue rasch drauf»). Gemessen wird nur auf den SVGs, alt gegen neu:
  topo  = Regelprüfung G5–G8 (Spurwechsel kreuzen, Knubbel, Gleis nicht angebunden, Gleise doppelt) – oberste Regel
  rest  = Regelprüfung G1–G4 (Nummern, Rundungen, Ecken, 90°) + Ruhe T7 (Treppen/Ecken)
  «Fehler? Topologie»  topo steigt                      -> zuerst ansehen, gilt als Fehler bis erklärt
  «schlechter?»        topo gleich/kleiner, rest steigt
  «vermutlich besser»  topo sinkt (Rest egal, Rangfolge), oder nichts steigt und mindestens eine Zahl sinkt
                       -> Daniel nickt ab oder widerspricht
  «gleichwertig»       alle Zahlen gleich (Lage, Perrons, Darstellung) -> Differenzbild erklären
Ausgabe: tabelle.json, tabelle.md und je Änderung <key>_diff.png (+ <key>_alt.svg, <key>_neu.svg).
Jede geänderte Zeile muss erklärt sein (gewollte Regel E9 oder Fehler) – sonst ist die Runde nicht fertig.
"""
import collections, datetime, glob, json, os, re, shutil, subprocess, sys, tempfile

ABN, OUT = sys.argv[1], sys.argv[2]
opt = lambda n: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else None
REF = opt("--ref") or "origin/ergebnisse"
SEIT, NEU, SEITE = opt("--seit"), opt("--neu"), opt("--seite")
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
TOPO = ("G5", "G6", "G7", "G8")


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
    return dict(z)


def einordnen(alt, neu):
    keys = set(alt) | set(neu)
    d = {k: neu.get(k, 0) - alt.get(k, 0) for k in keys if neu.get(k, 0) != alt.get(k, 0)}
    t = sum(d.get(k, 0) for k in TOPO)          # Rangfolge der Grundsätze: Topologie zuerst, dann der Rest
    if any(d.get(k, 0) > 0 for k in TOPO): e = "Fehler? Topologie"
    elif t < 0: e = "vermutlich besser"
    elif any(v > 0 for v in d.values()): e = "schlechter?"
    elif d: e = "vermutlich besser"
    else: e = "gleichwertig"
    return e, ", ".join(f"{k} {alt.get(k, 0)}→{neu.get(k, 0)}" for k in sorted(d))


if SEITE or not NEU:
    html = open(SEITE).read() if SEITE else git("show", f"{REF}:ergebnisse/seite/index.html").decode()
else:
    html = git("show", f"{REF}:ergebnisse/seite/index.html").decode()
m_pl = re.search(r"const PLANS = (\[.*?\]);\n", html, re.S)
PLANS = json.loads(m_pl.group(1))
A = abnahmen(ABN)
zeilen = []
for p in PLANS:
    k = p["key"]; path = f"ergebnisse/seite/plaene/{k}.svg"
    log = [l.split() for l in git("log", REF, "--format=%h %cI", "--", path).decode().splitlines() if l.strip()]
    if not log: zeilen.append(dict(key=k, gruppe=p.get("gruppe"), basis="neu", stellen=None)); continue
    if k in A:
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
    e, delta = einordnen(ma, mn)
    zeilen.append(dict(z, stellen=int(m.group(1)) if m else -1, letzte_aenderung=log[0][1][:16],
                       einordnung=e, delta=delta, alt=ma, neu=mn))
    print(f"{k:28s} {art:32s} {zeilen[-1]['stellen']:>4} Stellen  {e}  {delta}")

RANG = {"Fehler? Topologie": 0, "schlechter?": 1, "gleichwertig": 2, "vermutlich besser": 3}
gz = [z for z in zeilen if z.get("stellen")]
zus = collections.Counter(z["einordnung"] for z in gz)
json.dump(dict(erzeugt=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), plaene=len(zeilen), geaendert=len(gz),
               einordnung=dict(zus), zeilen=zeilen), open(os.path.join(OUT, "tabelle.json"), "w"), ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "tabelle.md"), "w") as f:
    f.write(f"{len(zeilen)} Pläne, {len(gz)} geändert: " + ", ".join(f"{v} {k}" for k, v in zus.items()) + "\n\n")
    f.write("| Plan | Gruppe | Basis | Stellen | Einordnung | Kennzahlen alt→neu | letzte Änderung |\n|---|---|---|---|---|---|---|\n")
    for z in sorted(gz, key=lambda z: (RANG.get(z["einordnung"], 9), not z["abgenommen"], -z["stellen"])):
        f.write(f"| {z['key']} | {z['gruppe']} | {z['basis']} | {z['stellen']} | {z['einordnung']} | {z['delta']} | "
                f"{z.get('letzte_aenderung', '')} |\n")
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
