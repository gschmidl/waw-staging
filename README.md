# Where Are We? for DOSBox Staging

[Where Are We?](https://www.eskimo.com/~edv/lockscroll/WhereAreWe/) by EDV Software (Eric Van Heest) is a freeware
companion for Might and Magic 1–3 and World of Xeen, The Bard's Tale 1–3 and Wizardry I–V: automaps, party,
monster, item and spell information, quest lists. It reads the memory of a DOSBox 0.74 process on Windows.

This is an unofficial port of its 1.2.0.0 development build that reads the game through
[DOSBox Staging](https://www.dosbox-staging.org/)'s HTTP API instead (DOSBox Staging 0.83 or newer). It runs with
DOSBox Staging, keeps working with later versions, and runs on Windows, Linux and macOS:

- **Windows**: the original's WinForms interface (.NET Framework 4.8).
- **Linux x64, macOS (Apple silicon and Intel)**: the same program on
  [Majorsilence.Forms](https://github.com/majorsilence/Majorsilence.Forms) (WinForms on Avalonia), self-contained.

## Downloads

The [releases](../../releases) have one zip per system. Each holds the program, the surface map images of the
original's site, and an [eXoDOS](https://www.retro-exo.com/) patch: `patch_exo.py` installs the program into eXoDOS
and, on Windows, gives the 12 supported games a "with Where Are We?" launcher option. See [exo/README.md](exo/README.md).

Outside eXoDOS: turn on DOSBox Staging's webserver (`[webserver]` `webserver_enabled = on`), start the game, start
Where Are We? (`-g MM1`, `MM2`, `MM3`, `MM45`, `BT1`, `BT2`, `BT3`, `WIZ1` … `WIZ5` picks the game). Put the surface
map images next to the program.

## What changed

- Game memory, the DOSBox window and the running program come from the API (port 8086 or 8080, or set in
  Options > DOSBox). The game is recognised by the running program's name, as the original recognised DOSBox
  0.74's window title.
- DOSBox Staging lays memory out differently from DOSBox 0.74: World of Xeen's CD marker and map scripts and MM3's
  monster table are searched for where the original used fixed addresses.
- eXoDOS's versions: The Bard's Tale III's THIEFP.EXE (a second memory map), MM3's MM3.COM loader, MM3 with the
  MT-32 driver.
- The surface map images are found next to the program (also The Bard's Tale's Skara Brae map, which the built-in
  map names with a folder of the map author's machine); with a `WhereAreWe.settings` file next to it the settings
  stay there too (portable), and started that way with a game on the command line (`-g`, as eXoDOS does) it skips
  the first-run setup wizard.
- Window placement on Windows: the DOSBox window is told apart from Windows' text input indicator (which DOSBox
  Staging's process also owns); window frames are measured right at any display scaling (the original was 7% off
  at 150%, so windows snapped and were arranged beside other windows); while "Keep DOSBox window location" is set
  (the original's default) every run lays out the map, Game Info, Encounters and Party around DOSBox, fitted into
  the room DOSBox leaves, instead of once ever, and other windows that would open over DOSBox open beside it.
- The macOS/Linux build: Windows-only calls answer like a system without them, and a few WinForms layout
  behaviours the windows rely on are reproduced on Majorsilence.Forms.

The original's features for Eye of the Beholder and Ultima are left as they are and were not tested.

## Building

The port is kept as a patch against a decompile of the original: this repository holds neither the original program
nor its decompiled source, only the changes (with a few lines of context each). On Windows, with git, the .NET 10 SDK
and `ilspycmd` 11.0.0.9375
(`dotnet tool install -g ilspycmd --version 11.0.0.9375`):

    python tools/build.py          downloads WhereAreWe-x64.zip and the surface maps from the original's site,
                                   decompiles WhereAreWe.exe into work/, applies port/, builds the Windows version
    python tools/make_release.py   builds the Linux and macOS versions too and writes release/*.zip

`work/` is a git repository: the decompile is its first commit and the port the second. After changing it,
`python tools/make_patch.py` writes `port/` again.

## Repository

- `port/`: `port.patch` (everything the port changes and adds) and the project file
- `exo/`: the eXoDOS patch (`patch_exo.py`), its README, `waw_staging.conf`, the program's README.txt
- `tools/`: build and release scripts, and the test rig: `wawprobe` (what the port reads, on the command line),
  `wawshot`/`wawshot-msf` (open the program's windows and capture them, Windows and headless), `fakeapi.py` (serve a
  RAM dump as the DOSBox Staging API), `exo_bootcheck.py`/`exo_optioncheck.py` (play eXoDOS's games under each of
  their launch options on a private desktop), `layout_check.py` (the same games with every window of the program open:
  laid out around DOSBox, none over it, also after DOSBox is resized), `layoutall.sh` (compare both builds' windows),
  `linux_check.sh` (the
  Linux build in WSL), `api074.py` (the API on top of a DOSBox 0.74 process, for comparing with the original)
- `tests/test_patch_exo.py`: the eXoDOS patch on a scratch copy of an eXo installation's launchers

## License

The files in this repository are under the MIT license (LICENSE). Where Are We? itself is EDV Software's freeware;
`port/port.patch` changes its decompiled code, and the release zips contain the changed program. Majorsilence.Forms,
Avalonia, SkiaSharp and .NET (in the Linux and macOS builds) come with their own licenses.
