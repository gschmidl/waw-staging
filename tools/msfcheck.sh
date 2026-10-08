#!/bin/sh
# Rebuild the Majorsilence build and capture its windows (plus control-tree dumps) against a DOSBox API,
# then put them next to an earlier WinForms run of the same steps.
#   tools/msfcheck.sh SCRATCH GAME TAG [STEPS]     (PORT defaults to 18099 = tools/fakeapi.py)
# WinForms reference: $SCRATCH/shots/$TAG-win (from tools/gamecheck.sh with the same steps).
here=$(cd "$(dirname "$0")" && pwd)
s=$1; game=$2; tag=$3
steps=${4:-miGameViewParty;miGameQuickRef;miGameShowInfo;miGameShowQuests}
port=${PORT:-18099}
out="$s/shots/$tag"
python -I "$here/build_msf.py" > "$s/build_msf.log" 2>&1 || { tail -20 "$s/build_msf.log"; exit 1; }
(cd "$here/wawshot-msf" && dotnet build -nologo -v q 2>&1 | grep -E " error " | head -5)
rm -rf "$out-msf"
WAWSHOT_OUT=$(cygpath -w "$out-msf") WAWSHOT_API=127.0.0.1:$port WAWSHOT_DELAY=${WAWSHOT_DELAY:-4000} WAWSHOT_STEPS=$steps \
    timeout 150 "$here/wawshot-msf/bin/Debug/net10.0/wawshot-msf.exe" -g "$game" > "$out-msf.out" 2>&1
echo "== Majorsilence (exit $?)"; head -5 "$out-msf.out"; grep -vE ' captured | click ' "$out-msf/wawshot.log"
python -I "$here/sidebyside.py" "$out-win" "$out-msf" "$s/sbs/$tag" --scale 0.7 > /dev/null
