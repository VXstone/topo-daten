"""Bausteine des Blaupausen-Prüfstands als synthetische OSM-Daten (Schritt 1, D. Eckenstein 6./8.11.2026).

Jeder Baustein ist eine kleine Region (Meterspur, Betreiber «PS», Linien 900/901) in lokalen Metern (x Ost, y Nord),
die um einen beliebigen Winkel gedreht als OSM-Elemente (Overpass-Form mit geometry) geschrieben wird. Der Prüfstand
rechnet sie mit demselben Code wie die Linien-Regionen (region_lauf.py) – geprüft werden also die gemeinsamen Bausteine
(Bahnhofplan, Ports, Stummel, Pfeile, Rundungen, connector, Lage), nicht eine Nachbildung.

  bau(name, drehung, datei) -> Netz          Baustein schreiben (drehung in Grad, Gegenuhrzeigersinn wie die Karte)
  BAUSTEINE                                   Name -> (Funktion, Beschreibung, Erwartung)

Erwartung je Baustein (für die Messung): «perrons» = Zahl der Perronflächen, «formen» = {Bahnhof: [Teile je Fläche]}
(U/L/T = 3/2/3 Balken in einer zusammenhängenden Fläche).
"""
import json, math, gzip

LAT0, LON0 = 46.80, 8.00
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110540
MS = dict(railway="narrow_gauge", gauge="1000", operator="PS")
A = 4.5                 # Gleisabstand (m)


