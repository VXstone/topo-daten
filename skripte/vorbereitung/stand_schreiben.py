"""Ergebnis der Vorbereitung in stand.json festhalten (Schlüssel "vorbereitung"; die übrigen Schlüssel bleiben).

python3 stand_schreiben.py <eingang> <aus> <stand.json>
Umgebung: SCHRITTE="name=outcome;…" (Ergebnis jedes Workflow-Schritts: success|failure|skipped).
Inhalt: Zeitpunkt, Status je SBB-Datensatz (OK/fehlt, ID, Anzahl, Felder, Kandidaten aus dem Katalog), Musterzeilen,
Zahlen der Ergebnisse und eine Stichprobe bekannter Betriebspunkte – weil Claude die Lauf-Logs nicht lesen kann.
"""
import sys, os, json, gzip, zipfile, datetime, unicodedata

ein, aus, stand_pfad = sys.argv[1:4]


def lade(p):
    try:
        return json.load(gzip.open(p, "rt") if p.endswith(".gz") else open(p))
    except Exception:
        return None


st = lade(stand_pfad) or {}
v = dict(erzeugt=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
         lauf=os.environ.get("LAUF", ""), schritte={}, datensaetze={}, ergebnisse={}, stichprobe={}, muster={})
for t in filter(None, os.environ.get("SCHRITTE", "").split(";")):
    k, _, o = t.partition("="); v["schritte"][k] = "OK" if o == "success" else (o or "?")

prot = lade(f"{ein}/sbb_laden.json") or {}
for ziel, e in prot.items():
    v["datensaetze"][ziel] = e
    gj = lade(f"{ein}/{ziel}.geojson")
    if gj and gj.get("features"):
        v["muster"][ziel] = [f.get("properties") for f in gj["features"][:3]]
# Perronkanten (verdichtet aus 21196_behig-haltekantepunkt): Gleisnummern und Lage je Kante
pk = lade(f"{aus}/perronkanten.json")
if isinstance(pk, list):
    _f = lambda z: unicodedata.normalize("NFKD", z or "").encode("ascii", "ignore").decode().lower()
    def _bsp(nm):
        return sorted([(x["bps"], x["gleis"], x["laenge"]) for x in pk if _f(x["bps"]) == _f(nm)], key=lambda t: str(t[1]))
    v["perronkanten"] = dict(status="OK", kanten=len(pk), betriebspunkte=len({x["bps"] for x in pk}),
                             mit_gleisnummer=sum(1 for x in pk if x.get("gleis")),
                             beispiele={nm: _bsp(nm) for nm in ("Grandson", "Les Hauts-Geneveys", "Neuchâtel", "Olten", "Rothrist", "Môtiers", "Couvet")})
else:
    v["perronkanten"] = dict(status="fehlt")
v["datensaetze"]["schweiz_bahn (OSM, Release daten)"] = dict(status="OK" if os.path.exists(f"{ein}/schweiz_bahn.json.gz") else "fehlt")

bp = lade(f"{aus}/betriebspunkte.json")
if isinstance(bp, list):
    q = {}
    for x in bp:
        k = "+".join(sorted(x.get("quellen", []))); q[k] = q.get(k, 0) + 1
    v["ergebnisse"]["betriebspunkte"] = dict(status="OK", anzahl=len(bp), nach_quellen=q,
                                             ohne_osm_stationsknoten=sum(1 for x in bp if not x.get("osm_node")),
                                             mit_ersatzknoten=sum(1 for x in bp if x.get("synthetisch_node")),
                                             personenverkehr=sum(1 for x in bp if x.get("personenverkehr")))
    for nm in ("Olten", "Olten Ost", "Rothrist", "Neuchâtel", "Neuchâtel-Vauseyon", "Onnens-Bonvillars", "Ligerz",
               "Gümmenen", "Les Deurres", "Riedbach"):
        _n = lambda z: unicodedata.normalize("NFKD", z or "").encode("ascii", "ignore").decode().lower()   # Neuchatel = Neuchâtel
        t = [x for x in bp if _n(x.get("name")).startswith(_n(nm))][:4]
        v["stichprobe"][nm] = [{k: x.get(k) for k in ("name", "abk", "typ", "bahnhof", "quellen", "osm_node", "synthetisch_node", "personenverkehr")} for x in t] or "nicht gefunden"
else:
    v["ergebnisse"]["betriebspunkte"] = dict(status="fehlt")

gn = lade(f"{aus}/gleisnummern.json")
if isinstance(gn, dict):
    v["ergebnisse"]["gleisnummern"] = dict(status="OK", betriebspunkte=len(gn),
                                           quelle_sbb_kante=sum(1 for x in gn.values() if x.get("quelle") == "SBB-Kante"),
                                           quelle_sbb=sum(1 for x in gn.values() if x.get("quelle") == "SBB"),
                                           quelle_osm=sum(1 for x in gn.values() if x.get("quelle") == "OSM"),
                                           mit_fragezeichen=sum(1 for x in gn.values() if any(q.get("nr") == "?" for q in x.get("querschnitt", []))),
                                           gross_von_hand=sum(1 for x in gn.values() if x.get("gross")))
    for nm in ("Grandson", "Les Hauts-Geneveys", "Concise", "Neuchâtel", "Couvet", "Môtiers", "Riedbach", "Gorgier-St-Aubin", "Bevaix", "Olten", "Onnens-Bonvillars"):
        _nn = lambda z: unicodedata.normalize("NFKD", z or "").encode("ascii", "ignore").decode().lower().replace("saint", "st")
        x = gn.get(nm) or next((w for k, w in gn.items() if _nn(k).startswith(_nn(nm))), None)
        v["stichprobe"]["Gleisnummern " + nm] = ([q.get("nr") for q in x.get("querschnitt", [])] + ([x.get("quelle")] if x.get("quelle") else [])) if x else "nicht gefunden"
else:
    v["ergebnisse"]["gleisnummern"] = dict(status="fehlt")

reg = {}
for f in sorted(os.listdir(aus)) if os.path.isdir(aus) else []:
    if f.startswith("bahnhoefe_") and f.endswith(".zip"):
        try: reg[f] = dict(status="OK", dateien=len(zipfile.ZipFile(f"{aus}/{f}").namelist()))
        except Exception: reg[f] = dict(status="fehlt")
    if f.startswith("region_") and f.endswith(".json.gz"):
        reg[f] = dict(status="OK", mb=round(os.path.getsize(f"{aus}/{f}") / 1e6, 1))
v["ergebnisse"]["ausschnitte"] = reg or dict(status="fehlt")
ae = lade(f"{aus}/aenderungen.json")
v["ergebnisse"]["aenderungen"] = (dict(status="OK", **({"hinweis": ae["hinweis"]} if "hinweis" in ae else {"betriebspunkte_mit_aenderung": len(ae) if isinstance(ae, (list, dict)) else None}))
                                  if ae is not None else dict(status="fehlt"))

st["vorbereitung"] = v
json.dump(st, open(stand_pfad, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v[k] for k in ("schritte", "ergebnisse")}, ensure_ascii=False, indent=1))
for z, e in v["datensaetze"].items(): print(z, e.get("status"), e.get("id"), e.get("anzahl"))
