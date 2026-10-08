"""Build the port from the original: download (or take) EDV Software's WhereAreWe-x64.zip, decompile WhereAreWe.exe
with ilspycmd 11.0.0.9375 into work/, apply port/port.patch and port/WhereAreWe.csproj, build the Windows version.

    python tools/build.py [--zip WhereAreWe-x64.zip] [--maps WhereAreWe-Surface_Maps-v1.1.0.zip] [--force]

Without --zip/--maps the files are downloaded from the original's site into orig/download/. work/ becomes a git
repository: the decompile is its first commit and the port its second, so `git diff HEAD~1` shows the port.
The surface map images go to orig/maps/ (tools/make_release.py puts them into the release zips).
Needs Windows, git, the .NET SDK and ilspycmd 11.0.0.9375 (dotnet tool install -g ilspycmd --version 11.0.0.9375);
another ilspycmd version decompiles differently and the patch won't apply.
Then python tools/make_release.py builds the Linux and macOS versions too and writes the release zips.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = 'https://www.eskimo.com/~edv/lockscroll/WhereAreWe/'
ORIGINAL = ('WhereAreWe-x64.zip', '047b3320a22509f86da97ed7c723207b')          # 1.2.0.0 development build
MAPS = ('WhereAreWe-Surface_Maps-v1.1.0.zip', '9db34cd47dbc4b9abdc6b0b47807ec74')
ILSPY = '11.0.0.9375'


def run(cmd, cwd=None):
    print('>', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode:
        sys.exit(r.returncode)


def fetch(given, name_md5):
    name, md5 = name_md5
    path = given or os.path.join(ROOT, 'orig', 'download', name)
    if not os.path.isfile(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print('downloading', SITE + name, flush=True)
        req = urllib.request.Request(SITE + name, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, 'wb') as f:
            shutil.copyfileobj(r, f)
    got = hashlib.md5(open(path, 'rb').read()).hexdigest()
    if got != md5:
        sys.exit(f'{path}: md5 {got}, expected {md5} (the site may have a newer build; the patch is for this one)')
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--zip', help=f'{ORIGINAL[0]} (default: download it)')
    ap.add_argument('--maps', help=f'{MAPS[0]} (default: download it)')
    ap.add_argument('--force', action='store_true', help='replace an existing work/')
    a = ap.parse_args()
    work = os.path.join(ROOT, 'work')
    if os.path.exists(work):
        if not a.force:
            sys.exit('work/ exists; --force replaces it')
        shutil.rmtree(work)
    version = subprocess.run(['ilspycmd', '--version'], capture_output=True, text=True).stdout
    if ILSPY not in version:
        sys.exit(f'needs ilspycmd {ILSPY}: dotnet tool install -g ilspycmd --version {ILSPY}')

    original = fetch(a.zip, ORIGINAL)
    exe_dir = os.path.join(ROOT, 'orig', 'x64')
    os.makedirs(exe_dir, exist_ok=True)
    with zipfile.ZipFile(original) as z:
        z.extract('WhereAreWe.exe', exe_dir)
    maps = fetch(a.maps, MAPS)
    with zipfile.ZipFile(maps) as z:
        z.extractall(os.path.join(ROOT, 'orig', 'maps'))

    run(['ilspycmd', '-p', '-o', work, os.path.join(exe_dir, 'WhereAreWe.exe')])
    git = ['git', '-c', 'core.autocrlf=false', '-c', 'user.name=build', '-c', 'user.email=build@localhost']
    run(git + ['init', '-q'], work)
    run(git + ['config', 'core.autocrlf', 'false'], work)
    run(git + ['add', '-A'], work)
    run(git + ['commit', '-q', '-m', f'ilspycmd {ILSPY} decompile of WhereAreWe.exe 1.2.0.0 ({ORIGINAL[0]}, md5 {ORIGINAL[1]})'], work)
    run(git + ['apply', '--binary', '--whitespace=nowarn', os.path.join(ROOT, 'port', 'port.patch')], work)
    shutil.copyfile(os.path.join(ROOT, 'port', 'WhereAreWe.csproj'), os.path.join(work, 'WhereAreWe.csproj'))
    run(git + ['add', '-A'], work)
    run(git + ['commit', '-q', '-m', 'Where Are We? on the DOSBox Staging HTTP API (port/port.patch)'], work)
    run(['dotnet', 'build', '-c', 'Release', '-nologo', '-v', 'q'], work)
    print('built', os.path.join('work', 'bin', 'Release', 'net48', 'WhereAreWe.exe'))


if __name__ == '__main__':
    main()
