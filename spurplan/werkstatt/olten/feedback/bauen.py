"""
Baut die Feedback-Seite (index.html) aus dem aktuellen Stand:
  Regionalplan (Netzplan mit data-st-Kennungen) + alle Spurpläne des Prüfstands mit Befund-Ebene.
  python3 feedback/bauen.py "Netzplan_09" "../20261012_Region Olten Netzplan_09.svg"
Die Einträge (Klicks) liegen in der Datenbank des Artefakts, nicht in der Seite.
"""
import os, sys, json, re, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); OL = os.path.dirname(HERE)
sys.path.insert(0, OL)
import importlib.util
spec = importlib.util.spec_from_file_location("ps", os.path.join(OL, "pruefstand.py")); ps = importlib.util.module_from_spec(spec)
sys.argv_saved = sys.argv; spec.loader.exec_module(ps)

region_label = sys.argv[1] if len(sys.argv) > 1 else "Netzplan"
region_svg = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "region.svg")
erg = json.load(open(os.path.join(OL, "pruefstand_ergebnis.json")))["ergebnis"]
basis = json.load(open(ps.BASIS)) if os.path.exists(ps.BASIS) else {}
stand = f"{datetime.date.today():%d.%m.%Y}"

def strip(svg):
    svg = re.sub(r"<\?xml[^>]*>", "", svg)
    return re.sub(r'(<svg[^>]*?)\s(width|height)="[^"]*"', r"\1", re.sub(r'(<svg[^>]*?)\s(width|height)="[^"]*"', r"\1", svg))

_ARB = json.load(open(os.path.join(HERE, "arbeit.json"))) if os.path.exists(os.path.join(HERE, "arbeit.json")) else {}
plans = []
reg = open(region_svg).read()
if "data-st=" not in reg: print("Warnung: Regionalplan ohne data-st-Kennungen")
plans.append(dict(key="region", name="Region Olten", gruppe="Region", label=region_label, svg=strip(reg), counts=None, status=None))
# weitere Regionalpläne (feedback/regionalplaene.json: [{key, name, label, svg}], z. B. Region Neuchâtel 15.10.)
_rp = os.path.join(HERE, "regionalplaene.json")
for _r in (json.load(open(_rp)) if os.path.exists(_rp) else []):
    plans.append(dict(key=_r["key"], name=_r["name"], gruppe="Region", label=_r["label"], svg=strip(open(_r["svg"]).read()), counts=None, status=None))
# Werkzeugkasten: Blaupausen-Bahnhof (alle Zeichenelemente, für Designentscheide und Hinweise)
import subprocess as _sp; _sp.run(["python3", os.path.join(HERE, "blaupause.py")], check=True)
plans.append(dict(key="blaupause", name="Blaupausen-Bahnhof", gruppe="Werkzeugkasten", label=f"Stand {stand}",
                  svg=strip(open(os.path.join(HERE, "blaupause.svg")).read()), counts=None, status=None))
# Blaupause 2 – Bahnhofstypen (16.10.): aus ne/vorlage.py gezeichnet, also genau wie die Vorlage-Pläne
_vp = next((q for q in (os.path.join(OL, "..", "..", "code", "vorlage.py"), "/home/claude/ne/vorlage.py") if os.path.exists(q)), "")   # Repo: spurplan/code/vorlage.py
if os.path.exists(_vp):
    _sp.run(["python3", _vp, "--blaupause2", os.path.join(HERE, "blaupause2.svg")], check=True, cwd=os.path.dirname(_vp), capture_output=True)
    plans.append(dict(key="blaupause2", name="Blaupause 2 – Bahnhofstypen", gruppe="Werkzeugkasten", label=f"Reinform + Zusätze · Stand {stand}",
                      svg=strip(open(os.path.join(HERE, "blaupause2.svg")).read()), counts=None, status=None))
for key, d, extra, name in ps.STATIONS:
    a = open(os.path.join(d, f"{key}_spurplan.svg")).read()
    c = open(os.path.join(d, f"{key}_spurplan_check.svg")).read()
    extra_ = c[len(a) - 7:-7] if c.startswith(a[:-7]) else ""
    ab = json.load(open(os.path.join(d, f"{key}_abstand.json"))) if os.path.exists(os.path.join(d, f"{key}_abstand.json")) else []
    _cm = {"zu nah": ("#c0f", "E"), "Weiche verdeckt": ("#f80", "W"), "90 Grad": ("#e00", "R")}
    mk = "".join(f'<circle cx="{x["x"]}" cy="{x["y"]}" r="12" fill="none" stroke="{_cm[x["art"]][0]}" stroke-width="2.5"/>'
                 f'<text x="{x["x"] + 14}" y="{x["y"] - 9}" font-size="13" fill="{_cm[x["art"]][0]}">{_cm[x["art"]][1]}</text>' for x in ab)
    svg = a[:-7] + f'<g class="befund">{extra_}{mk}</g></svg>'
    cnt = {k: erg.get(key, {}).get(k, 0) for k in ps.KEYS}
    tot = sum(cnt.values())
    _wieder = key in _ARB.get("reihenfolge", [])          # Referenz wieder geöffnet (Arbeitsliste)
    st = "abgenommen" if (key in basis and not _wieder) else ("sauber" if tot == 0 else "offen")
    plans.append(dict(key=key, name=name, gruppe="Referenz" if d == ps.REG else "Region Olten", label=f"Stand {stand}",
                      svg=strip(svg), counts=cnt, status=st))
