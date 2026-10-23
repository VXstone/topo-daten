"""Planrand-Prüfung (Regel D. Eckenstein 20.10. abends): Streckengleise enden am Planrand immer im Doppelspurabstand
(eine Ebene, 24 px), Gleise verschiedener Linien im doppelten Abstand (48 px).

python3 planrand_pruefung.py [ordner] [--lane 24]
Liest alle <bahnhof>_ports.json (Anschlüsse am Längsrand, kind=edge) und meldet benachbarte Abgänge derselben Seite,
deren Abstand nicht passt.
"""
import sys, json, glob, os, collections
d = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
LANE = float(sys.argv[sys.argv.index("--lane") + 1]) if "--lane" in sys.argv else 24.0
n = 0
for f in sorted(glob.glob(os.path.join(d, "*_ports.json"))):
    try: P = json.load(open(f))["ports"]
    except Exception: continue
    st = os.path.basename(f)[:-11]
    S = collections.defaultdict(list)
    for p in P:
        if p.get("kind") == "edge": S[(p["dx"], round(p["x"]))].append(p)
    for (dx, x), ps in S.items():
        ps.sort(key=lambda p: p["y"])
        for a, b in zip(ps, ps[1:]):
            dy = round(b["y"] - a["y"], 1)
            soll = LANE if a.get("ref") == b.get("ref") else 2 * LANE
            if abs(dy - soll) > 0.6 and not (a.get("ref") != b.get("ref") and abs(dy - LANE) <= 0.6):
                n += 1
                print(f"{st}\t{'rechts' if dx > 0 else 'links'} x{x}\tLinie {a.get('ref')}/{b.get('ref')}: Abstand {dy:g} px statt {soll:g}")
print(f"Planrand: {n} Befunde", file=sys.stderr)
