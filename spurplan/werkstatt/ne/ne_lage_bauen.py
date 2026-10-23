"""Lage Region Neuchâtel: Reihen mit Kastenbreiten aus den Spurplänen (ports.json) aneinanderreihen (15.10.2026)."""
import json, math
S = 0.42; G = 80; T60 = math.tan(math.radians(60))
R = 150          # Reihenabstand / Treppenstufe (vorher 380-400: zu viel Leerraum, 15.10.)
def hw(k):       # halbe Breite der Gleisanlage (ohne Blattrand und Beschriftung der Abgänge)
    P = json.load(open(f"{k}_ports.json")); cx = (P["x_hi"] + P["x_lo"]) / 2
    xs = [P["x_lo"], P["x_hi"]] + [p["x"] for p in P["ports"] if p["kind"] == "edge"]     # Abgänge können über den Rand reichen (Zihlbrücke)
    return max(cx - min(xs), max(xs) - cx) * S + 20
L = json.load(open("ne_region_lage.json"))
pos = {}
def put(name, x, y): pos[name] = [round(x), round(y)]
# 210 West, von Neuchâtel nach links (y = 0)
x = 0; put("Neuchâtel", 0, 0)
x -= hw("neuchatel") + 120; put("Abzweig #29", x, 0)
x -= 120 + hw("serrieres"); put("Serrières", x, 0)
x -= hw("serrieres") + G + hw("auvernier"); put("Auvernier", x, 0); xa = x
x -= hw("auvernier") + G + hw("colombier"); put("Colombier", x, 0); xc = x
x -= hw("colombier") + G + hw("boudry"); put("Boudry", x, 0)
put("Abgang 210 #38", x - hw("boudry") - 80 - 1.6 * R / T60 - 30, 1.6 * R)
# 219 (y = -380): Bôle über Colombier/Boudry, weiter nach Westen
Y = -R; x = xc - 100; put("Bôle", x, Y); xb = x
x -= hw("bole") + G + 540 + hw("champ_du_moulin"); put("Champ du Moulin", x, Y)   # Schlucht; westlich der Abgänge Yverdon/La Chaux-de-Fonds
x -= hw("champ_du_moulin") + G + hw("noiraigue"); put("Noiraigue", x, Y)
x -= hw("noiraigue") + G + hw("travers"); put("Travers", x, Y)
x -= hw("travers") + 160; put("Abgang 219 #40", x, Y + 40); put("Abgang 221 #45", x, Y - 40)
# 223 (y = -760): Chambrelien (Spitzkehre) westlich von Bôle, Corcelles östlich
Y = -2 * R; x = pos["Boudry"][0] - 60; put("Chambrelien", x, Y)    # Chambrelien westlich von Boudry
put("Abgang 224 #43", x + hw("chambrelien") + 60 + 1.6 * R / T60, Y - 1.6 * R)   # Spitzkehre: La Chaux-de-Fonds rechts oben (Hinweis 15.10.)
x = max(xc + 60, x + hw("chambrelien") + G + 100 + hw("corcelles_peseux")); put("Corcelles-Peseux", x, Y)   # Corcelles östlich von Colombier
# 210 Ost: Treppe nach rechts oben, je zwei Bahnhöfe pro Stufe
x = hw("neuchatel") + R / T60 + 120 + hw("saint_blaise_cff"); put("Saint-Blaise CFF", x, -R)
x += hw("saint_blaise_cff") + R / T60 + G + hw("cornaux"); put("Cornaux", x, -2 * R)
x += hw("cornaux") + G + hw("cressier"); put("Cressier", x, -2 * R)
x += hw("cressier") + R / T60 + G + hw("le_landeron"); put("Le Landeron", x, -3 * R)
x += hw("le_landeron") + G + hw("la_neuveville"); put("La Neuveville", x, -3 * R)
x += hw("la_neuveville") + R / T60 + G + hw("twann"); put("Twann", x, -4 * R)
put("Abgang 210 #44", x + hw("twann") + 160, -4 * R)
# 220 (y = +400)
x = hw("neuchatel") + R / T60 + 120 + hw("saint_blaise_lac"); put("Saint Blaise-Lac", x, R)
x += hw("saint_blaise_lac") + G + hw("marin_epagnier"); put("Marin-Epagnier", x, R)
x += hw("marin_epagnier") + G + hw("zihlbrucke"); put("Zihlbrücke", x, R)
x += hw("zihlbrucke") + G + hw("gampelen"); put("Gampelen", x, R)
x += hw("gampelen") + G + hw("ins"); put("Ins", x, R)
# Kerzers–Murten (Hinweis 15.10. abends), Anordnung wie im Dreieck-Netzplan vom 1.10.: Kerzers senkrecht (Kreuzung,
# Ins links oben, Lyss rechts oben, Murten links unten, Bern rechts unten), untere Reihe Murten – Muntelier – #30 – Galmiz,
# 256 von Ins über Sugiez (senkrecht) nach #30.
XINS = x
def pr(k, rot=0):     # Randabgänge (dx, ref, x, y) relativ zur Kastenmitte im Regionalmassstab, gedreht
    P = json.load(open(f"{k}_ports.json")); cx = (P["x_hi"] + P["x_lo"]) / 2; cy = (P["y_lo"] + P["y_hi"]) / 2
    out = []
    for p in P["ports"]:
        if p["kind"] != "edge": continue
        u, v = (p["x"] - cx) * S, (p["y"] - cy) * S
        if rot == 90: u, v = -v, u
        elif rot == 180: u, v = -u, -v
        elif rot:
            c_, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot)); u, v = u * c_ - v * s_, u * s_ + v * c_
        out.append((p["dx"], p.get("ref"), round(u, 1), round(v, 1)))
    for p in P["ports"]:        # seitliche Abzweige (kind side) als dx 2/-2
        if p["kind"] != "side": continue
        u, v = (p["x"] - cx) * S, (p["y"] - cy) * S
        if rot: c_, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot)); u, v = u * c_ - v * s_, u * s_ + v * c_
        out.append((2 * p["dx"], p.get("ref"), round(u, 1), round(v, 1)))
    return out
