"""Region für Spur- und Regionalpläne aus der Schweiz-Datei vorbereiten (auch Schmal- und 800-mm-Spur).

  python3 region_vorbereiten.py <schweiz_bahn.json.gz> <konfig.json> <ausgabeordner>

Konfig (Beispiel spurplan/regionen/mob/region.json):
  bbox            [S, W, N, E]
  linien          Schmalspur-Linien (ref), die ganz gezeichnet werden; dazu alle Nebengleise derselben Betreiber
  betreiber       Betreiber dieser Linien (Nebengleise ohne ref)
  aeste           {"Bahnhof": m} – andere Schmalspurlinien nur in diesem Umkreis um den Bahnhof (Abzweig angedeutet)
  normalspur      {"Bahnhof": m} – Normalspur nur in diesem Umkreis (Spurplan dort mit --hauptgleise)
  radius          Standard-Ausschnitt je Betriebspunkt (m), "radius_je" {Bahnhof: m}
  integriert      {"Halt": "Bahnhof"} – kein eigener Plan, liegt im Spurplan des Bahnhofs (R14)
  weg_namen       Teilstrings von Stationsnamen, die nicht gezeichnet werden (z. B. "(funi)")

Schmalspur wird für die Skripte als railway=rail / gauge=1435 geführt, die echte Spurweite steht im Tag "spur"
(Zeichnung braun). Ausgabe: region.json (alle Elemente der Region), <slug>.json je Betriebspunkt (Kreis, nur der
eigene Stationsknoten als railway=station), betriebspunkte.json.
"""
import gzip, json, math, os, re, sys, unicodedata
from shapely.geometry import LineString, Point

SRC, KONF, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
K = json.load(open(KONF))
os.makedirs(OUT, exist_ok=True)
S, W, N, E = K["bbox"]
D = json.load(gzip.open(SRC) if SRC.endswith(".gz") else open(SRC))
D = D["elements"] if "elements" in D else D
LAT0 = (S + N) / 2; KX = 111320 * math.cos(math.radians(LAT0)); KY = 110540
xy = lambda g: ((g["lon"] - W) * KX, (g["lat"] - S) * KY)
inbox = lambda g: S <= g["lat"] <= N and W <= g["lon"] <= E
SCHMAL = {"narrow_gauge"}
def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

ways = [e for e in D if e["type"] == "way" and "geometry" in e and any(inbox(g) for g in e["geometry"])]
nodes = [e for e in D if e["type"] == "node" and inbox(e)]
stations = {e["tags"]["name"]: e for e in nodes if e.get("tags", {}).get("railway") in ("station", "halt") and e["tags"].get("name")}

def kreis(w, name, R):
    """Teil des Ways im Umkreis R um den Stationsknoten (ID wie cut.py)."""
    st = stations[name]; c = xy(st)
    runs, cur = [], []
    for n, g in zip(w["nodes"], w["geometry"]):
        if math.dist(xy(g), c) <= R: cur.append((n, g))
        elif cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    out = []
    for k, r in enumerate(runs):
        if len(r) < 2: continue
        v = dict(w); v["id"] = w["id"] if k == 0 else w["id"] * 100 + k
        v["nodes"] = [n for n, _ in r]; v["geometry"] = [g for _, g in r]; out.append(v)
    return out

keep = []
LIN, BET = set(K["linien"]), set(K.get("betreiber", []))
haupt = [w for w in ways if w["tags"].get("railway") in SCHMAL and w["tags"].get("ref") in LIN]
H = [LineString([xy(g) for g in w["geometry"]]) for w in haupt]
def nah(w, m):
    L = LineString([xy(g) for g in w["geometry"]]) if len(w["geometry"]) > 1 else Point(xy(w["geometry"][0]))
    return any(L.distance(h) < m for h in H)
for w in ways:
    t = w["tags"]; rw = t.get("railway")
    if rw in SCHMAL:
        if t.get("ref") in LIN or (t.get("operator") in BET and not t.get("ref")) or (not t.get("operator") and not t.get("ref") and nah(w, 60)):
            keep.append(w); continue
        for st_, R in K.get("aeste", {}).items(): keep += kreis(w, st_, R)
    elif rw == "rail":
        for st_, R in K.get("normalspur", {}).items(): keep += kreis(w, st_, R)
    elif rw == "platform" or t.get("public_transport") == "platform":
        keep.append(w)
# Perrons nur an gezeichneten Gleisen
G = [LineString([xy(g) for g in w["geometry"]]) for w in keep if w["tags"].get("railway") in SCHMAL | {"rail"} and len(w["geometry"]) > 1]
def an_gleis(w, m=25):
    L = LineString([xy(g) for g in w["geometry"]]) if len(w["geometry"]) > 1 else Point(xy(w["geometry"][0]))
    return any(L.distance(g) < m for g in G)
