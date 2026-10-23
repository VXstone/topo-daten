#!/bin/sh
# Netzplan einer Region: ./run_netz.sh region.json olten_region "Region Olten" S,W,N,E Ausgabe.svg
python3 netz_topologie.py $1 $2 $4 | grep -v "^  "
python3 netz_stationen.py $1 $2 > /dev/null
python3 netz_layout.py $2
python3 netz_render.py $2 "$3" "$5"
