"""exo/patch_exo.py on a scratch eXo folder made from a real one's launchers.

    py tests/test_patch_exo.py EXO_FOLDER [--program DIR]

Copies EXO_FOLDER's eXoDOS\\!dos folders of the supported games (plus MM4, which must stay untouched),
util\\choice.exe and util\\setconsole.exe into a scratch folder; DOSBox Staging is a stand-in that only holds the
string the patch looks for. The patch is checked, applied, applied again, switched to another Staging folder and
reverted; the folder must end up as it was. The generated menus then run with cmd from the eXo folder, the way
eXo's launch.bat calls them (choice gets its answer piped in), with stub programs in place of DOSBox and
Where Are We? that record how they were started (taskkill is replaced by an echo: the test never stops a
real program).
"""
import argparse
import filecmp
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PATCH = ROOT / 'exo' / 'patch_exo.py'
sys.path.insert(0, str(ROOT / 'exo'))
import patch_exo  # noqa: E402

STUB_CS = r'''
using System; using System.IO;
static class Stub { static int Main(string[] a) {
  string log = Environment.GetEnvironmentVariable("STUB_LOG");
  File.AppendAllText(log, System.Diagnostics.Process.GetCurrentProcess().MainModule.FileName + " | "
      + Environment.CurrentDirectory + " | " + string.Join(" ", Array.ConvertAll(a, s => "[" + s + "]")) + "\r\n");
  return 0; } }
'''
CSC = Path(os.environ['WINDIR']) / 'Microsoft.NET' / 'Framework64' / 'v4.0.30319' / 'csc.exe'

failures = 0


def check(what, ok, detail=''):
    global failures
    print(('ok   ' if ok else 'FAIL ') + what + (f'  ({detail})' if detail and not ok else ''))
    if not ok:
        failures += 1


