"""Window layout check: each patched eXo game started the way its "with Where Are We?" option does (DOSBox Staging,
the game's dosbox.conf + options.conf + waw_staging.conf, test_port.conf), played into the game where
exo_optioncheck.py knows how, with Where Are We? (the tools/wawshot harness and a copy of a settings file) opening
every window from its menus; all on a private desktop. Then, and again after DOSBox is resized, it checks the
layout: the map flush right of DOSBox, no window over DOSBox, every window on DOSBox's screen, the layout's windows
(map, Game Info, Encounters, Party) clear of each other.

    python layout_check.py EXO [--fresh-from SOURCE_EXO] [--settings FILE] [--harness DIR] [--maps DIR] [--out DIR]
                           [RUN ...]
EXO should be a scratch copy (make_scratch_exo.py): the games run in it. With --fresh-from each run's game is
unzipped anew from SOURCE_EXO first (a party a run left in Wizardry's maze sends the next run's keys elsewhere).
"""
import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import exo_optioncheck  # noqa: E402  (its RUNS: menu keys that reach the game proper)

PORT = 18086
DESKTOP = 'waw-layout'
# Party and Game Info: opened by the layout itself (their menu items toggle them, so not clicked)
MENUS = ['miGameShowEncounters', 'miGameShowSpells', 'miGameShowMonsters', 'miGameShowQuests', 'miGameShowShops',
         'miGameScripts', 'miGameQuickRef', 'miGameShowItems', 'miGameCreationAssistant', 'miEditFind']
# games exo_optioncheck.py doesn't play: as far as exo_bootcheck.py gets them (BT1 out of the guild)
EXTRA = {
    'mm2': ('MM2', 'mm2', ['{space}', ('wait', 8)]),
    'xeen': ('MM6', 'mm45', ['1', ('wait', 12)]),
    'bt1': ('bardtal1', 'bt1', [('wait', 4), '{space}', ('wait', 3), 'a', ('wait', 3), '{enter}', ('wait', 3), 'e',
                                ('wait', 3)]),
    'bt2': ('bardtal2', 'bt2', ['{space}', ('wait', 8)]),
    'wiz5': ('wizar5', 'wiz5', ['1', '2', ('wait', 8)]),
}
RUNS = {**{k: v for k, v in exo_optioncheck.RUNS.items()}, **EXTRA}
# watcher timeline (seconds after Where Are We? starts): menus are clicked from WAWSHOT_DELAY on, one per 2.5 s
DELAY = 10
T_BEFORE = DELAY + 2.5 * len(MENUS) + 4
T_RESIZE = T_BEFORE + 0.5
T_AFTER = T_RESIZE + 4
T_END = T_AFTER + 0.5
TOLERANCE = 2


def api_up():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/v1/dosbox/info', timeout=1):
            return True
    except Exception:
        return False


def start_hidden(pidfile, cmd, cwd, env=()):
    args = [sys.executable, '-I', os.path.join(HERE, 'start_hidden.py'), '--desktop', DESKTOP, '--pidfile', pidfile,
            '--cwd', cwd]
    for e in env:
        args += ['--env', e]
    subprocess.run([*args, '--', *cmd], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   stdin=subprocess.DEVNULL, timeout=60)
    return int(open(pidfile).read().strip())


# ---- watcher (runs on the private desktop) ----

