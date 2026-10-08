#!/bin/sh
# Run both builds of the port against the test DOSBox: the WinForms build on a private desktop and the
# Majorsilence build headless, each opening the main game windows; then save a RAM dump.
#   tools/gamecheck.sh SCRATCH GAME TAG [STEPS]
here=$(cd "$(dirname "$0")" && pwd)
s=$1; game=$2; tag=$3
steps=${4:-miGameViewParty;miGameQuickRef;miGameShowInfo;miGameShowQuests;miGameShowSpells}
port=${PORT:-18086}
out="$s/shots/$tag"
rm -rf "$out-win" "$out-msf"
WAWSHOT_OUT=$(cygpath -w "$out-win") WAWSHOT_API=127.0.0.1:$port WAWSHOT_DELAY=${WAWSHOT_DELAY:-6000} WAWSHOT_STEPS=$steps \
    python -I "$here/run_hidden.py" --timeout 90 -- "$(cygpath -w "$here/wawshot/bin/Debug/net48/wawshot.exe")" -g "$game" > /dev/null
echo "== WinForms"; grep -vE ' captured ' "$out-win/wawshot.log"; grep -c ' captured ' "$out-win/wawshot.log"
WAWSHOT_OUT=$(cygpath -w "$out-msf") WAWSHOT_API=127.0.0.1:$port WAWSHOT_DELAY=${WAWSHOT_DELAY:-6000} WAWSHOT_STEPS=$steps \
    timeout 150 "$here/wawshot-msf/bin/Debug/net10.0/wawshot-msf.exe" -g "$game" > "$out-msf.out" 2>&1
echo "== Majorsilence (exit $?)"; head -5 "$out-msf.out"; grep -vE ' captured ' "$out-msf/wawshot.log"; grep -c ' captured ' "$out-msf/wawshot.log"
"$here/wawprobe/bin/Debug/net48/wawprobe.exe" dump "$(cygpath -w "$s/ram/$tag.bin")" "127.0.0.1:$port" | tail -1
