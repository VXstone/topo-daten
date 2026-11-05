"""Suche für die Regionallage (Stufe C, 5.11.2026, D. Eckenstein: «möglichst weit automatisiert ruhige Pläne»).

Statt für jeden Haken eine neue Lageregel zu bauen, probiert der Code Varianten aus und behält die ruhigste. Massstab ist
der Unruhe-Wert (qualitaet.unruhe) der Regionalprüfungen, die von der Lage abhängen: Topologie im Regionalplan (T1–T8,
netz_lage --pruefen), Lage gegen die Karte (L2/L3, Grundsatz 2), Zeichenregeln (regel_pruefung G2–G8) und Ruhe im
Regionalplan (ruhe.py --region).
Die Bahnhofspläne selbst ändern sich nicht.

Stellschrauben (je Knotenbahnhof, d. h. automatisch auf 30° gedrehte Pläne):
  Drehung ±30°, ±60°, ±90°  (Lage «drehung», wird dabei fest); je Bahnhof die beste Variante (nicht die erste bessere)

  python3 lage_suche.py <NAME> [--max-sek 900] [--json lage_suche.json]     (im Arbeitsordner der Region)
Ergebnis: <NAME>_lage.json mit «drehung» der besten Variante (nur wenn besser als die Ausgangslage), Protokoll als JSON.
Konfig: Lage auto.suche false = aus; auto.suche_schritte (Standard [30, -30, 60, -60]).
"""
import json, os, sys, shutil, subprocess, time, tempfile, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import qualitaet as Q

NAME = sys.argv[1]
MAXS = float(sys.argv[sys.argv.index("--max-sek") + 1]) if "--max-sek" in sys.argv else 900.0
OUTJ = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else "lage_suche.json"
LF = f"{NAME}_lage.json"
L0 = json.load(open(LF))
AUTO = L0.get("auto") or {}
if AUTO.get("suche") is False:
    print("Lagesuche aus (auto.suche false)"); sys.exit(0)
SCHRITTE = AUTO.get("suche_schritte", [30, -30, 60, -60, 90, -90])
MINGEWINN = AUTO.get("suche_min", 6)      # Drehung nur bei spürbarem Gewinn (Vereina: Klosters für 2 Punkte gedreht)

# eigener Arbeitsordner: netz_lage schreibt Lage und Prüfdateien in den aktuellen Ordner
TMP = tempfile.mkdtemp(prefix="lage_suche_")
for f in os.listdir("."):
    if os.path.isfile(f) and not f.endswith((".png", ".gz")): shutil.copy(f, TMP)


def bewerten(drehung):
    """Unruhe des Regionalplans mit fester Drehung {Bahnhof: Grad} (übrige Pläne automatisch)."""
    L = json.loads(json.dumps(L0))
    L["drehung"] = {**L0.get("drehung", {}), **drehung}
    json.dump(L, open(os.path.join(TMP, LF), "w"), ensure_ascii=False, indent=1)
    r = subprocess.run(["python3", os.path.join(HERE, "netz_lage.py"), NAME, "Suche", "suche.svg", "--pruefen"],
                       cwd=TMP, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not os.path.exists(os.path.join(TMP, "suche.svg")): return None, {}
    k = collections.Counter()
    tr = os.path.join(TMP, "topologie_region.json")
    if os.path.exists(tr):
        for t in json.load(open(tr)): k[f"topo_{t['regel']}"] += 1
    lp = os.path.join(TMP, "lage_pruefung.json")                       # Grundsatz 2: Lage gegen die Karte
    if os.path.exists(lp):
        for t in json.load(open(lp)): k[f"lage_{t['regel']}"] += 1
    subprocess.run(["python3", os.path.join(HERE, "regel_pruefung.py"), "suche.svg", "--json", "suche_regeln.json"],
                   cwd=TMP, capture_output=True, text=True, timeout=600)
    rg = os.path.join(TMP, "suche_regeln.json")
    if os.path.exists(rg):
        for x in json.load(open(rg)): k[f"regel_{x.get('regel', '?')}"] += 1
    subprocess.run(["python3", os.path.join(HERE, "ruhe.py"), ".", "--region", "suche.svg", "--json", "suche_ruhe.json"],
                   cwd=TMP, capture_output=True, text=True, timeout=600)
    ru = os.path.join(TMP, "suche_ruhe.json")
    if os.path.exists(ru):
        for x in json.load(open(ru)):
            if x.get("plan") == "Regionalplan": k["ruhe_treppen" if x["art"] == "Treppe" else "ruhe_ecken"] += 1
    u, teile = Q.unruhe(dict(k))
    return u, dict(k)


t0 = time.time()
# Ausgangslage: Drehungen, die netz_lage automatisch gewählt hat (Knotenbahnhöfe sind auf 30° gerundet)
u0, k0 = bewerten({})
L_aus = json.load(open(os.path.join(TMP, LF)))
auto_ = L_aus.get("drehung_auto", {})
knoten = sorted(n for n, w in auto_.items() if abs(w / 30 - round(w / 30)) < 1e-6)
knoten = [n for n in knoten if n not in L0.get("drehung", {})]          # von Hand fest: nicht anfassen
best = {n: int(round(auto_[n])) for n in knoten}
best_u, best_k = u0, k0
proto = [dict(schritt="Ausgang", drehung=dict(best), unruhe=u0, kennzahlen=k0)]
print(f"Lagesuche {NAME}: Ausgang Unruhe {u0} {k0}; Knotenbahnhöfe {knoten}")
if u0 is None:
    print("Ausgangslage nicht bewertbar"); sys.exit(0)
besser = True; runde = 0
while besser and time.time() - t0 < MAXS and runde < 4:
    besser = False; runde += 1
    for n in knoten:
        if time.time() - t0 > MAXS: break
        kand = None
        for d in SCHRITTE:
            v = dict(best); v[n] = ((best[n] + d + 180) % 360) - 180
            u, k = bewerten(v)
            proto.append(dict(schritt=f"{n} {d:+d}", drehung={n: v[n]}, unruhe=u, kennzahlen=k))
            if u is not None and u <= best_u - MINGEWINN and (kand is None or u < kand[1]): kand = (v, u, k)
        if kand:
            print(f"  {n}: {best[n]} -> {kand[0][n]}  Unruhe {best_u} -> {kand[1]}")
            best, best_u, best_k = kand; besser = True
print(f"Lagesuche {NAME}: Unruhe {u0} -> {best_u} in {time.time() - t0:.0f} s, {len(proto)} Varianten")
erg = dict(ausgang=dict(unruhe=u0, kennzahlen=k0), ergebnis=dict(unruhe=best_u, kennzahlen=best_k),
           drehung={n: w for n, w in best.items() if w != int(round(auto_[n]))}, varianten=proto)
json.dump(erg, open(OUTJ, "w"), ensure_ascii=False, indent=1)
if best_u < u0:
    L = json.load(open(LF)); L["drehung"] = {**L.get("drehung", {}), **erg["drehung"]}
    L.setdefault("suche", {})["drehung"] = erg["drehung"]
    json.dump(L, open(LF, "w"), ensure_ascii=False, indent=1)
    print("Lage übernommen:", erg["drehung"])
shutil.rmtree(TMP, ignore_errors=True)