x += hw("ins") + 60; put("Abzweig #35", x, R)
x += 60 + hw("muntschemier"); put("Müntschemier", x, R)
KP = pr("kerzers", 90); k_ins = [q for q in KP if q[1] == "220" and q[0] < 0][0]; k_lys = [q for q in KP if q[1] == "251" and q[0] < 0][0]
k_mur = [q for q in KP if q[1] == "251" and q[0] > 0][0]; k_brn = [q for q in KP if q[1] == "220" and q[0] > 0][0]
YR = R + 20                                 # Gleishöhe Reihe Ins (ungefähr, wird unten ausgerichtet)
KY = YR + 90 - k_ins[3]                     # oberer Abgang 90 unter der Reihe
KX = x + hw("muntschemier") + G + 100 + 90 / T60 - k_ins[2]
put("Kerzers", KX, KY)
put("Abgang 251 #41", KX + k_lys[2] + 240 / T60 + 120, KY + k_lys[3] - 240)   # Lyss: 60° nach rechts oben, kurzer Auslauf
put("Abgang 220 #39", KX + k_brn[2] + 120 / T60 + 120, KY + k_brn[3] + 120)
YL = KY + k_mur[3] + 100                    # untere Reihe
x = KX + k_mur[2] - 100 / T60 - 40 - hw("galmiz"); put("Galmiz", x, YL)
x -= hw("galmiz") + 110; put("Abzweig #30", x, YL); X30 = x
x -= 60 + hw("muntelier_lowenberg"); put("Muntelier-Löwenberg", x, YL)
x -= hw("muntelier_lowenberg") + G + hw("murten"); put("Murten", x, YL)
put("Abgang 251 #42", x - hw("murten") - 160, YL); put("Abgang 255 #46", x - hw("murten") - 60 - 110 / T60, YL + 110)
# Ausrichten (15.10.): benachbarte Bahnhöfe einer Reihe so in der Höhe verschieben, dass die durchgehenden Gleise
# gerade weiterlaufen (keine S-Knicke auf freier Strecke). Versatz = Mittel der Randabgänge der zugewandten Seite.
KEY = {"Travers": "travers", "Noiraigue": "noiraigue", "Champ du Moulin": "champ_du_moulin", "Bôle": "bole",
       "Boudry": "boudry", "Colombier": "colombier", "Auvernier": "auvernier", "Serrières": "serrieres", "Neuchâtel": "neuchatel",
       "Chambrelien": "chambrelien", "Corcelles-Peseux": "corcelles_peseux", "Saint Blaise-Lac": "saint_blaise_lac",
       "Marin-Epagnier": "marin_epagnier", "Zihlbrücke": "zihlbrucke", "Gampelen": "gampelen", "Ins": "ins",
       "Cornaux": "cornaux", "Cressier": "cressier", "Le Landeron": "le_landeron", "La Neuveville": "la_neuveville",
       "Saint-Blaise CFF": "saint_blaise_cff", "Twann": "twann", "Müntschemier": "muntschemier", "Kerzers": "kerzers",
       "Galmiz": "galmiz", "Muntelier-Löwenberg": "muntelier_lowenberg", "Murten": "murten", "Sugiez": "sugiez"}
ROT = {"Kerzers": 90, "Sugiez": 60}     # Kerzers senkrecht, Sugiez unter 60° (Daniel 16.10.: schräge Lage erlaubt)
REF = {}      # Kette -> nur Abgänge dieser Linie zum Ausrichten (Chambrelien: 223, nicht 224)
def pys(name, d):     # Höhen der Randabgänge auf Seite d (relativ zur Kastenmitte, Regionalmassstab), Drehung 180 beachtet
    P = json.load(open(f"{KEY[name]}_ports.json")); cy = (P["y_lo"] + P["y_hi"]) / 2; f = -1 if ROT.get(name) == 180 else 1
    return sorted(f * (p["y"] - cy) * S for p in P["ports"] if p["kind"] == "edge" and p["dx"] == f * d and (name not in REF or p["ref"] == REF[name]))
