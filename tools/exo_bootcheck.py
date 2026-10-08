"""Boot each patched eXo game the way its "with Where Are We?" option does (DOSBox Staging, the game's
dosbox.conf + options.conf + waw_staging.conf, from the eXo folder), on a private desktop the user never sees;
answer the game's own DOS menus through the API, then ask Where Are We?'s detection (tools/wawprobe) which game
runs. Only the DOSBox this script starts is stopped.

    python exo_bootcheck.py EXO_FOLDER [--staging emulators\\dosbox\\staging] [GAMEDIR ...]
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, 'wawprobe', 'bin', 'Debug', 'net48', 'wawprobe.exe')
PORT = 8086

# eXoDOS\!dos folder: (keys for the game's DOS menus, wawprobe game name, known game it must report)
GAMES = {
    'MM1': (['1'], 'mm1', 'MightAndMagic1'),
    'MM2': (['{space}'], 'mm2', 'MightAndMagic2'),
    'MM3': (['1'], 'mm3', 'MightAndMagic3'),
    'MM6': (['1'], 'mm45', 'MightAndMagic45'),
    'bardtal1': ([], 'bt1', 'BardsTale1'),
    'bardtal2': (['{space}'], 'bt2', 'BardsTale2'),
    'bardtal3': (['2'], 'bt3', 'BardsTale3'),
    'wizar1': (['2'], 'wiz1', 'Wizardry1'),
    'wizar2': (['1', '2'], 'wiz2', 'Wizardry2'),
    'wizar3': (['1', '2'], 'wiz3', 'Wizardry3'),
    'wizar4': (['2'], 'wiz4', 'Wizardry4'),
    'wizar5': (['1', '2'], 'wiz5', 'Wizardry5'),
}


def log(text):
    if os.environ.get('BOOTCHECK_VERBOSE'):
        print('   ', time.strftime('%H:%M:%S'), text, flush=True)


def api_up():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/v1/dosbox/info', timeout=1) as r:
            return json.loads(r.read())
    except Exception:
        return None


def probe(*args):
    r = subprocess.run([PROBE, *args], capture_output=True, text=True, timeout=60)
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exo')
    ap.add_argument('--staging', default='emulators\\dosbox\\staging')
    ap.add_argument('games', nargs='*')
    a = ap.parse_args()
    if api_up():
        sys.exit(f'something already answers on port {PORT}; not starting another DOSBox')
    scratch = os.environ.get('BOOTCHECK_TMP', os.path.join(os.environ['TEMP'], 'waw_bootcheck'))
    os.makedirs(scratch, exist_ok=True)
    failures = 0
    for folder in a.games or list(GAMES):
        keys, short, known = GAMES[folder]
        had = {n: os.path.exists(os.path.join(a.exo, n)) for n in ('stdout.txt', 'stderr.txt')}
        var = os.path.join(a.exo, 'eXoDOS', '!dos', folder)
        pidfile = os.path.join(scratch, f'{folder}.pid')
        cmd = [os.path.join(a.exo, a.staging, 'dosbox.exe'), '-conf', os.path.join(var, 'dosbox.conf'),
               '-conf', '.\\emulators\\dosbox\\options.conf', '-conf', '.\\emulators\\dosbox\\waw_staging.conf',
               '-noconsole', '-exit']
        subprocess.run([sys.executable, '-I', os.path.join(HERE, 'start_hidden.py'), '--pidfile', pidfile,
                        '--cwd', a.exo, '--env', 'SDL_WINDOWS_DPI_SCALING=0', '--', *cmd], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=60)
        pid = int(open(pidfile).read().strip())
        log(f'{folder}: DOSBox pid {pid}')
        result = 'no API'
        try:
            for _ in range(60):
                if api_up():
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError
            log('API up')
            time.sleep(4)
            for k in keys:
                log(f'key {k}')
                subprocess.run([sys.executable, '-I', os.path.join(HERE, 'bdakeys.py'), '--port', str(PORT), k],
                               capture_output=True, timeout=30)
                time.sleep(3)
            result = 'not detected'
            for _ in range(20):
                log('probe')
                info = probe('info', f'127.0.0.1:{PORT}')
                if f'known game: {known}' in info:
                    scan = probe('scan', short, f'127.0.0.1:{PORT}')
                    init = next((ln for ln in scan.splitlines() if ln.startswith('Init(')), '')
                    program = next((ln for ln in info.splitlines() if ln.startswith('program:')), '')
                    result = f'ok  {program}  {init}' if ': True' in init else f'scan failed: {init}'
                    break
                time.sleep(2)
            else:
                result += ' (' + ' / '.join(ln for ln in info.splitlines() if ln.startswith(('program', 'known'))) + ')'
        except RuntimeError:
            pass
        finally:
            subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True)
            for _ in range(20):
                if not api_up():
                    break
                time.sleep(0.5)
            for n, existed in had.items():
                p = os.path.join(a.exo, n)
                if not existed and os.path.exists(p):
                    os.remove(p)
        ok = result.startswith('ok')
        failures += not ok
        print(f'{folder:9s} {result}', flush=True)
    print('all ok' if not failures else f'{failures} FAILED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
