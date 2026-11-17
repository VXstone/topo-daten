"""Alle Dienststellen aus atlas (Nachfolger DIDOK) – Bahn (SBB und andere), Tram, Bus, Schiff, Seilbahn, Betriebspunkte.

python3 dienststellen.py <eingang> <aus> [lokale.csv|.zip]   (lokale Datei: ohne Download, zum Testen)

Quelle 1: opentransportdata.swiss / opendata.swiss, Datensatz «service-point» (atlas v2),
          Ressource «actual-date-swiss-service-point» (nur heute gültige Versionen), über die CKAN-API gesucht,
          weil sich die Datei-URL bei jeder Publikation ändert.
Quelle 2 (Ersatz): data.sbb.ch «dienststellen-gemass-opentransportdataswiss» (CSV-Export).

Ergebnis in <aus>:
  dienststellen.csv.gz      eine Zeile je Dienststelle, einheitliche Spalten (siehe SPALTEN)
  dienststellen_roh.csv.gz  die Quelldatei unverändert (alle Felder)
  dienststellen_stand.json  Quelle, Anzahl, Zahlen je Verkehrsmittel, Spalten, Stichprobe (auch für stand.json)
Nur Python-Standardbibliothek.
"""
import sys, os, io, csv, json, gzip, zipfile, datetime, unicodedata, urllib.request

ein, aus = sys.argv[1:3]
os.makedirs(ein, exist_ok=True); os.makedirs(aus, exist_ok=True)
UA = {"User-Agent": "topo-daten (GitHub Actions; +https://github.com/VXstone/topo-daten)"}

CKAN = ["https://data.opentransportdata.swiss/api/3/action/package_show?id={}",
        "https://ckan.opendata.swiss/api/3/action/package_show?id={}",
        "https://opendata.swiss/api/3/action/package_show?id={}"]
SLUGS = ["service-point-v2", "service-points-actual-date", "service-points-full", "service-point"]
BEVORZUGT = ["actual-date-swiss-service-point", "actual_date-swiss-service-point", "swiss-service-point"]
SBB_ERSATZ = ["https://data.sbb.ch/api/explore/v2.1/catalog/datasets/{}/exports/csv?delimiter=%3B",
              ]
SBB_IDS = ["dienststellen-gemass-opentransportdataswiss", "dienststellen-gemass-opentransportdata-ch-didok"]

# Ausgabespalte -> mögliche Quellspalten (normalisiert: klein, nur a-z0-9_)
ALIAS = {
    "nummer": ["number", "servicepointnumber", "bpuic", "didok", "didok_code", "nummer"],
    "nummer_kurz": ["numbershort", "number_short", "didok_kurz"],
    "land": ["uiccountrycode", "uic_country_code", "laendercode"],
    "sloid": ["sloid"],
    "abk": ["abbreviation", "abkuerzung", "abkurzung", "abk", "operatingpointabbreviation"],
    "name": ["designationofficial", "designation_official", "bezeichnung_offiziell", "designationlong", "name", "bezeichnung"],
    "name_lang": ["designationlong", "designation_long", "langbezeichnung"],
    "lat": ["wgs84north", "wgs84_north", "lat", "latitude", "n_wgs84"],
    "lon": ["wgs84east", "wgs84_east", "lon", "lng", "longitude", "e_wgs84"],
    "geopos": ["geopos", "geo_point_2d", "geoposition"],
    "lv95e": ["lv95east", "lv95_east", "e_lv95"],
    "lv95n": ["lv95north", "lv95_north", "n_lv95"],
    "hoehe": ["height", "hoehe", "z"],
    "verkehrsmittel": ["meansoftransport", "means_of_transport", "verkehrsmittel"],
    "haltestelle": ["stoppoint", "stop_point", "haltestelle"],
    "haltestellentyp": ["stoppointtype", "stop_point_type"],
    "betriebspunkt": ["operatingpoint", "operating_point", "betriebspunkt"],
    "betriebspunkt_fahrplan": ["operatingpointwithtimetable", "operating_point_with_timetable"],
    "betriebspunkt_typ": ["operatingpointtype", "operating_point_type", "operatingpointtechnicaltimetabletype",
                          "operatingpointtraffictype"],
    "gueterverkehr": ["freightservicepoint", "freight_service_point"],
    "grenzpunkt": ["borderpoint", "border_point"],
    "betreiber_abk": ["businessorganisationabbreviationde", "businessorganisationabbreviation", "go_abkuerzung_de"],
    "betreiber": ["businessorganisationdescriptionde", "businessorganisationdescription", "go_bezeichnung_de"],
    "betreiber_sboid": ["businessorganisation", "sboid"],
    "gemeinde": ["localityname", "municipalityname", "gemeindename"],
    "kanton": ["cantonabbreviation", "kantonskuerzel", "cantonname"],
    "status": ["status"],
    "gueltig_von": ["validfrom", "valid_from", "gueltig_von"],
    "gueltig_bis": ["validto", "valid_to", "gueltig_bis"],
}
SPALTEN = ["nummer", "sloid", "abk", "name", "name_lang", "lat", "lon", "hoehe", "verkehrsmittel", "haltestelle",
           "haltestellentyp", "betriebspunkt", "betriebspunkt_fahrplan", "betriebspunkt_typ", "gueterverkehr", "grenzpunkt",
           "betreiber_abk", "betreiber", "betreiber_sboid", "gemeinde", "kanton", "status", "gueltig_von", "gueltig_bis"]

