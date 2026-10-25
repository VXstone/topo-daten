"""Prüfungen auf dem Netzmodell (D. Eckenstein 25.10.2026: «Gleise als Netz mit Koordinaten»).

  python3 netz_pruefung.py <bahnhof>          liest <bahnhof>_netz.json (spurplan_schema) und <bahnhof>.json (OSM)

Jeder Befund nennt die Regel-ID aus dem Regelkatalog (Doc «Regelwerk Spurpläne», Tab Regelkatalog), Plankoordinaten
und die OSM-Elemente. Ausgabe: <bahnhof>_netz_befunde.json und eine Zusammenfassung auf stdout.

Regeln (v1):
  T10  Durchfahrgleis grün: Gleis, das an beiden Enden über Weichen ohne Richtungswechsel ins Streckengleis führt,
       ist im Personenverkehr befahrbar (Ausnahme service=yard), sofern zwischen den Anschlüssen mindestens
       200 m Nebengleis liegen und das Gleis selbst mindestens 100 m lang ist oder eine Gleisnummer hat (sonst
       Verbindungsstück/Spurwechsel, schwarz nach E1); gezeichnet schwarz = Befund
  A5   Perron neben seinem Gleis: kein Gleis läuft durch das Perron
  D11  Gleisnummer nur an Perrongleisen: jede gezeichnete Nummer hat ein Perron daneben
  D12  Perrons vollständig: jede Gleisnummer mit Perron in OSM/SBB ist gezeichnet (Zählung)
  S1   Weichen sichtbar: jede OSM-Weiche im Planfenster liegt auf einem gezeichneten Gleis
  D6   Stillgelegtes nicht zeichnen
  Z2   Abgang mit Linie und Richtungsort
"""
import json, math, sys, collections

B = sys.argv[1]
N = json.load(open(f"{B}_netz.json"))
_raw = json.load(open(f"{B}.json"))
if isinstance(_raw, dict) and "elements" not in _raw:
    _raw = _raw.get(B) or next(iter(_raw.values()))
OSM = _raw["elements"] if isinstance(_raw, dict) else _raw

BEF = []
def bef(regel, x, y, text, **osm):
    BEF.append(dict(regel=regel, x=round(x, 1) if x is not None else None, y=round(y, 1) if y is not None else None,
                    text=text, **osm))

KN = N["knoten"]
LAT0 = sum(v["lat"] for v in KN.values()) / max(1, len(KN))
KX, KY = 111320 * math.cos(math.radians(LAT0)), 110540
m_xy = lambda lat, lon: (lon * KX, lat * KY)

# ---- OSM-Graph (Normalspur und Schmalspur, ohne Stillgelegtes)
WAYS = {e["id"]: e for e in OSM if e["type"] == "way" and e.get("tags", {}).get("railway") in ("rail", "narrow_gauge")
        and not e["tags"].get("disused")}
P = {}
NB = collections.defaultdict(set)
WAY_OF_EDGE = {}
for w in WAYS.values():
    for n, g in zip(w["nodes"], w["geometry"]): P[n] = m_xy(g["lat"], g["lon"])
    for a, b in zip(w["nodes"], w["nodes"][1:]):
        NB[a].add(b); NB[b].add(a); WAY_OF_EDGE[(a, b)] = WAY_OF_EDGE[(b, a)] = w["id"]
haupt = lambda wid: WAYS[wid]["tags"].get("service") is None

def winkel(a, b, c):
    """Richtungsänderung in Grad beim Weg a→b→c"""
    v1 = (P[b][0] - P[a][0], P[b][1] - P[a][1]); v2 = (P[c][0] - P[b][0], P[c][1] - P[b][1])
    l1, l2 = math.hypot(*v1), math.hypot(*v2)
    if l1 < 1e-6 or l2 < 1e-6: return 0.0
    return math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)))))

def weg_zum_haupt(prev, cur, max_m=1500, max_dreh=40):
    """Fährt ab (prev→cur) ohne Richtungswechsel weiter; Länge auf Nebengleisen bis zum ersten Hauptgleis (ohne
    service), None wenn keines erreichbar"""
    import heapq
    seen = set(); hq = [(0.0, prev, cur)]
    while hq:
        d, a, b = heapq.heappop(hq)
        if (a, b) in seen or d > max_m: continue
        seen.add((a, b))
        if haupt(WAY_OF_EDGE[(a, b)]): return d
        for c in NB[b]:
            if c != a and winkel(a, b, c) < max_dreh:
                heapq.heappush(hq, (d + math.dist(P[b], P[c]), b, c))
    return None
laenge = lambda ns: sum(math.dist(P[a], P[b]) for a, b in zip(ns, ns[1:]))
MIN_DURCHFAHRT_M = 200      # Nebengleis zwischen den beiden Hauptgleis-Anschlüssen: Platz für einen Zug (sonst Spurwechsel, E1)

# ---- T10 Durchfahrgleis
gl_way = collections.defaultdict(list)
for g in N["gleise"]: gl_way[g["way"]].append(g)
def plan_mitte(way):
    pts = [(KN[str(n)]["x"], KN[str(n)]["y"]) for g in gl_way.get(way, []) for n in g["knoten"]
           if str(n) in KN and KN[str(n)]["y"] is not None]
    if not pts: return None, None
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

