"""viewBox seitlich so erweitern, dass alle Beschriftungen ganz sichtbar sind (Abgangstexte am Rand abgeschnitten)."""
import re, sys
for f in sys.argv[1:]:
    s = open(f).read()
    m = re.search(r'viewBox="(-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)"', s)
    x0, y0, w, h = map(float, m.groups())
    lo, hi = x0, x0 + w
    for t in re.finditer(r'<text ([^>]*)>([^<]*)<', s):
        at = dict(re.findall(r'([\w-]+)="([^"]*)"', t[1])); txt = t[2]
        if "x" not in at: continue
        x, fs, anc = float(at["x"]), float(at.get("font-size", 16)), at.get("text-anchor", "start")
        tw = len(txt) * 0.56 * fs
        a = x - (tw if anc == "end" else tw / 2 if anc == "middle" else 0); b = a + tw
        lo, hi = min(lo, a - 12), max(hi, b + 12)
    if lo < x0 or hi > x0 + w:
        nb = f'viewBox="{lo:.0f} {y0:.0f} {hi - lo:.0f} {h:.0f}" width="{hi - lo:.0f}"'
        s = re.sub(r'viewBox="[^"]*" width="[^"]*"', nb, s, count=1)
        s = s.replace('<rect width="100%" height="100%" fill="#fff"/>', f'<rect x="{lo:.0f}" width="100%" height="100%" fill="#fff"/>', 1)
        s = re.sub(r'(<rect) (y="-?[\d.]+" width="100%")', rf'\1 x="{lo:.0f}" \2', s, count=1)
        open(f, "w").write(s); print(f, "erweitert", round(x0 - lo), round(hi - x0 - w))
