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
"""
import json, os, re, sys, ast, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASIS = os.path.join(os.path.dirname(HERE), "qualitaet_basis.json")


def messen(b, check=None, regeln=None):
    k = {}
    if check:
        c = check if isinstance(check, dict) else ast.literal_eval(check)
        for x in "ABCDE": k[f"topo_{x}"] = int(c.get(x, 0))
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
    pj = f"{b}_ports.json"
    if os.path.exists(pj):
        P = json.load(open(pj))["ports"]
        g = collections.defaultdict(list)
        for p in P:
            if p.get("kind") == "edge" and p.get("pax"): g[(p.get("dx"), p.get("ref"))].append(p["y"])
        k["randabstand"] = sum(1 for ys in g.values() for a, c in zip(sorted(ys), sorted(ys)[1:]) if c - a > 30)
    return k


def vergleichen(mess, basis):
    out = {}
    for b, k in sorted(mess.items()):
        alt = basis.get(b)
        if alt is None: out[b] = dict(status="neu"); continue
        d = {x: k.get(x, 0) - alt.get(x, 0) for x in sorted(set(k) | set(alt)) if k.get(x, 0) != alt.get(x, 0)}
        schlechter = {x: v for x, v in d.items() if v > 0}; besser = {x: v for x, v in d.items() if v < 0}
        out[b] = dict(status="schlechter" if schlechter else ("besser" if besser else "gleich"), schlechter=schlechter, besser=besser)
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
            print(f"  {b:22} {e['status']:10} " + " ".join(f"{x}{'+' if n > 0 else ''}{n}" for x, n in {**e.get('schlechter', {}), **e.get('besser', {})}.items()))
        if opt("--json"): json.dump(v, open(opt("--json"), "w"), ensure_ascii=False, indent=1)
    elif a[0] == "basis":
        mess = json.load(open(a[1])); ziel = a[2] if len(a) > 2 else BASIS
        bas = json.load(open(ziel)) if os.path.exists(ziel) else {}
        bas.update(mess); json.dump(dict(sorted(bas.items())), open(ziel, "w"), ensure_ascii=False, indent=1)
        print(len(mess), "Bahnhöfe in die Basis", ziel)
