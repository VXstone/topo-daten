"""Kennzahlen je Spurplan und Vergleich mit der Basis (27.10.2026, «Code besser machen», Schritt 1).

Ein Plan wird nicht nur auf Gleichheit geprüft, sondern gemessen. Jede Kennzahl ist «weniger ist besser».
Verschlechtert eine Änderung eine Zahl gegenüber spurplan/qualitaet_basis.json, steht das im Bericht.

  python3 qualitaet.py messen <bahnhof> [--check "{'A': 1, ...}"] [--regeln regeln.json]   (im Arbeitsordner des Plans)
        -> <bahnhof>_qualitaet.json
  python3 qualitaet.py vergleichen <messungen.json> [basis.json] [--json ausgabe.json]
        messungen.json = {bahnhof: kennzahlen}; Ausgabe: je Bahnhof besser/schlechter/gleich mit den Deltas
  python3 qualitaet.py basis <messungen.json> [basis.json]      neue Basis schreiben (nach einer abgenommenen Verbesserung)

Kennzahlen:
  topo_A..topo_E   Topologieprüfung (spurplan_check): offene Verbindungen, Überlagerungen/Scheinverbindungen, …
  netz_<Regel>     Befunde der Netzprüfung je Regel-ID (T10, A1, W1, W2, F2, F7, F10, Z1, Z2, D11, …)
  regel_<G>        Befunde der Regelprüfung (G1–G8)
  boegen_pax       Ausrundungen in Personengleisen (jeder Versatz/Knick im grünen Gleis kostet zwei)
  boegen_alle      Ausrundungen in allen Gleisen
  randabstand      Streckengleise derselben Linie am Planrand, die mehr als eine Achse auseinanderliegen (A4)
  ruhe_treppen/ruhe_ecken  T7 (ruhe.py), wenn <b>_ruhe.json im Arbeitsordner liegt
Unruhe-Wert: unruhe(kennzahlen) mit GEWICHTE (Topologie 50 je Befund, Treppe 8, Ecke 4, G4/G7 10, G6/G8 3, G2 2 …).
"""
import json, os, re, sys, ast, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASIS = os.path.join(os.path.dirname(HERE), "qualitaet_basis.json")


def messen(b, check=None, regeln=None):
    k = {}
    if check:
        c = check if isinstance(check, dict) else ast.literal_eval(check)
        for x in "ABCDEF": k[f"topo_{x}"] = int(c.get(x, 0))
    if regeln and os.path.exists(regeln):
        r = json.load(open(regeln))
        r = collections.Counter(x["regel"] for x in r) if isinstance(r, list) else r
        for g, n in r.items(): k[f"regel_{g}"] = int(n)
    nb = f"{b}_netz_befunde.json"
    if os.path.exists(nb):
        for g, n in collections.Counter(x["regel"] for x in json.load(open(nb))["befunde"]).items(): k[f"netz_{g}"] = n
    svg = f"{b}_spurplan.svg"
    if os.path.exists(svg):
        s = open(svg).read()
        bp = ba = 0
        for m in re.finditer(r'<path d="([^"]+)"([^>]*)>', s):
            at = m.group(2)
            if re.search(r'fill="#', at) or 'stroke="#fff"' in at or "stroke-opacity" in at: continue
            sw = re.search(r'stroke-width="([\d.]+)"', at)
            if not sw or float(sw.group(1)) not in (3.6, 1.6): continue
            q = m.group(1).count("Q")
            ba += q
            if 'stroke="#00862f"' in at and float(sw.group(1)) == 3.6: bp += q
        k["boegen_pax"] = bp; k["boegen_alle"] = ba
    rj = f"{b}_ruhe.json"                        # T7 je Bahnhofsplan (5.11.2026, auch im Workflow plaene)
    if os.path.exists(rj):
        r_ = json.load(open(rj)); k["ruhe_treppen"] = sum(1 for x in r_ if x.get("art") == "Treppe"); k["ruhe_ecken"] = sum(1 for x in r_ if x.get("art") == "Ecke")
    pj = f"{b}_ports.json"
    if os.path.exists(pj):
        P = json.load(open(pj))["ports"]
        g = collections.defaultdict(list)
        for p in P:
            if p.get("kind") == "edge" and p.get("pax"): g[(p.get("dx"), p.get("ref"))].append(p["y"])
        k["randabstand"] = sum(1 for ys in g.values() for a, c in zip(sorted(ys), sorted(ys)[1:]) if c - a > 30)
    return k