def off(name, d):
    ys = pys(name, d); return sum(ys) / len(ys) if ys else 0.0
def offp(a_, b_, da):      # Versatz-Paar fuer a_ (Seite da) gegen b_ (Seite -da)
    ya, yb = pys(a_, da), pys(b_, -da)
    if len(ya) == 1 and len(yb) >= 2: return ya[0], yb[0]       # Einspur gegen Doppelspur: oberes Gleis gerade
    if len(yb) == 1 and len(ya) >= 2: return ya[0], yb[0]
    return off(a_, da), off(b_, -da)
def ausrichten(kette, anker):          # kette von links nach rechts
    i0 = kette.index(anker)
    for i in range(i0 + 1, len(kette)):
        a_, b_ = kette[i - 1], kette[i]; oa, ob = offp(a_, b_, 1); pos[b_][1] = round(pos[a_][1] + oa - ob)
    for i in range(i0 - 1, -1, -1):
        a_, b_ = kette[i + 1], kette[i]; oa, ob = offp(a_, b_, -1); pos[b_][1] = round(pos[a_][1] + oa - ob)
REF["Auvernier"] = "210"
ausrichten(["Boudry", "Colombier", "Auvernier", "Serrières", "Neuchâtel"], "Neuchâtel")
pos["Abzweig #29"][1] = round(pos["Serrières"][1] + off("Serrières", 1))   # Abzweig auf Gleishöhe
ausrichten(["Travers", "Noiraigue", "Champ du Moulin", "Bôle"], "Bôle")
REF["Chambrelien"] = "223"
ausrichten(["Chambrelien", "Corcelles-Peseux"], "Corcelles-Peseux")
REF["Kerzers"] = "220"
ausrichten(["Saint Blaise-Lac", "Marin-Epagnier", "Zihlbrücke", "Gampelen", "Ins", "Müntschemier"], "Saint Blaise-Lac")
pos["Abzweig #35"][1] = round(pos["Ins"][1] + off("Ins", 1))
ausrichten(["Murten", "Muntelier-Löwenberg", "Galmiz"], "Galmiz")
pos["Abzweig #30"][1] = round(pos["Galmiz"][1] + off("Galmiz", -1))
pos["Abgang 251 #42"][1] = round(pos["Murten"][1] + off("Murten", -1))
# Sugiez schräg (60°): die 256 läuft von Ins (#35) unter 60° nach rechts unten durch Sugiez und dann unter 60° nach
# links unten in den seitlichen Abzweig von Muntelier – ohne senkrechte Stücke. Lage so, dass beide Schrägen genau treffen.
SPp = pr("sugiez", 60); b_ = max(SPp, key=lambda q: q[3])           # unteres (rechtes) Ende
MP = [q for q in pr("muntelier_lowenberg", 0) if abs(q[0]) == 2]
if MP:
    Mp = (pos["Muntelier-Löwenberg"][0] + MP[0][2], pos["Muntelier-Löwenberg"][1] + MP[0][3])
    P0 = (pos["Abzweig #35"][0] + 50, pos["Abzweig #35"][1])
    ux, uy = 0.5, math.sqrt(3) / 2; lx, ly = -0.5, math.sqrt(3) / 2
    ax_, ay_ = Mp[0] - P0[0] - b_[2], Mp[1] - P0[1] - b_[3]
    t_ = (ax_ * ly - ay_ * lx) / (ux * ly - uy * lx)
    tp_ = min(SPp, key=lambda q: q[3])                                  # oberes (linkes) Ende
    t_min = (60 - tp_[3]) / uy                                          # oberes Ende mindestens 60 unter der Reihe Ins
    t_ = max(t_, t_min)
    put("Sugiez", P0[0] + t_ * ux, P0[1] + t_ * uy)
ausrichten(["Cornaux", "Cressier"], "Cornaux")
ausrichten(["Le Landeron", "La Neuveville"], "Le Landeron")
# Abgänge am Rand auf Höhe der Gleise des Nachbarbahnhofs (kein Knick vor dem Blattrand)
pos["Abgang 210 #44"][1] = round(pos["Twann"][1] + off("Twann", 1))
# Travers: 219 (Fleurier) liegt im Plan oben, 221 (Pontarlier) unten -> Abgänge entsprechend (keine Kreuzung)
pos["Abgang 219 #40"][1] = pos["Travers"][1] - 40; pos["Abgang 221 #45"][1] = pos["Travers"][1] + 40
for k_ in [k_ for k_ in L if k_.startswith("Abzweig #") or k_.startswith("Abgang ")]: del L[k_]   # alte Knotennummern (Topologie neu)
L.update(pos); L["frueh"] = ["Bôle|Auvernier"]; L["drehung"] = {"Champ du Moulin": 0, "Chambrelien": 0, "Müntschemier": 0, "Galmiz": 0, "Muntelier-Löwenberg": 0, "Murten": 0, **ROT}
L["spaet_anteil_strecke"] = {"Corcelles-Peseux|#29": 0.97}
json.dump(L, open("ne_region_lage.json", "w"), ensure_ascii=False, indent=1)
print(pos)
