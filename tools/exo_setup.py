"""Prepare an eXoDOS game for a DOSBox Staging API test, laid out exactly like eXo.

    python exo_setup.py EXO_ROOT SCRATCH GAMEDIR [GAMEDIR...] [--port 18086] [--zip NAME ...]

Unzips each game's zip from EXO_ROOT\\eXo\\eXoDOS into SCRATCH\\exo\\eXoDOS (skipped if already there) and
writes SCRATCH\\conf\\<first GAMEDIR>.conf: eXo's own [dosbox]/[cpu]/[autoexec] settings with the
".\\eXoDOS\\" paths made absolute, plus the web server, a left-monitor window and a capture folder.
"""
import argparse
import os
import re
import zipfile


def read_conf(path):
    sections, sec = {}, None
    for line in open(path, encoding='latin-1').read().splitlines():
        s = line.strip()
        m = re.match(r'^\[(\w+)\]$', s)
        if m:
            sec = m.group(1).lower()
            sections.setdefault(sec, [])
            continue
        if sec and s and not s.startswith('#'):
            sections[sec].append(line.rstrip())
    return sections


def find_zip(exo_root, gamedir, explicit):
    """eXo names a game's launcher .bat in !dos\\<dir> after its zip."""
    zdir = os.path.join(exo_root, 'eXo', 'eXoDOS')
    if explicit:
        return explicit if os.path.isabs(explicit) else os.path.join(zdir, explicit)
    for name in os.listdir(os.path.join(zdir, '!dos', gamedir)):
        if name.endswith(').bat'):
            return os.path.join(zdir, name[:-4] + '.zip')
    raise SystemExit('no launcher .bat for ' + gamedir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exo_root')
    ap.add_argument('scratch')
    ap.add_argument('gamedirs', nargs='+')
    ap.add_argument('--port', type=int, default=18086)
    ap.add_argument('--zip', action='append', default=[])
    ap.add_argument('--d074', action='store_true', help='config for DOSBox 0.74 (tools/api074.py) on its own game copy')
    a = ap.parse_args()
    games = os.path.join(a.scratch, 'exo074' if a.d074 else 'exo', 'eXoDOS')
    os.makedirs(games, exist_ok=True)
    zips = a.zip + [None] * (len(a.gamedirs) - len(a.zip))
    for gamedir, zname in zip(a.gamedirs, zips):
        if os.path.isdir(os.path.join(games, gamedir)):
            continue
        zpath = find_zip(a.exo_root, gamedir, zname)
        print('unzipping', os.path.basename(zpath))
        with zipfile.ZipFile(zpath) as z:
            z.extractall(games)
    main_dir = a.gamedirs[0]
    conf = read_conf(os.path.join(a.exo_root, 'eXo', 'eXoDOS', '!dos', main_dir, 'dosbox.conf'))
    capture = os.path.join(a.scratch, 'cap')
    os.makedirs(capture, exist_ok=True)
    if a.d074:
        out = ['[sdl]', 'fullscreen=false', 'output=surface', '[mixer]', 'nosound=true']
    else:
        out = ['[sdl]', 'fullscreen = false', 'window_position = -2300,120',
               '[capture]', f'capture_dir = "{capture}"', 'default_image_capture_formats = upscaled',
               '[mixer]', 'nosound = true',
               '[webserver]', 'webserver_enabled = on', f'webserver_port = {a.port}']
    for sec in ('dosbox', 'cpu'):
        out.append(f'[{sec}]')
        for line in conf.get(sec, []):
            key = line.split('=')[0].strip().lower()
            if key in ('memsize', 'machine', 'cycles', 'core', 'cputype'):
                out.append(line.strip())
    out.append('[autoexec]')
    for line in conf.get('autoexec', []):
        out.append(re.sub(r'\.\\eXoDOS\\', lambda m: games.replace('\\', '\\\\') + '\\\\', line, flags=re.I)
                   .replace('\\\\', '\\'))
    os.makedirs(os.path.join(a.scratch, 'conf'), exist_ok=True)
    path = os.path.join(a.scratch, 'conf', main_dir + ('-074' if a.d074 else '') + '.conf')
    open(path, 'w', encoding='latin-1').write('\n'.join(out) + '\n')
    print(path)
    print('\n'.join(out))


if __name__ == '__main__':
    main()
