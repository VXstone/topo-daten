"""Region Olten im Repo bauen (26.10.2026, «Olten zügeln»): Bahnhofspläne + Regionalplan aus spurplan/werkstatt/olten.

  python3 spurplan/code/region_olten_lauf.py [--bericht pfad.json]

Arbeitet in einer Kopie der Werkstatt (/tmp/region_olten), mit spurplan_schema/-warp/netz_pruefung aus code/ und
netz_lage.py der Werkstatt. Je Bahnhof aus werkstatt/olten/region_olten.json die ganze Kette wie run.sh
(schema --nowarp → warp → schema → warp → schema → --bare), dann Netzprüfung, dann
netz_lage.py olten_region "Region Olten" feedback/region.svg (+ --pruefen). Die neuen Dateien (Plan, bare, ports,
warp, region.svg) werden in die Werkstatt zurückgeschrieben, damit bauen.py (Workflow seite) sie verwendet.
Der Bericht nennt je Bahnhof, ob sich Plan/bare gegenüber dem Stand im Repo geändert haben, und die Netzbefunde.
"""
import json, os, shutil, subprocess, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
WS = os.path.join(SP, "werkstatt", "olten"); TMP = "/tmp/region_olten"
K = json.load(open(os.path.join(WS, "region_olten.json")))
BER = sys.argv[sys.argv.index("--bericht") + 1] if "--bericht" in sys.argv else None

shutil.rmtree(TMP, ignore_errors=True); shutil.copytree(WS, TMP)
for f in ("spurplan_schema.py", "spurplan_warp.py", "spurplan_check.py", "netz_pruefung.py"):
    shutil.copy(os.path.join(HERE, f), TMP)
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
alt_r = lesen(os.path.join(TMP, R["ausgabe"]))
rc, o = sh(["netz_lage.py", R["name"], R["titel"], R["ausgabe"]])
bericht["region"] = dict(ok=rc == 0, log=o[-1500:])
if rc == 0:
    bericht["region"]["geaendert"] = lesen(os.path.join(TMP, R["ausgabe"])) != alt_r
    shutil.copy(os.path.join(TMP, R["ausgabe"]), os.path.join(WS, R["ausgabe"]))
    rc, o = sh(["netz_lage.py", R["name"], R["titel"], "/tmp/region_olten_pruef.svg", "--pruefen"])
    bericht["region"]["pruefung"] = o[-3000:]
print("Region Olten:", json.dumps({k: v for k, v in bericht["region"].items() if k != "pruefung" and k != "log"}, ensure_ascii=False))
if BER: json.dump(bericht, open(BER, "w"), ensure_ascii=False, indent=1)
