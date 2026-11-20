"""
Bahnhofregister, Prüfung «OSM-Verdacht» und Sperre «veraltet» (Schritt V3, Entscheid D. Eckenstein 20.11.2026;
REGELN Kopf «Register und Sperre VR», Ebene 6).

Jeder Bahnhof steht einmal im Register, Schlüssel = SBB-Abkürzung (atlas/Dienststellen), dazu BPUIC, atlas-Koordinaten,
OSM-Station, Linien, Regionen und je Plan Quelle/Workflow, Code-Commit und Fingerabdruck des letzten Baus.

  python3 spurplan/code/bahnhofregister.py --seite /tmp/seite/index.html --plaene /tmp/seite/plaene \
      --netz-dir <netz> --daten <ordner mit dienststellen.csv.gz, betriebspunkte.json, gleisnummern.json> \
      --osm schweiz_bahn.json.gz --out /tmp/seite/register [--stabil spurplan/netz/bahnhoefe.json] \
      [--sha <GITHUB_SHA>] [--ref origin/ergebnisse] [--basis spurplan/veraltet_basis.json] [--laufend plaene,regionen]
  python3 spurplan/code/bahnhofregister.py --selbsttest     (Sperre greift: alter Plan → rot)

Ausgabe in --out: register.json (alles), osm_verdacht.json/.md, osm_verdacht.svg (Karte «OSM-Verdacht» der Seite),
veraltet.md. --stabil schreibt den Teil ohne Commit/Fingerabdruck (ändert sich nur, wenn Bahnhöfe/Pläne/Daten ändern).
Rückgabe 1, wenn ein Plan veraltet ist, der nicht in --basis steht (Sperre), sonst 0.
"""
import csv, gzip, hashlib, json, math, os, re, subprocess, sys, unicodedata, collections, html as _html

HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); ROOT = os.path.dirname(SP)
AB_M = 150            # atlas ↔ OSM: ab hier Verdacht (Vorgabe Schritt V3: «> ~150 m»)
BAHN_VM = {"TRAIN", "RACK_RAILWAY", "CABLE_RAILWAY", "METRO", "", "UNKNOWN"}
WERKZEUG = {"blaupause", "blaupause2", "fragen", "pruefstand", "osm_verdacht"}


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    s = re.sub(r"\bb\.\s*o\.?", "bei olten", s)
    s = re.sub(r"\b(st)\.", r"\1 ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


KANTONE = set("ag ai ar be bl bs fr ge gl gr ju lu ne nw ow sg sh so sz tg ti ur vd vs zg zh".split())


def tok(s):
    """Namens-Wörter ohne Kantonskürzel und Einzelbuchstaben (i.S.), «saint» = «st» (Saint-Blaise Lac = St-Blaise-Lac)."""
    t = [("st" if w == "saint" else w) for w in norm(s).split()]
    return frozenset(w for w in t if w not in KANTONE and len(w) > 1)


def dist(a, b):
    la = math.radians((a[0] + b[0]) / 2)
    return math.hypot((a[0] - b[0]) * 111195, (a[1] - b[1]) * 111195 * math.cos(la))


def git(*a, cwd=ROOT):
    r = subprocess.run(["git", *a], capture_output=True, cwd=cwd)
    return r.stdout.decode(errors="replace") if r.returncode == 0 else ""


def ist_vorfahr(alt, neu):
    """True, wenn Commit alt in der Geschichte von neu liegt (oder gleich ist)."""
    if not alt or not neu: return False
    return subprocess.run(["git", "merge-base", "--is-ancestor", alt, neu], cwd=ROOT, capture_output=True).returncode == 0


# ---------------------------------------------------------------- Daten
def lade_daten(dd, osm_pfad):
    R = list(csv.DictReader(gzip.open(os.path.join(dd, "dienststellen.csv.gz"), "rt", encoding="utf-8"), delimiter=";"))
    D = [r for r in R if r["abk"] and r["verkehrsmittel"] in BAHN_VM and r["lat"] and r["gueltig_bis"] >= "2026"]
    for r in D: r["ll"] = (float(r["lat"]), float(r["lon"])); r["n"] = norm(r["name"]); r["t"] = tok(r["name"])
    BP = json.load(open(os.path.join(dd, "betriebspunkte.json")))
    GN = json.load(open(os.path.join(dd, "gleisnummern.json"))) if os.path.exists(os.path.join(dd, "gleisnummern.json")) else {}
    E = json.load(gzip.open(osm_pfad))["elements"]
    ST = [e for e in E if e["type"] == "node" and (e.get("tags") or {}).get("railway") in ("station", "halt")]
    for e in ST: e["ll"] = (e["lat"], e["lon"]); e["n"] = norm(e["tags"].get("name"))
    return D, BP, GN, ST


def plan_ort(netz, key):
    """Mittelpunkt der Knoten mit Koordinaten (Netzmodell eines Plans); sonst Median der OSM-Knoten des Werkstatt-Auszugs
    (werkstatt/<ordner>/<key>.json), sonst None."""
    p = [(v["lat"], v["lon"]) for v in (netz or {}).get("knoten", {}).values() if v.get("lat") is not None]
    if p: return (sum(a for a, _ in p) / len(p), sum(b for _, b in p) / len(p))
    for d in ("werkstatt/olten/reg", "werkstatt/ne", "werkstatt/olten"):
        f = os.path.join(SP, d, f"{key}.json")
        if not os.path.exists(f): continue
        try: E = json.load(open(f)).get("elements", [])
        except (ValueError, AttributeError): continue
        la = sorted(e["lat"] for e in E if e.get("lat")); lo = sorted(e["lon"] for e in E if e.get("lon"))
        if la: return (la[len(la) // 2], lo[len(lo) // 2])
    return None


def namen(p):
    teile = [t.strip() for t in re.split(r"\s+·\s+", p["name"]) if t.strip()]
    k = p["key"].split("__")[-1].replace("_", " ")
    c = teile + ([" ".join(teile)] if len(teile) > 1 else []) + [k]
    return list(dict.fromkeys(tok(x) for x in c if tok(x)))


def finde_dienststellen(p, D, ort):
    """Dienststellen eines Plans je Namensteil: (1) gleiche Namens-Wörter (ohne Kantonskürzel), Zug vor Betriebspunkt, dann
    die nächste zum Plan; (2) sonst Namens-Wörter des Plans in denen der Dienststelle enthalten, ≤ 3 km vom Plan
    (Riedbach = Bern Riedbach, Serrières = Neuchâtel-Serrières); (3) sonst die nächste Bahn-Dienststelle ≤ 500 m.
    Rückgabe Liste (Zeile, wie)."""
    tref = []
    zug = lambda r: r["verkehrsmittel"] not in ("TRAIN", "RACK_RAILWAY")
    for n in namen(p):
        c = [r for r in D if r["t"] == n]
        wie = "name"
        if not c and ort:
            c = [r for r in D if n < r["t"] and dist(r["ll"], ort) <= 3000]; wie = "name_teil"
        if not c: continue
        c.sort(key=lambda r: (zug(r), len(r["t"]), dist(r["ll"], ort) if ort else 0))
        if c[0]["abk"] not in {r["abk"] for r, _ in tref}: tref.append((c[0], wie))
    if not tref and ort:
        c = sorted(D, key=lambda r: dist(r["ll"], ort))
        if c and dist(c[0]["ll"], ort) <= 500: tref.append((c[0], "naehe"))
    return tref


def finde_osm(r, ST):
    by_uic = [e for e in ST if e["tags"].get("uic_ref") == r["nummer"]]
    if by_uic: return min(by_uic, key=lambda e: dist(e["ll"], r["ll"])), "uic_ref"
    by_ref = [e for e in ST if e["tags"].get("railway:ref") == r["abk"]]
    if by_ref: return min(by_ref, key=lambda e: dist(e["ll"], r["ll"])), "railway:ref"
    by_n = [e for e in ST if e["n"] == r["n"] and dist(e["ll"], r["ll"]) < 3000]
    if by_n: return min(by_n, key=lambda e: dist(e["ll"], r["ll"])), "name"
    nah = [e for e in ST if dist(e["ll"], r["ll"]) < 400]
    if nah: return min(nah, key=lambda e: dist(e["ll"], r["ll"])), "naehe"
    return None, None


# ---------------------------------------------------------------- Herkunft je Plan
def herkunft(p, cfg, sha, ref):
    """Quelle, Workflow und Code-Commit des letzten Baus eines Plans."""
    k, lab = p["key"], p.get("label") or ""
    if k in cfg["olten"] or k == "region": return dict(quelle="Werkstatt Olten", workflow="seite", commit=sha, art="code")
    if k in cfg["referenz"]:          # Karte = Datei werkstatt/olten/reg (auch Ins: Werkstatt NE baut ins nur für den Regionalplan)
        f = f"spurplan/werkstatt/olten/reg/{k}_spurplan.svg"
        c = git("log", "-1", "--format=%H %cs", "--", f).split()
        return dict(quelle="Referenz (Werkstatt-Datei olten/reg)", workflow="seite (Datei)", commit=c[0] if c else None,
                    datum=c[1] if len(c) > 1 else None, art="datei")
    if k == "region_ne" or k in cfg["ne"]: return dict(quelle="Werkstatt NE", workflow="seite", commit=sha, art="code")
    if k in cfg["repo"]:
        return dict(quelle="Repo-Bahnhof", workflow="plaene", commit=cfg["plaene_commit"].get(k), art="code")
    if "__" in k or (k.startswith("region_") and k[7:] in cfg["regionen"]):
        r = k.split("__")[0] if "__" in k else k[7:]
        return dict(quelle=f"Linien-Region {r}", workflow="regionen", commit=cfg["regionen_commit"].get(r), art="code")
    m = re.search(r"fest seit (\S+)", lab)
    return dict(quelle="fest (zusatz_plaene.json)", workflow="-", commit=None, datum=m.group(1) if m else None, art="fest")


def plaene_commits(ref, repo_keys):
    """Code-Commit je Repo-Bahnhof: letzter Lauf «plaene» auf ergebnisse, dessen Gesamtbericht den Bahnhof nennt."""
    out = {}
    for line in git("log", ref, "--format=%H %s", "-n", "200", "--", "ergebnisse/bericht.json").splitlines():
        h, s = line.split(" ", 1)
        try: b = json.loads(git("show", f"{h}:ergebnisse/bericht.json") or "{}")
        except ValueError: continue
        m = re.search(r"\(([0-9a-f]{7,40})\)", s); c = b.get("code_commit") or (m.group(1) if m else None)
        for k in b.get("bahnhoefe", {}):
            if k in repo_keys and k not in out: out[k] = c
        if len(out) == len(repo_keys): break
    return out


def regionen_commits(ref, regionen):
    out = {}
    for r in regionen:
        line = git("log", "-1", ref, "--format=%H %s", "--", f"ergebnisse/region_{r}/bericht.json").strip()
        if not line: continue
        h, s = line.split(" ", 1)
        try: b = json.loads(git("show", f"{h}:ergebnisse/region_{r}/bericht.json") or "{}")
        except ValueError: b = {}
        m = re.search(r"\(([0-9a-f]{7,40})\)", s); out[r] = b.get("code_commit") or (m.group(1) if m else None)
    return out


def code_stand(main="HEAD"):
    """Letzter Commit auf main, der spurplan/code/ ändert (gegen ihn wird «veraltet» gemessen)."""
    return git("log", "-1", "--format=%H", main, "--", "spurplan/code").strip()


# ---------------------------------------------------------------- Register bauen
def bauen(PLANS, plaene_dir, netz_dir, D, BP, GN, ST, sha, ref):
    sp = lambda *a: os.path.join(SP, *a)
    cfg = dict(olten=set(json.load(open(sp("werkstatt", "olten", "region_olten.json")))["bahnhoefe"]),
               ne=set(json.load(open(sp("werkstatt", "ne", "region_ne.json")))["bahnhoefe"]),
               repo={k for k in json.load(open(sp("bahnhoefe.json"))) if not k.startswith("_")},
               regionen=sorted(os.listdir(sp("regionen"))), referenz={"thun", "ins", "murten", "kerzers"})
    cfg["plaene_commit"] = plaene_commits(ref, cfg["repo"]); cfg["regionen_commit"] = regionen_commits(ref, cfg["regionen"])
    BPa = {b["abk"]: b for b in BP if b.get("abk")}
    REG, plaene, ohne = {}, {}, []
    # Vorlauf: Hauptzuordnung je Plan – eine Dienststelle, die Hauptbahnhof eines Plans ist, wird nie «Teil» eines anderen
    _prim, _netz = {}, {}
    for p in PLANS:
        k = p["key"]
        if k in WERKZEUG or p["gruppe"] == "Region": continue
        f = os.path.join(netz_dir, f"{k}.json") if netz_dir else ""
        _netz[k] = json.load(open(f)) if f and os.path.exists(f) else None
        _prim[k] = finde_dienststellen(p, D, plan_ort(_netz[k], k))
    PRIM = {r["abk"] for v in _prim.values() for r, _ in v}
    for p in PLANS:
        k = p["key"]
        if k in WERKZEUG: continue
        svg = os.path.join(plaene_dir, f"{k}.svg") if plaene_dir else None
        fp = hashlib.sha256(open(svg, "rb").read()).hexdigest()[:12] if svg and os.path.exists(svg) else None
        h = herkunft(p, cfg, sha, ref)
        region = (k[7:] if k.startswith("region_") else "olten") if (k == "region" or k.startswith("region_")) else (
            k.split("__")[0] if "__" in k else "olten" if p["gruppe"].startswith("Olten") else "ne" if p["gruppe"].startswith("NE") else None)
        pl = dict(key=k, name=p["name"], gruppe=p["gruppe"], region=region, fingerabdruck=fp, **h)
        plaene[k] = pl
        if p["gruppe"] == "Region": pl["regionalplan"] = True; continue
        nz = _netz[k]; ort = plan_ort(nz, k); ds = list(_prim[k])
        # Teile desselben Orts (Chambrelien cul-de-sac, Vauseyon bif …): ≤ 1 km, alle Namenswörter des Bahnhofs im Namen,
        # Zug-Halt oder SBB-Betriebspunkt – zählen zum Plan, nicht als «Betriebspunkt ohne Plan»
        for r0, _ in list(ds):
            for r in D:
                if r["abk"] in PRIM or r["abk"] in {x["abk"] for x, _ in ds} or not (r0["t"] < r["t"]): continue
                if dist(r["ll"], r0["ll"]) <= 1000 and (r["verkehrsmittel"] in ("TRAIN", "RACK_RAILWAY") or r["abk"] in BPa):
                    ds.append((r, "teil"))
        if not ds: ohne.append(k); pl["abk"] = []; continue
        pl["abk"] = [r["abk"] for r, _ in ds]
        if ort: pl["ort"] = [round(ort[0], 6), round(ort[1], 6)]
        linien_osm = sorted({g.get("ref") for g in (nz or {}).get("gleise", []) if g.get("ref")} |
                            {a.get("ref") for a in (nz or {}).get("abgaenge", []) if a.get("ref")})
        perr_osm = sorted({t.strip() for x in (nz or {}).get("perrons_osm", []) for t in re.split(r"[;,/]", x.get("ref") or "") if t.strip()})
        for r, wie in ds:
            e = REG.setdefault(r["abk"], dict(abk=r["abk"], name=r["name"], bpuic=int(r["nummer"]),
                                             atlas=[round(r["ll"][0], 6), round(r["ll"][1], 6)], betreiber=r["betreiber_abk"],
                                             verkehrsmittel=r["verkehrsmittel"], plaene=[], regionen=[], linien=[]))
            e["plaene"].append(k)
            if region and region not in e["regionen"]: e["regionen"].append(region)
            if wie != "name": e["zuordnung"] = wie
            b = BPa.get(r["abk"])
            if b and b.get("linie"): e["linie_sbb"] = str(b["linie"]); e["km"] = b.get("km")
            if wie != "teil": e["linien"] = sorted(set(e["linien"]) | set(linien_osm))
            if ort and dist(ort, r["ll"]) > 3000: e["plan_weit_weg_m"] = round(dist(ort, r["ll"]))
            if "osm" not in e:
                o, w = finde_osm(r, ST)
                e["osm"] = None if o is None else dict(node=o["id"], name=o["tags"].get("name"), ref=o["tags"].get("railway:ref"),
                                                        uic_ref=o["tags"].get("uic_ref"), railway=o["tags"]["railway"],
                                                        ll=[o["lat"], o["lon"]], abstand_m=round(dist(o["ll"], r["ll"])), wie=w)
            g = GN.get(r["name"])
            if g and g.get("perrons"):
                e["gleise_perron_sbb"] = sorted({t.strip() for x in g["perrons"] if x.get("nr") for t in re.split(r"[;,/]", str(x["nr"])) if t.strip()}, key=_nk)
            if nz is not None and perr_osm and wie != "teil": e.setdefault("gleise_perron_osm", perr_osm)
    # mehrfach: derselbe Bahnhof in mehreren Werkstätten/Quellen (Anlass Neuchâtel/Onnens-Bonvillars Olten + NE)
    mehrfach = {}
    for k in plaene:
        if plaene[k].get("regionalplan"): continue
        orte = [d for d in ("werkstatt/olten", "werkstatt/ne", "bahnhoefe") if any(
            f.startswith(k + "_") or f == k for f in os.listdir(os.path.join(SP, d)))]
        if len(orte) > 1: mehrfach[k] = orte
    return REG, plaene, ohne, mehrfach, cfg


def _nk(s):
    m = re.match(r"(\d+)(.*)", s); return (int(m.group(1)), m.group(2)) if m else (10 ** 6, s)


# ---------------------------------------------------------------- OSM-Verdacht
def verdacht(REG, plaene, ohne, D, BP, PLANS):
    V = []
    def add(code, abk, text, **kw): V.append(dict(code=code, abk=abk, text=text, **kw))
    for a, e in sorted(REG.items()):
        o = e.get("osm")
        pax = e["verkehrsmittel"] in ("TRAIN", "RACK_RAILWAY")
        if o is None or o["wie"] == "naehe":
            if pax: add("OK", a, f"{e['name']}: keine OSM-Station mit diesem Namen, dieser Abkürzung oder BPUIC"
                                 + (f" (nächste: {o['name']}, {o['abstand_m']} m)" if o else ""))
            continue
        if o["abstand_m"] > AB_M: add("OA", a, f"{e['name']}: OSM-Station {o['abstand_m']} m vom atlas-Punkt", abstand_m=o["abstand_m"])
        ta, to = tok(e["name"]), tok(o["name"])     # Kantonskürzel, «St/Saint» und Ortsvorsatz (Bern Riedbach) sind keine Abweichung
        if not (ta <= to or to <= ta): add("ON", a, f"Name atlas «{e['name']}» ≠ OSM «{o['name']}»")
        if o["ref"] and o["ref"] != a: add("OR", a, f"{e['name']}: Abkürzung atlas {a} ≠ OSM railway:ref {o['ref']}")
        if o["uic_ref"] and o["uic_ref"] != str(e["bpuic"]): add("OU", a, f"{e['name']}: BPUIC atlas {e['bpuic']} ≠ OSM uic_ref {o['uic_ref']}")
        if e.get("linie_sbb") and e["linien"] and e["linie_sbb"] not in e["linien"]:
            add("OL", a, f"{e['name']}: Linie SBB {e['linie_sbb']} (km {e.get('km')}) nicht unter den OSM-Linien im Plan ({', '.join(e['linien'])})")
        s, os_ = e.get("gleise_perron_sbb"), e.get("gleise_perron_osm")
        fehlt = [x for x in (s or []) if x not in set(os_ or [])]
        if s and os_ and fehlt:     # SBB gilt (Vorgabe Daniel): SBB-Gleis mit Perron, das in OSM keinen Perron hat
            add("OG", a, f"{e['name']}: Gleis mit Perron laut SBB {'/'.join(fehlt)} ohne Perron-ref in OSM (SBB {'/'.join(s)} · OSM {'/'.join(os_)})")
        if e.get("plan_weit_weg_m"): add("OP", a, f"{e['name']}: Plan liegt {e['plan_weit_weg_m']} m vom atlas-Punkt (Zuordnung prüfen)")
    for k in ohne: add("OX", None, f"Plan {k} ({plaene[k]['name']}): keine Dienststelle mit Abkürzung gefunden")
    # Betriebspunkt im Perimeter ohne Plan
    reg_abk = set(REG)
    from shapely.geometry import MultiPoint, Point
    for r in sorted({p["region"] for p in plaene.values() if p.get("region")}):
        st = [e for e in REG.values() if r in e["regionen"]]
        if len(st) < 3: continue
        # Perimeter = Vieleck um die Bahnhöfe der Region (REGELN 4.10), ~300 m Rand
        hull = MultiPoint([(e["atlas"][1], e["atlas"][0]) for e in st]).convex_hull.buffer(0.004)
        inn = lambda ll: hull.contains(Point(ll[1], ll[0]))
        rj = os.path.join(SP, "regionen", r, "region.json")
        if os.path.exists(rj):           # Linien-Region: Betreiber aus der Konfig; Halte (Zug/Zahnrad) im Vieleck
            K = json.load(open(rj)); bt = set(K.get("betreiber", [])); integ = {norm(x) for x in K.get("integriert", {})}
            kand = [(x["abk"], x["name"]) for x in D if x["betreiber_abk"] in bt and x["verkehrsmittel"] in ("TRAIN", "RACK_RAILWAY")
                    and inn(x["ll"]) and x["n"] not in integ]
        else:                             # Werkstatt-Region: Personenverkehrs-Betriebspunkte auf den Linien der Bahnhöfe
            lin = {e.get("linie_sbb") for e in st if e.get("linie_sbb")}
            kand = [(b["abk"], b["name"]) for b in BP if b.get("abk") and str(b.get("linie")) in lin and b.get("personenverkehr")
                    and inn((b["lat"], b["lon"]))]
        for a, n in sorted(set(kand)):
            if a not in reg_abk: add("OB", a, f"Region {r}: Betriebspunkt {n} ({a}) im Perimeter ohne Plan", region=r)
    return V


# ---------------------------------------------------------------- Veraltet
def veraltet(plaene, stand, laufend):
    """Plan aus Code, dessen Bau-Commit den letzten Code-Commit nicht enthält. Datei/fest: als «fest» gelistet."""
    out = []
    for k, p in plaene.items():
        if p["art"] in ("fest", "datei"):
            alt = not ist_vorfahr(stand, p.get("commit")) if p.get("commit") else True
            p["veraltet"] = "fest" if alt else False
            if alt: out.append(dict(key=k, art=p["art"], commit=(p.get("commit") or "")[:7], datum=p.get("datum"), quelle=p["quelle"]))
            continue
        ok = ist_vorfahr(stand, p.get("commit"))
        p["veraltet"] = not ok
        if not ok:
            out.append(dict(key=k, art="code", commit=(p.get("commit") or "?")[:7], quelle=p["quelle"], workflow=p["workflow"],
                            wartet=p["workflow"] in laufend))
    return out


# ---------------------------------------------------------------- Karte «OSM-Verdacht»
TITEL = {"OA": "OSM-Station > 150 m vom atlas-Punkt", "ON": "Name atlas ≠ OSM", "OR": "Abkürzung atlas ≠ OSM railway:ref",
         "OU": "BPUIC atlas ≠ OSM uic_ref", "OL": "Linie SBB nicht unter den OSM-Linien im Plan",
         "OG": "Gleise mit Perron SBB ≠ OSM", "OK": "Keine OSM-Station gefunden", "OP": "Plan weit weg vom atlas-Punkt",
         "OX": "Plan ohne Dienststelle", "OB": "Betriebspunkt im Perimeter ohne Plan", "VV": "Plan veraltet (Code neuer als Bau)",
         "VF": "Plan fest / Datei – älter als der Code (bis V4/N2/P2b)",
         "MF": "Bahnhof an mehreren Orten geführt (Werkstatt Olten / NE / Repo)"}


def karte(V, VA, stand, n_reg, n_pl, mehrfach=None):
    zeilen = [("h", f"OSM-Verdacht und Herkunft · Register {n_reg} Bahnhöfe, {n_pl} Pläne · Code-Stand {stand[:7]}"),
              ("t", "Nur Befund, keine Sperre: Daniel entscheidet je Zeile «OSM korrigieren» oder «Ausnahme» (REGELN Ebene 6) – Pin mit A / B."), ("s", "")]
    g = collections.defaultdict(list)
    for v in V: g[v["code"]].append(v["text"])
    for x in VA:
        if x["art"] == "code": g["VV"].append(f"{x['key']} – {x['quelle']}, gebaut mit {x['commit']}" + (" (Lauf läuft noch)" if x.get("wartet") else ""))
        else: g["VF"].append(f"{x['key']} – {x['quelle']}" + (f", Stand {x['datum']}" if x.get("datum") else ""))
    for k, o in sorted((mehrfach or {}).items()): g["MF"].append(f"{k}: Dateien in {', '.join(o)}")
    for c in ("VV", "MF", "OA", "ON", "OR", "OU", "OL", "OG", "OK", "OP", "OX", "OB", "VF"):
        if not g.get(c): continue
        zeilen.append(("g", f"{c} · {TITEL[c]} ({len(g[c])})"))
        for t in (g[c] if c != "VF" else [", ".join(s.split(" – ")[0] for s in g[c])]): zeilen.append(("z", t))
        zeilen.append(("s", ""))
    # lange Zeilen umbrechen
    out = []
    for art, t in zeilen:
        while len(t) > 150:
            i = t.rfind(" ", 0, 150); i = i if i > 40 else 150
            out.append((art, t[:i])); t = "   " + t[i:].lstrip(); art = "z" if art != "h" else "t"
        out.append((art, t))
    y, els = 40, []
    for art, t in out:
        if art == "s": y += 8; continue
        st = {"h": 'font-size="22" font-weight="700"', "g": 'font-size="16" font-weight="700" fill="#a40"',
              "t": 'font-size="14" fill="#555"', "z": 'font-size="14"'}[art]
        els.append(f'<text x="{30 if art != "z" else 50}" y="{y}" {st}>{_html.escape(t)}</text>')
        y += {"h": 30, "g": 24, "t": 20, "z": 19}[art]
    W, H = 1500, y + 20
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">'
            f'<rect width="{W}" height="{H}" fill="#fff"/>' + "".join(els) + "</svg>")


# ---------------------------------------------------------------- Hauptprogramm
def main():
    seite, out = arg("--seite"), arg("--out")
    html = open(seite).read()
    PLANS = json.loads(re.search(r"const PLANS = (\[.*?\]);\n", html, re.S).group(1))
    D, BP, GN, ST = lade_daten(arg("--daten"), arg("--osm"))
    sha = arg("--sha") or git("rev-parse", "HEAD").strip(); ref = arg("--ref", "origin/ergebnisse")
    REG, plaene, ohne, mehrfach, cfg = bauen(PLANS, arg("--plaene"), arg("--netz-dir"), D, BP, GN, ST, sha, ref)
    stand = code_stand(arg("--main", "HEAD"))
    laufend = set(filter(None, (arg("--laufend", "") or "").split(",")))
    VA = veraltet(plaene, stand, laufend)
    V = verdacht(REG, plaene, ohne, D, BP, PLANS)
    ausn = json.load(open(os.path.join(SP, "netz", "osm_ausnahmen.json"))) if os.path.exists(os.path.join(SP, "netz", "osm_ausnahmen.json")) else {}
    V = [v for v in V if f"{v['code']}:{v['abk']}" not in ausn]       # REGELN 6: von Daniel als Ausnahme bestätigt
    os.makedirs(out, exist_ok=True)
    R = dict(_zweck="Bahnhofregister (V3, 20.11.2026): jeder Bahnhof einmal, Schlüssel SBB-Abkürzung. Erzeugt von code/bahnhofregister.py im Workflow seite.",
             code_stand=stand, seite_commit=sha, bahnhoefe=dict(sorted(REG.items())), plaene=plaene, ohne_dienststelle=ohne, mehrfach=mehrfach)
    json.dump(R, open(os.path.join(out, "register.json"), "w"), ensure_ascii=False, indent=1)
    if arg("--stabil"):
        S = dict(R); S.pop("code_stand"); S.pop("seite_commit")
        S["plaene"] = {k: {x: v for x, v in p.items() if x not in ("commit", "fingerabdruck", "veraltet", "datum")} for k, p in plaene.items()}
        S["_zweck"] = R["_zweck"] + " Ohne Commit/Fingerabdruck (die stehen auf «ergebnisse» in seite/register/register.json)."
        os.makedirs(os.path.dirname(os.path.abspath(arg("--stabil"))), exist_ok=True)
        json.dump(S, open(arg("--stabil"), "w"), ensure_ascii=False, indent=1)
    json.dump(V, open(os.path.join(out, "osm_verdacht.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(out, "osm_verdacht.md"), "w") as f:
        f.write(f"# OSM-Verdacht ({len(V)}) – Register {len(REG)} Bahnhöfe, {len(plaene)} Pläne\n\n")
        for c, n in collections.Counter(v["code"] for v in V).most_common(): f.write(f"- {c} {TITEL[c]}: {n}\n")
        f.write("\n| Code | Abk | Befund |\n|---|---|---|\n")
        for v in V: f.write(f"| {v['code']} | {v['abk'] or ''} | {v['text']} |\n")
        if mehrfach: f.write("\n## Mehrfach geführt\n\n" + "".join(f"- {k}: {', '.join(o)}\n" for k, o in sorted(mehrfach.items())))
    open(os.path.join(out, "osm_verdacht.svg"), "w").write(karte(V, VA, stand, len(REG), len(plaene), mehrfach))
    basis = set(json.load(open(arg("--basis")))["fest"]) if arg("--basis") and os.path.exists(arg("--basis")) else set()
    neu = [x for x in VA if x["art"] == "code" and x["key"] not in basis and not x.get("wartet")]
    neu += [x for x in VA if x["art"] != "code" and x["key"] not in basis]
    with open(os.path.join(out, "veraltet.md"), "w") as f:
        f.write(f"# Veraltet gegen Code-Stand {stand[:7]}\n\n")
        for x in VA: f.write(f"- {'NEU ' if x in neu else ''}{x['key']}: {x['quelle']}, Commit {x.get('commit') or '-'}"
                             f"{' (Lauf läuft noch)' if x.get('wartet') else ''}\n")
    print(f"Register: {len(REG)} Bahnhöfe, {len(plaene)} Pläne, ohne Dienststelle {len(ohne)}, mehrfach {len(mehrfach)}; "
          f"OSM-Verdacht {len(V)} " + str(dict(collections.Counter(v['code'] for v in V))) +
          f"; veraltet {sum(1 for x in VA if x['art'] == 'code')} aus Code, {sum(1 for x in VA if x['art'] != 'code')} fest/Datei; Code-Stand {stand[:7]}")
    for x in neu: print("NEU veraltet:", x["key"], x["quelle"], x.get("commit"))
    return 1 if neu else 0


def selbsttest():
    """Sperre greift: ein Plan aus Code, gebaut mit einem Commit vor dem letzten Code-Commit, ist veraltet (→ rot);
    gebaut mit dem Code-Stand selbst ist er es nicht."""
    stand = code_stand()
    vor = git("log", "-1", "--format=%H", f"{stand}~1").strip() if stand else ""
    if not stand or not vor: print("Selbsttest: zu wenig Geschichte (fetch-depth)"); return 1
    P = {"alt": dict(art="code", commit=vor, quelle="Test", workflow="regionen"),
         "neu": dict(art="code", commit=stand, quelle="Test", workflow="regionen"),
         "wartet": dict(art="code", commit=vor, quelle="Test", workflow="plaene")}
    VA = {x["key"]: x for x in veraltet(P, stand, {"plaene"})}
    ok = "alt" in VA and "neu" not in VA and VA.get("wartet", {}).get("wartet") is True
    print("Selbsttest veraltet:", "bestanden" if ok else f"NICHT bestanden {VA}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selbsttest() if "--selbsttest" in sys.argv else main())
