"""Hinweis-Abdeckung (Schritt V1, 12.11.2026, D. Eckenstein «wir übersehen was»).

  python3 hinweis_abdeckung.py <hinweise.json> <plaene_dir> <befunde_dir> [--netz <dir>] [--radius 40]
          [--ohne G2] [--json out.json] [--md out.md]

Misst, wie viele offene Hinweise Daniels eine automatische Prüfung «sieht»: ein Hinweis gilt als abgedeckt, wenn im
selben Plan ein Befund näher als --radius px (Standard 40) liegt. Regeln in --ohne zählen nicht (Standard G2, die
Ausrundungsmeldung liegt an fast jeder Weiche und würde alles abdecken).

<hinweise.json>  offene Hinweise der Feedback-Seite (Sammlung «feedback», status offen): id, plan, bahnhof, lx, ly, x, y,
                 optional anker {id, dx, dy} (OSM-Knoten aus <key>_netz.json, so wandert der Pin mit dem Plan mit)
<plaene_dir>     <key>.svg wie auf der Seite (nur für die Liste der vorhandenen Pläne)
<befunde_dir>    ein oder mehrere Ordner (mit Komma): <key>.json je Plan, Liste {regel, x, y, ...} bzw. {"befunde": [...]}
                 in Plankoordinaten; alle Ordner zusammen zählen. --regel: regel_pruefung.py (G1–G8) auf den Plänen mit
                 Hinweisen dazurechnen; --messen: pruefstand_messen.py (Q/P/F/K/Z/E/X, Ebene aus dem Netzmodell).
Zuordnung Hinweis -> Plan: Bahnhofsplan, wenn es ihn gibt (Region MOB -> mob__<b>, Region Vereina -> vereina__<b>,
Region Olten -> <b>), mit lx/ly bzw. Anker; sonst der Plan des Hinweises mit x/y.
"""
import argparse, json, math, os, subprocess, sys, tempfile

ap = argparse.ArgumentParser()
ap.add_argument("hinweise"); ap.add_argument("plaene"); ap.add_argument("befunde")
ap.add_argument("--netz"); ap.add_argument("--radius", type=float, default=40.0)
ap.add_argument("--ohne", default="G2"); ap.add_argument("--json"); ap.add_argument("--md")
ap.add_argument("--regel", action="store_true"); ap.add_argument("--messen", action="store_true")
A = ap.parse_args()
OHNE = {r for r in A.ohne.split(",") if r}
KEYS = {f[:-4] for f in os.listdir(A.plaene) if f.endswith(".svg")}
PRAEFIX = {"region_mob": "mob__", "region_vereina": "vereina__", "region": "", "region_ne": ""}


def netz_knoten(key):
    for f in ([os.path.join(A.netz, f"{key}.json"), os.path.join(A.netz, f"{key}_netz.json")] if A.netz else []):
        if os.path.exists(f):
            return json.load(open(f)).get("knoten", {})
    return {}


def ort(h):
    """(plan_key, x, y) des Hinweises im Plan, in dem die Prüfungen rechnen"""
    b = h.get("bahnhof")
    if h["plan"] in PRAEFIX and b and h.get("lx") is not None:
        k = PRAEFIX[h["plan"]] + b if not b.startswith(PRAEFIX[h["plan"]] or "\0") else b
        if k in KEYS: return k, h["lx"], h["ly"]
    k = h["plan"]
    an = h.get("anker")
    if an:
        kn = netz_knoten(k).get(str(an["id"]))
        if kn and kn.get("y") is not None: return k, kn["x"] + an["dx"], kn["y"] + an["dy"]
    if h.get("lx") is not None and k not in PRAEFIX: return k, h["lx"], h["ly"]
    return k, h["x"], h["y"]


_RP = {}
def regelpruefung(key):
    if key not in _RP:
        _RP[key] = []
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "regel_pruefung.py"),
                            os.path.join(A.plaene, f"{key}.svg"), "--json", os.path.join(d, "r.json")], capture_output=True, timeout=300)
            try:
                r = json.load(open(os.path.join(d, "r.json"))); _RP[key] = r if isinstance(r, list) else r.get("befunde", [])
            except Exception: pass
    return _RP[key]


