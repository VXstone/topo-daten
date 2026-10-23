"""Gleisnummern für Vorlage-Bahnhöfe aus SBB Open Data (perronoberflache: p_nr = Kundengleisnummer am Perron).
Regelprüfung G1 (D. Eckenstein 19.10.: "alle Bhf mit Gleis-Nr").

python3 gleisnummern_sbb.py <bahnhof> ["<bps_name>"] [--schreiben]
Ablauf: Querschnitt der Gleise in der Bahnhofsmitte wie typ_vorschlag.py (oben = links der Fahrrichtung), jeder SBB-Perron
(Punkt) wird quer zur Achse eingeordnet. Haus-/Aussenperron: Nummer an das nächste Gleis; "a/b": Gleise ober- und unterhalb
(näheres Gleis zuerst nach Abstand); Dienstperron zählt nicht. Ergebnis = Override vorlage.gleise (von oben nach unten).
"""
import json, gzip, math, sys
import typ_vorschlag as T

SBB = "/tmp/claude-0/sbb/po.geojson.gz"

def zuweisen(nr, ds, pl):
    """Perron (Nummern, Querlage d) -> Gleise (ds, oben zuerst). Aussen liegende Perrons zuerst (eindeutig), jedes Gleis
    nur eine Nummer; bei a/b bekommt das Gleis auf der Seite der kleineren bekannten Nummern die kleinere (Grandson 1 | 2 | 3)."""
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

def nummern(key, bps=None):
    v = T.vorschlag(key); q = v["_osm"]["querschnitt"]          # [(d, nr, service, haupt)], oben zuerst
    E, PO = T.lade(key)
    st = next(e for e in E if e["type"] == "node" and e.get("tags", {}).get("railway") == "station")
    lat0, lon0 = st["lat"], st["lon"]; kx = 111320 * math.cos(math.radians(lat0))
    xy = lambda la, lo: ((lo - lon0) * kx, (la - lat0) * 110540)
    ports = [p for p in PO["ports"] if p["kind"] == "edge"]
    L = [p for p in ports if p["dx"] < 0]; R = [p for p in ports if p["dx"] > 0]
    if L and R:
        a = xy(sum(p["lat"] for p in L) / len(L), sum(p["lon"] for p in L) / len(L))
        b = xy(sum(p["lat"] for p in R) / len(R), sum(p["lon"] for p in R) / len(R))
    else: a, b = (-1, 0), (1, 0)
    u = (b[0] - a[0], b[1] - a[1]); nu = math.hypot(*u); u = (u[0] / nu, u[1] / nu); nrm = (-u[1], u[0])
    proj = lambda p: (p[0] * u[0] + p[1] * u[1], p[0] * nrm[0] + p[1] * nrm[1])
    name = bps or PO.get("title") or st["tags"].get("name")
    name = {"Cressier": "Cressier NE", "Saint-Blaise CFF": "St-Blaise CFF", "Gorgier-Saint-Aubin": "Gorgier-St-Aubin",
            "Bôle": "Bole", "Couvet": "Couvet CFF", "Muntelier-Löwenberg": "Muntelier-Lowenberg", "Cornaux": "Cornaux NE",
            "Colombier": "Colombier NE", "Serrières": "Neuchatel-Serrieres", "Champ du Moulin": "Champ-du-Moulin"}.get(name, name)
    F0 = [f for f in json.load(gzip.open(SBB))["features"] if f["properties"].get("bps_name") == name]
    # mehrere Flächen desselben Perrons (Grandson 2/3, La Neuveville): zusammenfassen, Mittel der Querlage
    grp = {}
    for f in F0:
        p = f["properties"]; g = f["geometry"]["coordinates"]
        while isinstance(g[0], list): g = g[0]
        grp.setdefault((p.get("p_nr"), p.get("perrontyp")), []).append((g[0], g[1]))
    F = [dict(properties=dict(p_nr=k[0], perrontyp=k[1]), geometry=dict(coordinates=[sum(a for a, b in v) / len(v), sum(b for a, b in v) / len(v)]))
         for k, v in grp.items()]
    ds = [t[0] for t in q]
    nr = [None] * len(q); info = []
    pl = []
    for f in F:
        p = f["properties"]
        if p.get("perrontyp") == "Dienstperron" or not p.get("p_nr"): continue
        g = f["geometry"]["coordinates"]
        while isinstance(g[0], list): g = g[0]
        s_, d_ = proj(xy(g[1], g[0]))
        if abs(s_) > 700: continue
        pl.append((p["p_nr"].split("/"), d_)); info.append((p["p_nr"], p["perrontyp"], round(d_, 1)))
    zuweisen(nr, ds, pl)
    # Ersatz, wo SBB nichts hat (BLS/TPF-Bahnhöfe): OSM-Perron mit ref (Kante = Gleisnummer)
    if not any(nr):
        pl = []
        for e in E:
            tg = e.get("tags", {})
            if e["type"] != "way" or not (tg.get("railway") == "platform" or tg.get("public_transport") == "platform"): continue
            ref = tg.get("ref") or tg.get("railway:track_ref") or tg.get("local_ref")
            if not ref or "disused:public_transport" in tg: continue
            pts = [proj(xy(g["lat"], g["lon"])) for g in e["geometry"]]
            s_ = sum(p[0] for p in pts) / len(pts); d_ = sum(p[1] for p in pts) / len(pts)
            if abs(s_) > 700: continue
            pl.append(([x.strip() for x in ref.replace(";", "/").split("/")], d_)); info.append(("OSM " + ref, None, round(d_, 1)))
        zuweisen(nr, ds, pl)
    return nr, q, info, name

if __name__ == "__main__":
    key = sys.argv[1]; bps = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    nr, q, info, name = nummern(key, bps)
    print(key, name, "Querschnitt", [t[0] for t in q], "SBB", info, "->", nr)
    if "--schreiben" in sys.argv:
        f = f"{key}_override.json"; o = json.load(open(f))
        vg = o.get("vorlage", {}).get("gleise")
        if vg is not None and len(vg) == len(nr) and any(nr):
            o["vorlage"]["gleise"] = [n or g for n, g in zip(nr, vg)]
            o["_gleisnummern"] = "SBB Open Data perronoberflache (gleisnummern_sbb.py, 19.10.2026)"
            json.dump(o, open(f, "w"), ensure_ascii=False, indent=1); print("geschrieben", o["vorlage"]["gleise"])
        else: print("nicht geschrieben: Gleiszahl Vorlage", vg, "Querschnitt", len(nr))
