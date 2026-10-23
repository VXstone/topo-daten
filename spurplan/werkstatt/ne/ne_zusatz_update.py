"""NE-Spurpläne in olten/feedback/zusatz_plaene.json erneuern (Gruppe bleibt, Label/Stand neu). 15.10.2026"""
import json, re, subprocess, ast, sys
ZUS = "/home/claude/olten/feedback/zusatz_plaene.json"
LABEL = sys.argv[1] if len(sys.argv) > 1 else "Entwurf 2 · Stand 15.10.2026"
def strip(svg):
    svg = re.sub(r"<\?xml[^>]*>", "", svg)
    for _ in range(2): svg = re.sub(r'(<svg[^>]*?)\s(width|height)="[^"]*"', r"\1", svg)
    return svg
GROSS_NE = {"neuchatel"}
# Pläne aus dem Repo-Lauf (Workflow «plaene», 21.10.): Label nennt den Lauf; das SVG holt repo_holen.py vorher ab
import os
REPO = json.load(open("repo_bericht.json")) if os.path.exists("repo_bericht.json") else {}          # mit --hauptgleise gezeichnet (wie ne_run.sh neuchatel --hauptgleise)
Z = json.load(open(ZUS))
for p in Z:
    if p.get("region") != "ne" and not p.get("gruppe", "").startswith("Region Neuchâtel"): continue
    key = p["key"]
    cnt = dict.fromkeys("ABCDEWR", 0)
    vorl = json.load(open(f"{key}_ports.json")).get("vorlage")
    if vorl:      # Typvorlage (16.10.): Topologie-Abgleich mit OSM aus vorlage.py statt Prüfung der Einzelgleise
        cnt["A"] = len(json.load(open(f"{key}_vorlage_befund.json")))
    else:
        # spurplan_check führt spurplan_schema aus: mit den Lauf-Optionen des Bahnhofs und in eine Zwischendatei, sonst wird der
        # Spurplan überschrieben (Neuchâtel 20.10. zweimal ohne --hauptgleise veröffentlicht)
        _opt = ["--hauptgleise"] if key in GROSS_NE else []
        out = subprocess.run(["python3", "spurplan_check.py", "--src", f"{key}.json", "--out", f"/tmp/_check_{key}.svg"] + _opt, capture_output=True, text=True).stdout
        mm = re.search(r"^eindeutig: (\{.*\})", out, re.M)
        if mm: cnt.update(ast.literal_eval(mm.group(1)))
    subprocess.run(["python3", "viewbox_text.py", f"{key}_spurplan.svg", f"{key}_spurplan_check.svg"], capture_output=True)
    subprocess.run(["python3", "abstand.py", f"{key}_spurplan.svg", "--min", "10.7", "--winkel", "--json", f"{key}_abstand.json"], capture_output=True)
    ab = json.load(open(f"{key}_abstand.json"))
    for x in ab: cnt[{"zu nah": "E", "Weiche verdeckt": "W", "90 Grad": "R"}[x["art"]]] += 1
    a = open(f"{key}_spurplan.svg").read(); c = open(f"{key}_spurplan_check.svg").read()
    extra = c[len(a) - 7:-7] if c.startswith(a[:-7]) else ""
    _cm = {"zu nah": ("#c0f", "E"), "Weiche verdeckt": ("#f80", "W"), "90 Grad": ("#e00", "R")}
    mk = "".join(f'<circle cx="{x["x"]}" cy="{x["y"]}" r="12" fill="none" stroke="{_cm[x["art"]][0]}" stroke-width="2.5"/>'
                 f'<text x="{x["x"] + 14}" y="{x["y"] - 9}" font-size="13" fill="{_cm[x["art"]][0]}">{_cm[x["art"]][1]}</text>' for x in ab)
    p["svg"] = strip(a[:-7] + f'<g class="befund">{extra}{mk}</g></svg>')
    p["counts"] = cnt; p["status"] = "sauber" if sum(cnt.values()) == 0 else "offen"; p["label"] = LABEL + (f" · Typvorlage {vorl}" if vorl else "")
    if key in REPO.get("bahnhoefe", {}): p["label"] = f"Repo-Lauf {REPO['erzeugt']} (GitHub VXstone/topo-daten)"
    print(f"{key:18s} {cnt}")
json.dump(Z, open(ZUS, "w"), ensure_ascii=False)
