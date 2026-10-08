#!/bin/sh
# Both builds' game windows for several saved RAM dumps (tools/fakeapi.py), side by side in $SCRATCH/sbs/lay_<game>.
#   tools/layoutall.sh SCRATCH [game=dump.bin ...]     (dumps in $SCRATCH/ram)
# Build the Majorsilence variant first (tools/msfcheck.sh or tools/build_msf.py).
here=$(cd "$(dirname "$0")" && pwd)
s=$1; shift
steps=${STEPS:-miGameViewParty;miGameQuickRef;miGameShowInfo;miGameShowQuests;miGameShowSpells;miGameShowMonsters;miGameShowItems}
for pair in "$@"; do
    game=${pair%%=*}; dump=${pair#*=}
    python -I "$here/fakeapi.py" "$s/ram/$dump" --port 18099 > /dev/null 2>&1 &
    api=$!
    sleep 2
    echo "=== $game ($dump)"
    PORT=18099 sh "$here/gamecheck.sh" "$s" "$game" "lay_$game" "$steps" 2>&1 | grep -E "^==|dialog|messagebox|xception" | grep -v "Exit Program"
    kill $api
    last=$(ls "$s/shots/lay_$game-win" | grep -E '^[0-9]+_MainForm.png$' | sort | tail -1 | cut -d_ -f1)
    python -I "$here/sidebyside.py" "$s/shots/lay_$game-win" "$s/shots/lay_$game-msf" "$s/sbs/lay_$game" --prefix "${last}_" --scale 0.7 > /dev/null
done