def run_patch(exo, program, *args):
    r = subprocess.run([sys.executable, str(PATCH), *args, '--release', str(program), str(exo)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def snapshot(folder):
    return {str(p.relative_to(folder)): p.read_bytes() for p in folder.rglob('*') if p.is_file()}


def make_exo(src, dst):
    for folder in list(patch_exo.GAMES) + ['MM4']:
        if (src / 'eXoDOS' / '!dos' / folder).is_dir():
            shutil.copytree(src / 'eXoDOS' / '!dos' / folder, dst / 'eXoDOS' / '!dos' / folder,
                            ignore=shutil.ignore_patterns('Extras', 'Magazines'))
            bat = dst / 'eXoDOS' / '!dos' / folder / 'exception.bat'
            if bat.is_file() and patch_exo.MARKER.encode() in bat.read_bytes():   # EXO_FOLDER is patched: as eXo ships
                bat.unlink()
    (dst / 'util').mkdir()
    for name in ('choice.exe', 'setconsole.exe'):
        shutil.copy2(src / 'util' / name, dst / 'util' / name)
    for staging in ('staging', 'staging0.83.0'):
        (dst / 'emulators' / 'dosbox' / staging).mkdir(parents=True)
        (dst / 'emulators' / 'dosbox' / staging / 'dosbox.exe').write_bytes(b'MZ stand-in webserver_enabled')
    (dst / 'emulators' / 'dosbox' / 'staging0.81.1').mkdir()
    (dst / 'emulators' / 'dosbox' / 'staging0.81.1' / 'dosbox.exe').write_bytes(b'MZ old staging')


def run_menu(exo, folder, answer, stub, alt=False):
    """Run a game's exception.bat like launch.bat (or AltLauncher.bat) does; what was started."""
    log = exo / 'stub.log'
    if log.exists():
        log.unlink()
    bat = exo / 'eXoDOS' / '!dos' / folder / 'exception.bat'
    text = bat.read_bytes().replace(b'taskkill /IM WhereAreWe.exe >nul 2>nul', b'echo TASKKILL')
    test = exo / 'eXoDOS' / '!dos' / folder / 'test_exception.bat'
    test.write_bytes(text)
    env = dict(os.environ, STUB_LOG=str(log), var=str(exo / 'eXoDOS' / '!dos' / folder))
    env.pop('conf', None)
    if alt:   # AltLauncher.bat: set dosbox=%folderpath:~19%dosbox.exe, conf=a Staging conf
        env['dosbox'] = 'staging0.81.1\\dosbox.exe'
        env['conf'] = '".\\emulators\\dosbox\\Staging_PP.conf"'
    else:     # launch.bat: the game's emulator from util\dosbox.txt
        env['dosbox'] = 'dosbox.exe'
    # stand-ins for every program the menu starts
    for exe in (exo / 'emulators' / 'dosbox' / 'dosbox.exe', exo / 'emulators' / 'dosbox' / 'staging0.81.1' / 'dosbox.exe',
                exo / 'emulators' / 'dosbox' / 'staging' / 'dosbox.exe', exo / 'util' / 'WhereAreWe' / 'WhereAreWe.exe'):
        exe.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stub, exe)
    r = subprocess.run(['cmd', '/c', str(test)], cwd=str(exo), env=env, input=answer + '\r\n',
                       capture_output=True, text=True, timeout=60)
    test.unlink()
    for _ in range(50):   # "start" doesn't wait for Where Are We?
        if not log.exists() or len(log.read_text().splitlines()) >= (2 if answer == '2' else 1):
            break
        subprocess.run(['cmd', '/c', 'ping -n 1 127.0.0.1 >nul'])
    lines = log.read_text().splitlines() if log.exists() else []
    return r.stdout, [ln.replace(str(exo), '<EXO>') for ln in lines]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exo')
    ap.add_argument('--release', default=str(ROOT / 'release' / 'waw-staging-0.2'))
    a = ap.parse_args()
    src, program = Path(a.exo), Path(a.release)
    tmp = Path(tempfile.mkdtemp(prefix='waw_patch_'))
    try:
        exo = tmp / 'eXo'
        make_exo(src, exo)
        before = snapshot(exo)
        rc, out = run_patch(exo, program, '--check', '--staging', 'emulators\\dosbox\\staging')
        check('--check runs', rc == 0 and 'would add the Where Are We? menu' in out, out)
        check('--check changes nothing', snapshot(exo) == before)
        rc, out = run_patch(exo, program, '--staging', 'emulators\\dosbox\\staging0.81.1')
        check('refuses a Staging without the API', rc != 0 and 'HTTP API' in out, out)
        check('...and changes nothing', snapshot(exo) == before)
        rc, out = run_patch(exo, program, '--staging', 'emulators\\dosbox\\staging')
        check('apply', rc == 0 and out.strip().endswith('done'), out)
        for folder in patch_exo.GAMES:
            bat = exo / 'eXoDOS' / '!dos' / folder / 'exception.bat'
            data = bat.read_bytes() if bat.is_file() else b''
            check(f'{folder}: exception.bat, CRLF only',
                  data.count(b'\r\n') == data.count(b'\n') > 0 and b'staging\\dosbox.exe' in data)
        check('MM4 untouched', not (exo / 'eXoDOS' / '!dos' / 'MM4' / 'exception.bat').exists())
        check('program installed', filecmp.cmp(program / 'windows' / 'WhereAreWe.exe',
                                                 exo / 'util' / 'WhereAreWe' / 'WhereAreWe.exe', shallow=False))
        maps = sorted(p.name for p in (program / 'maps').iterdir())
        check('map images installed', len(maps) == 7 and all((exo / 'util' / 'WhereAreWe' / m).is_file() for m in maps))
        check('settings file created empty', (exo / 'util' / 'WhereAreWe' / 'WhereAreWe.settings').stat().st_size == 0)
        check('conf installed', (exo / 'emulators' / 'dosbox' / 'waw_staging.conf').is_file())
        rc, out = run_patch(exo, program, '--staging', 'emulators\\dosbox\\staging')
        check('apply again: nothing to do', rc == 0 and 'nothing to do' in out, out)
        rc, out = run_patch(exo, program, '--staging', 'emulators\\dosbox\\staging0.83.0')
        check('switch Staging', rc == 0 and out.count('update ') == len(patch_exo.GAMES), out)
        mm1 = (exo / 'eXoDOS' / '!dos' / 'MM1' / 'exception.bat').read_bytes()
        check('...to staging0.83.0', b'staging0.83.0\\dosbox.exe' in mm1)
        # an exception.bat that isn't ours stays
        foreign = exo / 'eXoDOS' / '!dos' / 'MM2' / 'exception.bat'
        foreign.write_bytes(b'@echo off\r\necho eXo\r\n')
        rc, out = run_patch(exo, program, '--staging', 'emulators\\dosbox\\staging')
        check("foreign exception.bat left alone", 'MM2\\exception.bat is not ours' in out
              and foreign.read_bytes() == b'@echo off\r\necho eXo\r\n', out)
        # settings and a saved map survive --revert
        (exo / 'util' / 'WhereAreWe' / 'WhereAreWe.settings').write_text('<WhereAreWe />')
        rc, out = run_patch(exo, program, '--revert')
        check('revert', rc == 0, out)
        check('revert keeps the foreign exception.bat', foreign.is_file())
        foreign.unlink()
        left = sorted(str(p.relative_to(exo)) for p in (exo / 'util' / 'WhereAreWe').iterdir())
        check('revert keeps settings only', left == ['util\\WhereAreWe\\WhereAreWe.settings'], str(left))
        shutil.rmtree(exo / 'util' / 'WhereAreWe')
        check('folder as before', snapshot(exo) == before,
              str(set(snapshot(exo)) ^ set(before)))

        # another platform's build: program and conf, no launchers
        rc, out = run_patch(exo, program, '--platform', 'linux-x64')
        installed = exo / 'util' / 'WhereAreWe'
        check('linux-x64: build installed, no launchers', rc == 0 and (installed / 'WhereAreWe').is_file()
              and (installed / 'libSkiaSharp.so').is_file()
              and not (exo / 'eXoDOS' / '!dos' / 'MM1' / 'exception.bat').exists(), out)
        rc, out = run_patch(exo, program, '--revert')
        shutil.rmtree(exo / 'util' / 'WhereAreWe', ignore_errors=True)
        check('linux-x64: revert leaves the folder as before', rc == 0 and snapshot(exo) == before,
              str(set(snapshot(exo)) ^ set(before)))

        # the menus, with stand-ins
        run_patch(exo, program, '--staging', 'emulators\\dosbox\\staging')
        stub = tmp / 'stub.exe'
        (tmp / 'stub.cs').write_text(STUB_CS)
        subprocess.run([str(CSC), '/nologo', '/out:' + str(stub), str(tmp / 'stub.cs')], check=True, capture_output=True)
        for folder, (game, title) in patch_exo.GAMES.items():
            out, ran = run_menu(exo, folder, '1', stub)
            want = f'<EXO>\\emulators\\dosbox\\dosbox.exe | <EXO> | [-conf] [<EXO>\\eXoDOS\\!dos\\{folder}\\dosbox.conf] ' \
                   f'[-conf] [.\\emulators\\dosbox\\options.conf] [-nomenu] [-noconsole]'
            check(f'{folder} option 1 = launch.bat\'s DOSBox line', ran == [want], f'{out!r} {ran}')
            out, ran = run_menu(exo, folder, '2', stub)
            waw = f'<EXO>\\util\\WhereAreWe\\WhereAreWe.exe | <EXO> | [-g] [{game}]'
            box = f'<EXO>\\emulators\\dosbox\\staging\\dosbox.exe | <EXO> | [-conf] [<EXO>\\eXoDOS\\!dos\\{folder}\\dosbox.conf] ' \
                  f'[-conf] [.\\emulators\\dosbox\\options.conf] [-conf] [.\\emulators\\dosbox\\waw_staging.conf] ' \
                  f'[-noconsole] [-exit]'
            check(f'{folder} option 2 = Where Are We? + Staging', sorted(ran) == sorted([waw, box]) and 'TASKKILL' in out,
                  f'{out!r} {ran}')
        game_dir = exo / 'eXoDOS' / 'MM1'
        game_dir.mkdir(parents=True)
        (game_dir / 'WhereAreWe.waw').write_bytes(b'')
        out, ran = run_menu(exo, 'MM1', '2', stub)
        check('MM1 option 2 opens a saved map',
              any(r.endswith('[-g] [MM1] [<EXO>\\eXoDOS\\MM1\\WhereAreWe.waw]') for r in ran), str(ran))
        out, ran = run_menu(exo, 'wizar1', '1', stub, alt=True)
        want = '<EXO>\\emulators\\dosbox\\staging0.81.1\\dosbox.exe | <EXO> | [-conf] [<EXO>\\eXoDOS\\!dos\\wizar1\\dosbox.conf] ' \
               '[-conf] [.\\emulators\\dosbox\\options.conf] [-conf] [.\\emulators\\dosbox\\Staging_PP.conf] [-exit] [-nomenu] [-noconsole]'
        check("option 1 from eXo's alternate launcher", ran == [want], str(ran))
        out, ran = run_menu(exo, 'bardtal1', '3', stub)
        check('option 3 starts nothing', ran == [], str(ran))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print('all ok' if not failures else f'{failures} FAILED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
