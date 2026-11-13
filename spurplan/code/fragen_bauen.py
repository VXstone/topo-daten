"""Karte «Fragen an Dani» (13.11.2026): offene Entscheide mit Ausschnitt aus dem echten Plan und Varianten A/B.

  python3 spurplan/code/fragen_bauen.py <plaene_dir> [--json spurplan/fragen/fragen.json] [--out spurplan/fragen/fragen.svg]

Je Frage ein Feld: links Nummer, Regelverweis, Frage, A/B; rechts der Planausschnitt (Vektor, eingebettet als <svg> mit
viewBox = fenster [x, y, b, h] in Plankoordinaten). Antworten gibt Daniel als Pin in das Feld («A», «B» oder Text).
"""
import json, os, re, sys, textwrap
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
PL = sys.argv[1]
J = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else os.path.join(SP, "fragen", "fragen.json")
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(SP, "fragen", "fragen.svg")
F = json.load(open(J))["fragen"]
W, TX, IW, IH, FH = 1500, 560, 880, 300, 340       # Breite, Textspalte, Bildfeld, Feldhöhe
FONT = "Fira Sans, Source Sans 3, Helvetica, Arial, sans-serif"


def innen(svg):
    m = re.search(r"<svg[^>]*>(.*)</svg>\s*$", svg, re.S)
    return m.group(1) if m else ""


def zeilen(t, n): return textwrap.wrap(t, n)


out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {110 + FH * len(F)}" font-family="{FONT}">',
       f'<rect width="{W}" height="{110 + FH * len(F)}" fill="#fff"/>',
       '<text x="30" y="52" font-size="34" font-weight="600" fill="#16201a">Fragen an Dani</text>',
       '<text x="30" y="84" font-size="17" fill="#5a665e">Antwort: Pin ins Feld mit «A», «B» oder eigenem Text. Vorschlag Claude jeweils A. '
       'Entscheide kommen danach in REGELN.md.</text>']
for i, q in enumerate(F):
    y0 = 110 + FH * i
    out.append(f'<rect x="20" y="{y0 + 10}" width="{W - 40}" height="{FH - 20}" rx="10" fill="#f4f7f5" stroke="#d2dad4"/>')
    out.append(f'<text x="40" y="{y0 + 48}" font-size="24" font-weight="600" fill="#00862f">{q["nr"]} · {escape(q["titel"])}</text>')
    out.append(f'<text x="40" y="{y0 + 72}" font-size="14" fill="#5a665e">{escape(q["regel"])} · Plan {escape(q["plan"])}</text>')
    y = y0 + 102
    for z in zeilen(q["frage"], 58): out.append(f'<text x="40" y="{y}" font-size="16" fill="#16201a">{escape(z)}</text>'); y += 21
    y += 8
    for k in ("a", "b"):
        zs = zeilen(q[k], 54)
        out.append(f'<text x="40" y="{y}" font-size="16" font-weight="600" fill="#16201a">{k.upper()}</text>')
        for z in zs: out.append(f'<text x="64" y="{y}" font-size="16" fill="#16201a">{escape(z)}</text>'); y += 21
        y += 6
    if q.get("notiz"):
        for z in zeilen(q["notiz"], 62): out.append(f'<text x="40" y="{y}" font-size="13" font-style="italic" fill="#5a665e">{escape(z)}</text>'); y += 17
    x, yy, b, h = q["fenster"]; s = min(IW / b, IH / h); bw, bh = b * s, h * s
    bx, by = TX + 20 + (IW - bw) / 2, y0 + 20 + (IH - bh) / 2
    p = os.path.join(PL, q["plan"] + ".svg")
    out.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="#fff" stroke="#d2dad4"/>')
    if os.path.exists(p):
        out.append(f'<svg x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" viewBox="{x} {yy} {b} {h}" font-family="{FONT}">'
                   + innen(open(p).read()) + '</svg>')
    else:
        out.append(f'<text x="{bx + 20:.1f}" y="{by + 40:.1f}" font-size="16" fill="#d4351c">Plan {escape(q["plan"])} fehlt</text>')
out.append("</svg>")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write("\n".join(out))
print(OUT, len(F), "Fragen")
