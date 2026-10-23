"""Live-Fassung der Feedback-Seite (andere Sitzungen) einmischen: Pläne, die diese Sitzung nicht selbst baut,
aus der Live-Fassung übernehmen (zusatz_plaene.json), dann neu bauen. Aufruf: python3 merge_live.py <live.html>"""
import json, sys, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
live = open(sys.argv[1]).read().split("\n")
def const(lines, name):
    l = [x for x in lines if x.startswith(f"const {name} = ")][0]
    return json.loads(l[len(f"const {name} = "):].rstrip(";"))
P = const(live, "PLANS")
own = {"region", "blaupause", "thun", "ins", "murten", "kerzers", "olten", "aarburg_oftringen", "rothrist", "zofingen", "safenwil",
       "wangen_bei_olten", "dulliken", "daniken", "schonenwerd", "tecknau", "laufelfingen", "olten_hammer", "region_ne"}
extra = [p for p in P if p["key"] not in own]
json.dump(extra, open(os.path.join(HERE, "zusatz_plaene.json"), "w"), ensure_ascii=False)
print("übernommen:", [p["key"] for p in extra])
# Untertitel der Live-Fassung übernehmen (andere Sitzungen ergänzen dort ihre Regionen)
import re
sub = [x for x in live if 'class="sub"' in x]
if sub:
    m = re.search(r'<span class="sub">(.*?) · Stand [^<]*</span>', sub[0])
    if m:
        t = open(os.path.join(HERE, "seite.html")).read()
        t = re.sub(r'<span class="sub">.*? · Stand \{\{STAND\}\}</span>', f'<span class="sub">{m.group(1)} · Stand {{{{STAND}}}}</span>', t)
        open(os.path.join(HERE, "seite.html"), "w").write(t)
        print("Untertitel:", m.group(1))
