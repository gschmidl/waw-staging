#!/usr/bin/env python3
"""Adds Where Are We? (the DOSBox Staging port) to an eXoDOS installation.

The launchers of the games Where Are We? supports get a menu: play the game as
before, or play it in DOSBox Staging with Where Are We? next to it:
Might and Magic 1, 2, 3 and World of Xeen, The Bard's Tale 1, 2 and 3,
Wizardry I to V.

- util\\WhereAreWe: the program for this system (Windows, Linux x64, macOS on
  Apple silicon or Intel; --platform picks another), the surface map images
  its built-in maps use, and an empty WhereAreWe.settings that keeps its
  settings (and its autosave file) in that folder. On macOS the program is
  taken out of quarantine and signed ad hoc (codesign), which Apple silicon
  needs to run it.
- emulators\\dosbox\\waw_staging.conf: DOSBox Staging's webserver (the HTTP API
  Where Are We? reads the game through) and eXo's MT-32 ROMs.
- Windows: eXoDOS\\!dos\\<game>\\exception.bat, the menu. Option 1 starts the
  game the way eXo's launcher (or its alternate launcher) would without the
  file; option 2 starts Where Are We? and the game in the given DOSBox Staging,
  and closes Where Are We? (it asks about unsaved maps) when DOSBox ends. A map
  saved as WhereAreWe.waw in the game's folder is opened the next time.
  An exception.bat that eXo put there is left alone.

usage: python patch_exo.py [--check | --revert] [--staging FOLDER]
                           [--platform NAME] EXO_FOLDER

EXO_FOLDER is eXoDOS's "eXo" folder, the one with eXoDOS, emulators and util in
it. --check shows what would change, --revert undoes it (WhereAreWe.settings,
the autosave file and saved maps stay). --staging is the DOSBox Staging folder,
relative to the eXo folder (default: emulators\\dosbox\\staging0.83.0); it has
to be Staging 0.83 or newer, which has the HTTP API. Run again with another
--staging to switch. --platform is windows, linux-x64, osx-arm64 or osx-x64
(default: this system).
"""
import argparse
import os
import platform as host
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = Path('util') / 'WhereAreWe'
CONF = Path('emulators') / 'dosbox' / 'waw_staging.conf'
SETTINGS = 'WhereAreWe.settings'
MARKER = 'rem Where Are We? menu (patch_exo.py of the Where Are We? DOSBox Staging port)'
PLATFORMS = ('windows', 'linux-x64', 'osx-arm64', 'osx-x64')
EXECUTABLES = ('WhereAreWe', 'createdump')   # Linux and macOS builds

# eXoDOS\!dos folder: (Where Are We?'s -g name, name in the menu)
GAMES = {
    'MM1': ('MM1', 'Might and Magic 1'),
    'MM2': ('MM2', 'Might and Magic 2'),
    'MM3': ('MM3', 'Might and Magic 3'),
    'MM6': ('MM45', 'World of Xeen'),
    'bardtal1': ('BT1', "The Bard's Tale 1"),
    'bardtal2': ('BT2', "The Bard's Tale 2"),
    'bardtal3': ('BT3', "The Bard's Tale 3"),
    'wizar1': ('WIZ1', 'Wizardry I'),
    'wizar2': ('WIZ2', 'Wizardry II'),
    'wizar3': ('WIZ3', 'Wizardry III'),
    'wizar4': ('WIZ4', 'Wizardry IV'),
    'wizar5': ('WIZ5', 'Wizardry V'),
}

CLEANUP = [
    'del stdout.txt',
    'del stderr.txt',
    'if exist glide.* del glide.*',
    'if exist .\\eXoDOS\\CWSDPMI.swp del .\\eXoDOS\\CWSDPMI.swp',
    'goto end',
]


