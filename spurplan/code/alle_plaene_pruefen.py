"""Regression über ALLE Pläne der Feedback-Seite (6.11.2026, Befund Olten: nur plaene/regionen wurden verglichen,
die Werkstatt-Pläne aus dem Workflow seite – Region Olten, Region Neuchâtel, Referenzen – nie).

  python3 spurplan/code/alle_plaene_pruefen.py <abnahme_ordner> <ausgabe_ordner> [--ref origin/ergebnisse]

<abnahme_ordner>: Export der Sammlung «abnahme» der Feedback-Seite (ArtifactData list mit out_dir), je Bahnhof
eine JSON-Datei mit «am». Vergleich je Plan (ergebnisse/seite/plaene/<key>.svg auf dem Branch «ergebnisse»):
  - abgenommen: Fassung zur Abnahmezeit (ältere Abnahmen als das Archiv: erste Fassung, 23.10.2026) gegen heute
  - nicht abgenommen: zuletzt veröffentlichte Fassung (--seit <commit>) bzw. erste Fassung gegen heute
Ausgabe: tabelle.json und tabelle.md (key, gruppe, basis, stellen) und <key>_diff.png für jede Änderung.
Jede geänderte Zeile muss erklärt sein (gewollte Regel E9 oder Fehler) – sonst ist die Runde nicht fertig.
"""
import datetime, glob, json, os, re, subprocess, sys

ABN, OUT = sys.argv[1], sys.argv[2]
REF = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else "origin/ergebnisse"
SEIT = sys.argv[sys.argv.index("--seit") + 1] if "--seit" in sys.argv else None
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)


def git(*a):
    return subprocess.run(["git"] + list(a), capture_output=True).stdout


html = git("show", f"{REF}:ergebnisse/seite/index.html").decode()
PLANS = json.loads(re.search(r"const PLANS = (\[.*?\]);\n", html, re.S).group(1))
A = {}
for f in glob.glob(os.path.join(ABN, "**", "*.json"), recursive=True):
    d = json.load(open(f))
    if d.get("bahnhof") and d.get("am"): A[d["bahnhof"]] = d["am"]
zeilen = []
for p in PLANS:
    k = p["key"]; path = f"ergebnisse/seite/plaene/{k}.svg"
    log = [l.split() for l in git("log", REF, "--format=%h %cI", "--", path).decode().splitlines() if l.strip()]
    if not log: zeilen.append(dict(key=k, gruppe=p.get("gruppe"), basis="fehlt", stellen=None)); continue
    if k in A:
        t = datetime.datetime.fromisoformat(A[k].replace("Z", "+00:00"))
        vor = [x for x in log if datetime.datetime.fromisoformat(x[1]) <= t]
        base, art = (vor[0], "Abnahme " + A[k][:10]) if vor else (log[-1], "Archivbeginn (Abnahme " + A[k][:10] + ")")
    elif SEIT:
        vor = [x for x in log if subprocess.run(["git", "merge-base", "--is-ancestor", x[0], SEIT]).returncode == 0]
        base, art = (vor[0], "veröffentlicht") if vor else (log[-1], "erste Fassung")
    else:
        base, art = log[-1], "erste Fassung"
    alt, neu = git("show", f"{base[0]}:{path}"), git("show", f"{REF}:{path}")
    if alt == neu:
        zeilen.append(dict(key=k, gruppe=p.get("gruppe"), basis=art, stellen=0)); continue
    fa, fn = os.path.join(OUT, f"{k}_alt.svg"), os.path.join(OUT, f"{k}_neu.svg")
    open(fa, "wb").write(alt); open(fn, "wb").write(neu)
    r = subprocess.run([sys.executable, os.path.join(HERE, "diff_bild.py"), fa, fn, os.path.join(OUT, f"{k}_diff.png"),
                        "--px", "1600"], capture_output=True, text=True)
    m = re.search(r"Differenzbild: (\d+)", r.stdout + r.stderr)
    zeilen.append(dict(key=k, gruppe=p.get("gruppe"), basis=art, stellen=int(m.group(1)) if m else -1,
                       letzte_aenderung=log[0][1][:16]))
json.dump(zeilen, open(os.path.join(OUT, "tabelle.json"), "w"), ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "tabelle.md"), "w") as f:
    f.write("| Plan | Gruppe | Basis | Stellen | letzte Änderung |\n|---|---|---|---|---|\n")
    for z in sorted(zeilen, key=lambda z: -(z["stellen"] or 0)):
        f.write(f"| {z['key']} | {z['gruppe']} | {z['basis']} | {z['stellen']} | {z.get('letzte_aenderung', '')} |\n")
g = [z for z in zeilen if z["stellen"]]
print(f"{len(zeilen)} Pläne geprüft, {len(g)} geändert: " + ", ".join(f"{z['key']} ({z['stellen']})" for z in g))
