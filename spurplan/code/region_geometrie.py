"""Geometrieprüfung eines Regionalplans (26.10.2026, Hinweise Region Olten).

  python3 region_geometrie.py <region.svg> [--json befunde.json]

Liest die Streckengleise des Regionalplans (grüne Pfade ausserhalb der Bahnhofsgruppen) und prüft:
  A1   Achsabstand: parallele Streckengleise liegen genau eine Achse (oder, verschiedene Linien, zwei Achsen)
       auseinander. Die Achse ist der häufigste Abstand im Plan. Befund, wenn zwei Gleise über mindestens 30 px
       parallel laufen und der Abstand weder ≈1 noch ≈2 Achsen ist (Toleranz 15 %).
  W6   Einmündung: ein Streckengleis endet nicht stumpf neben einem Nachbargleis, das an der Stelle durchläuft;
       das wegfallende Gleis mündet mit Ausrundung ins Nachbargleis.
"""
import re, sys, json, math, collections
from svgpathtools import parse_path, Line

SVG = sys.argv[1]
s = open(SVG).read()
GREEN = "#00862f"

# ---- Streckengleise: grüne Pfade ausserhalb von <g>
paths = []; PORT = []; tiefe = 0
for m in re.finditer(r'<g\b[^>]*>|</g>|<path\b[^>]*/>', s):
    t = m.group(0)
    if t.startswith("<g"): tiefe += 1
    elif t == "</g>": tiefe -= 1
    elif tiefe == 0 and 'stroke="' in t and f'stroke="{GREEN}"' not in t and 'stroke="#fff"' not in t:
        d = re.search(r'\bd="([^"]*)"', t)       # Portale, Brückenflügel: Gleisenden dort sind keine Einmündung
        if d:
            try: PORT.extend(e.start for e in parse_path(d.group(1)))
            except Exception: pass
    elif tiefe == 0 and f'stroke="{GREEN}"' in t:
        d = re.search(r'\bd="([^"]*)"', t)
        if d: paths.append(d.group(1))

segs = []        # (subpfad-nr, a, b, richtung, länge)
enden = []       # (subpfad-nr, punkt, richtung nach aussen)
k = 0
for d in paths:
    try: P = parse_path(d)
    except Exception: continue
    for sub in P.continuous_subpaths():
        if sub.length() < 1: continue
        for e in sub:
            if isinstance(e, Line) and abs(e.end - e.start) >= 4:
                v = e.end - e.start; segs.append((k, e.start, e.end, v / abs(v), abs(v)))
        a0 = sub[0]; a1 = sub[-1]
        d0 = a0.start - a0.point(min(1, 3 / max(a0.length(), 1e-6)))
        d1 = a1.end - a1.point(max(0, 1 - 3 / max(a1.length(), 1e-6)))
        if abs(d0) > 1e-6: enden.append((k, a0.start, d0 / abs(d0)))
        if abs(d1) > 1e-6: enden.append((k, a1.end, d1 / abs(d1)))
        k += 1

# ---- Bahnhofsgruppen (data-st): Gleisenden an deren Rand sind Anschlüsse an den Spurplan
BOX = []
for m in re.finditer(r'<g\b[^>]*data-st="[^"]*"[^>]*transform="([^"]*)"[^>]*>', s):
    tiefe_ = 1; i_ = m.end(); inhalt = []
    for t in re.finditer(r'<g\b[^>]*>|</g>|<path\b[^>]*/>', s[i_:]):
        x = t.group(0)
        if x.startswith("<g"): tiefe_ += 1
        elif x == "</g>":
            tiefe_ -= 1
            if not tiefe_: break
        else:
            d = re.search(r'\bd="([^"]*)"', x)
            if d: inhalt.append(d.group(1))
    pts = []
    for d in inhalt:
        try: pts += [z for e in parse_path(d) for z in (e.start, e.end)]
        except Exception: pass
    if not pts: continue
    ops = re.findall(r'(translate|rotate|scale)\(([^)]*)\)', m.group(1))
    def tf(z, ops=ops):
        for op, arg in reversed(ops):
            v = [float(a) for a in re.split(r'[ ,]+', arg.strip())]
            if op == "translate": z = z + complex(v[0], v[1] if len(v) > 1 else 0)
            elif op == "scale": z = z * v[0]
            else: z = z * complex(math.cos(math.radians(v[0])), math.sin(math.radians(v[0])))
        return z
    q = [tf(z) for z in pts]
    BOX.append((min(z.real for z in q) - 3, min(z.imag for z in q) - 3, max(z.real for z in q) + 3, max(z.imag for z in q) + 3))
print("BOX", len(BOX), [tuple(round(v) for v in b) for b in BOX][:3]) if "--debug" in sys.argv else None
im_bahnhof = lambda p: any(b[0] <= p.real <= b[2] and b[1] <= p.imag <= b[3] for b in BOX)

def quer(p, a, u):
    """Abstand von p zur Geraden durch a mit Richtung u, und Lage entlang u"""
    w = p - a
    return (w * u.conjugate()).imag, (w * u.conjugate()).real

# ---- Achse: häufigster Abstand paralleler Stücke
paare = []
lang = [x for x in segs if x[4] >= 30]
for i in range(len(lang)):
    k1, a1, b1, u1, L1 = lang[i]
    for j in range(i + 1, len(lang)):
        k2, a2, b2, u2, L2 = lang[j]
        if k1 == k2 or abs((u1 * u2.conjugate()).imag) > 0.026: continue       # nicht parallel (> 1.5°)
        qa, la = quer(a2, a1, u1); qb, lb = quer(b2, a1, u1)
        dist = abs((qa + qb) / 2)
        if dist > 60 or dist < 0.5: continue
        lo, hi = max(0, min(la, lb)), min(L1, max(la, lb))
        if hi - lo >= 30: paare.append((dist, hi - lo, a1 + u1 * (lo + hi) / 2))
