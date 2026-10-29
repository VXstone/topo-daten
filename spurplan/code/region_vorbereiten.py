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
# Betriebspunkte (29.10.2026, Vereina): nicht nur station/halt, sondern jede benannte Betriebsstelle aus OSM
# (Kreuzungs-/Abzweigstellen, Autoverlad, Bahnhofsteile). Gleiche railway:ref = ein Betriebspunkt. Punkte ohne Weiche
# fallen weg (Blockstellen), ausser Personenhalte. Netz: Hauptgleisweichen fern jedes Betriebspunkts werden gemeldet
# und als «?»-Betriebspunkt gezeichnet, damit keine Weiche still verschwindet.
BP_TYP = K.get("bp_typen", ["station", "halt", "yard", "junction", "spur_junction", "crossover", "service_station", "car_shuttle", "site"])
RANG = {t_: i for i, t_ in enumerate(BP_TYP)}
sw_nodes = [e for e in nodes if e.get("tags", {}).get("railway") == "switch" and e["id"] in used]
def n_weichen(e, R=250): return sum(1 for q in sw_nodes if math.dist(xy(q), xy(e)) < R)
kand = [e for e in nodes if e.get("tags", {}).get("railway") in BP_TYP and e["tags"].get("name")]
gruppen = {}
for e in sorted(kand, key=lambda e: RANG[e["tags"]["railway"]]):
    t = e["tags"]; key_ = t.get("railway:ref")
    if not key_:                                   # ohne Abkürzung: zum Punkt gleichen Namens oder zum nächsten bis 150 m
        nah_ = [k_ for k_, g_ in gruppen.items() if g_[0]["tags"]["name"] == t["name"] or math.dist(xy(g_[0]), xy(e)) < 150]
        key_ = nah_[0] if nah_ else f"_{e['id']}"
    gruppen.setdefault(key_, []).append(e)
betr, dienst = [], set()
for key_, g_ in gruppen.items():
    st = g_[0]; name = st["tags"]["name"]; typ = st["tags"]["railway"]
    if any(x in name for x in weg) or name in K.get("integriert", {}): continue      # integriert: Halt liegt im Plan des Nachbarbahnhofs (Regel R14)
    pv = any(e["tags"]["railway"] in ("station", "halt") for e in g_)
    if min((Point(xy(st)).distance(g) for g in G), default=1e9) > (40 if pv else 80): continue
    if not pv and n_weichen(st) == 0: print(f"  ohne Weiche, kein Plan: {name} ({typ})"); continue
    stations[name] = st; betr.append(st)
    if not pv: dienst.add(name)
# Netz: jede Weiche auf einem Streckengleis der Linien gehört zu einem Betriebspunkt. Bis «weiche_bp_m» (1000 m) wird sie
# dem nächsten zugeschlagen (dessen Radius wächst bis zur Weiche + 150 m, Kreuzungsschleifen im Vereinatunnel, Weichenkopf
# Selfranga); weiter weg entsteht ein «?»-Betriebspunkt, der im Log gemeldet wird.
haupt_n = {n for w in keep if w["tags"].get("ref") in LIN and not w["tags"].get("service") for n in w["nodes"]}
R_MIN = {}
frei = []
for q in sw_nodes:
    if q["id"] not in haupt_n or not betr: continue
    b_ = min(betr, key=lambda b: math.dist(xy(q), xy(b))); d_ = math.dist(xy(q), xy(b_))
    if d_ <= K.get("weiche_bp_m", 1000): R_MIN[b_["tags"]["name"]] = max(R_MIN.get(b_["tags"]["name"], 0), d_ + 150)
    else: frei.append(q)
cl = []
for q in frei:
    c_ = next((c_ for c_ in cl if any(math.dist(xy(q), xy(r_)) < 300 for r_ in c_)), None)
    (c_.append(q) if c_ else cl.append([q]))
for i, c_ in enumerate(cl):
    la = sum(q["lat"] for q in c_) / len(c_); lo = sum(q["lon"] for q in c_) / len(c_)
    nm = f"? Weichen {i + 1}"
    print(f"  Hauptgleisweichen ohne Betriebspunkt: {len(c_)} bei {la:.5f},{lo:.5f} -> «{nm}»")
    st = dict(type="node", id=-(i + 1), lat=la, lon=lo, tags=dict(railway="junction", name=nm))
    stations[nm] = st; betr.append(st); dienst.add(nm); nodes.append(st)
    R_MIN[nm] = max(math.dist(xy(q), xy(st)) for q in c_) + 150