class Netz:
    def __init__(s, drehung=0.0):
        s.nid = 1000; s.wid = 1; s.nodes = {}; s.el = []; s.rot = math.radians(drehung)

    def p(s, x, y, tags=None):
        c, si = math.cos(s.rot), math.sin(s.rot); X, Y = x * c - y * si, x * si + y * c
        s.nid += 1; s.nodes[s.nid] = dict(lat=round(LAT0 + Y / KY, 8), lon=round(LON0 + X / KX, 8))
        if tags: s.tag(s.nid, tags)
        return s.nid

    def tag(s, n, tags):
        for e in s.el:
            if e["type"] == "node" and e["id"] == n: e["tags"].update(tags); return
        s.el.append(dict(type="node", id=n, tags=dict(tags), **s.nodes[n]))

    def way(s, ns, **tags):
        s.wid += 1; s.el.append(dict(type="way", id=s.wid, nodes=list(ns), geometry=[s.nodes[n] for n in ns], tags=tags)); return s.wid

    def kette(s, pts, step=40.0, **tags):
        """Way durch Punkte (Knoten-ID oder (x, y)), Zwischenknoten alle step m"""
        out = []
        for q in pts:
            q_id = q if isinstance(q, int) else None
            b = s.xy(q) if q_id else q
            if out:
                a = s.xy(out[-1]); n = int(math.dist(a, b) // step)
                for k in range(1, n): out.append(s.p(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
            out.append(q_id if q_id else s.p(*b))
        s.way(out, **tags); return out

    def xy(s, n):
        g = s.nodes[n]; X, Y = (g["lon"] - LON0) * KX, (g["lat"] - LAT0) * KY
        c, si = math.cos(-s.rot), math.sin(-s.rot); return (X * c - Y * si, X * si + Y * c)

    def flaeche(s, pts, **tags):
        ns = [s.p(*q) for q in pts]; s.way(ns + [ns[0]], **tags)

    def speichern(s, f):
        with gzip.open(f, "wt") as fh: json.dump(dict(elements=s.el), fh)

    def bbox_stationen(s, rand_m=1500):
        """Ausschnitt um die Stationsknoten: Strecken laufen über den Rand hinaus und werden Abgänge"""
        st = [e for e in s.el if e["type"] == "node" and e["tags"].get("railway") == "station"]
        la = [e["lat"] for e in st]; lo = [e["lon"] for e in st]
        return [round(min(la) - rand_m / KY, 5), round(min(lo) - rand_m / KX, 5), round(max(la) + rand_m / KY, 5), round(max(lo) + rand_m / KX, 5)]

    def bbox(s, rand=0.008):
        la = [g["lat"] for g in s.nodes.values()]; lo = [g["lon"] for g in s.nodes.values()]
        return [round(min(la) - rand, 5), round(min(lo) - rand, 5), round(max(la) + rand, 5), round(max(lo) + rand, 5)]


class Gleis:
    """gerades Gleis: Ursprung o, Richtung w (Grad), quer = seitlicher Versatz (links positiv). Knoten bei Bedarf (t entlang)."""
    def __init__(s, N, o=(0, 0), w=0.0, quer=0.0):
        s.N = N; s.o = o; s.u = (math.cos(math.radians(w)), math.sin(math.radians(w))); s.q = quer; s.k = {}

    def pt(s, t):
        return (s.o[0] + s.u[0] * t - s.u[1] * s.q, s.o[1] + s.u[1] * t + s.u[0] * s.q)

    def at(s, t, tags=None):
        t = round(t, 2)
        if t not in s.k: s.k[t] = s.N.p(*s.pt(t))
        if tags: s.N.tag(s.k[t], tags)
        return s.k[t]

    def ways(s, t0, t1, schnitte=(), tags_fn=None, step=40.0):
        cuts = sorted({round(t0, 2), round(t1, 2)} | {round(c, 2) for c in schnitte if t0 < c < t1})
        for c in cuts: s.at(c)
        t = t0 + step
        while t < t1 - 1: s.at(t); t += step
        ks = sorted(t for t in s.k if t0 - 1e-6 <= t <= t1 + 1e-6)
        for a, b in zip(cuts, cuts[1:]):
            ns = [s.k[t] for t in ks if a - 1e-6 <= t <= b + 1e-6]
            s.N.way(ns, **(tags_fn(a, b) if tags_fn else dict(MS, ref="900")))


def _tags(ref, nr=None, halte=(), halb=150, service=None):
    def f_(a, b):
        t = dict(MS)
        if ref: t["ref"] = ref
        if service: t["service"] = service
        if nr and any(x0 - halb <= a and b <= x0 + halb for x0 in halte): t["railway:track_ref"] = nr
        return t
    return f_


def _perron(N, x0, y, seite, ref, L=150, B=3.0):
    """Seitenperron entlang der x-Achse (seite +1 = nördlich der Kante y)"""
    N.flaeche([(x0 - L / 2, y), (x0 + L / 2, y), (x0 + L / 2, y + seite * B), (x0 - L / 2, y + seite * B)], railway="platform", ref=ref)


def _spurwechsel(N, g_von, g_nach, t, L=40.0):
    a = g_von.at(t, dict(railway="switch")); b = g_nach.at(t + L, dict(railway="switch"))
    N.way([a, b], **dict(MS, service="crossover")); return [t, t + L]


def _doppelspur(N, halte, extra_schnitte=(), x0=-3500, x1=6500, perrons="aussen"):
    """Doppelspur 900 (Gl. 1 y=0, Gl. 2 y=-A) mit Bahnhöfen (Spurwechsel beidseits, Perrons)"""
    g1 = Gleis(N, quer=0.0); g2 = Gleis(N, quer=-A)
    sch = list(extra_schnitte)
    for x, nm in halte:
        sch += _spurwechsel(N, g1, g2, x - 260) + _spurwechsel(N, g2, g1, x + 220)
        sch += [x - 150, x + 150]
        N.p(x, -A / 2, dict(railway="station", name=nm))
        if perrons == "aussen":
            _perron(N, x, 1.6, +1, "1"); _perron(N, x, -A - 1.6, -1, "2")
    g1.ways(x0, x1, sch, _tags("900", "1", [x for x, _ in halte]))
    g2.ways(x0, x1, sch, _tags("900", "2", [x for x, _ in halte]))
    return g1, g2


# ------------------------------------------------------------------ Reinformen
def r3_kreuzung(N):
    """Einspur mit Kreuzungsgleis, zwei Aussenperrons (Blaupause R3)"""
    g = Gleis(N); k = Gleis(N, quer=A)
    sch = []
    for x, nm in ((0, "Alpha"), (3000, "Beta")):
        a = g.at(x - 220, dict(railway="switch")); b = g.at(x + 220, dict(railway="switch"))
        sch += [x - 220, x + 220]
        k.ways(x - 180, x + 180, (), _tags(None, "1", [x], service="siding"))
        N.way([a, k.at(x - 180)], **MS, service="siding"); N.way([k.at(x + 180), b], **MS, service="siding")
        N.p(x, A / 2, dict(railway="station", name=nm))
        _perron(N, x, A + 1.6, +1, "1"); _perron(N, x, -1.6, -1, "2")
    g.ways(-3500, 6500, sch + [x + d for x in (0, 3000) for d in (-150, 150)], _tags("900", "2", [0, 3000]))


def r5_halt(N):
    """Doppelspur, Halt mit Spurwechseln beidseits, zwei Aussenperrons (Blaupause R5 + Z1/Z2)"""
    _doppelspur(N, [(0, "Alpha"), (3000, "Beta")])


def r7_ueberholung(N):
    """Doppelspur mit Überholgleisen beidseits und zwei Mittelperrons (Blaupause R7)"""
    g1, g2 = _doppelspur(N, [(0, "Alpha"), (3000, "Beta")], perrons="keine")
    for x in (0, 3000):
        for g, q, nr, s_ in ((g1, A, "1", +1), (g2, -2 * A, "4", -1)):
            u = Gleis(N, quer=q)
            u.ways(x - 170, x + 170, (), _tags(None, nr, [x], service="siding"))
            N.way([g.at(x - 200, dict(railway="switch")), u.at(x - 170)], **MS, service="siding")
            N.way([u.at(x + 170), g.at(x + 200, dict(railway="switch"))], **MS, service="siding")
            yk = q - s_ * A / 2          # Mittelperron zwischen Überholgleis und Streckengleis
            N.flaeche([(x - 75, yk - 1.4), (x + 75, yk - 1.4), (x + 75, yk + 1.4), (x - 75, yk + 1.4)], railway="platform",
                      ref=("2;1" if s_ > 0 else "3;4"))


# ------------------------------------------------------------------ Abgänge
def _abzweig(N, phi):
    """Doppelspur 900 Alpha–Beta; östlich Alpha zweigt Doppelspur 901 unter phi nach Norden ab, Ziel Gamma"""
    g1, g2 = _doppelspur(N, [(0, "Alpha"), (3000, "Beta")], extra_schnitte=(320, 360))
    s1 = g1.at(320, dict(railway="switch"))
    # Gleisdreieck vermeiden: 901 beginnt an Gl. 1 (Weiche), zweites Gleis über Spurwechsel von Gl. 2
    s2 = g2.at(360, dict(railway="switch"))
    u = (math.cos(math.radians(phi)), math.sin(math.radians(phi))); n = (-u[1], u[0])
    p1 = g1.pt(320); L = 2600
    a1 = [s1, (p1[0] + u[0] * L, p1[1] + u[1] * L)]
    # zweites Gleis rechts (quer -A) parallel; Anschluss an Gl. 2 schräg über Gl. 1 hinweg wäre eine Kreuzung – daher
    # beginnt es an Gl. 1 weiter östlich (Weiche) und läuft parallel
    t2 = 320 + A / math.tan(math.radians(phi)) + A / math.sin(math.radians(phi)) * 0 + 30
    s2b = g1.at(t2, dict(railway="switch"))
    p2 = g1.pt(t2); q2 = (p1[0] + u[0] * 60 - n[0] * A, p1[1] + u[1] * 60 - n[1] * A)
    a2 = [s2b, q2, (p1[0] + u[0] * L - n[0] * A, p1[1] + u[1] * L - n[1] * A)]
    N.kette(a1, **MS, ref="901"); N.kette(a2, **MS, ref="901")
    e = (p1[0] + u[0] * 1000, p1[1] + u[1] * 1000)
    N.p(e[0] - n[0] * A / 2, e[1] - n[1] * A / 2, dict(railway="station", name="Gamma"))


def ab30(N): _abzweig(N, 30)
def ab60(N): _abzweig(N, 60)


def sagliains(N):
    """Fall h9o9: zwei parallele Nebengleise verlassen den Bahnhof Alpha unter 60° nach Süden zum Verlad «Delta»"""
    g1, g2 = _doppelspur(N, [(0, "Alpha"), (3000, "Beta")], extra_schnitte=(180, 240))
    phi = -60; u = (math.cos(math.radians(phi)), math.sin(math.radians(phi))); n = (-u[1], u[0])
    L = 1300
    for t0, q in ((180, 0.0), (240, -A)):
        s = g2.at(t0, dict(railway="switch")); p = g2.pt(t0)
        # Parallelversatz quer zur Schräge (A), Start am Gleis 2
        st = (p[0] + u[0] * 20 + n[0] * q, p[1] + u[1] * 20 + n[1] * q)
        en = (p[0] + u[0] * L + n[0] * q, p[1] + u[1] * L + n[1] * q)
        ns = N.kette([s, st, en], **MS, service="siding")
        N.tag(ns[-1], dict(railway="buffer_stop"))
    pe = g2.pt(210); c = (pe[0] + u[0] * (L - 120), pe[1] + u[1] * (L - 120))
    N.p(c[0], c[1], dict(railway="station", name="Delta"))
    N.flaeche([(c[0] + u[0] * 60 + n[0] * 2.2, c[1] + u[1] * 60 + n[1] * 2.2), (c[0] - u[0] * 60 + n[0] * 2.2, c[1] - u[1] * 60 + n[1] * 2.2),
               (c[0] - u[0] * 60 + n[0] * 5.2, c[1] - u[1] * 60 + n[1] * 5.2), (c[0] + u[0] * 60 + n[0] * 5.2, c[1] + u[1] * 60 + n[1] * 5.2)],
              railway="platform", ref="1")



def _buendel_knick(N, knick, abstand):
    """S1 (Sagliains-Portal, 12.11.2026): zwei Nebengleise laufen nördlich von Gl. 1 parallel (Querabstand «abstand» m) nach
    Westen und knicken gemeinsam um «knick» Grad nach Norden zum Verlad «Delta». Geografisch bleiben sie parallel: der Knick
    des äusseren (nördlichen) Gleises liegt um abstand·tan(knick/2) weiter östlich. Im Plan muss der Querabstand nach dem
    Knick gleich sein wie davor (Messung QK)."""
    g1, g2 = _doppelspur(N, [(0, "Alpha"), (3000, "Beta")], extra_schnitte=(200,))
    phi = math.radians(180 - knick); u = (math.cos(phi), math.sin(phi)); L = 1300
    w = g1.at(200, dict(railway="switch")); y1 = A; x_k1 = -540                 # inneres Gleis: Knick bei x_k1
    ns1 = N.kette([w, (160, y1), (x_k1, y1), (x_k1 + u[0] * L, y1 + u[1] * L)], **MS, service="siding")
    N.tag(ns1[-1], dict(railway="buffer_stop"))
    # äusseres Gleis zweigt vom inneren ab (Weiche bei x = 60), Knick geografisch parallel
    w2 = [n for n in ns1 if abs(N.xy(n)[0] - 120) < 25 and abs(N.xy(n)[1] - y1) < 0.5]
    w2 = w2[0] if w2 else N.p(120, y1)
    N.tag(w2, dict(railway="switch"))
    y2 = y1 + abstand; x_k2 = x_k1 + abstand * math.tan(math.radians(knick) / 2)
    ns2 = N.kette([w2, (90, y2), (x_k2, y2), (x_k2 + u[0] * L, y2 + u[1] * L)], **MS, service="siding")
    N.tag(ns2[-1], dict(railway="buffer_stop"))
    c = (x_k1 + u[0] * (L - 120), y1 + abstand / 2 + u[1] * (L - 120)); n = (-u[1], u[0])
    N.p(c[0], c[1], dict(railway="station", name="Delta"))
    N.flaeche([(c[0] + u[0] * 60 - n[0] * 4, c[1] + u[1] * 60 - n[1] * 4), (c[0] - u[0] * 60 - n[0] * 4, c[1] - u[1] * 60 - n[1] * 4),
               (c[0] - u[0] * 60 - n[0] * 7, c[1] - u[1] * 60 - n[1] * 7), (c[0] + u[0] * 60 - n[0] * 7, c[1] + u[1] * 60 - n[1] * 7)],
              railway="platform", ref="1")


def buendel_knick(N): _buendel_knick(N, 60, A)
def buendel_knick_eng(N): _buendel_knick(N, 30, 0.55 * A)

# ------------------------------------------------------------------ Ebenen
def unterwerfung(N):
    """Aarau West: Einspur 901 läuft nördlich neben der Doppelspur 900, taucht östlich Alpha darunter durch (Tunnel,
    layer -1) und läuft südlich weiter nach Gamma"""
    _doppelspur(N, [(0, "Alpha"), (3000, "Beta")])
    q0 = 2 * A + 3
    a = (-3500, q0); b = (250, q0); c = (300 + 60, q0 - 30); d = (480, -A - 16); e = (560, -A - 26)
    w = N.kette([a, b, c], **MS, ref="901")
    N.kette([w[-1], d], **MS, ref="901", tunnel="yes", layer="-1")
    N.kette([N.nid, e, (900, -A - 120), (5200, -2400)], **MS, ref="901")


def zwischengerade(N):
    """Doppelspur macht zwischen Alpha und Beta einen geografischen Versatz von 40 m (zwei 30°-Bögen, 25 m Gerade
    dazwischen) – im Schema soll die Strecke ohne Treppe/kurze Zwischengerade durchlaufen"""
    pts = []
    dx = 20 / math.tan(math.radians(30))          # 30°-Bogen über 20 m quer
    for q in (0.0, -A):
        geo = [(-3500, q), (1300, q), (1300 + dx, q + 20), (1300 + dx + 25, q + 20), (1300 + 2 * dx + 25, q + 40), (6500, q + 40)]
        pts.append(N.kette(geo, **MS, ref="900"))
    for (x0, yoff, nm) in ((0, 0, "Alpha"), (3000, 40, "Beta")):
        N.p(x0, yoff - A / 2, dict(railway="station", name=nm))
        _perron(N, x0, yoff + 1.6, +1, "1"); _perron(N, x0, yoff - A - 1.6, -1, "2")
    # Spurwechsel als Weichen (je Bahnhof einer), damit die Bahnhöfe Pläne bekommen
    for (x0, yoff) in ((0, 0), (3000, 40)):
        a = _naechster(N, pts[0], (x0 + 200, yoff)); b = _naechster(N, pts[1], (x0 + 240, yoff - A))
        N.tag(a, dict(railway="switch")); N.tag(b, dict(railway="switch")); N.way([a, b], **MS, service="crossover")


def _naechster(N, ns, p):
    return min(ns, key=lambda n: math.dist(N.xy(n), p))


def gleissprung(N):
    """Basel: Gl. 3 (Durchgangsgleis) liegt westlich neben Gl. 2; nach dem Ende des Abstellgleises 4 rückt es in OSM
    ohne Weiche um 6 m nach aussen. Ein durchgehendes Gleis wechselt die Ebene nur an Weiche oder Werfung."""
    g1, g2 = _doppelspur(N, [(0, "Alpha"), (3000, "Beta")], extra_schnitte=(-420, 420))
    q3 = -2 * A
    sw_w = g2.at(-420, dict(railway="switch")); sw_o = g2.at(420, dict(railway="switch"))
    w3 = N.kette([sw_w, (-380, q3), (-100, q3), (60, q3 - 6), (380, q3 - 6), sw_o], **MS, service="siding", **{"railway:track_ref": "3"})
    # Abstellgleis 4 westlich, endet bei x = -20 (Prellbock), danach rückt Gl. 3 auf seinen Platz
    k = _naechster(N, w3, (-380, q3))
    N.tag(k, dict(railway="switch"))
    w4 = N.kette([k, (-340, q3 - 6), (-20, q3 - 6)], **MS, service="siding")
    N.tag(w4[-1], dict(railway="buffer_stop"))
    _perron(N, 0, q3 - 1.6 - 0, -1, "3", L=120)


def perronformen(N):
    """Perronformen U/L/T (Montreux, Thun, Basel): Kopfgleise 3 und 4 östlich enden an Prellböcken;
    U um Gl. 4 (beide Kanten + Querstück am Prellbock), L an Gl. 3 (Längsbalken + Querstück), T verbindet die Mittelperrons
    1|2 und L am Kopf"""
    g1, g2 = _doppelspur(N, [(0, "Alpha"), (3000, "Beta")], perrons="keine", extra_schnitte=(-380, -330))
    # Stumpengleise 3, 4 nördlich von Gl. 1 (Weichen westlich des Spurwechsels bei −260 m), Prellböcke bei x = 90
    for q, nr, t0 in ((A + 6, "3", -330), (2 * A + 12, "4", -380)):
        s = g1.at(t0, dict(railway="switch")); ns = N.kette([s, (t0 + 40, q), (90, q)], **MS, service="siding", **{"railway:track_ref": nr})
        N.tag(ns[-1], dict(railway="buffer_stop"))
    q3, q4 = A + 6, 2 * A + 12
    # U um Gl. 4: Balken südlich (zwischen 3 und 4), nördlich, Querstück östlich des Prellbocks
    N.flaeche([(-80, q4 - 1.6), (92, q4 - 1.6), (92, q4 + 1.6), (-80, q4 + 1.6), (-80, q4 + 4.6), (96, q4 + 4.6),
               (96, q4 - 4.6), (-80, q4 - 4.6)], railway="platform", ref="4")
    # L an Gl. 3 (Längsbalken südlich von 3 = zwischen 1 und 3) mit Querstück am Kopf, verbunden mit dem U nicht
    N.flaeche([(-80, q3 - 1.6), (92, q3 - 1.6), (92, q3 + 1.6), (96, q3 + 1.6), (96, q3 - 4.6), (-80, q3 - 4.6)],
              railway="platform", ref="3")
    # Seitenperron Gl. 2 (Kontrolle: einfacher Balken)
    _perron(N, 0, -A - 1.6, -1, "2")


def buendel_versatz(N):
    """R1b (Aarau Ost – Rupperswil): Vierspur aus zwei Doppelspuren 900/901. In Alpha liegt zwischen den Paaren ein
    Überholgleis (der Plan zeichnet dort eine Lücke von einer Ebene), Beta hat keins. Die Gleise verlassen Alpha also
    ungleich verteilt; die Strecken sollen als Bündel andocken: jedes Paar bleibt in sich parallel im Gleisabstand
    (ein nötiger Versatz gilt fürs ganze Paar), zum Planrand hin bleibt der Querabstand des Bahnhofs (kein Trichter)."""
    q = [0.0, -A, -3 * A, -4 * A]
    gs = [Gleis(N, quer=y) for y in q]
    sch = []
    for x, nm in ((0, "Alpha"), (3000, "Beta")):
        sch += _spurwechsel(N, gs[0], gs[1], x - 260) + _spurwechsel(N, gs[1], gs[0], x + 220)
        sch += _spurwechsel(N, gs[2], gs[3], x - 220) + _spurwechsel(N, gs[3], gs[2], x + 260)
        sch += [x - 150, x + 150]
        N.p(x, -2 * A, dict(railway="station", name=nm))
        _perron(N, x, 1.6, +1, "1"); _perron(N, x, -4 * A - 1.6, -1, "4")
    # Überholgleis zwischen den Paaren in Alpha (beidseits an Gl. 2)
    a = gs[1].at(-330, dict(railway="switch")); b = gs[1].at(330, dict(railway="switch")); sch += [-330, 330]
    N.kette([a, (-290, -2 * A), (290, -2 * A), b], **MS, service="siding")
    for g_, ref, nr in zip(gs, ("900", "900", "901", "901"), ("1", "2", "3", "4")):
        g_.ways(-3500, 6500, sch, _tags(ref, nr, [0, 3000]))


BAUSTEINE = {
    "r3_kreuzung": (r3_kreuzung, "Einspur, Kreuzungsgleis, zwei Aussenperrons (R3)", dict(perrons=4)),
    "r5_halt": (r5_halt, "Doppelspur, Halt mit Spurwechseln, zwei Aussenperrons (R5, Z1/Z2)", dict(perrons=4)),
    "r7_ueberholung": (r7_ueberholung, "Doppelspur, Überholgleise beidseits, Mittelperrons (R7)", dict(perrons=4)),
    "ab30": (ab30, "Doppelspur zweigt unter 30° ab (schräger Abgang)", dict()),
    "ab60": (ab60, "Doppelspur zweigt unter 60° ab (schräger Abgang)", dict()),
    "sagliains": (sagliains, "zwei Nebengleise verlassen den Plan unter 60° (h9o9 Sagliains)", dict()),
    "unterwerfung": (unterwerfung, "Einspur taucht unter der Doppelspur durch (Aarau West)", dict()),
    "zwischengerade": (zwischengerade, "geografischer Versatz 40 m zwischen zwei Bahnhöfen (Zwischengerade)", dict()),
    "gleissprung": (gleissprung, "durchgehendes Gleis rückt ohne Weiche nach aussen (Basel)", dict()),
    "perronformen": (perronformen, "Perronformen U und L an Kopfgleisen (Montreux, Thun, Basel)", dict(formen={"Alpha": {"U": 1, "L": 1}})),
    "buendel_knick": (buendel_knick, "zwei Nebengleise knicken gemeinsam um 60°, Abstand 1 Ebene (Sagliains, S1)", dict()),
    "buendel_knick_eng": (buendel_knick_eng, "zwei Nebengleise knicken gemeinsam um 30°, Abstand 0,55 Ebene (Sagliains, S1)", dict()),
    "buendel_versatz": (buendel_versatz, "Vierspur, Lücke zwischen den Paaren ½ Ebene breiter (Aarau Ost, R1b)", dict(perrons=2)),
}


def bau(name, drehung, datei):
    N = Netz(drehung); BAUSTEINE[name][0](N); N.speichern(datei); return N