# Bahnhöfe aus dem Workflow «plaene» (spurplan/bahnhoefe.json, 26.10.2026): Plan aus ergebnisse/<b>/spurplan.svg,
# vom Workflow «seite» nach feedback/repo_<b>.svg gelegt; Gruppe/Name aus zusatz_plaene.json, sonst Gruppe «Repo-Bahnhöfe»
_bj = os.path.join(OL, "..", "..", "bahnhoefe.json")
_zmeta = {p_["key"]: p_ for p_ in (json.load(open(os.path.join(HERE, "zusatz_plaene.json"))) if os.path.exists(os.path.join(HERE, "zusatz_plaene.json")) else [])}
_rber = json.load(open(os.path.join(HERE, "repo_bericht.json"))) if os.path.exists(os.path.join(HERE, "repo_bericht.json")) else {}
def _repo_counts(b_):
    """Befundzahlen eines Repo-Bahnhofs für die Abnahme (29.10.2026: ohne counts fehlte der Knopf «Abnehmen»)"""
    e_ = _rber.get("bahnhoefe", {}).get(b_) or {}
    c_ = {f"netz_{k_}": v_ for k_, v_ in (e_.get("netz") or {}).items()}
    import ast as _ast
    try: c_.update({f"topo_{k_}": v_ for k_, v_ in _ast.literal_eval(e_.get("topologie") or "{}").items()})
    except Exception: pass
    return c_ or {"befunde": 0}
for _b in ([k_ for k_ in json.load(open(_bj)) if not k_.startswith("_")] if os.path.exists(_bj) else []):
    _f = os.path.join(HERE, f"repo_{_b}.svg")
    if not os.path.exists(_f) or any(p_["key"] == _b for p_ in plans): continue
    _m = _zmeta.get(_b, {}); _nb = (_rber.get("bahnhoefe", {}).get(_b) or {}).get("netz") or {}
    _svg = open(_f).read(); _tt = re.findall(r'font-weight="700"[^>]*>([^<]+)</text>', _svg)
    plans.append(dict(key=_b, name=_m.get("name") or (_tt[-1] if _tt else _b), gruppe=_m.get("gruppe", "Repo-Bahnhöfe (Workflow plaene)"),
                      label=f"Workflow plaene {_rber.get('erzeugt', '')}" + (" · Netzprüfung " + ", ".join(f"{k_} {v_}" for k_, v_ in sorted(_nb.items())) if _nb else " · Netzprüfung ohne Befunde"),
                      svg=strip(_svg), counts=_m.get("counts") or _repo_counts(_b), status=_m.get("status", "offen"), **({"region": _m["region"]} if _m.get("region") else {})))
# Anker für mitwandernde Hinweis-Pins (26.10.2026): Weichen, Gleisenden, Kreuzungen aus dem Netzmodell des Bahnhofs
def _anker(key_):
    for f_ in (os.path.join(HERE, f"repo_{key_}_netz.json"), os.path.join(OL, f"{key_}_netz.json")):
        if os.path.exists(f_):
            try:
                K_ = json.load(open(f_))["knoten"]
                return [[int(i_), v_["x"], v_["y"]] for i_, v_ in K_.items() if v_.get("y") is not None and v_.get("typ") in ("switch", "buffer_stop", "railway_crossing")]
            except Exception: return None
    return None
_zus = os.path.join(HERE, "zusatz_plaene.json")   # Pläne aus anderen Sitzungen (z. B. Basel/Bern, Grosse Knoten) übernehmen
if os.path.exists(_zus):
    _have = {p_["key"] for p_ in plans}
    plans += [p_ for p_ in json.load(open(_zus)) if p_["key"] not in _have]
import subprocess; subprocess.run(["python3", os.path.join(HERE, "legende.py")], check=True)
leg = open(os.path.join(HERE, "legende.json")).read()
tpl = open(os.path.join(HERE, "seite.html")).read().replace("/*LEGENDE*/[]", leg.replace("</", "<\\/"))
_arb = os.path.join(HERE, "arbeit.json")   # Arbeitsliste: Reihenfolge, aktueller Bahnhof, "Neu in dieser Fassung"
tpl = tpl.replace("/*ARBEIT*/{}", json.dumps(json.load(open(_arb)) if os.path.exists(_arb) else {}, ensure_ascii=False).replace("</", "<\\/"))
for p_ in plans:
    if p_.get("gruppe") != "Region" and p_.get("key"):
        a_ = _anker(p_["key"])
        if a_: p_["anker"] = a_
out = tpl.replace("/*PLANS*/[]", json.dumps(plans, ensure_ascii=False).replace("</", "<\\/")).replace("{{STAND}}", stand)
open(os.path.join(HERE, "index.html"), "w").write(out)
if os.environ.get("PLAENE_DIR"):       # je Plan eine SVG-Datei (Workflow «seite»: Ausschnitte an den Hinweisstellen)
    os.makedirs(os.environ["PLAENE_DIR"], exist_ok=True)
    for p_ in plans: open(os.path.join(os.environ["PLAENE_DIR"], f"{p_['key']}.svg"), "w").write(p_["svg"])
print("index.html", len(out) // 1024, "KB,", len(plans), "Pläne")
