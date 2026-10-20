"""Gemeinsame Hilfen der Vorbereitung (Lesen der Abzüge, lokale Meter, Geometrie)."""
import json, gzip, math, os

def lade_osm(pfad):
    op = gzip.open if pfad.endswith(".gz") else open
    d = json.load(op(pfad, "rt", encoding="utf-8"))
    return d["elements"] if isinstance(d, dict) else d

def lade_geojson(pfad):
    if not os.path.exists(pfad) or os.path.getsize(pfad) < 10: return []
    d = json.load(open(pfad, encoding="utf-8"))
    return d.get("features", d if isinstance(d, list) else [])

def feld(props, *stichworte, ausser=()):
    """Feldname per Stichwort finden (die SBB-Exporte benennen Felder je Datensatz anders)."""
    for s in stichworte:
        for k in props:
            if s in k.lower() and not any(a in k.lower() for a in ausser): return k
    return None

def punkt(geom):
    """Repräsentativer Punkt (lat, lon) einer GeoJSON-Geometrie."""
    if not geom: return None
    c = geom["coordinates"]
    if geom["type"] == "Point": return (c[1], c[0])
    pts = []
    def flach(x):
        if isinstance(x[0], (int, float)): pts.append(x)
        else:
            for y in x: flach(y)
    flach(c)
    return (sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts))

def linie(geom):
    """Punktliste (lat, lon) einer Linien-/Flächengeometrie."""
    c = geom["coordinates"]
    while isinstance(c[0][0], list): c = c[0]
    return [(p[1], p[0]) for p in c]

class Lokal:
    """lat/lon -> Meter um einen Bezugspunkt"""
    def __init__(self, la0, lo0): self.la0, self.lo0, self.kx = la0, lo0, 111320 * math.cos(math.radians(la0))
    def __call__(self, la, lo): return ((lo - self.lo0) * self.kx, (la - self.la0) * 110540)

def m(a, b):
    """Abstand in Metern zweier (lat, lon)"""
    return math.hypot((a[0] - b[0]) * 110540, (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0])))

def normalspur(e):
    t = e.get("tags", {})
    return e.get("type") == "way" and t.get("railway") == "rail" and t.get("gauge", "1435") in ("1435", "1435;1000") \
        and t.get("usage") != "tourism" and "geometry" in e

def seg_abstand(p, a, b):
    """Abstand Punkt-Strecke in Metern (lokale Ebene) und Fusspunkt"""
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy or 1e-9
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    fx, fy = ax + t * dx, ay + t * dy
    return math.hypot(px - fx, py - fy), (fx, fy), (dx, dy)

def name_gleich(a, b):
    """grober Namensvergleich (SBB-Kurznamen ohne Akzente, 'St-' für 'Saint-', Zusätze wie 'NE', 'CFF')"""
    import unicodedata, re
    def n(s):
        s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
        s = s.replace("saint-", "st-").replace("saint ", "st-")
        s = re.sub(r"\b(ne|cff|sbb|fr|vd|be|bls)\b", "", s)
        return re.sub(r"[^a-z]", "", s)
    return n(a) == n(b) or (n(a) and n(b) and (n(a).startswith(n(b)) or n(b).startswith(n(a))))