prot = dict(erzeugt=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), versucht=[])


def hole_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def lade(url, ziel):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(ziel, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b)
    return ziel


def atlas():
    for slug in SLUGS:
        for api in CKAN:
            u = api.format(slug)
            try:
                pkg = hole_json(u)
            except Exception as e:
                prot["versucht"].append(f"{u}: {type(e).__name__} {e}"[:200]); continue
            if not pkg.get("success"):
                prot["versucht"].append(f"{u}: success=false"); continue
            res = pkg["result"].get("resources", [])
            for pref in BEVORZUGT:
                kand = []
                for r in res:
                    d = r.get("download_url") or r.get("url") or ""
                    if pref in d.lower() and d.lower().split("?")[0].endswith((".csv", ".zip")):
                        kand.append((r.get("issued") or r.get("created") or "", d))
                if kand:
                    kand.sort(reverse=True)
                    ausgabe, d = kand[0]
                    name = d.split("?")[0].rsplit("/", 1)[-1]
                    try:
                        p = lade(d, f"{ein}/{name}")
                    except Exception as e:
                        prot["versucht"].append(f"{d}: {type(e).__name__} {e}"[:200]); continue
                    prot.update(quelle="atlas (opentransportdata.swiss)", datensatz=slug, datei=name, url=d, publiziert=ausgabe)
                    prot["versucht"].append(f"{u}: OK {name}")
                    return p
            prot["versucht"].append(f"{u}: {len(res)} Ressourcen, keine passt")
    return None


def sbb_ersatz():
    for ds in SBB_IDS:
        for vorlage in SBB_ERSATZ:
            u = vorlage.format(ds)
            try:
                p = lade(u, f"{ein}/{ds}.csv")
            except Exception as e:
                prot["versucht"].append(f"{u}: {type(e).__name__} {e}"[:200]); continue
            if os.path.getsize(p) < 1000:
                prot["versucht"].append(f"{u}: zu klein"); continue
            prot.update(quelle="data.sbb.ch (Ersatz)", datensatz=ds, datei=os.path.basename(p), url=u)
            prot["versucht"].append(f"{u}: OK")
            return p
    return None


def oeffne(p):
    if zipfile.is_zipfile(p):
        z = zipfile.ZipFile(p)
        n = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        return io.TextIOWrapper(z.open(n), encoding="utf-8-sig", newline="")
    return open(p, encoding="utf-8-sig", newline="")


norm = lambda s: "".join(c for c in (s or "").lower().strip().lstrip("﻿") if c.isalnum() or c == "_")


def zahl(v):
    try:
        return float(str(v).replace(",", ".")) if v not in (None, "") else None
    except ValueError:
        return None


def lv95_wgs84(e, n):
    y, x = (e - 2600000) / 1e6, (n - 1200000) / 1e6
    lon = 2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x * x - 0.0436 * y ** 3
    lat = 16.9023892 + 3.238272 * x - 0.270978 * y * y - 0.002528 * x * x - 0.0447 * y * y * x - 0.0140 * x ** 3
    return lat * 100 / 36, lon * 100 / 36


if len(sys.argv) > 3:
    quelle = sys.argv[3]; prot.update(quelle="lokal", datei=os.path.basename(quelle))
else:
    quelle = atlas() or sbb_ersatz()
