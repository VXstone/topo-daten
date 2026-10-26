"""Region Olten im Repo bauen (26.10.2026, «Olten zügeln»): Bahnhofspläne + Regionalplan aus spurplan/werkstatt/olten.

  python3 spurplan/code/region_olten_lauf.py [--konfig werkstatt/<ordner>/region_<x>.json] [--bericht pfad.json]

Standard-Konfig: werkstatt/olten/region_olten.json. Neuchâtel (26.10.): werkstatt/ne/region_ne.json (Ausgabe in
werkstatt/olten/feedback/region_ne.svg, dort liest bauen.py die Regionalpläne).

Arbeitet in einer Kopie der Werkstatt (/tmp/region_olten), mit spurplan_schema/-warp/netz_pruefung aus code/ und
netz_lage.py der Werkstatt. Je Bahnhof aus werkstatt/olten/region_olten.json die ganze Kette wie run.sh
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

shutil.rmtree(TMP, ignore_errors=True); shutil.copytree(WS, TMP)
for f in ("spurplan_schema.py", "spurplan_warp.py", "spurplan_check.py", "netz_pruefung.py"):
    shutil.copy(os.path.join(HERE, f), TMP)
for f in K.get("code_falls_fehlt", ["lage_auto.py"]):      # Hilfsmodule der Werkstatt, die dort fehlen (NE: lage_auto)
    if not os.path.exists(os.path.join(TMP, f)): shutil.copy(os.path.join(HERE, f), TMP)
py = sys.executable
def sh(args, timeout=900):
    r = subprocess.run([py] + args, cwd=TMP, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")
lesen = lambda p: open(p, "rb").read() if os.path.exists(p) else None

bericht = dict(bahnhoefe={}, region={})
for b, opt in K["bahnhoefe"].items():
    alt = {k: lesen(os.path.join(TMP, f"{b}_{k}")) for k in ("spurplan.svg", "bare.svg")}
    w = os.path.join(TMP, f"{b}_warp.json")
    if os.path.exists(w): os.remove(w)
    rc = 0; log = []
    for a in (["spurplan_schema.py", "--src", f"{b}.json", "--nowarp"] + opt, ["spurplan_warp.py", b],
              ["spurplan_schema.py", "--src", f"{b}.json"] + opt, ["spurplan_warp.py", b],
              ["spurplan_schema.py", "--src", f"{b}.json"] + opt,
              ["spurplan_schema.py", "--src", f"{b}.json", "--bare", "--out", f"{b}_bare.svg"] + opt):
        rc, o = sh(a); log.append(o[-800:])
        if rc: break
    e = dict(ok=rc == 0, optionen=opt)
    if rc: e["fehler"] = log[-1]
    else:
        e["plan_geaendert"] = lesen(os.path.join(TMP, f"{b}_spurplan.svg")) != alt["spurplan.svg"]
        e["bare_geaendert"] = lesen(os.path.join(TMP, f"{b}_bare.svg")) != alt["bare.svg"]
        rc2, o2 = sh(["netz_pruefung.py", b])
        nb = os.path.join(TMP, f"{b}_netz_befunde.json")
        e["netz"] = dict(collections.Counter(x["regel"] for x in json.load(open(nb))["befunde"])) if os.path.exists(nb) else o2[-300:]
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
if BER: json.dump(bericht, open(BER, "w"), ensure_ascii=False, indent=1)
