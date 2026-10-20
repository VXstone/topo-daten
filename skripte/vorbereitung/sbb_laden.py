"""SBB Open Data (data.sbb.ch) laden – robust gegen geänderte Datensatz-IDs (20.10.2026).

python3 sbb_laden.py <eingang> <protokoll.json>
Je Ziel werden bekannte IDs der Reihe nach versucht; scheitern alle, sucht das Skript im Katalog nach Stichworten
und versucht die Treffer. Ergebnis je Ziel: Datei <eingang>/<ziel>.geojson und ein Protokolleintrag
{status: OK|fehlt, id, anzahl, geometrie, felder, versucht, katalog}. Das Protokoll landet in stand.json,
weil die Lauf-Logs ausserhalb von GitHub nicht lesbar sind.
"""
import sys, json, urllib.request, urllib.parse, collections

B = "https://data.sbb.ch/api/explore/v2.1/catalog/datasets"
UA = {"User-Agent": "topo-daten (GitHub Actions)"}
ZIELE = {
    "perronoberflache": dict(ids=["perronoberflache"], suche=["perronoberfl"]),
    "perronkante": dict(ids=["perronkante", "perronkanten", "haltestelle-perronkante", "haltestelle-perronkante-inkl-bls", "haltestelle-haltekante"],
                        suche=["perronkante", "haltekante"]),
    "betriebspunkte": dict(ids=["linie-mit-betriebspunkten", "dienststellen-gemass-opentransportdata-ch-didok",
                                "betriebspunkte", "betriebspunkt"], suche=["betriebspunkt", "dienststelle", "didok"]),
}


def hole(url, timeout=300):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def katalog(wort):
    q = urllib.parse.urlencode({"where": f'search("{wort}")', "select": "dataset_id", "limit": 50})
    try:
        return [d.get("dataset_id") for d in json.loads(hole(f"{B}?{q}", 60)).get("results", [])]
    except Exception as e:
        return [f"Fehler: {type(e).__name__}"]


def versuche(ds, ziel_pfad):
    raw = hole(f"{B}/{ds}/exports/geojson")
    d = json.loads(raw)
    fs = d.get("features", [])
    if not fs: raise ValueError("leer")
    open(ziel_pfad, "wb").write(raw)
    felder = sorted({k for f in fs[:200] for k in (f.get("properties") or {})})
    geo = collections.Counter((f.get("geometry") or {}).get("type") for f in fs[:2000])
    return dict(anzahl=len(fs), felder=felder[:60], geometrie=dict(geo))


KANTE_FELDER = ("designation", "gleis", "kante", "track", "length", "lange", "laenge", "nummer")


def PRUEF_KANTE(pfad, info=None):
    """Brauchbar als Perronkanten, wenn >= 10 % der Objekte ein Kanten-/Gleis-/Längenfeld mit Wert haben."""
    fs = json.load(open(pfad)).get("features", [])
    ok = lambda pr: any(v not in (None, "", 0, "ok", "true", "false", True, False) and any(w in k.lower() for w in KANTE_FELDER)
                        and "sloid" not in k.lower() and k.lower() != "haltekante"          # "haltekante": "ok" ist nur ein Merker
                        for k, v in (pr or {}).items())
    mit = sum(1 for f in fs if ok(f.get("properties")))
    if info is not None:
        info["felder"] = sorted({k for f in fs[:200] for k in (f.get("properties") or {})})[:60]
        info["muster"] = [f.get("properties") for f in fs[:2]]; info["mit_kantenfeld"] = mit; info["anzahl"] = len(fs)
    return mit >= 0.1 * max(len(fs), 1)


ein, prot = sys.argv[1], sys.argv[2]
P = {}
for ziel, cfg in ZIELE.items():
    e = dict(status="fehlt", id=None, versucht=[])
    e["katalog"] = {w: katalog(w) for w in cfg["suche"]}       # Kandidaten immer festhalten (Wahl im nächsten Lauf)
    gefunden = [x for v in e["katalog"].values() for x in v if x and not x.startswith("Fehler")]
    for ds in list(dict.fromkeys(cfg["ids"] + gefunden)):
        try:
            r_ = versuche(ds, f"{ein}/{ziel}.geojson")
            _inf = {}
            if ziel == "perronkante" and not PRUEF_KANTE(f"{ein}/{ziel}.geojson", _inf):
                # haltestelle-haltekante liefert nur Haltestellen ohne Kantennummer/Länge (Lauf 20.10.) -> nicht brauchbar
                e["versucht"].append(f"{ds}: geladen, aber ohne Kantennummer/Länge"); e.setdefault("abgelehnt", {})[ds] = _inf; continue
            e.update(r_); e.update(status="OK", id=ds); e["versucht"].append(f"{ds}: OK"); break
        except Exception as x:
            e["versucht"].append(f"{ds}: {type(x).__name__} {str(x)[:80]}")
    if e["status"] != "OK":
        import os
        if os.path.exists(f"{ein}/{ziel}.geojson") and ziel == "perronkante": os.rename(f"{ein}/{ziel}.geojson", f"{ein}/{ziel}_unbrauchbar.geojson")
    P[ziel] = e
    print(ziel, e["status"], e["id"], e.get("anzahl"))
json.dump(P, open(prot, "w"), ensure_ascii=False, indent=1)
