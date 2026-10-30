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

RAND = {}        # künstlicher Randknoten -> (innerer Knoten, äusserer Knoten), für die Fernpunkte
def kreis_runs(w, c, R, innen=None):
    """Teilstücke eines Ways im Kreis R um c (oder im Bereich innen(p)). Am Rand wird ein Punkt eingefügt (29.10.2026,
    Sagliains Nord: der 6,4 km lange Tunnel-Way hat im 400-m-Kreis nur seinen Endknoten und fiel ganz weg)."""
    runs, cur = [], []
    ns, gs = w["nodes"], w["geometry"]
    if innen is None: innen = lambda p_: math.dist(p_, c) <= R
    def rand(i, j):                       # Schnittpunkt der Strecke i→j mit dem Kreis (i innen, j aussen)
        a, b = xy(gs[i]), xy(gs[j]); lo, hi = 0.0, 1.0
        for _ in range(30):
            m = (lo + hi) / 2
            if innen((a[0] + m * (b[0] - a[0]), a[1] + m * (b[1] - a[1]))): lo = m
            else: hi = m
        g = dict(lat=gs[i]["lat"] + lo * (gs[j]["lat"] - gs[i]["lat"]), lon=gs[i]["lon"] + lo * (gs[j]["lon"] - gs[i]["lon"]))
        nid = -(abs(w["id"]) * 1000 + min(i, j) * 2 + (0 if i < j else 1)) - 10 ** 15
        RAND[nid] = (ns[i], ns[j]); return (nid, g)
    for i, (n, g) in enumerate(zip(ns, gs)):
        inn = innen(xy(g))
        if inn:
            if not cur and i > 0: cur.append(rand(i, i - 1))
            cur.append((n, g))
        elif cur:
            cur.append(rand(i - 1, i)); runs.append(cur); cur = []
    if cur: runs.append(cur)
    runs = [r for r in runs if len(r) > 2 or (len(r) == 2 and math.dist(xy(r[0][1]), xy(r[-1][1])) > 1.0)]   # geschlossene Perronflächen behalten
    # Verdichten: Randstücke über 40 m ohne Knoten (Tunnel) alle 25 m teilen, damit das Planfenster nicht an der Weiche schneidet
    out_ = []
    for ri, r in enumerate(runs):
        rr = [r[0]]
        for k_, ((n1, g1), (n2, g2)) in enumerate(zip(r, r[1:])):
            L_ = math.dist(xy(g1), xy(g2)); m_ = int(L_ // 25)
            _rand = lambda n_: -2 * 10 ** 15 < n_ < -10 ** 14
            if L_ > 40 and (_rand(n1) or _rand(n2)):      # nur das Stück am Kreisrand (sonst ändern sich Bahnhofspläne)
                for q in range(1, m_ + 1):
                    f_ = q / (m_ + 1)
                    rr.append((-3 * 10 ** 15 - (abs(w["id"]) * 100 + ri) * 10 ** 5 - k_ * 100 - q,
                               dict(lat=g1["lat"] + f_ * (g2["lat"] - g1["lat"]), lon=g1["lon"] + f_ * (g2["lon"] - g1["lon"]))))
            rr.append((n2, g2))
        out_.append(rr)
    return out_

def kreis(w, name, R):
    """Teil des Ways im Umkreis R um den Stationsknoten (ID wie cut.py)."""
    st = stations[name]; c = xy(st)
    runs = kreis_runs(w, c, R)
    out = []
    for k, r in enumerate(runs):
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
def _radius(st):
    name = st["tags"]["name"]
    return K.get("radius_je", {}).get(name, max(K.get("radius_dienst", 400), R_MIN.get(name, 0)) if name in dienst else K.get("radius", 700))   # Bahnhöfe: Radius unverändert (abgenommene Pläne)
_KR = [(st["id"], xy(st), _radius(st)) for st in betr]
# Bereiche (30.10.2026, Verkettung): überlappen sich zwei Kreise, gehört jeder Punkt nur zum nächsten Betriebspunkt
# (Grenze in der Mitte, «bp_voronoi_m» Zuschlag über die Mitte hinaus). Vorher lagen dieselben Gleise in zwei Plänen
# (Sasslatsch / Sagliains Sasslatsch, Sagliains / Autoverlad) und erschienen im Regionalplan doppelt oder als Pfeile.
# «bp_voronoi»: false = nur Kreise wie bisher.
# Grenze nicht in der Mitte zwischen den Betriebspunkten, sondern zwischen ihren äussersten Weichen (Betriebspunkt und alle
# Verzweigungen, die zu ihm gehören, sind die «Kerne» des Bereichs): so bleibt hinter jeder Weiche Platz für die
# abgehenden Gleise (Sagliains Sasslatsch: Nebengleis 46 m nach der Weiche abgeschnitten, fiel mit dem Streckengleis zusammen).
_VOR = K.get("bp_voronoi", True); _VTOL = K.get("bp_voronoi_m", 0)
import numpy as _np, collections
ntag_ = {e["id"]: e.get("tags", {}) for e in nodes}
_dg_all = collections.Counter(n for w in out_w if w["tags"].get("railway") == "rail" for a_, b_ in zip(w["nodes"], w["nodes"][1:]) for n in (a_, b_))
_npos = {n: xy(g) for w in out_w if w["tags"].get("railway") == "rail" for n, g in zip(w["nodes"], w["geometry"])}
_verzw = [n for n in _npos if _dg_all[n] >= 3 or ntag_.get(n, {}).get("railway") == "switch"]
_KERN = {i_: [c_] for i_, c_, R_ in _KR}
for n in _verzw:
    _cov = [(math.dist(_npos[n], c_), i_) for i_, c_, R_ in _KR if math.dist(_npos[n], c_) <= R_]
    if _cov: _KERN[min(_cov)[1]].append(_npos[n])
_KERN = {i_: _np.array(v_, float) for i_, v_ in _KERN.items()}
def _dk(p_, i_): return float(_np.min(_np.hypot(*(_KERN[i_] - _np.array(p_, float)).T)))
def _bereich(sid, c, R):
    andere = [(i2, c2, R2) for i2, c2, R2 in _KR if i2 != sid and math.dist(c, c2) < R + R2 + 200]
    if not _VOR or not andere: return lambda p_: math.dist(p_, c) <= R
    return lambda p_: math.dist(p_, c) <= R and all(_dk(p_, sid) <= _dk(p_, i2) + _VTOL for i2, c2, R2 in andere if math.dist(p_, c2) <= R2)
for st in betr:
    name = st["tags"]["name"]; key = slug(name); R = _radius(st)
    c = xy(st); el = []; innen_ = _bereich(st["id"], c, R)
    for e in out_n:
        if e["type"] == "node" and e["id"] in BPIDS:
            if e["id"] != st["id"]: continue
            e = dict(e); e["tags"] = dict(e["tags"], railway="station"); e["tags"].pop("public_transport", None)
            el.append(e); continue
        if innen_(xy(e)): el.append(e)
    sp_here = {w["tags"].get("spur", "1435") for w in out_w if w["tags"].get("railway") == "rail" and min(math.dist(xy(g), c) for g in w["geometry"]) < 100}   # 100 m: Betriebsstellenknoten liegen in OSM oft neben dem Gleis (Selfranga Süd 61 m)
    for w in out_w:
        if w["tags"].get("railway") == "rail" and w["tags"].get("spur", "1435") not in sp_here: continue   # nur die Spuren dieses Betriebspunkts (Belmont: keine SBB-Gleise)
        if w["tags"].get("railway") == "platform" or w["tags"].get("public_transport") == "platform":
            # Perron nur beim nächstgelegenen Betriebspunkt (29.10.2026: Perron 3/4 Sagliains lag im Kreis des Autoverlads)
            _pm = (sum(xy(g)[0] for g in w["geometry"]) / len(w["geometry"]), sum(xy(g)[1] for g in w["geometry"]) / len(w["geometry"]))
            if min(betr, key=lambda b_: math.dist(xy(b_), _pm))["id"] != st["id"]: continue
        _perron = w["tags"].get("railway") == "platform" or w["tags"].get("public_transport") == "platform"
        runs = kreis_runs(w, c, R, None if _perron else innen_)     # Perrons ganz (schon dem nächsten Betriebspunkt zugeteilt)
        for k, r in enumerate(runs):
            v = dict(w); v["id"] = w["id"] if k == 0 else w["id"] * 100 + k
            v["nodes"] = [n for n, _ in r]; v["geometry"] = [g for _, g in r]; el.append(v)
    json.dump({"elements": el}, open(os.path.join(OUT, f"{key}.json"), "w"))
    spuren = sorted({w["tags"].get("spur", "1435") for w in out_w if w["tags"].get("railway") == "rail"
                     and min(math.dist(xy(g), c) for g in w["geometry"]) < 100})
    BP[key] = dict(name=name, id=st["id"], lat=st["lat"], lon=st["lon"], radius=R, spuren=spuren,
                   weichen=sum(1 for e in out_n if e.get("tags", {}).get("railway") == "switch" and math.dist(xy(e), c) < min(R, 600)),
                   normalspur=name in K.get("normalspur", {}), dienst=name in dienst)
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
    for rid, (i_, o_) in RAND.items():    # künstliche Randknoten: Richtung innen → aussen
        if i_ in _GF and o_ in _GF[i_]: F[str(rid)] = {str(o_): _fern(i_, o_)}
    json.dump(F, open(os.path.join(OUT, f"{key}_fern.json"), "w"))
# Fernpunkte an den offenen Enden der Regionsdaten (30.10.2026, Abgang 915 West hiess «Landquart»: die Strecke nach
# Davos läuft zuerst nach Westen): je Endknoten eines Streckengleises, das in den vollständigen Daten weiterläuft, der
# erste Punkt 3 km Luftlinie weiter. topologie_linien.py peilt die Abgangsziele darauf.
_kept_ids = {w["id"] for w in out_w}
_deg_k = collections.Counter(n for w in out_w if w["tags"].get("railway") == "rail" for n in (w["nodes"][0], w["nodes"][-1]))
_mid_k = {n for w in out_w if w["tags"].get("railway") == "rail" for n in w["nodes"][1:-1]}
FE = {}
for w in out_w:
    if w["tags"].get("railway") != "rail" or w["tags"].get("service"): continue
    for n in (w["nodes"][0], w["nodes"][-1]):
        if _deg_k[n] != 1 or n in _mid_k: continue
        if n in RAND:                      # künstlicher Randpunkt (Kreis um einen Ast): innen -> aussen
            i_, o_ = RAND[n]
            if i_ in _GF and o_ in _GF[i_]: FE[str(n)] = _fern(i_, o_)
            continue
        if n not in _GF: continue
        drin = w["nodes"][1] if n == w["nodes"][0] else w["nodes"][-2]
        for m in _GF[n]:
            if m != drin and m in _PF: FE[str(n)] = _fern(n, m); break
json.dump(FE, open(os.path.join(OUT, "fern_enden.json"), "w")); print("Fernpunkte an Datenenden:", len(FE))
# Übersicht der Schmalspur-Linien im Ausschnitt (ref / Betreiber), damit neue Regionen die richtigen «linien» bekommen
import collections
_r = collections.Counter((w["tags"].get("ref", "-"), w["tags"].get("operator", "-"), w["tags"].get("name", "")[:30]) for w in ways if w["tags"].get("railway") in SCHMAL | {"rail"} and w["tags"].get("usage") in ("main", "branch", None))
print("Linien im Ausschnitt (ref, Betreiber, Name: Anzahl Ways):")
for (r_, o_, n_), c_ in sorted(_r.items(), key=lambda x: -x[1])[:25]: print(f"  {r_:8s} {o_:20s} {n_:30s} {c_}")
print(f"Region: {len(out_w)} Ways, {len(out_n)} Knoten, {len(BP)} Betriebspunkte")
for k, v in sorted(BP.items(), key=lambda x: x[1]["lon"]): print(f"  {k:28s} {v['name']:28s} Weichen {v['weichen']:2d} Spur {','.join(v['spuren'])}")
