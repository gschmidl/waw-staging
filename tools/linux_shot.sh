#!/bin/bash
# Run the Linux build's headless harness (tools/wawshot-msf published for linux-x64) inside WSL against
# tools/fakeapi.py serving a RAM dump, both in the VM (no Windows firewall involved).
#   linux_shot.sh WORKDIR DUMP GAME OUTDIR [STEPS]
# WORKDIR holds harness/ and fakeapi.py; OUTDIR gets the PNGs, the control dumps and wawshot.log.
work=$1; dump=$2; game=$3; out=$4
steps=${5:-miGameViewParty;miGameQuickRef;miGameShowInfo;miGameShowQuests}
python3 "$work/fakeapi.py" "$dump" --port 18099 > "$out.api.log" 2>&1 &
api=$!
sleep 2
rm -rf "$out"; mkdir -p "$out"
WAWSHOT_OUT="$out" WAWSHOT_API=127.0.0.1:18099 WAWSHOT_DELAY=4000 WAWSHOT_STEPS="$steps" \
    timeout 180 "$work/harness/wawshot-msf" -g "$game" > "$out.out" 2>&1
echo "harness exit $?"
kill $api
head -5 "$out.out"
grep -vE ' captured | click ' "$out/wawshot.log"
ls "$out" | grep -c png
