"""Baut die Spurpläne im Repo und prüft sie (Workflow «plaene»; D. Eckenstein 21.10.: «Skripte laufen im Repo, Claude prüft»).

python3 spurplan/code/lauf.py [bahnhof …]          (ohne Angabe: alle aus spurplan/bahnhoefe.json)
Je Bahnhof in einem Arbeitsordner: Schema ohne Entzerrung → Entzerrung → Schema → Entzerrung → Schema (wie run.sh),
bare-Fassung, Typvorlage falls im Override; danach Prüfungen:
  Topologie (spurplan_check A–D …), Verbindungen (verbindungen_pruefen), Regelprüfung G1–G8 (regel_pruefung),
  Planrand (planrand_pruefung), Netzprüfung (netz_pruefung, Regel-IDs des Katalogs), Differenzbild gegen spurplan/vergleich/<b>_spurplan.svg (abgenommen bzw. zuletzt
  veröffentlicht), PNG des Plans.
Ausgabe: ergebnisse/<b>/ (spurplan.svg, bare.svg, ports.json, spurplan.png, diff.png, bericht.json) und
ergebnisse/bericht.json (Übersicht). Byte-Vergleich mit der Vergleichsfassung steht im Bericht (gleich: true/false).
"""
import sys, os, json, shutil, subprocess, glob, re, hashlib, datetime
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # spurplan/
C = os.path.join(R, "code"); B = json.load(open(os.path.join(R, "bahnhoefe.json")))
OUT = os.path.join(os.path.dirname(R), "ergebnisse"); os.makedirs(OUT, exist_ok=True)
liste = sys.argv[1:] or [k for k in B if not k.startswith("_")]
def sh(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")
gesamt = {}
for b in liste:
    cfg = B[b]; opt = cfg.get("optionen", [])
    w = os.path.join("/tmp", "spurplan_lauf", b); shutil.rmtree(w, ignore_errors=True); os.makedirs(w)
    for f in glob.glob(os.path.join(C, "*.py")): shutil.copy(f, w)
    if os.path.exists(os.path.join(C, "linienenden.json")): shutil.copy(os.path.join(C, "linienenden.json"), w)   # Richtungsorte
    rl = os.path.join(C, f"region_lines_{cfg.get('region_lines', '')}.json")
    if os.path.exists(rl): shutil.copy(rl, os.path.join(w, "region_lines.json"))
    for f in glob.glob(os.path.join(R, "bahnhoefe", b, "*")): shutil.copy(f, w)
    log = []; ok = True
    py = [sys.executable]
    schritte = [py + ["spurplan_schema.py", "--src", f"{b}.json", "--nowarp"] + opt, py + ["spurplan_warp.py", b],
                py + ["spurplan_schema.py", "--src", f"{b}.json"] + opt, py + ["spurplan_warp.py", b],
                py + ["spurplan_schema.py", "--src", f"{b}.json"] + opt,
                py + ["spurplan_check.py", "--src", f"{b}.json", "--out", f"/tmp/spurplan_lauf/_check_{b}.svg"] + opt,
                py + ["spurplan_schema.py", "--src", f"{b}.json", "--bare", "--out", f"{b}_bare.svg"] + opt]
    if os.path.exists(os.path.join(w, f"{b}_warp.json")): os.remove(os.path.join(w, f"{b}_warp.json"))
    ber = dict(bahnhof=b, optionen=opt)
    # B13 (26.10.2026, Hinweis Konolfingen): Perrons aus SBB Open Data, sofern das Override keine «platforms» von Hand hat.
    # Daten: SBB_PO oder perronoberflache.geojson.gz im Repo-Wurzelordner (Workflow lädt sie aus dem Release «daten»).
    _po = os.environ.get("SBB_PO") or os.path.join(os.path.dirname(R), "perronoberflache.geojson.gz")
    if os.path.exists(_po) and cfg.get("sbb_perrons", True):
        p_ = subprocess.run(py + ["spurplan_schema.py", "--src", f"{b}.json", "--nowarp"] + opt, cwd=w, capture_output=True,
                            text=True, env=dict(os.environ, SPUR_FENSTER="1"))
        p_ = subprocess.run(py + ["sbb_perrons.py", b] + ([cfg["sbb_name"]] if cfg.get("sbb_name") else []) + ["--auto"],
                            cwd=w, capture_output=True, text=True, env=dict(os.environ, SBB_PO=_po))
        ber["sbb_perrons"] = (p_.stdout or p_.stderr).strip().splitlines()[-6:]; log.append("$ sbb_perrons.py\n" + (p_.stdout or "") + (p_.stderr or ""))
    for i, s in enumerate(schritte):
        rc, o = sh(s, w); log.append(f"$ {' '.join(s[1:])}\n{o[-3000:]}")
        if rc: ok = False; ber["fehler"] = f"Schritt {i + 1}: {' '.join(s[1:])}"; break
        if "spurplan_check.py" in s[1]:
            m = re.search(r"Befunde: (\{.*\})", o); ber["topologie"] = m.group(1) if m else None
    if ok and '"vorlage"' in open(os.path.join(w, f"{b}_override.json")).read():
        rc, o = sh(py + ["vorlage.py", b], w); log.append(o[-2000:])
    if ok:
        rc, o = sh(py + ["verbindungen_pruefen.py", b] + opt, w); log.append(o[-4000:])
        m = re.search(r"→ (\d+) Abweichungen", o); ber["verbindungen_abweichungen"] = int(m.group(1)) if m else None
        ber["verbindungen"] = [l.strip() for l in o.splitlines() if "ABWEICHUNG" in l or "fehlt im Plan" in l]
        rc, o = sh(py + ["regel_pruefung.py", f"{b}_spurplan.svg", "--json", "regeln.json"], w)
        ber["regeln"] = json.load(open(os.path.join(w, "regeln.json"))) if os.path.exists(os.path.join(w, "regeln.json")) else o[-500:]
        rc, o = sh(py + ["planrand_pruefung.py", "."], w)
        ber["planrand"] = [l for l in o.splitlines() if l.startswith(b + "\t")]
        rc, o = sh(py + ["netz_pruefung.py", b], w); log.append(o[-3000:])      # Netzmodell (25.10.): Befunde mit Regel-ID und OSM-Way
        _nb = os.path.join(w, f"{b}_netz_befunde.json")
        ber["netz"] = json.load(open(_nb))["befunde"] if os.path.exists(_nb) else o[-500:]
        rc, o = sh(py + ["qualitaet.py", "messen", b, "--check", str(ber.get("topologie") or "{}"), "--regeln", "regeln.json"], w)
        _qj = os.path.join(w, f"{b}_qualitaet.json")
        ber["qualitaet"] = json.load(open(_qj)) if os.path.exists(_qj) else o[-300:]      # Kennzahlen (27.10.)
        d = os.path.join(OUT, b); os.makedirs(d, exist_ok=True)
        for src, dst in ((f"{b}_spurplan.svg", "spurplan.svg"), (f"{b}_bare.svg", "bare.svg"), (f"{b}_ports.json", "ports.json"),
                         (f"{b}_netz.json", "netz.json"), (f"{b}_netz_befunde.json", "netz_befunde.json")):
            if os.path.exists(os.path.join(w, src)): shutil.copy(os.path.join(w, src), os.path.join(d, dst))
        try:
            import cairosvg
            cairosvg.svg2png(url=os.path.join(d, "spurplan.svg"), write_to=os.path.join(d, "spurplan.png"), output_width=1600, background_color="white")
        except Exception as e: ber["png"] = str(e)
        alt = os.path.join(R, "vergleich", f"{b}_spurplan.svg")
        if os.path.exists(alt):
            neu = os.path.join(d, "spurplan.svg")
            ber["gleich_wie_vergleich"] = hashlib.md5(open(alt, "rb").read()).hexdigest() == hashlib.md5(open(neu, "rb").read()).hexdigest()
            rc, o = sh(py + ["diff_bild.py", alt, neu, os.path.join(d, "diff.png"), "--px", "1600", "--liste", os.path.join(w, "diff.json")], w)
            ber["differenz"] = json.load(open(os.path.join(w, "diff.json"))) if os.path.exists(os.path.join(w, "diff.json")) else o[-500:]
    ber["ok"] = ok
    os.makedirs(os.path.join(OUT, b), exist_ok=True)
    open(os.path.join(OUT, b, "log.txt"), "w").write("\n".join(log))
    json.dump(ber, open(os.path.join(OUT, b, "bericht.json"), "w"), ensure_ascii=False, indent=1)
    gesamt[b] = {k: ber.get(k) for k in ("ok", "fehler", "topologie", "verbindungen_abweichungen", "gleich_wie_vergleich")}
    gesamt[b]["regeln"] = (dict(__import__("collections").Counter(x["regel"] for x in ber["regeln"])) if isinstance(ber.get("regeln"), list) else ber.get("regeln"))
    gesamt[b]["netz"] = (dict(__import__("collections").Counter(x["regel"] for x in ber["netz"])) if isinstance(ber.get("netz"), list) else ber.get("netz"))
    gesamt[b]["differenz_stellen"] = len(ber["differenz"]) if isinstance(ber.get("differenz"), list) else None
    print(b, json.dumps(gesamt[b], ensure_ascii=False))
# Kennzahlen gegen die Basis (spurplan/qualitaet_basis.json): besser / schlechter / gleich je Bahnhof
_mess = {b: json.load(open(os.path.join(OUT, b, "bericht.json"))).get("qualitaet") for b in liste}
_mess = {b: k for b, k in _mess.items() if isinstance(k, dict)}
json.dump(_mess, open(os.path.join(OUT, "qualitaet_messung.json"), "w"), ensure_ascii=False, indent=1)
sys.path.insert(0, C); import qualitaet as _Q
_bas = json.load(open(_Q.BASIS)) if os.path.exists(_Q.BASIS) else {}
_verg = _Q.vergleichen(_mess, _bas)
print("Kennzahlen gegen die Basis:")
for b, e in _verg.items(): print(f"  {b:22} {e['status']}", e.get("schlechter") or "", e.get("besser") or "")
for b in gesamt: gesamt[b]["qualitaet"] = _verg.get(b)
json.dump(dict(erzeugt=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), lauf=os.environ.get("LAUF", ""),
               bahnhoefe=gesamt), open(os.path.join(OUT, "bericht.json"), "w"), ensure_ascii=False, indent=1)