durchfahr = set()
for wid, w in WAYS.items():
    sv = w["tags"].get("service")
    if sv not in ("siding", "spur", "crossover") or len(w["nodes"]) < 2: continue
    ns = w["nodes"]
    if laenge(ns) < 100 and not w["tags"].get("railway:track_ref"): continue   # kurzes Verbindungsstück ohne Gleisnummer = Spurwechsel
    # Gleis als Ganzes: von beiden Enden aus, jeweils vom Gleis weg, muss ein Hauptgleis erreichbar sein
    da = weg_zum_haupt(ns[1], ns[0]); db = weg_zum_haupt(ns[-2], ns[-1])
    if da is not None and db is not None and sv != "crossover" and da + db + laenge(ns) >= MIN_DURCHFAHRT_M:
        durchfahr.add(wid)
        if wid in gl_way and not any(g["pax"] for g in gl_way[wid]):
            x, y = plan_mitte(wid)
            bef("T10", x, y, f"Durchfahrgleis (beidseitig ans Streckengleis angeschlossen, {da + db + laenge(ns):.0f} m Nebengleis, service={sv}) schwarz gezeichnet",
                way=wid, gleis=w["tags"].get("railway:track_ref"))

# ---- D6 Stillgelegtes
for g in N["gleise"]:
    if g.get("stillgelegt"):
        x, y = plan_mitte(g["way"]); bef("D6", x, y, "stillgelegtes Gleis gezeichnet", way=g["way"])

# ---- Perrons, Nummern (A5, D11, D12)
lanes = sorted({g["y"] for g in N["gleise"] if g["y"] is not None})
def gleis_an(y_, x0, x1, tol):
    """gezeichnete Gleise (Ebenen), die im x-Bereich auf Höhe y_ ± tol liegen"""
    r = []
    for g in N["gleise"]:
        if g["y"] is None: continue
        xs = [KN[str(n)]["x"] for n in g["knoten"] if str(n) in KN]
        if not xs or max(xs) < x0 or min(xs) > x1: continue
        if abs(g["y"] - y_) <= tol: r.append(g)
    return r
for p in N["perrons"]:
    durch = gleis_an(p["y"], p["x0"] + 5, p["x1"] - 5, 3.5)
    if durch:
        bef("A5", (p["x0"] + p["x1"]) / 2, p["y"], "Gleis läuft durch das Perron", way=durch[0]["way"])
for t in N["nummern"]:
    ok = any(p["x0"] - 40 <= t["x"] <= p["x1"] + 40 and 6 <= abs(p["y"] - t["y"]) <= 16 for p in N["perrons"])
    if not ok:
        bef("D11", t["x"], t["y"], f"Gleisnummer {t['text']} ohne Perron daneben (Perron fehlt oder Nummer zu viel)")
_osm_refs = sorted({r for p in N["perrons_osm"] for r in str(p.get("ref") or "").replace(",", ";").split(";") if r})
_num = sorted({t["text"] for t in N["nummern"]})
if len(N["perrons"]) < len(_num) / 2:
    bef("D12", None, None, f"{len(N['perrons'])} Perron(s) gezeichnet für {len(_num)} Gleisnummern {_num}; "
        f"OSM-Perrons: {len(N['perrons_osm'])} (ref {_osm_refs or '–'}) – SBB-Perrondaten nachladen (B13)")
for r in _osm_refs:
    if r not in _num: bef("D11", None, None, f"OSM-Perron ref {r} hat keine gleichnamige Gleisnummer im Plan")

# ---- S1 Weichen sichtbar
_auf_haupt = {n for w in WAYS.values() if w["tags"].get("service") is None for n in w["nodes"]}
fehl = [w for w in N["weichen_osm"] if not w["im_plan"] and w["id"] in _auf_haupt]     # Grundsatz 3: Weichen ab Hauptgleis
for w in fehl:
    bef("S1", None, None, "OSM-Weiche an einem Hauptgleis im Planfenster liegt auf keinem gezeichneten Gleis", node=w["id"],
        lat=round(w["lat"], 6), lon=round(w["lon"], 6))

# ---- Z2 Abgänge
for a in N["abgaenge"]:
    if a.get("pax") and not a.get("town"):
        bef("Z2", a.get("x"), a.get("y"), f"Abgang Linie {a.get('ref') or '?'} ohne Richtungsort", way=a.get("way"))

json.dump(dict(bahnhof=B, befunde=BEF, durchfahrgleise=sorted(durchfahr)), open(f"{B}_netz_befunde.json", "w"),
          ensure_ascii=False, indent=1)
z = collections.Counter(b["regel"] for b in BEF)
print(f"Netzprüfung {B}: {dict(sorted(z.items())) or 'keine Befunde'}; Durchfahrgleise {len(durchfahr)}")
for b in BEF:
    print(f"  {b['regel']:4} x={b['x']} y={b['y']}  {b['text']}" + (f"  (way {b['way']})" if b.get("way") else "")
          + (f"  (node {b['node']})" if b.get("node") else ""))