def watch(dpid, wpid, out):
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    user32 = ctypes.WinDLL('user32')
    dwm = ctypes.WinDLL('dwmapi')
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    class MONITORINFO(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', wintypes.RECT), ('rcWork', wintypes.RECT),
                    ('dwFlags', wintypes.DWORD)]

    def frame(h):
        r = wintypes.RECT()
        if dwm.DwmGetWindowAttribute(h, 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:
            user32.GetWindowRect(h, ctypes.byref(r))
        return [r.left, r.top, r.right, r.bottom]

    def snapshot():
        wins = []

        def cb(h, l):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if pid.value not in (dpid, wpid) or not user32.IsWindowVisible(h):
                return True
            c = ctypes.create_unicode_buffer(128)
            user32.GetClassNameW(h, c, 128)
            if c.value.startswith('UAC') or c.value == '#32770':
                return True
            if pid.value == dpid and c.value != 'SDL_app':
                return True
            t = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, t, 256)
            wins.append({'dosbox': pid.value == dpid, 'title': t.value, 'frame': frame(h), 'hwnd': h})
            return True
        user32.EnumWindows(proc(cb), 0)
        work = None
        for w in wins:
            if w['dosbox']:
                mi = MONITORINFO(cbSize=ctypes.sizeof(MONITORINFO))
                user32.GetMonitorInfoW(user32.MonitorFromWindow(w['hwnd'], 2), ctypes.byref(mi))
                work = [mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom]
        return {'windows': wins, 'work': work}

    start = time.time()
    result = {}
    while time.time() - start < T_END:
        t = time.time() - start
        if 'before' not in result and t >= T_BEFORE:
            result['before'] = snapshot()
        if 'resized' not in result and t >= T_RESIZE:
            d = [w for w in snapshot()['windows'] if w['dosbox']]
            if d:
                f = d[0]['frame']
                ok = user32.SetWindowPos(d[0]['hwnd'], 0, 0, 0, f[2] - f[0] + 200, f[3] - f[1] + 150,
                                         0x0002 | 0x0004 | 0x0010)
                result['resized'] = bool(ok)
        if 'after' not in result and t >= T_AFTER:
            result['after'] = snapshot()
        time.sleep(0.2)
    json.dump(result, open(out, 'w'), indent=1)


# ---- checks ----

