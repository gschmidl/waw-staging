"""Builds the eXoDOS patch zips, one per system:
release/waw-staging-<version>-{windows,linux-x64,macos-apple-silicon,macos-x64}.zip.

    python tools/make_release.py [--version 0.2] [--no-build] [--maps DIR]

release/waw-staging-<version>/ is the full tree: exo/README.md, exo/patch_exo.py, exo/waw_staging.conf, maps/ (the
surface map images of the WAW site's maps download; --maps, default orig/maps) and one folder per build, each with
exo/README.txt:
  windows/    the net48 Release build of work/ (WinForms)
  linux-x64/, osx-arm64/, osx-x64/   the Majorsilence build (tools/build_msf.py), self-contained
Each zip holds the top files, maps/ and its system's build folder under
waw-staging-<version>-<system>/. No debug symbols. Linux/macOS executables are stored with mode 755 so unzip
keeps them runnable.
"""
import argparse
import os
import shutil
import stat
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NET48 = os.path.join(ROOT, 'work', 'bin', 'Release', 'net48')
MSF = os.path.join(ROOT, 'build', 'msf')
WINDOWS = ('WhereAreWe.exe', 'WhereAreWe.exe.config', 'System.Buffers.dll', 'System.Memory.dll',
           'System.Numerics.Vectors.dll', 'System.Resources.Extensions.dll',
           'System.Runtime.CompilerServices.Unsafe.dll')
RIDS = ('linux-x64', 'osx-arm64', 'osx-x64')
EXECUTABLES = ('WhereAreWe', 'createdump')
# one zip per system: release/waw-staging-<version>-<system>.zip
# no debug information: it would carry the build machine's paths (the .pdb's) into the programs
NO_DEBUG = ('-p:DebugType=none', '-p:DebugSymbols=false')
ZIPS = {'windows': ('windows',), 'linux-x64': ('linux-x64',), 'macos-apple-silicon': ('osx-arm64',),
        'macos-x64': ('osx-x64',)}


def run(cmd, cwd):
    print('>', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode:
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', default='0.2')
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--maps', default=os.path.join(ROOT, 'orig', 'maps'))
    a = ap.parse_args()
    if not a.no_build:
        run(['dotnet', 'build', '-c', 'Release', '--no-incremental', '-nologo', '-v', 'q', *NO_DEBUG], os.path.join(ROOT, 'work'))
        run([sys.executable, '-I', os.path.join(HERE, 'build_msf.py')], ROOT)
        for rid in RIDS:
            run(['dotnet', 'publish', '-c', 'Release', '--self-contained', 'true', '-nologo', '-v', 'q', '-r', rid,
                 *NO_DEBUG], MSF)
    extra = sorted(n for n in os.listdir(NET48) if n.endswith('.dll') and n not in WINDOWS)
    if extra:
        sys.exit('net48 build has files this script does not know: ' + ', '.join(extra))
    top = f'waw-staging-{a.version}'
    out = os.path.join(ROOT, 'release', top)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    for name in ('README.md', 'patch_exo.py', 'waw_staging.conf'):
        shutil.copy2(os.path.join(ROOT, 'exo', name), out)
    shutil.copytree(a.maps, os.path.join(out, 'maps'))
    os.makedirs(os.path.join(out, 'windows'))
    for name in WINDOWS:
        shutil.copy2(os.path.join(NET48, name), os.path.join(out, 'windows'))
    for rid in RIDS:
        src = os.path.join(MSF, 'bin', 'Release', 'net10.0', rid, 'publish')
        shutil.copytree(src, os.path.join(out, rid), ignore=shutil.ignore_patterns('*.pdb'))
    for build in ('windows',) + RIDS:
        shutil.copy2(os.path.join(ROOT, 'exo', 'README.txt'), os.path.join(out, build))
    old = os.path.join(ROOT, 'release', top + '.zip')   # the one-zip layout of before
    if os.path.exists(old):
        os.remove(old)
    leaks = local_paths(out)
    if leaks:
        sys.exit('build machine paths in: ' + ', '.join(leaks))
    for system, builds in ZIPS.items():
        write_zip(out, f'{top}-{system}', builds)


def local_paths(tree):
    """Files of the tree that contain this machine's path to the project or the user's home folder."""
    needles = set()
    for path in (ROOT, os.path.expanduser('~')):
        needles |= {path.encode(), path.replace(os.sep, '/').encode(), path.encode('utf-16-le')}
    found = []
    for dirpath, dirs, files in os.walk(tree):
        for f in files:
            data = open(os.path.join(dirpath, f), 'rb').read()
            if any(n.lower() in data.lower() for n in needles):
                found.append(os.path.relpath(os.path.join(dirpath, f), tree))
    return found


def write_zip(tree, name, builds):
    """release/NAME.zip: the tree's top files and maps/ plus the given build folders, under NAME/."""
    zpath = os.path.join(os.path.dirname(tree), name + '.zip')
    parts = ['', 'maps'] + list(builds)
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for part in parts:
            folder = os.path.join(tree, part)
            for f in sorted(os.listdir(folder)):
                full = os.path.join(folder, f)
                if not os.path.isfile(full):
                    continue
                arc = '/'.join(x for x in (name, part, f) if x)
                info = zipfile.ZipInfo.from_file(full, arc)
                runnable = f in EXECUTABLES and part in RIDS
                info.create_system = 3   # Unix: unzip applies the mode bits only then
                info.external_attr = ((stat.S_IFREG | (0o755 if runnable else 0o644)) << 16)
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(full, 'rb') as fh:
                    z.writestr(info, fh.read(), compresslevel=9)
    sizes = {}
    for info in zipfile.ZipFile(zpath).infolist():
        part = info.filename.split('/')[1] if info.filename.count('/') > 1 else '(top)'
        n, s = sizes.get(part, (0, 0))
        sizes[part] = (n + 1, s + info.file_size)
    print(zpath, os.path.getsize(zpath), 'bytes:',
          ', '.join(f'{part} {n} files {s / 1e6:.1f} MB' for part, (n, s) in sorted(sizes.items())))


if __name__ == '__main__':
    main()
