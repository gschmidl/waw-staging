#!/bin/sh
# Type keys into the test DOSBox (BIOS buffer), wait, print what WAW reads, and take a screenshot.
#   tools/step.sh SCRATCH GAME SHOTNAME [WAIT_SECONDS] KEYS...     (KEYS as for bdakeys.py)
here=$(cd "$(dirname "$0")" && pwd)
s=$1; game=$2; name=$3; shift 3
wait=2
case "$1" in [0-9]*) wait=$1; shift ;; esac
port=${PORT:-18086}
[ $# -gt 0 ] && python -I "$here/bdakeys.py" --port "$port" "$@"
python -I -c "import time,sys; time.sleep(float(sys.argv[1]))" "$wait"
"$here/wawprobe/bin/Debug/net48/wawprobe.exe" scan "$game" "127.0.0.1:$port" | grep -E '^\['
sh "$here/shot.sh" "$s" "$name"
