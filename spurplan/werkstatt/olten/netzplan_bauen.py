"""
Regionalplan mit Prüfbericht (unten links) und Zeichenerklärung (unten rechts) bauen.
  python3 netzplan_bauen.py 10        -> <Datum>_Region Olten Netzplan_10.svg
"""
import subprocess, sys, re, datetime, html, os
nn = sys.argv[1]
out = subprocess.run(["python3", "netz_lage.py", "olten_region", "Region Olten", "nl.svg", "--pruefen"],
                     capture_output=True, text=True).stdout
rep = out[out.find("== Prüfung 1"):].strip().splitlines() if "== Prüfung 1" in out else []
ab = subprocess.run(["python3", "abstand.py", "nl.svg", "--min", "4.5"], capture_output=True, text=True).stdout.strip()
rep += ["== Prüfung 4: Abstand (zu nah / Weiche verdeckt) ==", "  " + ab]
svg = open("nl.svg").read()
vb = [float(v) for v in re.search(r'viewBox="([^"]*)"', svg).group(1).split()]
x0, y0, W, H = vb
# Prüfbericht unten links
yb = y0 + H - 40 - 14 * len(rep)
BOLD = ' font-weight="700"'
txt = "".join(f'<text x="{x0 + 40:.0f}" y="{yb + 14 * i:.0f}" font-size="11"{BOLD if l.startswith("==") else ""} fill="#555">{html.escape(l)}</text>'
              for i, l in enumerate(rep))
# Zeichenerklärung unten rechts
leg = open("feedback/legende.svg").read()
lw, lh = [float(v) for v in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', leg).groups()]
sc = 0.55
lbody = re.sub(r"^.*?<svg[^>]*>", "", leg, flags=re.S).replace("</svg>", "")
lx, ly = x0 + W - 40 - lw * sc, y0 + H - 40 - lh * sc
legend = f'<g transform="translate({lx:.0f},{ly:.0f}) scale({sc})">{lbody}</g>'
svg = svg.replace("</svg>", f"<g>{txt}</g>{legend}</svg>")
fn = f"{datetime.date.today():%Y%m%d}_Region Olten Netzplan_{nn}.svg"
open(fn, "w").write(svg)
print(fn); print("\n".join(rep))
