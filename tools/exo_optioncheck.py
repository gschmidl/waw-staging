"""Play each patched eXo game into the game proper under every option of its own DOS menu (sound card, display),
the way the "with Where Are We?" launcher option starts it, on a private desktop; at each checkpoint ask
Where Are We?'s detection (tools/wawprobe scan) whether it found the game AND its static data (a monster list
it couldn't read makes it re-acquire the game every 3 s, and after 20 times it shows "re-acquired 20 times").

    python exo_optioncheck.py EXO_FOLDER [RUN ...]       (RUN names below; default all)
Keys go through the BIOS keyboard buffer (tools/bdakeys.py), so games with their own INT 9 handler (Xeen) are
not covered here.
"""
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, 'wawprobe', 'bin', 'Debug', 'net48', 'wawprobe.exe')
PORT = 18086                                            # test_port.conf; the launcher option's 8086 is the user's
TEST_CONF = os.path.join(HERE, 'test_port.conf')

WIZ_PARTY = ['s', 'g', 'a', 'b', 'c', 'd', 'e', 'f', '{enter}', 'l']   # start, tavern, add six, leave
WIZ_MAZE = ['e', 'm', ('wait', 6), 'l', 'n']                            # edge of town, maze, leave camp, not upstairs

# run name: (eXoDOS\!dos folder, wawprobe game, steps); a step is a key, ('wait', s) or ('check', label)
RUNS = {
    'mm3-sb': ('MM3', 'mm3', ['1', ('wait', 8), '{esc}', '{esc}', 's', 'TEST{enter}', ('wait', 10), ('check', 'in game')]),
    'mm3-mt32': ('MM3', 'mm3', ['2', ('wait', 8), '{esc}', '{esc}', 's', 'TEST{enter}', ('wait', 10), ('check', 'in game')]),
    'wiz1-composite': ('wizar1', 'wiz1', ['1', ('wait', 6), *WIZ_PARTY, ('check', 'castle'), *WIZ_MAZE, ('check', 'maze')]),
    'wiz1-rgb': ('wizar1', 'wiz1', ['2', ('wait', 6), *WIZ_PARTY, ('check', 'castle'), *WIZ_MAZE, ('check', 'maze')]),
    'wiz2-composite': ('wizar2', 'wiz2', ['1', '1', ('wait', 6), *WIZ_PARTY, ('check', 'castle'), *WIZ_MAZE, ('check', 'maze')]),
    'wiz2-rgb': ('wizar2', 'wiz2', ['1', '2', ('wait', 6), *WIZ_PARTY, ('check', 'castle'), *WIZ_MAZE, ('check', 'maze')]),
    'wiz3-composite': ('wizar3', 'wiz3', ['1', '1', ('wait', 6), *WIZ_PARTY, ('check', 'castle'), *WIZ_MAZE, ('check', 'maze')]),
    'wiz3-rgb': ('wizar3', 'wiz3', ['1', '2', ('wait', 6), *WIZ_PARTY, ('check', 'castle'), *WIZ_MAZE, ('check', 'maze')]),
    'wiz4-composite': ('wizar4', 'wiz4', ['1', ('wait', 6), 's', ('wait', 4), 'p', ('wait', 4), '{enter}', ('wait', 8),
                                          '{enter}', ('wait', 25), ('check', 'level 10')]),
    'wiz4-rgb': ('wizar4', 'wiz4', ['2', ('wait', 6), 's', ('wait', 4), 'p', ('wait', 4), '{enter}', ('wait', 8),
                                    '{enter}', ('wait', 25), ('check', 'level 10')]),
    'bt3-tandy': ('bardtal3', 'bt3', ['1', ('wait', 10), '{esc}', ('wait', 6), 'y', ('wait', 8), ('party', 'wilderness')]),
    'bt3-sb': ('bardtal3', 'bt3', ['2', ('wait', 10), '{esc}', ('wait', 6), 'y', ('wait', 8), ('party', 'wilderness')]),
    'bt3-mt32': ('bardtal3', 'bt3', ['3', ('wait', 10), '{esc}', ('wait', 6), 'y', ('wait', 8), ('party', 'wilderness')]),
    'mm1-normal': ('MM1', 'mm1', ['1', ('wait', 8), '{enter}', ('wait', 4), '{esc}', ('wait', 4), '{enter}', ('wait', 4), '1',
                                  ('wait', 4), '{ctrl-a}', '{ctrl-b}', '{ctrl-c}', '{ctrl-d}', '{ctrl-e}', '{ctrl-f}', 'x',
                                  ('wait', 5), ('party', 'Sorpigal')]),
    'mm1-gfxmod': ('MM1', 'mm1', ['2', ('wait', 8), '{enter}', ('wait', 4), '{esc}', ('wait', 4), '{enter}', ('wait', 4), '1',
                                  ('wait', 4), '{ctrl-a}', '{ctrl-b}', '{ctrl-c}', '{ctrl-d}', '{ctrl-e}', '{ctrl-f}', 'x',
                                  ('wait', 5), ('party', 'Sorpigal')]),
}