# Unruhe-Wert (5.11.2026, Stufe A «verlässlich messen»): eine Zahl je Plan bzw. Region, kleiner ist besser. Topologie wiegt so
# schwer, dass ein einziger Befund jede Verschönerung überwiegt (oberste Regel). Gewichte: GEWICHTE, Schlüssel ohne Eintrag 1.
GEWICHTE = {
    # Topologie (hart): Bahnhofsplan A–F, Region T1–T8, Verkettung V/S, Perron fehlt P1
    **{f"topo_{x}": 50 for x in "ABCDEF"}, **{f"topo_T{i}": 50 for i in range(1, 9)},
    **{f"verk_{x}": 50 for x in ("V1", "V2", "V3", "S1", "S2", "S3")}, "perron_P1": 30,
    # Ruhe (D. Eckenstein 4.11.: Treppen sehr unruhig, dann unmotivierte Ecken)
    "ruhe_treppen": 8, "ruhe_ecken": 4,
    # Zeichenregeln: 90° (G4) und nicht angebunden (G7) schwer, Knubbel G6, Weiche ohne Ausrundung G2, deckungsgleich G8
    "regel_G4": 10, "regel_G7": 10, "regel_G6": 3, "regel_G8": 3, "regel_G2": 2, "regel_G1": 1,
    "randabstand": 5, "planrand": 5,
    # Lage gegen die Karte (Grundsatz 2): L2 vertauschtes Paar N/S bzw. O/W (zählt paarweise), L3 Achse/Seite/Reihenfolge
    "lage_L2": 10, "lage_L3": 20, "lage_L4": 30,
    # L3a Achse > 60° neben der Karte: nur Hinweis (D. Eckenstein 5.11.: Geografie leitet die Reihenfolge, nicht die Lage)
    "lage_L3a": 0,
    # reine Zählgrössen, kein Mangel
    "boegen_pax": 0, "boegen_alle": 0,
}
def unruhe(k):
    """(Summe, {Kennzahl: Beitrag}) – Netzbefunde (netz_*) zählen je 2, unbekannte Kennzahlen je 1."""
    teile = {}
    for x, n in (k or {}).items():
        if not isinstance(n, (int, float)) or not n: continue
        w = GEWICHTE.get(x, 2 if x.startswith("netz_") else 1)
        if w: teile[x] = w * n
    return sum(teile.values()), teile
def region_kennzahlen(b):
    """Kennzahlen eines Regionsberichts (region_lauf bericht.json) in derselben Form wie die Bahnhofsmessung."""
    k = {}
    for g, n in (b.get("topologie_region") or {}).items(): k[f"topo_{g}"] = int(n)
    for g, n in (b.get("verkettung") or {}).items(): k[f"verk_{g}"] = int(n)
    for g, n in (b.get("perrons") or {}).items(): k[f"perron_{g}"] = int(n)
    for g, n in (b.get("regeln") or {}).items(): k[f"regel_{g}"] = int(n)
    if b.get("ruhe"): k["ruhe_treppen"] = int(b["ruhe"].get("treppen", 0)); k["ruhe_ecken"] = int(b["ruhe"].get("ecken", 0))
    if b.get("planrand") is not None: k["planrand"] = int(b["planrand"])
    for g, n in (b.get("lage") or {}).items(): k[f"lage_{g}"] = int(n)
    return k


def vergleichen(mess, basis):
    out = {}
    for b, k in sorted(mess.items()):
        alt = basis.get(b)
        if alt is None: out[b] = dict(status="neu"); continue
        # Kennzahl, die es in der Basis noch nicht gab (neue Prüfung): nicht als Verschlechterung werten, nur melden
        neu_ = {x: k[x] for x in k if x not in alt and not x.startswith(("topo_", "verk_", "perron_"))}
        d = {x: k.get(x, 0) - alt.get(x, 0) for x in sorted(set(k) | set(alt)) if k.get(x, 0) != alt.get(x, 0) and x not in neu_}
        d = {x: v for x, v in d.items() if not (x.startswith("lage_") and GEWICHTE.get(x) == 0)}   # Hinweise (L3a) nie schlechter/besser
        schlechter = {x: v for x, v in d.items() if v > 0}; besser = {x: v for x, v in d.items() if v < 0}
        # Topologiebefunde (A offene Verbindung, B Scheinverbindung/Überlagerung, F Weichenrichtung) sind nie «normal»,
        # auch wenn sie in der Basis stehen (28.10.2026, Vauseyon: A stand seit Beginn in der Basis und fiel nicht auf)
        offen = {x: k[x] for x in ("topo_A", "topo_B", "topo_F") if k.get(x, 0) > 0}
        out[b] = dict(status="schlechter" if schlechter else ("besser" if besser else "gleich"), schlechter=schlechter, besser=besser,
                      topologie_offen=offen, neu=neu_, unruhe=unruhe(k)[0], unruhe_basis=unruhe({**alt, **neu_})[0])
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda n: a[a.index(n) + 1] if n in a else None
    if a[0] == "messen":
        b = a[1]; k = messen(b, opt("--check"), opt("--regeln"))
        json.dump(k, open(f"{b}_qualitaet.json", "w"), ensure_ascii=False, indent=1); print(b, json.dumps(k, ensure_ascii=False))
    elif a[0] == "vergleichen":
        mess = json.load(open(a[1])); bas = json.load(open(a[2] if len(a) > 2 and not a[2].startswith("--") else BASIS)) if os.path.exists(BASIS) or (len(a) > 2 and os.path.exists(a[2])) else {}
        v = vergleichen(mess, bas)
        for b, e in v.items():
            print(f"  {b:22} {e['status']:10} " + " ".join(f"{x}{'+' if n > 0 else ''}{n}" for x, n in {**e.get('schlechter', {}), **e.get('besser', {})}.items())
                  + (f"  | Topologie offen: {e['topologie_offen']}" if e.get("topologie_offen") else ""))
        if opt("--json"): json.dump(v, open(opt("--json"), "w"), ensure_ascii=False, indent=1)
    elif a[0] == "basis":
        mess = json.load(open(a[1])); ziel = a[2] if len(a) > 2 else BASIS
        bas = json.load(open(ziel)) if os.path.exists(ziel) else {}
        bas.update(mess); json.dump(dict(sorted(bas.items())), open(ziel, "w"), ensure_ascii=False, indent=1)
        print(len(mess), "Bahnhöfe in die Basis", ziel)
