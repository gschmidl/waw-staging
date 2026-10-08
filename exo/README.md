# Where Are We? for DOSBox Staging — eXoDOS patch

Adds [Where Are We?](https://www.eskimo.com/~edv/lockscroll/WhereAreWe/) (EDV Software's companion tool, in a
port that reads the game through DOSBox Staging's HTTP API) to an eXoDOS installation.

On Windows, the launchers of Might and Magic 1, 2, 3, World of Xeen, The Bard's Tale 1, 2, 3 and Wizardry I–V get
a menu:

    Press 1 to play Might and Magic 1
    Press 2 to play Might and Magic 1 with Where Are We?
    Press 3 to Quit

Option 1 starts the game as eXo did before. Option 2 starts Where Are We? and runs the game in DOSBox Staging with
its webserver on; when DOSBox ends, Where Are We? is closed (it asks about an unsaved map). A map saved as
`WhereAreWe.waw` in the game's folder (`eXoDOS\MM1` and so on) is opened the next time.

## Applying it

Needs Python 3 and, on Windows, a DOSBox Staging 0.83 or newer inside the eXo folder.

    python patch_exo.py --check X:\eXoDOS\eXo
    python patch_exo.py X:\eXoDOS\eXo
    python patch_exo.py --staging emulators\dosbox\staging X:\eXoDOS\eXo
    python patch_exo.py --revert X:\eXoDOS\eXo

`--staging` names the DOSBox Staging folder relative to the eXo folder (default `emulators\dosbox\staging0.83.0`).
`--platform` (windows, linux-x64, osx-arm64, osx-x64) installs another system's build; the default is the system
the script runs on.

What it changes:

- `util\WhereAreWe\`: the build for the platform, the surface map images, and an empty `WhereAreWe.settings` so that
  its settings and autosave file stay in that folder. On macOS the program is taken out of quarantine and signed
  ad hoc, which Apple silicon needs.
- `emulators\dosbox\waw_staging.conf`: the webserver, and eXo's MT-32 ROMs for DOSBox Staging.
- Windows only: `eXoDOS\!dos\<game>\exception.bat` for the 12 games (eXo has none for them). An `exception.bat` that
  is not the patch's is left alone. The German and Spanish versions are not changed.

`--revert` removes all of it; `WhereAreWe.settings` (if it holds settings), the autosave file and saved maps stay.

Games are installed by eXo as usual; the patch only changes their launchers.

## Contents

There is one release zip per system; each holds:

- `patch_exo.py`, `waw_staging.conf`
- `maps\`: the surface map images from the original's site (`WhereAreWe-Surface_Maps-v1.1.0.zip`)
- the system's build, with `README.txt`:
  - Windows zip: `windows\`, `WhereAreWe.exe` (.NET Framework 4.8, the original's WinForms interface) with its config
    and libraries
  - Linux zip: `linux-x64\`, a self-contained build (Majorsilence.Forms on Avalonia; nothing to install)
  - macOS Apple silicon zip: `osx-arm64\`; macOS x64 (Intel) zip: `osx-x64\`; self-contained like the Linux one
