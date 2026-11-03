"""Regionalplan einer Linien-Region aus der Schweiz-Datei bauen (Region MOB, 21.10.2026).

  python3 spurplan/code/region_lauf.py <region> [--daten schweiz_bahn.json.gz] [--nur-lage]

Ablauf in /tmp/spurplan_region/<region>:
  1. region_vorbereiten.py   Ausschnitt, Schmalspur als Tag "spur", ein Ausschnitt je Betriebspunkt
  2. topologie_linien.py     Betriebspunkte entlang der Linien, Abgänge, Bahnhofsachsen
  3. je Bahnhof spurplan_schema.py (+ warp) wie run.sh, dazu die --bare-Fassung für den Regionalplan
  4. netz_lage.py            automatische Lage (Lagedatei aus der Konfig "lage"), Regionalplan mit Prüfungen
  5. regel_pruefung.py, region_winkel (falls vorhanden)
Ergebnis nach ergebnisse/region_<region>/: region.svg, region.png, bericht.json, log.txt, je Bahnhof <b>_spurplan.svg.
Konfig: spurplan/regionen/<region>/region.json (+ optionale <bahnhof>_override.json im selben Ordner).
"""
import json, os, sys, shutil, subprocess, time, glob
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
REG = sys.argv[1]
DATEN = os.path.abspath(sys.argv[sys.argv.index("--daten") + 1] if "--daten" in sys.argv else os.path.join(REPO, "schweiz_bahn.json.gz"))
KDIR = os.path.join(REPO, "spurplan", "regionen", REG); K = json.load(open(os.path.join(KDIR, "region.json")))
WORK = os.path.join("/tmp/spurplan_region", REG); OUT = os.path.join(REPO, "ergebnisse", f"region_{REG}")
NUR_LAGE = "--nur-lage" in sys.argv
if not NUR_LAGE: shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
LOG = []
def sh(cmd, timeout=900):
    t0 = time.time(); r = subprocess.run(cmd, cwd=WORK, capture_output=True, text=True, timeout=timeout)
    LOG.append(f"$ {' '.join(cmd)}  ({time.time() - t0:.1f} s, rc {r.returncode})\n{r.stdout[-3000:]}{r.stderr[-3000:]}")
    return r
for f in glob.glob(os.path.join(KDIR, "*.json")):
    if os.path.basename(f) != "region.json": shutil.copy(f, WORK)
py = lambda s: os.path.join(HERE, s)
shutil.copy(os.path.join(HERE, "spurplan_schema.py"), WORK)      # spurplan_check.py führt das Schema aus dem Arbeitsordner aus
import atexit
atexit.register(lambda: open(os.path.join(OUT, "log.txt"), "w").write("\n\n".join(LOG)))   # Log auch bei Abbruch
NAME = K.get("name", f"{REG}_region")
if not NUR_LAGE:
    sh(["python3", py("region_vorbereiten.py"), DATEN, os.path.join(KDIR, "region.json"), WORK])
    # Knotenpläne (3.11.2026): Strangbild zeigt, wo zwischen Betriebspunkten keine ruhige Strecke liegt; dann die Region
    # mit gemeinsamen Plänen neu vorbereiten (Konfig «knotenplaene»: false = ein Plan je Betriebspunkt wie bisher)
    if K.get("strangbild", True) and K.get("knotenplaene", True):
        sh(["python3", py("straenge.py"), "region.json", "betriebspunkte.json", os.path.join(KDIR, "region.json"), NAME, "--knoten"])
        if os.path.exists(os.path.join(WORK, "knoten.json")) and json.load(open(os.path.join(WORK, "knoten.json"))):
            sh(["python3", py("region_vorbereiten.py"), DATEN, os.path.join(KDIR, "region.json"), WORK, "knoten.json"])
sh(["python3", py("topologie_linien.py"), "region.json", "betriebspunkte.json", os.path.join(KDIR, "region.json"), NAME])
# Strangbild (3.11.2026, Strangprüfer): Strecken, Gleiszahl und Fahrbeziehungen aus OSM; ersetzt die Topologie der
# Linienachsen (die Achsdateien je Bahnhof bleiben aus topologie_linien.py). Konfig «strangbild»: false = Linienachsen.
if K.get("strangbild", True):
    sh(["python3", py("straenge.py"), "region.json", "betriebspunkte.json", os.path.join(KDIR, "region.json"), NAME, "--topologie"]
       + (["--bereiche"] if not NUR_LAGE else []))