BPIDS = {b["id"] for b in betr}
out_n = [e for e in nodes if e["id"] in used and e.get("tags", {}).get("railway") not in BP_TYP] + betr
json.dump({"elements": out_n + out_w}, open(os.path.join(OUT, "region.json"), "w"))
# Rohausschnitt (alle Elemente im Rahmen, alle Tags) für lokale Fehlersuche: region_lauf.py --daten roh.json.gz
with gzip.open(os.path.join(OUT, "roh.json.gz"), "wt") as f_: json.dump({"elements": [e for e in D if (e["type"] == "node" and inbox(e)) or (e["type"] == "way" and "geometry" in e and any(inbox(g) for g in e["geometry"]))]}, f_)
# je Betriebspunkt: Kreis, nur der eigene Stationsknoten
BP = {}
for st in betr:
    name = st["tags"]["name"]; key = slug(name); R = K.get("radius_je", {}).get(name, max(K.get("radius_dienst", 400), R_MIN.get(name, 0)) if name in dienst else K.get("radius", 700))   # Bahnhöfe: Radius unverändert (abgenommene Pläne)
    c = xy(st); el = []
    for e in out_n:
        if e["type"] == "node" and e["id"] in BPIDS:
            if e["id"] != st["id"]: continue
            e = dict(e); e["tags"] = dict(e["tags"], railway="station"); e["tags"].pop("public_transport", None)
        if math.dist(xy(e), c) <= R: el.append(e)
    sp_here = {w["tags"].get("spur", "1435") for w in out_w if w["tags"].get("railway") == "rail" and min(math.dist(xy(g), c) for g in w["geometry"]) < 100}   # 100 m: Betriebsstellenknoten liegen in OSM oft neben dem Gleis (Selfranga Süd 61 m)
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
                     and min(math.dist(xy(g), c) for g in w["geometry"]) < 100})
    BP[key] = dict(name=name, id=st["id"], lat=st["lat"], lon=st["lon"], radius=R, spuren=spuren,
                   weichen=sum(1 for e in out_n if e.get("tags", {}).get("railway") == "switch" and math.dist(xy(e), c) < min(R, 600)),
                   normalspur=name in K.get("normalspur", {}))
json.dump(BP, open(os.path.join(OUT, "betriebspunkte.json"), "w"), ensure_ascii=False, indent=1)
# Fernpunkte für Abgangsziele (29.10.2026, Klosters: 910 und 915 verlassen den Bahnhof in Schleifen, die Peilung am
# Planrand zeigt nach Westen). Aus den vollständigen Daten (nicht dem gekürzten Ausschnitt): je Knoten im Ausschnitt
# eines Betriebspunkts und je Nachbar der erste Punkt 3 km Luftlinie weiter auf dem Streckengleis (gleiche Linie, möglichst gerade).
# spurplan_schema.py peilt mit <slug>_fern.json auf diesen Punkt.
import networkx as _nx
_GF = _nx.Graph(); _PF = {}; _RF = {}
for w in D:
    if w["type"] != "way" or "geometry" not in w or w["tags"].get("railway") not in SCHMAL | {"rail"} or w["tags"].get("service"): continue
    for n, g in zip(w["nodes"], w["geometry"]): _PF[n] = xy(g)
    for a_, b_ in zip(w["nodes"], w["nodes"][1:]): _GF.add_edge(a_, b_); _RF[(a_, b_)] = _RF[(b_, a_)] = w["tags"].get("ref")
def _fern(n0, n1, R_=3000.0, L=15000.0):
    """Weiter auf der Strecke, bis 3 km Luftlinie erreicht sind (Kehren: Klosters–Cavadürli), höchstens 15 km Gleis."""
    prev, cur, d = n0, n1, math.dist(_PF[n0], _PF[n1]); r0 = _RF.get((n0, n1))
    while d < L and math.dist(_PF[cur], _PF[n0]) < R_:
        nx_ = [m for m in _GF[cur] if m != prev]
        if not nx_: break
        h0 = math.atan2(_PF[cur][1] - _PF[prev][1], _PF[cur][0] - _PF[prev][0])
        m = min(nx_, key=lambda m: (_RF.get((cur, m)) != r0, abs((math.atan2(_PF[m][1] - _PF[cur][1], _PF[m][0] - _PF[cur][0]) - h0 + math.pi) % (2 * math.pi) - math.pi)))
        d += math.dist(_PF[cur], _PF[m]); prev, cur = cur, m
    x_, y_ = _PF[cur]
    return [S + y_ / KY, W + x_ / KX]
for key, b in BP.items():
    c = xy(b); F = {}
    for n in _GF:
        if math.dist(_PF[n], c) <= b["radius"]: F[str(n)] = {str(m): _fern(n, m) for m in _GF[n]}
    json.dump(F, open(os.path.join(OUT, f"{key}_fern.json"), "w"))
# Übersicht der Schmalspur-Linien im Ausschnitt (ref / Betreiber), damit neue Regionen die richtigen «linien» bekommen
import collections
_r = collections.Counter((w["tags"].get("ref", "-"), w["tags"].get("operator", "-"), w["tags"].get("name", "")[:30]) for w in ways if w["tags"].get("railway") in SCHMAL | {"rail"} and w["tags"].get("usage") in ("main", "branch", None))
print("Linien im Ausschnitt (ref, Betreiber, Name: Anzahl Ways):")
for (r_, o_, n_), c_ in sorted(_r.items(), key=lambda x: -x[1])[:25]: print(f"  {r_:8s} {o_:20s} {n_:30s} {c_}")
print(f"Region: {len(out_w)} Ways, {len(out_n)} Knoten, {len(BP)} Betriebspunkte")
for k, v in sorted(BP.items(), key=lambda x: x[1]["lon"]): print(f"  {k:28s} {v['name']:28s} Weichen {v['weichen']:2d} Spur {','.join(v['spuren'])}")
