"""Start DOSBox Staging visibly the way the "with Where Are We?" launcher option does (game dosbox.conf,
options.conf, waw_staging.conf, from the eXo folder), after a lead time so the user can stop typing, plus extra
test configs (capture folder); then move the window to the left monitor. Writes the PID to a file.

    python run_staging_exo.py EXO GAMEDIR PIDFILE [--delay 30] [--conf EXTRA.conf ...] [--staging FOLDER]
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exo')
    ap.add_argument('game')
    ap.add_argument('pidfile')
    ap.add_argument('--delay', type=int, default=30)
    ap.add_argument('--conf', action='append', default=[])
    ap.add_argument('--staging', default=r'emulators\dosbox\staging')
    a = ap.parse_args()
    time.sleep(a.delay)
    var = os.path.join(a.exo, 'eXoDOS', '!dos', a.game)
    cmd = [os.path.join(a.exo, a.staging, 'dosbox.exe'), '-conf', os.path.join(var, 'dosbox.conf'),
           '-conf', r'.\emulators\dosbox\options.conf', '-conf', r'.\emulators\dosbox\waw_staging.conf']
    for c in a.conf:
        cmd += ['-conf', c]
    cmd += ['-noconsole', '-exit']
    env = dict(os.environ, SDL_WINDOWS_DPI_SCALING='0')
    p = subprocess.Popen(cmd, cwd=a.exo, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    open(a.pidfile, 'w').write(str(p.pid))
    print('started PID', p.pid, flush=True)
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'move_window.py'), str(p.pid), '-2400', '60'])


if __name__ == '__main__':
    main()