T = json.load(open(os.path.join(WORK, f"{NAME}_topologie.json")))
BP = json.load(open(os.path.join(WORK, "betriebspunkte.json"))); key_of = {v["name"]: k for k, v in BP.items()}
STD = K.get("override_standard", {})
_SB_ANKER = json.load(open(os.path.join(WORK, f"{NAME}_straenge.json"))).get("anker_m", {}) if os.path.exists(os.path.join(WORK, f"{NAME}_straenge.json")) else {}
bericht = dict(region=REG, erzeugt=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), bahnhoefe={})
def _bahnhof(n):
    b = key_of[n["name"]]; ov = os.path.join(WORK, f"{b}_override.json")
    o = json.load(open(ov)) if os.path.exists(ov) else {}
    _eigen_sw = "sw_search_m" in o.get("cfg", {})           # Bahnhofs-Override legt die Weichensuche selbst fest
    for k_, v_ in STD.items():                              # Standard-Override der Region, Bahnhofs-Override hat Vorrang
        if k_ == "cfg": o["cfg"] = {**v_, **o.get("cfg", {})}
        else: o.setdefault(k_, v_)
    # Weichensuche über den ganzen Bereich einer Dienststelle (30.10.2026): der Ausschnitt enthält nur die eigenen Gleise
    # (Bereichsgrenze zum Nachbarn), also gehört jede Weiche darin in diesen Plan (Selfranga: Doppelspurbeginn 600 m
    # vom Betriebspunkt; Sagliains Sasslatsch: Abzweig Nebengleis am Fensterrand). Bahnhofs-Override hat Vorrang.
    if not _eigen_sw and K.get("weichen_ganzer_bereich", True) and BP[b].get("dienst"):     # nur Dienststellen (Bahnhöfe: Fenster wie bisher, Zweisimmen)
        o.setdefault("cfg", {})["sw_search_m"] = max(o.get("cfg", {}).get("sw_search_m", 0), BP[b]["radius"])
    o.setdefault("cfg", {}).setdefault("haupt_fortsetzung", 0.15)  # Hauptgleis gerade weiter (3.11.2026), nur Regionen
    o["cfg"].setdefault("rules", {}).setdefault("r28e", True)       # Personengleis am Randpunkt läuft längs an den Rand
    o["cfg"].setdefault("hauptgleis_funktion", True)                 # Perron-/Fortsetzungsgleise sind Hauptgleise (3.11.2026, MOB)
    o["cfg"].setdefault("perron_frei", True)                          # Perron nicht über Gleise/Weichenbögen (3.11.2026, MOB)
    o["cfg"]["rules"].setdefault("r49", True)
    o["cfg"]["rules"].setdefault("r28f", True)                      # Streckengleis im Bogen läuft an den Planrand (Gruben, La Tine)                       # zu eng für 60°: volle Schräge statt 90° (Sagliains West)
    # Fenster bis zur fernsten Weiche, an der ein Strang dieses Betriebspunkts beginnt (3.11.2026, Montbovon; Strangbild)
    _am = _SB_ANKER.get(b)
    if _am and not _eigen_sw and K.get("fenster_strangbild", True):
        o.setdefault("cfg", {})["sw_search_m"] = max(o.get("cfg", {}).get("sw_search_m", 0), _am + 30)
    if BP[b].get("titel"):                                  # Knotenplan: Titel mit allen Betriebspunkten, Weichen im ganzen Bereich
        o.setdefault("cfg", {}).setdefault("titel", BP[b]["titel"])
        if not _eigen_sw: o["cfg"]["sw_search_m"] = max(o["cfg"].get("sw_search_m", 0), BP[b]["radius"])
    json.dump(o, open(ov, "w"), ensure_ascii=False, indent=1)
    if NUR_LAGE and os.path.exists(os.path.join(WORK, f"{b}_ports.json")): return
    opt = K.get("optionen_je", {}).get(n["name"], K.get("optionen", []))
    src = ["--src", f"{b}.json"] + opt
    if os.path.exists(os.path.join(WORK, f"{b}_warp.json")): os.remove(os.path.join(WORK, f"{b}_warp.json"))
    # Hinweis: spurplan_schema schreibt meta.json in den Arbeitsordner (wird nicht gebraucht, parallele Läufe stören sich nicht)
    sh(["python3", py("spurplan_schema.py")] + src + ["--nowarp"]); sh(["python3", py("spurplan_warp.py"), b])
    sh(["python3", py("spurplan_schema.py")] + src); sh(["python3", py("spurplan_warp.py"), b])
    r = sh(["python3", py("spurplan_schema.py")] + src)
    c = sh(["python3", py("spurplan_check.py")] + src + ["--out", f"/tmp/_chk_{b}.svg"])
    sh(["python3", py("spurplan_schema.py")] + src + ["--bare", "--out", f"{b}_bare.svg"])
    befund = next((l for l in c.stdout.splitlines() if l.startswith("Befunde")), "?")
    ok = os.path.exists(os.path.join(WORK, f"{b}_ports.json")) and r.returncode == 0
    bericht["bahnhoefe"][b] = dict(name=n["name"], ok=ok, befunde=befund, optionen=opt)
    if os.path.exists(os.path.join(WORK, f"{b}_spurplan.svg")): shutil.copy(os.path.join(WORK, f"{b}_spurplan.svg"), OUT)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
    list(ex.map(_bahnhof, [n for n in T["nodes"] if n["kind"] == "station" and n["name"] in key_of]))
