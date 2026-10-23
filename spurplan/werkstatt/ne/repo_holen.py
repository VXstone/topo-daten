"""Ergebnisse des Repo-Laufs (Branch «ergebnisse») holen: Bericht + Spurplan/bare/ports je Bahnhof in den Arbeitsordner."""
import json, subprocess, base64
def holen(p):
    o = subprocess.run(["gh", "api", f"repos/VXstone/topo-daten/contents/{p}?ref=ergebnisse", "--jq", ".content"], capture_output=True, text=True, check=True).stdout
    return base64.b64decode(o)
B = json.loads(holen("ergebnisse/bericht.json")); open("repo_bericht.json", "w").write(json.dumps(B, ensure_ascii=False))
for b, x in B["bahnhoefe"].items():
    if not x.get("ok"): print(b, "Lauf fehlgeschlagen:", x.get("fehler")); continue
    for src, dst in (("spurplan.svg", f"{b}_spurplan.svg"), ("bare.svg", f"{b}_bare.svg"), ("ports.json", f"{b}_ports.json")):
        open(dst, "wb").write(holen(f"ergebnisse/{b}/{src}"))
    print(b, "geholt", B["erzeugt"])
