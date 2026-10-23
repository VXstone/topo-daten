"""Differenzbild Regionalplan (D. Eckenstein 20.10.: jede Runde ein Bild mit allen Stellen, die sich ausserhalb der
Hinweisstellen geändert haben).

python3 diff_bild.py <alt.svg> <neu.svg> <ausgabe.png> [--hinweise h.json] [--liste out.json] [--px 3000]
- rendert beide Pläne im gemeinsamen Ausschnitt (Vereinigung der viewBoxen), vergleicht pixelweise,
  fasst geänderte Pixel zu Kästen zusammen und zeichnet sie auf den neuen Plan:
  rot = Änderung ausserhalb der Hinweise (erklären oder zurücknehmen), blau = an einer Hinweisstelle (gewollt).
- je Kasten: Lage in Plankoordinaten und nächster Bahnhof (data-name der eingebetteten Spurpläne).
Vergleichsbasis: bis zur Abnahme die zuletzt veröffentlichte Fassung, danach die abgenommene (feedback/vergleich/).
"""
import re, sys, json, argparse, subprocess, os, tempfile
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ap = argparse.ArgumentParser()
ap.add_argument("alt"); ap.add_argument("neu"); ap.add_argument("out")
ap.add_argument("--hinweise"); ap.add_argument("--liste"); ap.add_argument("--px", type=int, default=3000)
A = ap.parse_args()
VB = os.environ.get("VBJS", "/tmp/claude-0/vb.js")

def vbox(f):
    m = re.search(r'viewBox="([-\d. ]+)"', open(f).read()); return [float(v) for v in m.group(1).split()]
a, b = vbox(A.alt), vbox(A.neu)
x0, y0 = min(a[0], b[0]), min(a[1], b[1]); x1, y1 = max(a[0] + a[2], b[0] + b[2]), max(a[1] + a[3], b[1] + b[3])
box = f"{x0} {y0} {x1 - x0} {y1 - y0}"
tmp = tempfile.mkdtemp()
env = dict(os.environ, NODE_PATH=subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip())
for k, f in (("a", A.alt), ("b", A.neu)):
    subprocess.run(["node", VB, f, box, f"{tmp}/{k}.png", str(A.px)], check=True, env=env)
ia = np.asarray(Image.open(f"{tmp}/a.png").convert("L"), float); ib = np.asarray(Image.open(f"{tmp}/b.png").convert("L"), float)
S = A.px / max(x1 - x0, y1 - y0)                       # px je Planeinheit (quadratisch, mittig)
ox = (A.px - (x1 - x0) * S) / 2; oy = (A.px - (y1 - y0) * S) / 2
to_plan = lambda px, py: (x0 + (px - ox) / S, y0 + (py - oy) / S)
to_px = lambda X, Y: (ox + (X - x0) * S, oy + (Y - y0) * S)
diff = np.abs(ia - ib) > 60
diff = ndimage.binary_dilation(diff, iterations=6)
lab, n = ndimage.label(diff)
objs = ndimage.find_objects(lab)
# Bahnhöfe (Lage der Spurplan-Gruppen im neuen Plan)
st = [(m[1], float(m[2]), float(m[3])) for m in re.finditer(r'data-name="([^"]+)" transform="translate\(([-\d.]+),([-\d.]+)\)', open(A.neu).read())]
hw = []
if A.hinweise:
    hw = [(float(h["x"]), float(h["y"])) for h in json.load(open(A.hinweise)) if "x" in h]
img = Image.open(f"{tmp}/b.png").convert("RGB"); dr = ImageDraw.Draw(img)
out = []
for sl in objs:
    if sl is None: continue
    py0, py1, px0, px1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
    if (px1 - px0) * (py1 - py0) < 30: continue
    X0, Y0 = to_plan(px0, py0); X1, Y1 = to_plan(px1, py1); cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    near = min(st, key=lambda s: (s[1] - cx) ** 2 + (s[2] - cy) ** 2)[0] if st else None
    gewollt = any(X0 - 40 <= hx <= X1 + 40 and Y0 - 40 <= hy <= Y1 + 40 for hx, hy in hw)
    col = (40, 90, 220) if gewollt else (220, 30, 30)
    dr.rectangle([px0 - 4, py0 - 4, px1 + 4, py1 + 4], outline=col, width=3)
    out.append(dict(x=round(cx, 1), y=round(cy, 1), b=round(X1 - X0), h=round(Y1 - Y0), bahnhof=near, gewollt=gewollt))
img.save(A.out)
rot = [o for o in out if not o["gewollt"]]
print(f"Differenzbild: {len(out)} geänderte Stellen, davon {len(rot)} ausserhalb der Hinweise")
for o in sorted(rot, key=lambda o: o["bahnhof"] or ""): print(f'  {o["bahnhof"]}: {o["x"]},{o["y"]} ({o["b"]}×{o["h"]})')
if A.liste: json.dump(out, open(A.liste, "w"), ensure_ascii=False, indent=1)