def launcher(folder, game, title, staging_exe):
    """The exception.bat text for a game (CRLF); staging_exe is the quoted dosbox.exe path from the eXo folder."""
    waw = '".\\util\\WhereAreWe\\WhereAreWe.exe"'
    saved = f'.\\eXoDOS\\{folder}\\WhereAreWe.waw'
    lines = [
        '@echo off',
        MARKER,
        'cd %VAR%',
        '..\\..\\..\\util\\setconsole.exe /reset',
        'echo.',
        f'echo Press 1 to play {title}',
        f'echo Press 2 to play {title} with Where Are We?',
        'echo Press 3 to Quit',
        'echo.',
        'echo Note: Where Are We? (EDV Software) is a companion tool with automaps,',
        'echo party, monster and item information and quest lists. It reads the',
        'echo game through DOSBox Staging, so option 2 runs the game in DOSBox',
        'echo Staging. To have your map opened next time, save it as',
        f'echo WhereAreWe.waw in eXoDOS\\{folder}.',
        'echo.',
        '..\\..\\..\\util\\choice /C:123 /N Please Choose:',
        '',
        'if errorlevel = 3 goto end',
        'if errorlevel = 2 goto waw',
        'if errorlevel = 1 goto game',
        '',
        ':game',
        '..\\..\\..\\util\\setconsole.exe /minimize',
        'cd ..',
        'cd ..',
        'cd ..',
        'if defined conf goto game_alt',
        'SET SDL_WINDOWS_DPI_SCALING=0',
        '".\\emulators\\dosbox\\%dosbox%" -conf "%var%\\dosbox.conf" -conf ".\\emulators\\dosbox\\options.conf" -nomenu -noconsole',
        'goto game_done',
        ':game_alt',
        # eXo's alternate launcher: %dosbox% is staging0.81.1\dosbox.exe there and %conf% its Staging settings
        '".\\emulators\\dosbox\\%dosbox%" -conf "%var%\\dosbox.conf" -conf ".\\emulators\\dosbox\\options.conf" -conf %conf% -exit -nomenu -noconsole',
        ':game_done',
        *CLEANUP,
        '',
        ':waw',
        '..\\..\\..\\util\\setconsole.exe /minimize',
        'cd ..',
        'cd ..',
        'cd ..',
        'SET SDL_WINDOWS_DPI_SCALING=0',
        f'if exist "{saved}" (start "" {waw} -g {game} "%CD%{saved[1:]}") else (start "" {waw} -g {game})',
        f'{staging_exe} -conf "%var%\\dosbox.conf" -conf ".\\emulators\\dosbox\\options.conf" '
        '-conf ".\\emulators\\dosbox\\waw_staging.conf" -noconsole -exit',
        'taskkill /IM WhereAreWe.exe >nul 2>nul',
        *CLEANUP,
        '',
        ':end',
    ]
    return ('\r\n'.join(lines) + '\r\n').encode('latin-1')


def this_platform():
    machine = host.machine().lower()
    if sys.platform == 'win32':
        return 'windows'
    if sys.platform == 'darwin':
        return 'osx-arm64' if machine in ('arm64', 'aarch64') else 'osx-x64'
    if sys.platform.startswith('linux') and machine in ('x86_64', 'amd64'):
        return 'linux-x64'
    return None


def has_webserver(exe):
    """DOSBox Staging 0.83+ (the webserver's settings are in the program)."""
    tail = b''
    with open(exe, 'rb') as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                return False
            if b'webserver_enabled' in tail + chunk:
                return True
            tail = chunk[-32:]