# Verkettung (30.10.2026): Ziel-Bahnhof je Abgang und Pfeil in <b>_ports.json, Prüfung V1–V3
_vk = sh(["python3", py("verkettung.py"), "region.json", "betriebspunkte.json", "--bericht", "verkettung.json"]
         + (["--topologie", f"{NAME}_topologie.json"] if K.get("topologie_aus_verkettung", not K.get("strangbild", True)) else [])
         + (["--straenge", f"{NAME}_straenge.json"] if K.get("strangbild", True) else []))
if os.path.exists(os.path.join(WORK, "verkettung.json")):
    _vb = json.load(open(os.path.join(WORK, "verkettung.json")))["befunde"]
    bericht["verkettung"] = {r_: sum(1 for b_ in _vb if b_["regel"] == r_) for r_ in ("V1", "V2", "V3", "S1", "S2", "S3")}
    shutil.copy(os.path.join(WORK, "verkettung.json"), OUT)
# Lage: aus der Konfig (Schlüssel "lage"), Koordinaten erzeugt netz_lage.py selbst (auto)
LF = os.path.join(WORK, f"{NAME}_lage.json")
if not os.path.exists(LF) or not NUR_LAGE: json.dump(K.get("lage", {"auto": {"c0": 30, "c1": 32, "p": 0.6, "gap": 58, "wg": 0.01}}), open(LF, "w"), ensure_ascii=False, indent=1)
shutil.copy(os.path.join(KDIR, "region.json"), os.path.join(WORK, "_konfig.json"))
r = sh(["python3", py("netz_lage.py"), NAME, K.get("titel", REG), "region.svg", "--pruefen"], timeout=1800)
bericht["netz_lage"] = r.returncode
# Topologie über die ganze Region (3.11.2026, T1–T4 aus netz_lage --pruefen): oberste Regel
if os.path.exists(os.path.join(WORK, "topologie_region.json")):
    import collections as _c
    _tr = json.load(open(os.path.join(WORK, "topologie_region.json")))
    bericht["topologie_region"] = dict(_c.Counter(t_["regel"] for t_ in _tr))
    shutil.copy(os.path.join(WORK, "topologie_region.json"), OUT)
if os.path.exists(os.path.join(WORK, "region.svg")):
    shutil.copy(os.path.join(WORK, "region.svg"), OUT); shutil.copy(LF, os.path.join(OUT, "lage.json"))
    rp = sh(["python3", py("regel_pruefung.py"), "region.svg", "--json", "regeln.json"])
    if os.path.exists(os.path.join(WORK, "regeln.json")):
        import collections
        bericht["regeln"] = dict(collections.Counter(x.get("regel", x.get("art", "?")) for x in json.load(open(os.path.join(WORK, "regeln.json")))))
    try:
        import cairosvg
        cairosvg.svg2png(url=os.path.join(WORK, "region.svg"), write_to=os.path.join(OUT, "region.png"), output_width=3000, background_color="white")
    except Exception as e: LOG.append(f"PNG: {e}")
for f_ in ("roh.json.gz", "betriebspunkte.json", f"{NAME}_topologie.json", f"{NAME}_straenge.json"):
    if os.path.exists(os.path.join(WORK, f_)): shutil.copy(os.path.join(WORK, f_), OUT)
json.dump(bericht, open(os.path.join(OUT, "bericht.json"), "w"), ensure_ascii=False, indent=1)
open(os.path.join(OUT, "log.txt"), "w").write("\n\n".join(LOG))
print(json.dumps({k: v for k, v in bericht.items() if k != "bahnhoefe"}, ensure_ascii=False))
print(sum(1 for v in bericht["bahnhoefe"].values() if v["ok"]), "von", len(bericht["bahnhoefe"]), "Bahnhöfen gezeichnet")
