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
