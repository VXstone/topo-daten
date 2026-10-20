"""Gleisnummern je Betriebspunkt (Regeln D. Eckenstein 20.10.2026):
- Quelle SBB vor OSM: zuerst SBB-Perronkanten (aus/perronkanten.json, kundengleisnr je Kante, genaueste Quelle,
  D. Eckenstein 20.10. abends), dann SBB perronoberflache p_nr, sonst OSM-Perron ref
- nur Gleise mit Perron bekommen eine Nummer; Halt mit einem Gleis: keine Nummer
- stillgelegte Perrons (OSM disused) zählen nicht
- Perron ohne Nummer in allen Quellen -> "?" (im Plan Fragezeichen-Symbol, von Hand eintragen)

python3 gleisnummern.py <eingang> <betriebspunkte.json> <aus.json>
Verfahren wie gleisnummern_sbb.py (in Neuchâtel geprüft): Querschnitt der Gleise in der Perronmitte quer zur
Hauptrichtung (PCA der Hauptgleise ±400 m), Perrons quer eingeordnet; aussen liegende Perrons zuerst, je Gleis eine
Nummer; bei "a/b" bekommt das Gleis auf der Seite der kleineren bekannten Nummer die kleinere.
Ausgabe: {Betriebspunkt: {"querschnitt": [{"d", "way", "nr"}] (oben = links der Hauptrichtung West->Ost),
                          "perrons": [...], "quelle": "SBB"|"OSM"|null, "einzelgleis": bool}}
"""
import sys, json, gzip, math, collections
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from gemeinsam import lade_osm, lade_geojson, punkt, m, normalspur, name_gleich

def zuweisen(nr, ds, pl):
    if not ds: return
    einz = sorted([(p, d) for p, d in pl if len(p) == 1], key=lambda t: 0 if (t[1] > max(ds) or t[1] < min(ds)) else 1)
    for p, d in einz:
        if p[0] in nr: continue
        if d > max(ds): c = [0]
        elif d < min(ds): c = [len(ds) - 1]
        else: c = sorted(range(len(ds)), key=lambda i: abs(ds[i] - d))
        c = [i for i in c if nr[i] is None] or [i for i in sorted(range(len(ds)), key=lambda i: abs(ds[i] - d)) if nr[i] is None]
        if c: nr[c[0]] = p[0]
    for p, d in pl:
        if len(p) != 2: continue
        oben = sorted([i for i, x in enumerate(ds) if x > d], key=lambda i: ds[i] - d)
        unten = sorted([i for i, x in enumerate(ds) if x < d], key=lambda i: d - ds[i])
        if not (oben and unten): continue
        a_, b_ = sorted(p, key=lambda x: int(x) if x.isdigit() else 0)
        kl_oben = any(n is not None and n.isdigit() and a_.isdigit() and int(n) < int(a_) and i < oben[0] for i, n in enumerate(nr))
        if kl_oben: nr[oben[0]], nr[unten[0]] = a_, b_
        else: nr[unten[0]], nr[oben[0]] = a_, b_