class Patcher:
    def __init__(self, exo, staging, release, platform, check):
        self.exo, self.release, self.platform, self.check, self.changes = exo, release, platform, check, 0
        self.staging = (exo / staging).resolve()
        try:
            self.exe = f'".\\{self.staging.relative_to(exo)}\\dosbox.exe"'   # launchers run from the eXo folder
        except ValueError:
            self.exe = f'"{self.staging}\\dosbox.exe"'

    def say(self, text):
        print(('would ' if self.check else '') + text)
        self.changes += 1

    def rel(self, p):
        try:
            return str(p.relative_to(self.exo))
        except ValueError:
            return str(p)

    def write(self, path, data, what='write'):
        if path.is_file() and path.read_bytes() == data:
            return
        self.say(f'{what} {self.rel(path)}')
        if not self.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def program_files(self, platform):
        """What goes into util\\WhereAreWe for a platform: its build and the map images."""
        files = [p for p in (self.release / platform).iterdir() if p.is_file() and p.name != SETTINGS]
        files += [p for p in (self.release / 'maps').iterdir() if p.is_file()]
        return sorted(files, key=lambda p: p.name.lower())

    def launchers(self):
        """(folder, -g name, title, exception.bat) of the supported games eXo has launchers for."""
        root = self.exo / 'eXoDOS' / '!dos'
        for folder, (game, title) in GAMES.items():
            if (root / folder).is_dir():
                yield folder, game, title, root / folder / 'exception.bat'

    def apply(self):
        dest = self.exo / DEST
        for f in self.program_files(self.platform):
            self.write(dest / f.name, f.read_bytes())
        if not (dest / SETTINGS).is_file():
            self.write(dest / SETTINGS, b'', 'create (keeps the settings in util\\WhereAreWe)')
        if self.platform != 'windows' and not self.check:
            for name in EXECUTABLES:
                if (dest / name).is_file():
                    os.chmod(dest / name, 0o755)
        if self.platform.startswith('osx') and sys.platform == 'darwin':
            self.say(f'clear the quarantine of {self.rel(dest)} and sign {self.rel(dest / "WhereAreWe")} ad hoc')
            if not self.check:
                subprocess.run(['xattr', '-dr', 'com.apple.quarantine', str(dest)], check=False)
                subprocess.run(['codesign', '--force', '--sign', '-', str(dest / 'WhereAreWe')], check=False)
        self.write(self.exo / CONF, (self.release / CONF.name).read_bytes())
        if self.platform != 'windows':
            return
        for folder, game, title, bat in self.launchers():
            if bat.is_file() and MARKER.encode() not in bat.read_bytes():
                print(f'warning: {self.rel(bat)} is not ours (an eXo update?); left alone')
                continue
            self.write(bat, launcher(folder, game, title, self.exe),
                       'update' if bat.is_file() else 'add the Where Are We? menu as')

    def revert(self):
        for folder, game, title, bat in self.launchers():
            if bat.is_file() and MARKER.encode() in bat.read_bytes():
                self.say(f'remove {self.rel(bat)}')
                if not self.check:
                    bat.unlink()
        if (self.exo / CONF).is_file():
            self.say(f'remove {self.rel(self.exo / CONF)}')
            if not self.check:
                (self.exo / CONF).unlink()
        dest = self.exo / DEST
        names = sorted({f.name for platform in PLATFORMS if (self.release / platform).is_dir()
                        for f in self.program_files(platform)}, key=str.lower)
        removed = [n for n in names if (dest / n).is_file()]
        if removed:
            self.say(f'remove {len(removed)} files from {self.rel(dest)}')
            if not self.check:
                for n in removed:
                    (dest / n).unlink()
        if dest.is_dir() and not self.check:
            settings = dest / SETTINGS
            if settings.is_file() and settings.stat().st_size == 0:
                settings.unlink()
            if not any(dest.iterdir()):
                dest.rmdir()
            else:
                print(f'kept {self.rel(dest)} (settings, autosave)')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('exo', help="eXoDOS's eXo folder (with eXoDOS, emulators and util in it)")
    ap.add_argument('--check', action='store_true', help='only show what would change')
    ap.add_argument('--revert', action='store_true', help='undo the changes')
    ap.add_argument('--staging', default='emulators\\dosbox\\staging0.83.0',
                    help='the DOSBox Staging folder, relative to the eXo folder (default: %(default)s)')
    ap.add_argument('--platform', choices=PLATFORMS, default=this_platform(),
                    help='the build to install (default: this system)')
    ap.add_argument('--release', default=str(HERE),
                    help='folder with the builds (windows, linux-x64, ...), maps and waw_staging.conf '
                         '(default: the one with this script)')
    a = ap.parse_args()
    exo = Path(a.exo).resolve()
    if not (exo / 'eXoDOS' / '!dos').is_dir() and (exo / 'eXo' / 'eXoDOS' / '!dos').is_dir():
        exo = exo / 'eXo'
    if not (exo / 'eXoDOS' / '!dos').is_dir():
        sys.exit(f'{exo} is not an eXo folder (no eXoDOS\\!dos in it)')
    release = Path(a.release).resolve()
    if not a.platform:
        sys.exit('no build for this system; --platform names one of: ' + ', '.join(PLATFORMS))
    if not a.revert and not (release / a.platform).is_dir():
        sys.exit(f'no {a.platform} build in {release}: this is another system\'s release zip; '
                 f'use the one for {a.platform} (or --release names a folder with it)')
    p = Patcher(exo, Path(a.staging), release, a.platform, a.check)
    if a.revert:
        p.revert()
    else:
        if a.platform == 'windows':
            exe = p.staging / 'dosbox.exe'
            if not exe.is_file():
                sys.exit(f'no DOSBox Staging at {exe} (--staging names another folder)')
            if not has_webserver(exe):
                sys.exit(f'{exe} has no HTTP API: Where Are We? needs DOSBox Staging 0.83 or newer')
        p.apply()
    if not p.changes:
        print('nothing would change' if a.check else 'nothing to do')
    elif not a.check:
        print('done')


if __name__ == '__main__':
    main()
