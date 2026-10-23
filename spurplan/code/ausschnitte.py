"""Kleine PNG-Ausschnitte an den Hinweisstellen (Workflow «seite», 23.10.2026: Claude liest nur noch die Ausschnitte).

  python3 ausschnitte.py <plaene_dir> <hinweise.json> <out_dir> [--halb 120]

hinweise.json: [{"id", "plan", "x", "y", "text", "status"}] (Plankoordinaten = SVG-Koordinaten, wie in der Datenbank der
Feedback-Seite). Je Hinweis <out_dir>/<id>.png (600 px, Fenster ±halb um den Punkt, roter Kreis an der Stelle) und
<out_dir>/index.json mit Plan, Text und Dateiname. Pläne, die fehlen, werden in index.json als "plan fehlt" vermerkt.
"""
import json, os, re, sys
import cairosvg
PL, HW, OUT = sys.argv[1:4]
H = float(sys.argv[sys.argv.index("--halb") + 1]) if "--halb" in sys.argv else 120.0
os.makedirs(OUT, exist_ok=True)
idx = []
for h in json.load(open(HW)):
    f = os.path.join(PL, f"{h['plan']}.svg")
    e = dict(id=h["id"], plan=h["plan"], text=h.get("text", ""), status=h.get("status"))
    if not os.path.exists(f): e["fehler"] = "plan fehlt"; idx.append(e); continue
    s = open(f).read(); x, y = float(h["x"]), float(h["y"])
    s = re.sub(r'viewBox="[^"]*"', f'viewBox="{x - H:.1f} {y - H:.1f} {2 * H:.1f} {2 * H:.1f}"', s, 1)
    for _ in range(2): s = re.sub(r'(<svg[^>]*?)\s(width|height)="[^"]*"', r"\1", s, 1)
    s = s.replace("<svg ", '<svg width="600" height="600" ', 1)
    s = s.replace("</svg>", f'<circle cx="{x}" cy="{y}" r="{H / 12:.1f}" fill="none" stroke="#e00" stroke-width="{H / 80:.2f}"/></svg>')
    try:
        cairosvg.svg2png(bytestring=s.encode(), write_to=os.path.join(OUT, f"{h['id']}.png"), background_color="white"); e["png"] = f"{h['id']}.png"
    except Exception as ex: e["fehler"] = str(ex)[:200]
    idx.append(e)
json.dump(idx, open(os.path.join(OUT, "index.json"), "w"), ensure_ascii=False, indent=1)
print(len(idx), "Hinweise,", sum(1 for e in idx if "png" in e), "Ausschnitte")
