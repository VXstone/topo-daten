"""Neuchâtel-Region: Ausschnitte je Bahnhof (Rechteck aus ne_region.json, dann Kreis), Override-Grundgerüst."""
import json, math, sys, os, subprocess
ST = {  # key: (name, osm-node, radius)
 "twann": ("Twann", 3081154447, 1500), "ligerz": ("Ligerz", 9831727481, 1500),
 "la_neuveville": ("La Neuveville", 3081154393, 1500), "le_landeron": ("Le Landeron", 5137617912, 1500),
 "cressier": ("Cressier", 3200044857, 1500), "cornaux": ("Cornaux", 3081154365, 1600),
 "saint_blaise_cff": ("Saint-Blaise CFF", 3081154429, 1300), "gampelen": ("Gampelen", 3092219560, 1500),
 "zihlbruecke": ("Zihlbrücke", 11808339007, 1300), "marin_epagnier": ("Marin-Epagnier", 3081154407, 1500),
 "saint_blaise_lac": ("Saint Blaise-Lac", 3081154428, 1300), "neuchatel": ("Neuchâtel", 3081154414, 2300),
 "serrieres": ("Serrières", 1948006333, 1500), "auvernier": ("Auvernier", 3081154344, 1600),
 "colombier": ("Colombier", 3081154360, 1500), "boudry": ("Boudry", 1951472692, 1500),
 "corcelles_peseux": ("Corcelles-Peseux", 3081154361, 1500), "chambrelien": ("Chambrelien", 1955142185, 1500),
 "bole": ("Bôle", 1951370014, 1300), "champ_du_moulin": ("Champ du Moulin", 1688809253, 1500),
 "noiraigue": ("Noiraigue", 300351185, 1500), "travers": ("Travers", 1944846875, 1600),
 # Kerzers–Murten (15.10.2026 abends; Kerzers und Murten selbst aus olten/reg, abgenommen)
 "muntschemier": ("Müntschemier", 3836116267, 1300), "sugiez": ("Sugiez", 3838637244, 1300),
 "muntelier_lowenberg": ("Muntelier-Löwenberg", 1976379410, 1000), "galmiz": ("Galmiz", 1976391941, 800),
 # Erweiterung 16.10.2026 abends (bis vor Yverdon, Payerne, Fribourg, Bümpliz Nord, Biel, La Chaux-de-Fonds)
 "avenches": ("Avenches", 1425180890, 2200), "bern_brunnen_westside": ("Bern Brünnen Westside", 1870421883, 1100),
 "bevaix": ("Bevaix", 3081154350, 1300), "concise": ("Concise", 983805184, 1300), "courtepin": ("Courtepin", 3664792744, 1300),
 "couvet": ("Couvet", 307412768, 1300), "cressier_fr": ("Cressier FR", 3664792745, 1100), "domdidier": ("Domdidier", 5286177951, 1300),
 "dompierre": ("Dompierre", 1446930653, 1100), "faoug": ("Faoug", 1975565226, 1100), "fraschels": ("Fräschels", 1976395718, 900),
 "gorgier_saint_aubin": ("Gorgier-Saint-Aubin", 696524685, 1300), "grandson": ("Grandson", 3081154377, 1300),
 "gummenen": ("Gümmenen", 3081154382, 1300), "kallnach": ("Kallnach", 3081154386, 1100), "kerzers_papiliorama": ("Kerzers Papiliorama", 2873268542, 800),
 "la_presta_mines_d_asphalte": ("La Presta - Mines d'Asphalte", 307412779, 900), "les_deurres": ("Les Deurres", 1949801868, 800),
 "les_geneveys_sur_coffrane": ("Les Geneveys-sur-Coffrane", 1955180993, 1300), "les_hauts_geneveys": ("Les Hauts-Geneveys", 1955180999, 1300),
 "motiers": ("Môtiers", 307412745, 1100), "munchenwiler_courgevaux": ("Münchenwiler-Courgevaux", 3664792746, 1100),
 "pensier": ("Pensier", 3664792747, 1100), "riedbach": ("Riedbach", 1870460759, 1100), "rosshausern": ("Rosshäusern", 3081154425, 1300),
 "tuscherz": ("Tüscherz", 1946558958, 1300),
}
TOWNS = {"Biel": [47.1325, 7.2426], "Ins": [46.9999, 7.0996], "Kerzers": [46.9751, 7.1929], "Bern": [46.9490, 7.4391],
 "Neuchâtel": [46.9966, 6.9358], "Twann": [47.0938, 7.1566], "Ligerz": [47.0840, 7.1348], "La Neuveville": [47.0628, 7.0954],
 "Le Landeron": [47.0566, 7.0663], "Cressier": [47.0519, 7.0395], "Cornaux": [47.0387, 7.0234], "Saint-Blaise": [47.0145, 6.9821],
 "Marin-Epagnier": [47.0090, 7.0107], "Gampelen": [47.0091, 7.0582], "Zihlbrücke": [47.0093, 7.0306],
 "Serrières": [46.9840, 6.9033], "Auvernier": [46.9796, 6.8777], "Colombier": [46.9677, 6.8490], "Boudry": [46.9595, 6.8352],
 "Bevaix": [46.9297, 6.8117], "Yverdon": [46.7814, 6.6408], "Corcelles-Peseux": [46.9834, 6.8838], "Chambrelien": [46.9673, 6.8125],
 "La Chaux-de-Fonds": [47.0986, 6.8251], "Les Geneveys-sur-Coffrane": [47.0151, 6.8532], "Bôle": [46.9691, 6.8380],
 "Champ-du-Moulin": [46.9599, 6.7750], "Noiraigue": [46.9549, 6.7218], "Travers": [46.9424, 6.6762], "Pontarlier": [46.9035, 6.3546],
 "Fleurier": [46.9025, 6.5822], "Buttes": [46.8889, 6.5512], "Murten": [46.9254, 7.1153], "Gals": [47.0270, 7.0480],
 "Payerne": [46.8197, 6.9384], "Fribourg": [46.8032, 7.1513], "Lyss": [47.0742, 7.3063],
 "Gümmenen": [46.9422, 7.2348], "Avenches": [46.8844, 7.0407], "Grandson": [46.8063, 6.6418], "Concise": [46.8509, 6.7232], "Couvet": [46.9239, 6.636], "Môtiers": [46.9118, 6.6103], "Tüscherz": [47.1141, 7.1959], "Kallnach": [47.0255, 7.2352], "Courtepin": [46.8674, 7.1227], "Les Hauts-Geneveys": [47.0472, 6.8748]}