def overlap(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w > TOLERANCE and h > TOLERANCE


def kind(title):
    if title.startswith('Where Are We?'):
        return 'map'
    if title.startswith('Game Information'):
        return 'info'
    if title.startswith('Party Information'):
        return 'party'
    if 'ncounter' in title:
        return 'encounters'
    return 'other'


def check(snap):
    problems = []
    dos = [w for w in snap['windows'] if w['dosbox']]
    waw = [w for w in snap['windows'] if not w['dosbox']]
    if not dos or not snap['work']:
        return ['no DOSBox window'], []
    d, work = dos[0]['frame'], snap['work']
    kinds = {kind(w['title']): w for w in waw}
    for k in ('map', 'info', 'party'):
        if k not in kinds:
            problems.append(f'no {k} window')
    if 'map' in kinds:
        m = kinds['map']['frame']
        if abs(m[0] - d[2]) > TOLERANCE or abs(m[1] - work[1]) > TOLERANCE:
            problems.append(f'map {m} not flush right of DOSBox {d}')
    for w in waw:
        f = w['frame']
        if overlap(f, d):
            problems.append(f'"{w["title"][:40]}" {f} over DOSBox {d}')
        if f[0] < work[0] - TOLERANCE or f[1] < work[1] - TOLERANCE or f[2] > work[2] + TOLERANCE or \
                f[3] > work[3] + TOLERANCE:
            problems.append(f'"{w["title"][:40]}" {f} off the screen {work}')
    layout = [w for w in waw if kind(w['title']) != 'other']
    for i, a in enumerate(layout):
        for b in layout[i + 1:]:
            if overlap(a['frame'], b['frame']):
                problems.append(f'"{a["title"][:30]}" and "{b["title"][:30]}" overlap')
    return problems, [f'{"(screen working area)":44s} {work}'] + [f'{w["title"][:44]:44s} {w["frame"]}' for w in [*dos, *waw]]


def run(name, a, scratch):
    folder, short, steps = RUNS[name]
    var = os.path.join(a.exo, 'eXoDOS', '!dos', folder)
    harness = os.path.join(scratch, 'harness')
    shutil.rmtree(harness, ignore_errors=True)
    shutil.copytree(a.harness, harness)
    if a.maps and os.path.isdir(a.maps):
        for f in os.listdir(a.maps):
            shutil.copy(os.path.join(a.maps, f), harness)
    # always portable (as eXoDOS installs it): a copy of the given settings, else an empty file (a fresh install);
    # without the file the harness would keep its settings in the user's profile from run to run
    text = ''
    if a.settings:
        text = open(a.settings, encoding='utf-8-sig').read().replace(os.path.dirname(os.path.abspath(a.settings)),
                                                                     harness)
    open(os.path.join(harness, 'WhereAreWe.settings'), 'w', encoding='utf-8').write(text)
    shots = os.path.join(a.out, name)
    shutil.rmtree(shots, ignore_errors=True)
    os.makedirs(shots)
    if a.fresh_from:
        subprocess.run([sys.executable, '-I', os.path.join(HERE, 'make_scratch_exo.py'), a.fresh_from, a.exo, folder],
                       check=True, capture_output=True, timeout=600)
    dpid = start_hidden(os.path.join(scratch, 'dosbox.pid'),
                        [os.path.join(a.exo, 'emulators', 'dosbox', 'staging', 'dosbox.exe'),
                         '-conf', os.path.join(var, 'dosbox.conf'), '-conf', r'.\emulators\dosbox\options.conf',
                         '-conf', r'.\emulators\dosbox\waw_staging.conf', '-conf', os.path.join(HERE, 'test_port.conf'),
                         '-noconsole', '-exit'], a.exo, ['SDL_WINDOWS_DPI_SCALING=0'])
    wpid = None
    try:
        for _ in range(60):
            if api_up():
                break
            time.sleep(0.5)
        time.sleep(6)
        for step in steps:
            if isinstance(step, tuple):
                # exo_optioncheck's checkpoints take a few seconds of probing; the keys after them count on that
                # (without the pause Wizardry's "L" reached the castle menu and left the game)
                time.sleep(step[1] if step[0] == 'wait' else 6)
                continue
            subprocess.run([sys.executable, '-I', os.path.join(HERE, 'bdakeys.py'), '--port', str(PORT), step],
                           capture_output=True, timeout=30)
            time.sleep(2.5)                                  # as exo_optioncheck.py
        if not api_up():
            return 1, ['  DOSBox exited during the game steps']
        wpid = start_hidden(os.path.join(scratch, 'waw.pid'), [os.path.join(harness, 'wawshot.exe'), '-g', short],
                            harness, [f'WAWSHOT_OUT={shots}', f'WAWSHOT_API=127.0.0.1:{PORT}',
                                      f'WAWSHOT_DELAY={DELAY * 1000}', 'WAWSHOT_STEPS=' + ';'.join(MENUS + ['none'] * 6)])
        result = os.path.join(shots, 'layout.json')
        subprocess.run([sys.executable, '-I', os.path.join(HERE, 'run_hidden.py'), '--desktop', DESKTOP, '--timeout',
                        str(int(T_END) + 30), '--', sys.executable, '-I', os.path.abspath(__file__), '--watch',
                        str(dpid), str(wpid), result], capture_output=True, timeout=T_END + 60)
    finally:
        for p in (wpid, dpid):
            if p:
                subprocess.run(['taskkill', '/PID', str(p), '/F'], capture_output=True)
        for _ in range(20):
            if not api_up():
                break
            time.sleep(0.5)
    if not os.path.isfile(result):
        return 1, ['  no layout.json (the watcher did not run)']
    data = json.load(open(result))
    lines, failures = [], 0
    for when in ('before', 'after'):
        if when not in data:
            lines.append(f'  {when}: no snapshot')
            failures += 1
            continue
        problems, windows = check(data[when])
        failures += len(problems)
        lines.append(f'  {when}' + (' DOSBox resized' if when == 'after' and data.get('resized') else '') + ':')
        lines += [f'    {w}' for w in windows] + [f'    PROBLEM {p}' for p in problems]
    return failures, lines


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--watch':
        watch(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
        return 0
    ap = argparse.ArgumentParser()
    ap.add_argument('exo')
    ap.add_argument('--fresh-from')
    ap.add_argument('--settings')
    ap.add_argument('--harness', default=os.path.join(HERE, 'wawshot', 'bin', 'Release', 'net48'))
    ap.add_argument('--maps', default=os.path.join(HERE, '..', 'orig', 'maps'))
    ap.add_argument('--out', default=os.path.join(os.environ['TEMP'], 'waw_layout'))
    ap.add_argument('runs', nargs='*')
    a = ap.parse_intermixed_args()
    if api_up():
        sys.exit(f'something already answers on port {PORT}')
    scratch = os.path.join(a.out, '_work')
    os.makedirs(scratch, exist_ok=True)
    total = 0
    for name in a.runs or list(RUNS):
        failures, lines = run(name, a, scratch)
        total += failures
        print(f'{name:15s} {"ok" if not failures else f"{failures} PROBLEMS"}', flush=True)
        print('\n'.join(lines), flush=True)
    print('all ok' if not total else f'{total} PROBLEMS')
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main())
