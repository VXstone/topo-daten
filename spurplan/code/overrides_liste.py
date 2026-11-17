"""Liste aller Ausnahmen je Ort (REGELN 6, Schritt V0/B1 17.11.2026).

  python3 spurplan/code/overrides_liste.py [--out <ordner>]      (Standard: Ausgabe auf stdout; mit --out overrides.md/.json)

Quellen: spurplan/bahnhoefe/*/…override*.json (Repo-Bahnhöfe), spurplan/werkstatt/{olten,ne}/**/…override*.json
(Werkstatt), spurplan/regionen/*/region.json (Optionen je Bahnhof). Jeder Schlüssel wird einer Art zugeordnet:
  Ortswissen   – nicht in OSM/SBB-Daten (Perronlage, Nummern, Personenverkehr): erlaubt (REGELN 6)
  Schalter     – cfg: Regel-Parameter je Ort; Ziel V2 = Standard für alle, Ausnahme nur mit Grund
  Typvorlage   – NE-Typvorlage (fest seit 21.10.), fällt mit N2 weg
  Geometrie    – Lage/Topologie von Hand (zeichnen, gerade, knoten, abgang …): nach Entscheid 13.11. abbauen (V2/N1/N2)
Grund = Feld «_quelle»/«_grund»/«_zweck» der Datei bzw. des Eintrags; fehlt er, steht «Grund fehlt».
"""
import collections, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
ORT = {"platforms", "perrons_px", "_gleisnummern", "nummern_weg", "nummern_px", "pax", "pax_ways", "r47_pax", "_perrons",
       "perron_einheitlich", "meterspur", "meterspur_cfg", "_behalten", "behalten"}
GRUND = ("_quelle", "_grund", "_zweck", "_anlass")
INFO = {"_aenderungen", "_knoten_lane"}


def art(k):
    if k in ORT: return "Ortswissen"
    if k == "cfg": return "Schalter"
    if k == "vorlage": return "Typvorlage"
    return "Geometrie"


def grund_von(d):
    for g in GRUND:
        v = d.get(g) if isinstance(d, dict) else None
        if v: return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)[:160]
    return None


def sammeln():
    zeilen = []
    for f in sorted(glob.glob(os.path.join(SP, "bahnhoefe", "**", "*override*.json"), recursive=True)
                    + glob.glob(os.path.join(SP, "werkstatt", "**", "*override*.json"), recursive=True)):
        rel = os.path.relpath(f, SP)
        try: d = json.load(open(f))
        except Exception as e: zeilen.append(dict(datei=rel, ort="?", schluessel="(unlesbar)", art="?", grund=str(e))); continue
        if not isinstance(d, dict): continue
        ort = re.sub(r"_?override(_\w+)?\.json$", "", os.path.basename(f)) or os.path.basename(os.path.dirname(f))
        weg = "Repo" if rel.startswith("bahnhoefe") else ("Werkstatt Olten" if "/olten" in rel else "Werkstatt NE")
        g0 = grund_von(d)
        # Sammeldateien (z. B. ne_vorlagen_overrides.json): je Bahnhof ein Eintrag
        if all(isinstance(v, dict) for k, v in d.items() if not k.startswith("_")) and not ({"cfg", "zeichnen", "platforms"} & set(d)):
            for o, dd in d.items():
                if o.startswith("_"): continue
                for k, v in dd.items():
                    if k in GRUND or k in INFO: continue
                    zeilen.append(dict(datei=rel, weg=weg, ort=o, schluessel=k, art=art(k), grund=grund_von(dd) or g0,
                                       umfang=len(v) if isinstance(v, (list, dict)) else 1))
            continue
        for k, v in d.items():
            if k in GRUND or k in INFO: continue
            if k == "cfg" and isinstance(v, dict):
                for c in v:
                    zeilen.append(dict(datei=rel, weg=weg, ort=ort, schluessel=f"cfg.{c}", art="Schalter", grund=g0, umfang=1))
                continue
            zeilen.append(dict(datei=rel, weg=weg, ort=ort, schluessel=k, art=art(k), grund=g0,
                               umfang=len(v) if isinstance(v, (list, dict)) else 1))
    for f in sorted(glob.glob(os.path.join(SP, "regionen", "*", "region.json"))):
        rel = os.path.relpath(f, SP); d = json.load(open(f)); reg = os.path.basename(os.path.dirname(f))
        for o, dd in (d.get("optionen_je") or d.get("bahnhoefe") or {}).items():
            if isinstance(dd, list):
                for k in dd: zeilen.append(dict(datei=rel, weg=f"Region {reg}", ort=o, schluessel=str(k), art="Schalter",
                                                grund=d.get("_zweck", "")[:60] or None, umfang=1))
                continue
            if not isinstance(dd, dict): continue
            for k, v in dd.items():
                if k in GRUND: continue
                zeilen.append(dict(datei=rel, weg=f"Region {reg}", ort=o, schluessel=k, art=art(k) if k != "cfg" else "Schalter",
                                   grund=grund_von(dd), umfang=len(v) if isinstance(v, (list, dict)) else 1))
    return zeilen


def md(z):
    a = collections.Counter(x["art"] for x in z); orte = collections.defaultdict(collections.Counter)
    for x in z: orte[(x["weg"], x["ort"])][x["art"]] += 1
    o = [f"# Ausnahmen je Ort (REGELN 6) – {len(z)} Einträge an {len(orte)} Orten: " + ", ".join(f"{v} {k}" for k, v in a.most_common()),
         "", "Erzeugt von `spurplan/code/overrides_liste.py`. Ziel (Entscheid 13.11.): nur Ortswissen bleibt; Geometrie abbauen.", "",
         "## Je Ort", "", "| Weg | Ort | Ortswissen | Schalter | Typvorlage | Geometrie |", "|---|---|---|---|---|---|"]
    for (w, ort), c in sorted(orte.items(), key=lambda kv: (-kv[1]["Geometrie"], kv[0])):
        o.append(f"| {w} | {ort} | {c['Ortswissen'] or ''} | {c['Schalter'] or ''} | {c['Typvorlage'] or ''} | {c['Geometrie'] or ''} |")
    o += ["", "## Einträge", "", "| Weg | Ort | Schlüssel | Art | Umfang | Grund | Datei |", "|---|---|---|---|---|---|---|"]
    for x in sorted(z, key=lambda x: (x["weg"], x["ort"], x["art"], x["schluessel"])):
        g = (x.get("grund") or "Grund fehlt").replace("|", "/").replace("\n", " ")[:140]
        o.append(f"| {x['weg']} | {x['ort']} | {x['schluessel']} | {x['art']} | {x.get('umfang', '')} | {g} | {x['datei']} |")
    return "\n".join(o) + "\n"


if __name__ == "__main__":
    z = sammeln()
    if "--out" in sys.argv:
        d = sys.argv[sys.argv.index("--out") + 1]; os.makedirs(d, exist_ok=True)
        json.dump(z, open(os.path.join(d, "overrides.json"), "w"), ensure_ascii=False, indent=1)
        open(os.path.join(d, "overrides.md"), "w").write(md(z))
    a = collections.Counter(x["art"] for x in z)
    print(f"Ausnahmen: {len(z)} Einträge, {len({(x['weg'], x['ort']) for x in z})} Orte:", dict(a),
          "| ohne Grund:", sum(1 for x in z if not x.get("grund")))
