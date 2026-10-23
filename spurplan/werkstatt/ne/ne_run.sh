#!/bin/sh
st=$1; shift
rm -f ${st}_warp.json
python3 spurplan_schema.py --src $st.json --nowarp "$@" >/dev/null
python3 spurplan_warp.py $st >/dev/null
python3 spurplan_schema.py --src $st.json "$@" >/dev/null
python3 spurplan_warp.py $st >/dev/null
python3 spurplan_schema.py --src $st.json "$@" | grep Bahnhof
python3 spurplan_check.py --src $st.json "$@" | grep "^Befunde"
python3 spurplan_schema.py --src $st.json --bare --out ${st}_bare.svg "$@" > /dev/null
# Typvorlage (16.10.2026): steht "vorlage" im Override, zeichnet vorlage.py den Plan nach Bahnhofstyp neu
if grep -q '"vorlage"' ${st}_override.json 2>/dev/null; then python3 vorlage.py $st; fi