hist = collections.Counter(round(p[0]) for p in paare)
ACHSE = None
if hist:
    kand = [d for d, n in hist.most_common(5) if d >= 4]
    ACHSE = float(sum(p[0] * p[1] for p in paare if kand and abs(p[0] - kand[0]) <= 1) /
                  max(1e-9, sum(p[1] for p in paare if kand and abs(p[0] - kand[0]) <= 1))) if kand else None

BEF = []
def bef(regel, z, text): BEF.append(dict(regel=regel, x=round(z.real, 1), y=round(z.imag, 1), text=text))

if ACHSE:
    gesehen = set()
    for dist, ueber, mz in paare:
        r = dist / ACHSE
        if r > 2.6 or abs(r - 1) <= 0.15 or abs(r - 2) <= 0.15: continue
        key = (round(mz.real / 40), round(mz.imag / 40))
        if key in gesehen: continue
        gesehen.add(key)
        bef("A1", mz, f"zwei Streckengleise {dist:.1f} px auseinander ({r:.2f} Achsen) über {ueber:.0f} px")

# ---- W6: stumpfes Ende neben durchlaufendem Nachbargleis
if ACHSE:
    for k1, p, u in enden:
        if any(abs(p - q) < 9 for q in PORT) or im_bahnhof(p): continue
        if any(k3 != k1 and abs(p - q) < 1.5 for k3, q, _ in enden): continue     # Pfad geht in einem anderen weiter
        if any(k3 != k1 and abs(quer(p, a3, u3)[0]) < 1.5 and -1.5 <= quer(p, a3, u3)[1] <= L3 + 1.5
               for k3, a3, b3, u3, L3 in segs): continue                          # Ende liegt auf einem Gleis: Weiche
        for k2, a2, b2, u2, L2 in segs:
            if k2 == k1 or abs((u * u2.conjugate()).imag) > 0.05: continue
            q, l = quer(p, a2, u2)
            if L2 >= 40 and 0.8 * ACHSE <= abs(q) <= 1.3 * ACHSE and 20 <= l <= L2 - 20:
                bef("W6", p, f"Gleis endet stumpf neben einem durchlaufenden Gleis ({abs(q):.1f} px daneben) – mit Ausrundung einmünden")
                break

# ---- F11: Versatz ohne Grund (zwei parallele Stücke, dazwischen ein kurzer Versatz unter einer halben Achse, 27.10.)
# ---- W8: Winkel–Gegenwinkel (kurzes Zwischenstück unter 1.5 Achsen zwischen zwei Knicken, das wegfallen könnte)
if ACHSE:
    for d in paths:
        ecken = []
        for c_, a_ in re.findall(r"([MLQ])([^MLQ]*)", d):
            v_ = [float(x) for x in re.findall(r"-?[\d.]+", a_)]
            if c_ == "M": ecken.append([complex(v_[0], v_[1])])
            elif c_ == "Q": ecken[-1].append(complex(v_[0], v_[1])); _q_end = complex(v_[2], v_[3])
            elif c_ == "L": _l = complex(v_[-2], v_[-1])
        # Ecken: M, Q-Kontrollpunkte, Endpunkt jedes Teilpfads
        for teil, m_ in zip(ecken, re.split(r"(?=M)", d)[1:]):
            letzte = re.findall(r"(-?[\d.]+),(-?[\d.]+)", m_)[-1]; pl = teil + [complex(float(letzte[0]), float(letzte[1]))]
            for k in range(1, len(pl) - 2):
                a0, a1, a2, a3 = pl[k - 1], pl[k], pl[k + 1], pl[k + 2]
                u1, u2, u3 = a1 - a0, a2 - a1, a3 - a2
                if min(abs(u1), abs(u3)) < 1e-6 or abs(u2) < 1e-6: continue
                par = abs((u1 / abs(u1) * (u3 / abs(u3)).conjugate()).imag) < 0.03 and (u1 * u3.conjugate()).real > 0
                quer = abs(((a2 - a1) * (u1 / abs(u1)).conjugate()).imag)
                if par and 0.3 < quer < 0.5 * ACHSE and abs(u2) < 3 * ACHSE:
                    bef("F11", (a1 + a2) / 2, f"Versatz {quer:.1f} px ohne Grund zwischen zwei parallelen Stücken")
                elif not par and abs(u2) < 1.5 * ACHSE and min(abs(u1), abs(u3)) > abs(u2):
                    w1 = math.degrees(abs(math.atan2((u2 * u1.conjugate()).imag, (u2 * u1.conjugate()).real)))
                    w2 = math.degrees(abs(math.atan2((u3 * u2.conjugate()).imag, (u3 * u2.conjugate()).real)))
                    if w1 > 15 and w2 > 15: bef("W8", (a1 + a2) / 2, f"kurzes Zwischenstück {abs(u2):.1f} px zwischen zwei Knicken ({w1:.0f}°/{w2:.0f}°)")

print(f"Regionalgeometrie {SVG}: Achse {ACHSE and round(ACHSE, 2)} px, {len(paths)} Streckenpfade; "
      f"{dict(collections.Counter(b['regel'] for b in BEF)) or 'keine Befunde'}")
for b in BEF: print(f"  {b['regel']:3} x={b['x']} y={b['y']}  {b['text']}")
if "--json" in sys.argv:
    json.dump(dict(plan=SVG, achse=ACHSE, befunde=BEF), open(sys.argv[sys.argv.index("--json") + 1], "w"),
              ensure_ascii=False, indent=1)
