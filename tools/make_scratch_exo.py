"""A scratch eXo folder for test runs that must not touch a real installation's game folders (saves):
DOSBox Staging, options.conf, waw_staging.conf and the MT-32 ROMs copied from EXO, the given games' dosbox.conf
and their folders unzipped fresh from EXO's zips.

    python make_scratch_exo.py EXO SCRATCH_EXO GAMEDIR [GAMEDIR ...]
"""
import os
import shutil
import sys
import zipfile


def skip_links(folder, names):
    """Links are not copied: eXo's Staging folder links eXoDOS and util into its webserver folder (the goldbox
    pages), and following them copied the whole collection."""
    return [n for n in names if os.path.islink(os.path.join(folder, n)) or os.path.isjunction(os.path.join(folder, n))]


def main():
    exo, dst, games = sys.argv[1], sys.argv[2], sys.argv[3:]
    for rel in (r'emulators\dosbox\staging', 'mt32'):
        if not os.path.isdir(os.path.join(dst, rel)):
            shutil.copytree(os.path.join(exo, rel), os.path.join(dst, rel), ignore=skip_links)
    for rel in (r'emulators\dosbox\options.conf', r'emulators\dosbox\waw_staging.conf'):
        shutil.copy2(os.path.join(exo, rel), os.path.join(dst, rel))
    for game in games:
        dos = os.path.join(exo, 'eXoDOS', '!dos', game)
        os.makedirs(os.path.join(dst, 'eXoDOS', '!dos', game), exist_ok=True)
        shutil.copy2(os.path.join(dos, 'dosbox.conf'), os.path.join(dst, 'eXoDOS', '!dos', game))
        bat = next(n for n in os.listdir(dos) if n.endswith(').bat'))
        target = os.path.join(dst, 'eXoDOS', game)
        if os.path.isdir(target):
            shutil.rmtree(target)
        with zipfile.ZipFile(os.path.join(exo, 'eXoDOS', bat[:-4] + '.zip')) as z:
            z.extractall(os.path.join(dst, 'eXoDOS'))
        print('unzipped', game)


if __name__ == '__main__':
    main()
