"""Regenerate port/ from work/ (the decompile repository the port is developed in):
port/port.patch = everything since work/'s first commit (the decompile) except the project file, and
port/WhereAreWe.csproj = the port's project file (the decompiler's has a machine-specific reference path).

    python tools/make_patch.py
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.join(ROOT, 'work')
PORT = os.path.join(ROOT, 'port')


def git(*args):
    return subprocess.run(['git', '-C', WORK, *args], check=True, capture_output=True).stdout


def main():
    if git('status', '--porcelain').strip():
        sys.exit('work/ has uncommitted changes; commit them first')
    base = git('rev-list', '--max-parents=0', 'HEAD').split()[0].decode()
    patch = git('diff', '--binary', '--full-index', base, 'HEAD', '--', '.', ':(exclude)WhereAreWe.csproj')
    os.makedirs(PORT, exist_ok=True)
    with open(os.path.join(PORT, 'port.patch'), 'wb') as f:
        f.write(patch)
    shutil.copyfile(os.path.join(WORK, 'WhereAreWe.csproj'), os.path.join(PORT, 'WhereAreWe.csproj'))
    files = sum(1 for line in patch.splitlines() if line.startswith(b'diff --git '))
    print(f'port/port.patch: {len(patch)} bytes, {files} files (since {base[:7]}); port/WhereAreWe.csproj')


if __name__ == '__main__':
    main()
