"""Regel-Lint (13.11.2026, D. Eckenstein: «wie verhindern wir, dass wieder Ergänzungs-md-Sachen entstehen?»).

  python3 spurplan/code/regeln_lint.py [--md bericht.md]

Prüft, dass spurplan/REGELN.md die einzige, hierarchische Regelquelle bleibt:
  FEHLER (Exit 1, Workflow rot)
    R1  Abschnitt ausserhalb der festen Gliederung (## 0.–7., Anhang; ### 1.A–1.D) – z. B. «## Entscheide 20.11.» unten angehängt
    R2  Datum in einer Überschrift (Chronologie gehört ins Feld «seit»/«alt», nicht in die Gliederung)
    R3  Regelnummer doppelt oder nicht in der Form Ebene.Nr / 7.Nr
    R4  neue Markdown-Datei unter spurplan/ mit Regelinhalt (Name enthält REGEL/ENTSCHEID/RULE), ausser den Archiven
  HINWEIS (Workflow bleibt grün, steht im Bericht)
    H1  cfg-Schalter im Code (region_lauf setdefault, spurplan_schema CFG.get(…, True/False)), der in REGELN.md nicht vorkommt
    H2  Zeile in UEBERGABE.md / IDEEN_REVIEW.md, die einen Entscheid Daniels festhält, ohne Verweis «REGELN x.y»
"""
import os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
ERLAUBT_H2 = [r"Wie dieses Regelwerk funktioniert", r"0\. ", r"1\. ", r"2\. ", r"3\. ", r"4\. ", r"5\. ", r"6\. ", r"7\. ", r"Anhang"]
ERLAUBT_H3 = [r"1\.[A-Z] "]
DATUM = re.compile(r"\b\d{1,2}\.\d{1,2}\.(\d{2,4})?\b")


def lint():
    F, H = [], []
    txt = open(os.path.join(SP, "REGELN.md"), encoding="utf-8").read().splitlines()
    nummern = {}
    for i, z in enumerate(txt, 1):
        m = re.match(r"^(#{2,3}) (.*)$", z)
        if m:
            erl = ERLAUBT_H2 if m[1] == "##" else ERLAUBT_H3
            if not any(re.match(e, m[2]) for e in erl): F.append(f"R1 REGELN.md:{i} Abschnitt ausserhalb der Gliederung: «{m[2]}»")
            if DATUM.search(m[2]): F.append(f"R2 REGELN.md:{i} Datum in Überschrift: «{m[2]}»")
        m = re.match(r"^\| *([^|]+?) *\|", z)
        if m and re.match(r"^\d", m[1]):
            nr = m[1]
            if not re.fullmatch(r"[0-7]\.\d{1,2}", nr): F.append(f"R3 REGELN.md:{i} Nummer «{nr}» nicht in der Form Ebene.Nr")
            elif nr in nummern: F.append(f"R3 REGELN.md:{i} Nummer {nr} doppelt (schon Zeile {nummern[nr]})")
            else: nummern[nr] = i
    for f in glob.glob(os.path.join(SP, "**", "*.md"), recursive=True):
        b = os.path.basename(f).upper()
        if f.endswith("REGELN.md") or "ARCHIV" in b or "/werkstatt/" in f: continue
        if any(w in b for w in ("REGEL", "ENTSCHEID", "RULE")): F.append(f"R4 {os.path.relpath(f, SP)}: Regeln gehören in REGELN.md")
    regeln = "\n".join(txt)
    keys = set()
    for f in ("region_lauf.py", "spurplan_schema.py", "netz_lage.py"):
        s = open(os.path.join(HERE, f), encoding="utf-8").read()
        keys |= set(re.findall(r'\["cfg"\](?:\["rules"\])?\.setdefault\("([a-z0-9_]+)"', s))
        keys |= set(re.findall(r'CFG\.get\("([a-z0-9_]+)", (?:True|False)\)', s))
        keys |= set(re.findall(r'L0\.get\("([a-z0-9_]+)", (?:True|False)\)', s))
    keys.discard("rules")
    for k in sorted(keys):
        if k not in regeln: H.append(f"H1 Schalter `{k}` ohne Regel in REGELN.md")
    for f in ("UEBERGABE.md", "IDEEN_REVIEW.md"):
        p = os.path.join(SP, f)
        if not os.path.exists(p): continue
        for i, z in enumerate(open(p, encoding="utf-8"), 1):
            if re.search(r"(Entscheid|Regel) (D\. Eckenstein|Daniel)|Daniel \d{1,2}\.\d{1,2}\.:", z) and "REGELN" not in z:
                H.append(f"H2 {f}:{i} Entscheid ohne Verweis «REGELN x.y»")
    return F, H, len(nummern)


if __name__ == "__main__":
    F, H, n = lint()
    L = [f"# Regel-Lint", "", f"{n} Regeln in REGELN.md · {len(F)} Fehler · {len(H)} Hinweise", ""] + [f"- {x}" for x in F + H]
    print("\n".join(L))
    if "--md" in sys.argv: open(sys.argv[sys.argv.index("--md") + 1], "w").write("\n".join(L) + "\n")
    sys.exit(1 if F else 0)
