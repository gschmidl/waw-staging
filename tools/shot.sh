#!/bin/sh
# Take a DOSBox Staging screenshot (Ctrl+F5 posted to the test instance) and print the new PNG's path.
#   tools/shot.sh SCRATCH [NAME]     SCRATCH holds stg.pid and the cap/ capture folder
here=$(cd "$(dirname "$0")" && pwd)
s=$1; name=${2:-}
pid=$(tr -d '\r\n ' < "$s/stg.pid")
before=$(ls -t "$s/cap"/*.png 2>/dev/null | head -1)
python -I "$here/postkeys.py" "$pid" ctrl+f5
for i in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.5
    new=$(ls -t "$s/cap"/*.png 2>/dev/null | head -1)
    [ -n "$new" ] && [ "$new" != "$before" ] && break
done
if [ -z "$new" ] || [ "$new" = "$before" ]; then echo "no new capture"; exit 1; fi
if [ -n "$name" ]; then mv "$new" "$s/cap/$name.png"; new="$s/cap/$name.png"; fi
cygpath -w "$new"
