#!/bin/sh
# Rebuild the Majorsilence build, publish the headless harness for linux-x64 and run it in WSL Debian against
# RAM dumps (tools/linux_shot.sh). Results land in SCRATCH/shots/linux_<game>.
#   tools/linux_check.sh SCRATCH game=dump.bin [game=dump.bin ...]       (dumps in SCRATCH/ram)
# The VM side works in $WAWTEST (a folder in the VM; default: wawtest in the VM user's home).
here=$(cd "$(dirname "$0")" && pwd)
s=$1; shift
vm=${WAWTEST:-\$HOME/wawtest}
python -I "$here/build_msf.py" > "$s/build_msf.log" 2>&1 || { tail -20 "$s/build_msf.log"; exit 1; }
rm -rf "$s/wawshot-linux"
(cd "$here/wawshot-msf" && dotnet publish -c Release --self-contained true -nologo -r linux-x64 -v q \
    -o "$(cygpath -w "$s/wawshot-linux")" 2>&1 | grep -E " error " | head -5)
ws=$(wsl.exe -d Debian -e wslpath -a "$(cygpath -w "$s")" | tr -d '\r')
wt=$(wsl.exe -d Debian -e wslpath -a "$(cygpath -w "$here")" | tr -d '\r')
MSYS_NO_PATHCONV=1 wsl.exe -d Debian -e bash -c "mkdir -p $vm && rm -rf $vm/harness && cp -r '$ws/wawshot-linux' $vm/harness \
    && chmod +x $vm/harness/wawshot-msf && cp '$wt/fakeapi.py' $vm/ \
    && tr -d '\r' < '$wt/linux_shot.sh' > $vm/linux_shot.sh"
for pair in "$@"; do
    game=${pair%%=*}; dump=${pair#*=}
    echo "=== $game ($dump)"
    MSYS_NO_PATHCONV=1 wsl.exe -d Debian -e bash -c "cp '$ws/ram/$dump' $vm/ && \
        STEPS='${STEPS:-miGameViewParty;miGameQuickRef;miGameShowInfo;miGameShowQuests}' \
        bash $vm/linux_shot.sh $vm $vm/$dump $game $vm/out_$game \
        && rm -rf '$ws/shots/linux_$game' && cp -r $vm/out_$game '$ws/shots/linux_$game'"
done