def api_up():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/v1/dosbox/info', timeout=1):
            return True
    except Exception:
        return False


def main():
    exo = sys.argv[1]
    names = sys.argv[2:] or list(RUNS)
    if api_up():
        sys.exit(f'something already answers on port {PORT}')
    failures = 0
    for name in names:
        folder, short, steps = RUNS[name]
        var = os.path.join(exo, 'eXoDOS', '!dos', folder)
        pidfile = os.path.join(os.environ['TEMP'], 'waw_optioncheck.pid')
        cmd = [os.path.join(exo, 'emulators', 'dosbox', 'staging', 'dosbox.exe'), '-conf', os.path.join(var, 'dosbox.conf'),
               '-conf', '.\\emulators\\dosbox\\options.conf', '-conf', '.\\emulators\\dosbox\\waw_staging.conf',
               '-conf', TEST_CONF, '-noconsole', '-exit']
        subprocess.run([sys.executable, '-I', os.path.join(HERE, 'start_hidden.py'), '--pidfile', pidfile, '--cwd', exo,
                        '--env', 'SDL_WINDOWS_DPI_SCALING=0', '--', *cmd], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60)
        pid = open(pidfile).read().strip()
        try:
            for _ in range(60):
                if api_up():
                    break
                time.sleep(0.5)
            time.sleep(6)
            for step in steps:
                if isinstance(step, tuple) and step[0] == 'wait':
                    time.sleep(step[1])
                elif isinstance(step, tuple) and step[0] in ('check', 'party'):
                    out = subprocess.run([PROBE, 'scan', short, f'127.0.0.1:{PORT}'], capture_output=True, text=True,
                                         timeout=60).stdout
                    init = next((ln for ln in out.splitlines() if ln.startswith('Init(')), 'no Init line')
                    state = next((ln for ln in out.splitlines() if ln.startswith('[')), '')
                    ok = ': True' in init and 'needs reinitialize False' in init
                    if step[0] == 'party':
                        ok = ok and 'chars=[]' not in state and 'chars=[' in state
                    failures += not ok
                    main_state = state.split(' main=')[1].split(' ')[0] if ' main=' in state else '?'
                    party = (' ' + state.split(' map=')[1][:110]) if step[0] == 'party' and ' map=' in state else ''
                    print(f'{"ok  " if ok else "FAIL"} {name:15s} {step[1]:9s} {init.split("; ")[-1]}  main={main_state}{party}',
                          flush=True)
                    if not ok:
                        for line in out.strip().splitlines()[:8]:
                            print('      ' + line, flush=True)
                else:
                    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'bdakeys.py'), '--port', str(PORT), step],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                    time.sleep(2.5)
        finally:
            subprocess.run(['taskkill', '/PID', pid, '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(20):
                if not api_up():
                    break
                time.sleep(0.5)
    print('all ok' if not failures else f'{failures} FAILED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