R = json.load(open("ne_region.json"))["elements"]
def keep(e):
    t = e.get("tags", {})
    if e["type"] == "node": return t.get("railway") in ("switch", "buffer_stop", "railway_crossing", "station", "halt")
    return t.get("railway") in ("rail", "platform") or (t.get("public_transport") == "platform" and t.get("train") == "yes")
R = [e for e in R if keep(e)]
for key, (name, nid, rad) in ST.items():
    if len(sys.argv) > 1 and key not in sys.argv[1:]: continue
    st = next(e for e in R if e["id"] == nid)
    out = []
    for e in R:
        if e["type"] == "node" and e.get("tags", {}).get("railway") in ("station", "halt"):
            if e["id"] != nid: continue
            e = dict(e); e["tags"] = dict(e["tags"], railway="station"); e["tags"].pop("public_transport", None)
        out.append(e)
    json.dump({"elements": out}, open(f"{key}_roh.json", "w"))
    subprocess.run(["python3", "cut.py", key, str(rad), f"{key}_roh.json"], check=True)
    ov = f"{key}_override.json"
    if not os.path.exists(ov):
        json.dump({"_quelle": f"Entwurf 14.10.2026 (Claude), {name}, OSM-Stand 12.10.", "cfg": {"towns": TOWNS, "margin_x": 330, "lt_dist_w": 2.0}}, open(ov, "w"), indent=1, ensure_ascii=False)
