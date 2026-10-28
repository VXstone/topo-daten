"""Region Olten im Repo bauen (26.10.2026, «Olten zügeln»): Bahnhofspläne + Regionalplan aus spurplan/werkstatt/olten.

  python3 spurplan/code/region_olten_lauf.py [--konfig werkstatt/<ordner>/region_<x>.json] [--bericht pfad.json]

Standard-Konfig: werkstatt/olten/region_olten.json. Neuchâtel (26.10.): werkstatt/ne/region_ne.json (Ausgabe in
werkstatt/olten/feedback/region_ne.svg, dort liest bauen.py die Regionalpläne).

Arbeitet in einer Kopie der Werkstatt (/tmp/region_olten); aller Code (spurplan_schema, -warp, netz_pruefung,
netz_lage, lage_auto) kommt aus code/. Je Bahnhof aus werkstatt/olten/region_olten.json die ganze Kette wie run.sh
(schema --nowarp → warp → schema → warp → schema → --bare), dann Netzprüfung, dann
netz_lage.py olten_region "Region Olten" feedback/region.svg (+ --pruefen, + region_geometrie.py). Die neuen Dateien (Plan, bare, ports,
warp, region.svg) werden in die Werkstatt zurückgeschrieben, damit bauen.py (Workflow seite) sie verwendet.
Der Bericht nennt je Bahnhof, ob sich Plan/bare gegenüber dem Stand im Repo geändert haben, und die Netzbefunde.
"""
import json, os, shutil, subprocess, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
KONF = os.path.abspath(sys.argv[sys.argv.index("--konfig") + 1]) if "--konfig" in sys.argv else os.path.join(SP, "werkstatt", "olten", "region_olten.json")
WS = os.path.dirname(KONF); TMP = "/tmp/" + os.path.splitext(os.path.basename(KONF))[0]
K = json.load(open(KONF))
BER = sys.argv[sys.argv.index("--bericht") + 1] if "--bericht" in sys.argv else None
OSM = sys.argv[sys.argv.index("--osm") + 1] if "--osm" in sys.argv else None     # schweiz_bahn.json.gz (Release «daten»)

shutil.rmtree(TMP, ignore_errors=True); shutil.copytree(WS, TMP)
# Code nur aus code/ (26.10.2026: eine Fassung für alle Regionen, die Werkstatt-Kopien sind gelöscht)
for f in ("spurplan_schema.py", "spurplan_warp.py", "spurplan_check.py", "netz_pruefung.py", "netz_lage.py", "lage_auto.py",
          "vorlage.py", "viewbox_text.py", "qualitaet.py"):
    shutil.copy(os.path.join(HERE, f), TMP)