if __name__ == "__main__":
    ein, bpf, aus = sys.argv[1:4]
    import os
    PK = collections.defaultdict(list)          # Perronkanten je Betriebspunkt-Name
    _pkf = os.path.join(os.path.dirname(aus) or ".", "perronkanten.json")
    if os.path.exists(_pkf):
        for k in json.load(open(_pkf)):
            if k.get("gleis") and k.get("mitte"): PK[k.get("bps") or ""].append(k)
    E = lade_osm(f"{ein}/schweiz_bahn.json.gz")
    BP = json.load(open(bpf))
    GL = [e for e in E if normalspur(e) and e["tags"].get("service") not in ("yard", "spur", "industrial")]
    idx = collections.defaultdict(list)
    for e in GL:
        for g in e["geometry"][::3] + e["geometry"][-1:]: idx[(round(g["lat"], 2), round(g["lon"], 2))].append(e)
    PL_OSM = collections.defaultdict(list); PL_WEG = collections.defaultdict(list)
    for e in E:
        t = e.get("tags", {})
        if e.get("type") != "way" or "geometry" not in e or not (t.get("railway") == "platform" or t.get("public_transport") == "platform"): continue
        q = (sum(g["lat"] for g in e["geometry"]) / len(e["geometry"]), sum(g["lon"] for g in e["geometry"]) / len(e["geometry"]))
        if t.get("disused") == "yes" or "disused:public_transport" in t:
            PL_WEG[(round(q[0], 2), round(q[1], 2))].append(q); continue
        PL_OSM[(round(q[0], 2), round(q[1], 2))].append((q, t.get("ref") or t.get("railway:track_ref") or t.get("local_ref")))
    SBB = collections.defaultdict(list)
    for f in lade_geojson(f"{ein}/perronoberflache.geojson"):
        p = f["properties"]; q = punkt(f.get("geometry"))
        if q and p.get("p_nr") and p.get("perrontyp") != "Dienstperron": SBB[p.get("bps_name")].append((q, p["p_nr"], p.get("perrontyp")))
    def nahe(tab, la, lo):
        return [x for dla in (-0.01, 0, 0.01) for dlo in (-0.01, 0, 0.01) for x in tab.get((round(la + dla, 2), round(lo + dlo, 2)), [])]
    R = {}
    for b in BP:
        la0, lo0 = b["lat"], b["lon"]; kx = 111320 * math.cos(math.radians(la0))
        xy = lambda la, lo: np.array([(lo - lo0) * kx, (la - la0) * 110540])
        ways = {e["id"]: e for e in nahe(idx, la0, lo0)}
        if not ways: continue
        hp = np.array([xy(g["lat"], g["lon"]) for e in ways.values() if not e["tags"].get("service") for g in e["geometry"]])
        hp = hp[np.hypot(*hp.T) < 400] if len(hp) else hp
        if len(hp) < 3: continue
        u = np.linalg.svd(hp - hp.mean(0))[2][0]
        if u[0] < 0: u = -u                                            # West -> Ost
        nrm = np.array([-u[1], u[0]])                                 # links = oben im Plan
        # Perrons: SBB vor OSM
        sb = next((v for k, v in SBB.items() if name_gleich(k, b["name"]) and v and m(v[0][0], (la0, lo0)) < 1200), None)
        # stillgelegt (OSM disused, kein aktiver OSM-Perron daneben): Perron zählt nicht (Onnens-Bonvillars, 20.10.)
        if sb:
            weg = nahe(PL_WEG, la0, lo0); akt = [q for q, _ in nahe(PL_OSM, la0, lo0)]
            weg7 = [w for w in weg if m(w, (la0, lo0)) < 700]; akt7 = [a for a in akt if m(a, (la0, lo0)) < 700]
            if weg7 and not akt7: sb = []                              # alle OSM-Perrons stillgelegt
            sb = [x for x in sb if not (any(m(x[0], w) < 40 for w in weg) and not any(m(x[0], a) < 40 for a in akt))]
        if sb and len({z for _, n_, _ in sb for z in str(n_).split("/")}) > 5:                                         # grosser Knoten: von Hand (sbb_perrons.py)
            R[b["name"]] = dict(querschnitt=[], quelle="SBB", gross=True, perrons=[dict(nr=n_) for _, n_, _ in sb]); continue
        # 1) SBB-Perronkanten: jede Kante gehört zum nächsten Gleis (Kante liegt ~1,7 m neben der Gleisachse)
        kanten = next((v for k_, v in PK.items() if name_gleich(k_, b["name"]) and m(tuple(v[0]["mitte"]), (la0, lo0)) < 1500), None)
        if kanten:      # stillgelegt (alle OSM-Perrons disused): keine Nummern (Onnens-Bonvillars)
            _w = [w for w in nahe(PL_WEG, la0, lo0) if m(w, (la0, lo0)) < 700]; _a = [q for q, _ in nahe(PL_OSM, la0, lo0) if m(q, (la0, lo0)) < 700]
            if _w and not _a: kanten = None
        if kanten and len({k_["gleis"] for k_ in kanten}) > 5:
            R[b["name"]] = dict(querschnitt=[], quelle="SBB-Kante", gross=True, perrons=[dict(nr=k_["gleis"]) for k_ in kanten]); continue
        if kanten:
            from shapely.geometry import LineString as _LS, Point as _Pt
            WL = {wid: _LS([xy(g["lat"], g["lon"]) for g in e["geometry"]]) for wid, e in ways.items() if len(e["geometry"]) > 1}
            way_nr = {}
            for k_ in kanten:
                pts_ = [xy(*k_[t_]) for t_ in ("anfang", "mitte", "ende")]
                best = None
                for wid, L_ in WL.items():
                    dd = float(np.mean([L_.distance(_Pt(p_)) for p_ in pts_]))
                    if dd < 6 and (best is None or dd < best[0]): best = (dd, wid)
                if best: way_nr.setdefault(best[1], set()).add(str(k_["gleis"]))
            sm = [xy(*k_["mitte"]) @ u for k_ in kanten]; S0 = float(np.median(sm))
            prof = []
            for e in ways.values():
                pts = [xy(g["lat"], g["lon"]) for g in e["geometry"]]
                for a, c in zip(pts, pts[1:]):
                    sa, sc = a @ u, c @ u
                    if (sa - S0) * (sc - S0) <= 0 and sa != sc:
                        t_ = (S0 - sa) / (sc - sa); d = float((a + (c - a) * t_) @ nrm)
                        if abs(d) < 80: prof.append((d, e["id"]))
            prof.sort(key=lambda t: -t[0]); Q = []
            for d, w in prof:
                if Q and abs(Q[-1]["d"] - d) < 2.5: continue
                Q.append(dict(d=round(d, 1), way=w, nr=None))
            # Kante, deren Gleis nicht im Querschnitt liegt (anderer Way): nächstes Gleis quer zur Kante
            for k_ in kanten:
                if any(str(k_["gleis"]) in way_nr.get(q["way"], ()) for q in Q): continue
                dk = float(xy(*k_["mitte"]) @ nrm)
                c = [q for q in Q if abs(q["d"] - dk) < 4.5 and q["way"] not in way_nr]
                if c: way_nr.setdefault(min(c, key=lambda q: abs(q["d"] - dk))["way"], set()).add(str(k_["gleis"]))
            for q in Q:
                n_ = sorted(way_nr.get(q["way"], ()), key=lambda x: (len(x), x))
                q["nr"] = n_[0] if n_ else None
            if Q and any(q["nr"] for q in Q):       # sonst: weiter mit Perronflächen/OSM
                if len(Q) == 1:
                    for q in Q: q["nr"] = None
                R[b["name"]] = dict(querschnitt=Q, quelle="SBB-Kante", einzelgleis=len(Q) == 1,
                                    perrons=[dict(nr=k_["gleis"], laenge=k_.get("laenge")) for k_ in kanten])
                continue
        quelle = "SBB" if sb else None
        pl = [(q, nr_) for q, nr_, _ in sb] if sb else [(q, r) for q, r in nahe(PL_OSM, la0, lo0) if m(q, (la0, lo0)) < 700]
        if not sb and pl: quelle = "OSM"
        if not pl: continue
        P = [(xy(*q) @ u, xy(*q) @ nrm, nr_) for q, nr_ in pl]
        S0 = float(np.median([p[0] for p in P]))
        prof = []
        for e in ways.values():
            pts = [xy(g["lat"], g["lon"]) for g in e["geometry"]]
            for a, c in zip(pts, pts[1:]):
                sa, sc = a @ u, c @ u
                if (sa - S0) * (sc - S0) <= 0 and sa != sc:
                    t_ = (S0 - sa) / (sc - sa); d = float((a + (c - a) * t_) @ nrm)
                    if abs(d) < 80: prof.append((d, e["id"]))
        prof.sort(key=lambda t: -t[0]); Q = []
        for d, w in prof:
            if Q and abs(Q[-1]["d"] - d) < 2.5: continue
            Q.append(dict(d=round(d, 1), way=w, nr=None))
        if not Q: continue
        ds = [q["d"] for q in Q]; nr = [None] * len(Q)
        zuweisen(nr, ds, [(str(n_).replace(";", "/").split("/"), d) for s_, d, n_ in P if n_])
        # Perron ohne Nummer: angrenzendes Gleis "?"
        for s_, d, n_ in P:
            if n_: continue
            i = min(range(len(ds)), key=lambda i: abs(ds[i] - d))
            if nr[i] is None: nr[i] = "?"
        for q, n_ in zip(Q, nr): q["nr"] = n_
        mit = [q for q in Q if q["nr"]]
        einzel = len(Q) == 1 or len(mit) <= 1 and len(Q) == 1
        if len(Q) == 1:
            for q in Q: q["nr"] = None
        R[b["name"]] = dict(querschnitt=Q, quelle=quelle, einzelgleis=len(Q) == 1,
                            perrons=[dict(nr=n_, d=round(d, 1), s=round(s_ - S0)) for s_, d, n_ in P])
    json.dump(R, open(aus, "w"), ensure_ascii=False, indent=0)
    print(len(R), "Betriebspunkte;", sum(1 for r in R.values() if r.get("quelle") == "SBB-Kante"), "aus Perronkanten;", sum(1 for r in R.values() if any(q["nr"] == "?" for q in r["querschnitt"])), "mit offenen Nummern (?)")