if not quelle:
    prot["status"] = "fehlt"
    json.dump(prot, open(f"{aus}/dienststellen_stand.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(prot, ensure_ascii=False, indent=1)); sys.exit(1)

with oeffne(quelle) as f0:
    kopf = f0.readline()
trenner = max(";,\t", key=kopf.count)
f = oeffne(quelle)
rd = csv.DictReader(f, delimiter=trenner)
kopf = rd.fieldnames or []
nk = {norm(h): h for h in kopf}
col = {k: next((nk[norm(a)] for a in al if norm(a) in nk), None) for k, al in ALIAS.items()}
if col["name_lang"] == col["name"]: col["name_lang"] = None
prot["quellspalten"] = kopf
prot["zuordnung"] = {k: v for k, v in col.items() if v}
prot["nicht_gefunden"] = [k for k, v in col.items() if not v]

heute = datetime.date.today().isoformat()
beste = {}
for row in rd:
    g = lambda k: (row.get(col[k]) or "").strip() if col[k] else ""
    try:
        if g("nummer"): num = int(float(g("nummer")))
        else: num = int(g("land")) * 100000 + int(g("nummer_kurz"))
    except (TypeError, ValueError):
        continue
    if num < 1000000: num += 8500000            # Kurznummer ohne Ländercode -> Schweiz
    von, bis = g("gueltig_von")[:10], g("gueltig_bis")[:10]
    lat, lon = zahl(g("lat")), zahl(g("lon"))
    if (lat is None or lon is None) and g("geopos"):
        t = g("geopos").replace(";", ",").split(",")
        if len(t) == 2: lat, lon = zahl(t[0]), zahl(t[1])
    if (lat is None or lon is None) and g("lv95e") and g("lv95n"):
        e, n = zahl(g("lv95e")), zahl(g("lv95n"))
        if e and n and e > 2e6: lat, lon = lv95_wgs84(e, n)
    z = {k: g(k) for k in SPALTEN if k not in ("nummer", "lat", "lon")}
    z.update(nummer=num, lat=round(lat, 6) if lat is not None else "", lon=round(lon, 6) if lon is not None else "",
             verkehrsmittel=z["verkehrsmittel"].replace(",", "|").replace(";", "|").replace(" ", ""))
    # mehrere Versionen: die heute gültige, sonst die mit dem spätesten Gültigkeitsende
    rang = (von <= heute <= bis if von and bis else True, bis, von)
    if num not in beste or rang >= beste[num][0]:
        beste[num] = (rang, z)

zeilen = sorted((z for _, z in beste.values()), key=lambda z: z["nummer"])
with gzip.open(f"{aus}/dienststellen.csv.gz", "wt", encoding="utf-8", newline="") as fo:
    w = csv.DictWriter(fo, fieldnames=SPALTEN, delimiter=";")
    w.writeheader(); w.writerows(zeilen)
with open(quelle, "rb") as fi, gzip.open(f"{aus}/dienststellen_roh.csv.gz", "wb") as fo:
    if zipfile.is_zipfile(quelle):
        zf = zipfile.ZipFile(quelle); fo.write(zf.read(next(n for n in zf.namelist() if n.lower().endswith(".csv"))))
    else:
        fo.write(fi.read())

vm = {}
for z in zeilen:
    for t in (z["verkehrsmittel"] or "ohne (Betriebspunkt)").split("|"):
        vm[t] = vm.get(t, 0) + 1
ascii_ = lambda s: unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
prot.update(status="OK", anzahl=len(zeilen),
            mit_abkuerzung=sum(1 for z in zeilen if z["abk"]),
            mit_koordinaten=sum(1 for z in zeilen if z["lat"] != ""),
            schweiz=sum(1 for z in zeilen if 8500000 <= z["nummer"] < 8600000),
            je_verkehrsmittel=dict(sorted(vm.items(), key=lambda t: -t[1])),
            stichprobe={nm: [{k: z[k] for k in ("nummer", "abk", "name", "verkehrsmittel", "betreiber_abk", "lat", "lon")}
                             for z in zeilen if ascii_(z["name"]).startswith(ascii_(nm))][:3] or "nicht gefunden"
                        for nm in ("Neuchâtel", "Fleurier", "Köniz", "Bern, Bümpliz", "Zürich, Paradeplatz", "Olten Ost",
                                   "Genève, Bel-Air", "Interlaken Ost", "Zermatt")})
json.dump(prot, open(f"{aus}/dienststellen_stand.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: prot[k] for k in prot if k not in ("quellspalten",)}, ensure_ascii=False, indent=1))
