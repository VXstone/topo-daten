"""
Bahn-Extrakt (OSM-PBF) -> JSON im Format von Overpass «out geom;».

  python3 umwandeln.py bahn.osm.pbf schweiz_bahn.json.gz

Behalten werden
  - Ways mit railway=rail|narrow_gauge|light_rail|subway|tram|funicular|monorail|
    preserved|construction|disused|platform, sowie public_transport=platform
  - alle Nodes mit einem railway-Tag (Weichen, Prellböcke, Bahnhöfe, Halte, Signale …)
  - Perrons als Multipolygon-Relation (26.10.2026, Solothurn/Konolfingen: Perrons 2/3, 5/6, 9/10 fehlten): je äusserer
    Ring ein Way-Element mit id = 4·10⁹ + Relations-id und tags + "_relation"; so lesen die Skripte sie wie Perron-Ways.
Ways erhalten wie bei Overpass: id, bounds, nodes, geometry, tags.
"""
import gzip, json, sys
import osmium

WAY_RAILWAY = {"rail", "narrow_gauge", "light_rail", "subway", "tram", "funicular", "monorail",
               "preserved", "construction", "disused", "platform"}


def way_behalten(tags):
    return tags.get("railway") in WAY_RAILWAY or tags.get("public_transport") == "platform"


class Sammler(osmium.SimpleHandler):
    def __init__(self, out):
        super().__init__()
        self.out, self.erst, self.n_nodes, self.n_ways, self.fehlt, self.n_rel = out, True, 0, 0, 0, 0

    def _schreiben(self, el):
        self.out.write(("" if self.erst else ",\n") + json.dumps(el, ensure_ascii=False, separators=(",", ":")))
        self.erst = False

    def node(self, n):
        if "railway" not in n.tags:
            return
        self._schreiben({"type": "node", "id": n.id, "lat": round(n.location.lat, 7),
                         "lon": round(n.location.lon, 7), "tags": {t.k: t.v for t in n.tags}})
        self.n_nodes += 1

    def way(self, w):
        tags = {t.k: t.v for t in w.tags}
        if not way_behalten(tags):
            return
        ids, geom = [], []
        for nd in w.nodes:
            if not nd.location.valid():
                self.fehlt += 1
                continue
            ids.append(nd.ref)
            geom.append({"lat": round(nd.location.lat, 7), "lon": round(nd.location.lon, 7)})
        if len(geom) < 2:
            return
        la = [g["lat"] for g in geom]; lo = [g["lon"] for g in geom]
        self._schreiben({"type": "way", "id": w.id,
                         "bounds": {"minlat": min(la), "minlon": min(lo), "maxlat": max(la), "maxlon": max(lo)},
                         "nodes": ids, "geometry": geom, "tags": tags})
        self.n_ways += 1

    def area(self, a):
        if a.from_way():
            return                     # Perron-Ways kommen schon über way()
        tags = {t.k: t.v for t in a.tags}
        if not way_behalten(tags):
            return
        for k, ring in enumerate(a.outer_rings()):
            ids = [n.ref for n in ring]
            geom = [{"lat": round(n.lat, 7), "lon": round(n.lon, 7)} for n in ring]
            if len(geom) < 2:
                continue
            la = [g["lat"] for g in geom]; lo = [g["lon"] for g in geom]
            self._schreiben({"type": "way", "id": 4_000_000_000 + a.orig_id() * 10 + k,
                             "bounds": {"minlat": min(la), "minlon": min(lo), "maxlat": max(la), "maxlon": max(lo)},
                             "nodes": ids, "geometry": geom, "tags": dict(tags, _relation=a.orig_id())})
            self.n_rel += 1


def main(src, dst):
    op = gzip.open if dst.endswith(".gz") else open
    with op(dst, "wt", encoding="utf-8") as out:
        out.write('{"version":0.6,"generator":"topo-daten/umwandeln.py","osm3s":{"copyright":'
                  '"The data included in this document is from www.openstreetmap.org. '
                  'The data is made available under ODbL."},"elements":[\n')
        h = Sammler(out)
        h.apply_file(src, locations=True, idx="flex_mem")
        out.write("\n]}\n")
    print(f"{h.n_nodes} Nodes, {h.n_ways} Ways, {h.n_rel} Perron-Relationen, {h.fehlt} fehlende Koordinaten -> {dst}")
    return h


if __name__ == "__main__":
    h = main(sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:          # optional: Kennzahlen als JSON
        json.dump({"nodes": h.n_nodes, "ways": h.n_ways}, open(sys.argv[3], "w"))