py = sys.executable
def sh(args, timeout=900, cwd=None):
    r = subprocess.run([py] + args, cwd=cwd or TMP, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")
lesen = lambda p: open(p, "rb").read() if os.path.exists(p) else None

bericht = dict(bahnhoefe={}, varianten={}, region={}, osm={})
# OSM-Ausschnitte aus dem Release (26.10.2026): Konfig «osm_bbox» {bahnhof: [Süd, West, Nord, Ost]} wie Overpass/Colab.
# Ohne --osm (oder ohne Eintrag) bleibt der Ausschnitt aus der Werkstatt. Der neue Ausschnitt wird auch in die
# Werkstatt geschrieben, damit lokale Läufe denselben Stand haben.
if OSM and K.get("osm_bbox"):
    sys.path.insert(0, os.path.join(os.path.dirname(SP), "skripte"))
    import gzip, ausschnitt as AU
    _ch = json.load(gzip.open(OSM)); _ch = _ch["elements"] if isinstance(_ch, dict) else _ch
    _ch = [e for e in _ch if AU.wie_colab(e)]
    for b, (s_, w_, n_, e_) in K["osm_bbox"].items():
        el = [x for x in _ch if (x["type"] == "node" and s_ <= x["lat"] <= n_ and w_ <= x["lon"] <= e_)
              or (x["type"] == "way" and AU.schneidet(x.get("geometry", []), s_, w_, n_, e_))]
        neu = json.dumps({"elements": el}, ensure_ascii=False)
        alt_ = lesen(os.path.join(WS, f"{b}.json"))
        bericht["osm"][b] = dict(elemente=len(el), geaendert=alt_ is None or json.loads(alt_) != json.loads(neu))
        for d_ in (TMP, WS): open(os.path.join(d_, f"{b}.json"), "w").write(neu)
    print("OSM aus Release:", json.dumps(bericht["osm"], ensure_ascii=False))
# Bahnhöfe aus dem Workflow «plaene» (27.10.2026, Vauseyon in Region NE): bare.svg und ports.json aus ergebnisse/<b>/
# (lokal) bzw. vom Branch «ergebnisse»; werden auch in die Werkstatt geschrieben
for b in K.get("repo_bahnhoefe", []):
    for f, ziel in (("bare.svg", f"{b}_bare.svg"), ("ports.json", f"{b}_ports.json")):
        q = os.path.join(os.path.dirname(SP), "ergebnisse", b, f); inh = lesen(q)
        if inh is None:
            r_ = subprocess.run(["git", "show", f"origin/ergebnisse:ergebnisse/{b}/{f}"], capture_output=True, cwd=SP)
            inh = r_.stdout if r_.returncode == 0 else None
        if inh:
            for d_ in (TMP, WS): open(os.path.join(d_, ziel), "wb").write(inh)
    bericht.setdefault("repo", {})[b] = os.path.exists(os.path.join(TMP, f"{b}_ports.json"))
def kette(b, opt, cwd=None):
    """ganze Kette wie run.sh; gibt (rc, letzte Ausgabe) zurück"""
    w = os.path.join(cwd or TMP, f"{b}_warp.json")
    if os.path.exists(w): os.remove(w)
    for a in (["spurplan_schema.py", "--src", f"{b}.json", "--nowarp"] + opt, ["spurplan_warp.py", b],
              ["spurplan_schema.py", "--src", f"{b}.json"] + opt, ["spurplan_warp.py", b],
              ["spurplan_schema.py", "--src", f"{b}.json"] + opt,
              ["spurplan_schema.py", "--src", f"{b}.json", "--bare", "--out", f"{b}_bare.svg"] + opt):
        rc, o = sh(a, cwd=cwd)
        if rc: return rc, o[-800:]
    return 0, ""

# Varianten in Unterordnern (26.10.2026, «Olten zügeln» Teil 2): Olten Ost, Regionalvarianten Olten Ost und Rothrist.
# Gebaut im eigenen Ordner mit dem Code aus code/; «nach_oben» kopiert Ergebnisse in die Werkstatt-Ebene, wo
# netz_lage.py sie liest (z. B. olten_ost_bare.svg -> olten_ost_regional_bare.svg). Der Ordner ist die Quelle.
for v in K.get("varianten", []):
    d_ = os.path.join(TMP, v["ordner"]); b = v["bahnhof"]
    for f in ("spurplan_schema.py", "spurplan_warp.py", "spurplan_check.py"):
        shutil.copy(os.path.join(HERE, f), d_)
    alt = {f: lesen(os.path.join(d_, f)) for f in v["nach_oben"]}
    rc, o = kette(b, v.get("optionen", []), cwd=d_)
    _topo = None
    if not rc:          # Grundregeln auch für Varianten prüfen (27.10., Kerzers: alle Weichen ab Hauptgleis gezeichnet?)
        import re as _re
        _o3 = sh(["spurplan_check.py", "--src", f"{b}.json"] + v.get("optionen", []), cwd=d_)[1]
        _m = _re.search(r"Befunde: (\{.*\})", _o3); _topo = _m.group(1) if _m else _o3[-300:]
    for n_ in v.get("nachlauf", []):          # z. B. kreuzungsbahnhof.py (Kerzers 27.10.): Plan für den Regionalplan umzeichnen
        if rc: break
        shutil.copy(os.path.join(HERE, n_), d_); rc, o = sh([n_, b], cwd=d_); print(o.strip()[-300:])
    e = dict(ok=rc == 0, ordner=v["ordner"], topologie=_topo)
    if rc: e["fehler"] = o
    else:
        e["geaendert"] = sorted(f for f in v["nach_oben"] if lesen(os.path.join(d_, f)) != alt[f])
        for f in os.listdir(d_):
            if f.startswith(b + "_") and f.endswith((".svg", ".json")) and not f.endswith("_override.json"):
                shutil.copy(os.path.join(d_, f), os.path.join(WS, v["ordner"], f))
        for f, ziel in list(v["nach_oben"].items()) + list(v.get("override_oben", {}).items()):
            shutil.copy(os.path.join(d_, f), os.path.join(TMP, ziel)); shutil.copy(os.path.join(d_, f), os.path.join(WS, ziel))
    bericht["varianten"][v["ordner"]] = e
    print("Variante", json.dumps(e, ensure_ascii=False))

for b, opt in K["bahnhoefe"].items():
    alt = {k: lesen(os.path.join(TMP, f"{b}_{k}")) for k in ("spurplan.svg", "bare.svg")}
    rc, o = kette(b, opt)
    e = dict(ok=rc == 0, optionen=opt)
    if rc: e["fehler"] = o
    else:
        e["plan_geaendert"] = lesen(os.path.join(TMP, f"{b}_spurplan.svg")) != alt["spurplan.svg"]
        e["bare_geaendert"] = lesen(os.path.join(TMP, f"{b}_bare.svg")) != alt["bare.svg"]
        rc2, o2 = sh(["netz_pruefung.py", b])
        nb = os.path.join(TMP, f"{b}_netz_befunde.json")
        e["netz"] = dict(collections.Counter(x["regel"] for x in json.load(open(nb))["befunde"])) if os.path.exists(nb) else o2[-300:]
        rc3, o3 = sh(["spurplan_check.py", "--src", f"{b}.json"] + opt)       # Kennzahlen (27.10.): Topologie + Netz + Geometrie
        import re as _re
        _m = _re.search(r"Befunde: (\{.*\})", o3); e["topologie"] = _m.group(1) if _m else None
        sh(["qualitaet.py", "messen", b, "--check", e["topologie"] or "{}"])
        _qj = os.path.join(TMP, f"{b}_qualitaet.json")
        if os.path.exists(_qj): e["qualitaet"] = json.load(open(_qj))
        for k in ("spurplan.svg", "bare.svg", "ports.json", "warp.json", "netz.json", "netz_befunde.json"):
            src = os.path.join(TMP, f"{b}_{k}")
            if os.path.exists(src): shutil.copy(src, os.path.join(WS, f"{b}_{k}"))
    bericht["bahnhoefe"][b] = e
    print(b, json.dumps(e, ensure_ascii=False))

R = K["region"]
ZIEL = os.path.normpath(os.path.join(WS, R["ausgabe"]))
alt_r = lesen(ZIEL)
rc, o = sh(["netz_lage.py", R["name"], R["titel"], "_region_neu.svg"])
bericht["region"] = dict(ok=rc == 0, log=o[-1500:])
if rc == 0:
    bericht["region"]["geaendert"] = lesen(os.path.join(TMP, "_region_neu.svg")) != alt_r
    shutil.copy(os.path.join(TMP, "_region_neu.svg"), ZIEL)
    rc, o = sh(["netz_lage.py", R["name"], R["titel"], "/tmp/region_olten_pruef.svg", "--pruefen"])
    bericht["region"]["pruefung"] = o[-3000:]
    r_ = subprocess.run([py, os.path.join(HERE, "region_geometrie.py"), ZIEL, "--json", "/tmp/region_geometrie.json"],
                        capture_output=True, text=True)        # A1 Achsabstand, W6 Einmündung (26.10.)
    print(r_.stdout[-1500:]); bericht["region"]["geometrie"] = (json.load(open("/tmp/region_geometrie.json"))
                                                                if r_.returncode == 0 else r_.stderr[-500:])
print(R["titel"] + ":", json.dumps({k: v for k, v in bericht["region"].items() if k != "pruefung" and k != "log"}, ensure_ascii=False))
# Kennzahlen gegen die Basis (27.10.)
sys.path.insert(0, HERE); import qualitaet as _Q
_mess = {b: e["qualitaet"] for b, e in bericht["bahnhoefe"].items() if isinstance(e.get("qualitaet"), dict)}
bericht["qualitaet_messung"] = _mess
bericht["qualitaet"] = _Q.vergleichen(_mess, json.load(open(_Q.BASIS)) if os.path.exists(_Q.BASIS) else {})
print("Kennzahlen gegen die Basis:")
for b, e in bericht["qualitaet"].items(): print(f"  {b:22} {e['status']}", e.get("schlechter") or "", e.get("besser") or "", ("| Topologie offen: " + str(e["topologie_offen"])) if e.get("topologie_offen") else "")
if BER: json.dump(bericht, open(BER, "w"), ensure_ascii=False, indent=1)