keep = [w for w in keep if (w["tags"].get("railway") not in ("platform",) and w["tags"].get("public_transport") != "platform") or an_gleis(w)]
# Schmalspur für die Skripte als Normalspur führen, echte Spurweite in "spur"
out_w = []
for w in keep:
    w = dict(w); t = dict(w["tags"])
    if t.get("railway") in SCHMAL:
        t["spur"] = t.get("gauge", "1000"); t["railway"] = "rail"; t["gauge"] = "1435"
    elif t.get("railway") == "rail" and t.get("gauge", "1435") != "1435":
        t["spur"] = t["gauge"]; t["gauge"] = "1435"          # 1000;1435 (Dreischienengleis) zählt als Normalspur
    w["tags"] = t; out_w.append(w)
used = {n for w in out_w for n in w["nodes"]}
weg = K.get("weg_namen", [])
betr = []
for name, st in stations.items():
    if any(x in name for x in weg) or name in K.get("integriert", {}): continue      # integriert: Halt liegt im Plan des Nachbarbahnhofs (Regel R14)
    if min((Point(xy(st)).distance(g) for g in G), default=1e9) > 40: continue
    betr.append(st)
out_n = [e for e in nodes if e["id"] in used and e.get("tags", {}).get("railway") not in ("station", "halt")] + betr
json.dump({"elements": out_n + out_w}, open(os.path.join(OUT, "region.json"), "w"))
# je Betriebspunkt: Kreis, nur der eigene Stationsknoten
BP = {}
for st in betr:
    name = st["tags"]["name"]; key = slug(name); R = K.get("radius_je", {}).get(name, K.get("radius", 700))
    c = xy(st); el = []
    for e in out_n:
        if e["type"] == "node" and e.get("tags", {}).get("railway") in ("station", "halt"):
            if e["id"] != st["id"]: continue
            e = dict(e); e["tags"] = dict(e["tags"], railway="station"); e["tags"].pop("public_transport", None)
        if math.dist(xy(e), c) <= R: el.append(e)
    sp_here = {w["tags"].get("spur", "1435") for w in out_w if w["tags"].get("railway") == "rail" and min(math.dist(xy(g), c) for g in w["geometry"]) < 60}
    for w in out_w:
        if w["tags"].get("railway") == "rail" and w["tags"].get("spur", "1435") not in sp_here: continue   # nur die Spuren dieses Betriebspunkts (Belmont: keine SBB-Gleise)
        runs, cur = [], []
        for n, g in zip(w["nodes"], w["geometry"]):
            if math.dist(xy(g), c) <= R: cur.append((n, g))
            elif cur: runs.append(cur); cur = []
        if cur: runs.append(cur)
        for k, r in enumerate(runs):
            if len(r) < 2: continue
            v = dict(w); v["id"] = w["id"] if k == 0 else w["id"] * 100 + k
            v["nodes"] = [n for n, _ in r]; v["geometry"] = [g for _, g in r]; el.append(v)
    json.dump({"elements": el}, open(os.path.join(OUT, f"{key}.json"), "w"))
    spuren = sorted({w["tags"].get("spur", "1435") for w in out_w if w["tags"].get("railway") == "rail"
                     and min(math.dist(xy(g), c) for g in w["geometry"]) < 60})
    BP[key] = dict(name=name, id=st["id"], lat=st["lat"], lon=st["lon"], radius=R, spuren=spuren,
                   weichen=sum(1 for e in out_n if e.get("tags", {}).get("railway") == "switch" and math.dist(xy(e), c) < 250),
                   normalspur=name in K.get("normalspur", {}))
json.dump(BP, open(os.path.join(OUT, "betriebspunkte.json"), "w"), ensure_ascii=False, indent=1)
# Übersicht der Schmalspur-Linien im Ausschnitt (ref / Betreiber), damit neue Regionen die richtigen «linien» bekommen
import collections
_r = collections.Counter((w["tags"].get("ref", "-"), w["tags"].get("operator", "-"), w["tags"].get("name", "")[:30]) for w in ways if w["tags"].get("railway") in SCHMAL | {"rail"} and w["tags"].get("usage") in ("main", "branch", None))
print("Linien im Ausschnitt (ref, Betreiber, Name: Anzahl Ways):")
for (r_, o_, n_), c_ in sorted(_r.items(), key=lambda x: -x[1])[:25]: print(f"  {r_:8s} {o_:20s} {n_:30s} {c_}")
print(f"Region: {len(out_w)} Ways, {len(out_n)} Knoten, {len(BP)} Betriebspunkte")
for k, v in sorted(BP.items(), key=lambda x: x[1]["lon"]): print(f"  {k:28s} {v['name']:28s} Weichen {v['weichen']:2d} Spur {','.join(v['spuren'])}")