def ebene(key):
    """Gleisabstand in px aus dem Netzmodell (y je Ebene), sonst 24"""
    for f in ([os.path.join(A.netz, f"{key}.json")] if A.netz else []):
        if os.path.exists(f):
            P = sorted({(g["ebene"], g["y"]) for g in json.load(open(f)).get("gleise", []) if g.get("ebene") is not None and g.get("y") is not None})
            d = [(b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(P, P[1:]) if b[0] != a[0]]
            if d: return abs(sorted(d)[len(d) // 2])
    return 24.0


_PM = {}
def messen(key):
    if key not in _PM:
        _PM[key] = []
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pruefstand_messen.py"),
                            os.path.join(A.plaene, f"{key}.svg"), "--lane", f"{ebene(key):.2f}", "--json", os.path.join(d, "m.json")],
                           capture_output=True, timeout=300)
            try: _PM[key] = [dict(b, regel="M" + b["regel"]) for b in json.load(open(os.path.join(d, "m.json"))).get("befunde", [])]
            except Exception: pass
    return _PM[key]


def befunde(key):
    B = []
    for d in A.befunde.split(","):
        f = os.path.join(d, f"{key}.json")
        if not d or not os.path.exists(f): continue
        r = json.load(open(f)); B += r if isinstance(r, list) else r.get("befunde", [])
    if A.regel and key in KEYS: B += regelpruefung(key)
    if A.messen and key in KEYS: B += messen(key)
    return [b for b in B if b.get("regel") not in OHNE and b.get("x") is not None and b.get("y") is not None]


H = json.load(open(A.hinweise))
zeilen = []
for h in H:
    k, x, y = ort(h)
    B = befunde(k)
    best = min(B, key=lambda b: math.hypot(b["x"] - x, b["y"] - y), default=None)
    d = math.hypot(best["x"] - x, best["y"] - y) if best else None
    nah = sorted({b["regel"] for b in B if math.hypot(b["x"] - x, b["y"] - y) < A.radius})
    zeilen.append(dict(id=h["id"], plan=k, x=round(x, 1), y=round(y, 1), text=h.get("text", "")[:70],
                       abgedeckt=bool(nah), regeln=nah, naechster=round(d, 1) if d is not None else None,
                       naechste_regel=best["regel"] if best else None, plan_da=k in KEYS))
n = sum(z["abgedeckt"] for z in zeilen)
erg = dict(abgedeckt=n, offen=len(zeilen), radius=A.radius, ohne=sorted(OHNE), hinweise=zeilen)
print(f"Hinweis-Abdeckung: {n}/{len(zeilen)} (Befund < {A.radius:.0f} px, ohne {','.join(sorted(OHNE)) or '-'})")
for z in zeilen:
    print(f"{'✓' if z['abgedeckt'] else '·'} {z['id'][:4]} {z['plan']:<28} {','.join(z['regeln']) or '-':<22} "
          f"{z['naechster'] if z['naechster'] is not None else '-':>7}  {z['text']}")
if A.json: json.dump(erg, open(A.json, "w"), ensure_ascii=False, indent=1)
if A.md:
    with open(A.md, "w") as f:
        f.write(f"# Hinweis-Abdeckung {n}/{len(zeilen)}\n\nBefund < {A.radius:.0f} px im selben Plan, ohne {', '.join(sorted(OHNE))}.\n\n"
                "| | Hinweis | Plan | Regeln | nächster px | Text |\n|---|---|---|---|---|---|\n")
        for z in zeilen:
            f.write(f"| {'✓' if z['abgedeckt'] else '·'} | {z['id'][:4]} | {z['plan']} | {', '.join(z['regeln'])} | "
                    f"{z['naechster'] if z['naechster'] is not None else ''} | {z['text']} |\n")
